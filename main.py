"""
Interview Assistant - FastAPI Backend
Real-time interview question detection and answer generation
"""
import asyncio
import json
from typing import Dict, List, Optional
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from config import get_settings, TONE_PRESETS, LENGTH_PRESETS, INDUSTRY_PRESETS, ROLE_PRESETS
from models import (
    UserProfile, SessionPrep, UserSettings, AnswerSettings,
    DetectedQuestion, GeneratedAnswer, TranscriptSegment,
    InterviewSession, SpeakerType, ProfileUpdate, Story, Experience
)
from services import (
    TranscriptionService, QuestionDetector, AnswerGenerator,
    AnswerHumanizer, ContextManager
)
from utils import ResumeParser, parse_job_description


# Application state
class AppState:
    def __init__(self):
        self.context_manager = ContextManager()
        self.transcription_service = TranscriptionService()
        self.question_detector = QuestionDetector()
        self.answer_generator = AnswerGenerator()
        self.humanizer = AnswerHumanizer()
        self.resume_parser = ResumeParser()

        # Active sessions and connections
        self.active_sessions: Dict[str, InterviewSession] = {}
        self.websocket_connections: Dict[str, WebSocket] = {}
        self.user_settings: Dict[str, UserSettings] = {}


app_state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    print("Starting Interview Assistant...")
    # Load default profile if exists
    app_state.context_manager.load_profile("default")
    yield
    # Shutdown
    print("Shutting down Interview Assistant...")


# Create FastAPI app
app = FastAPI(
    title="Interview Assistant",
    description="Real-time interview question detection and answer generation",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Health Check
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


# ============================================================================
# Profile Management
# ============================================================================

class ProfileCreateRequest(BaseModel):
    name: str
    headline: Optional[str] = None
    summary: Optional[str] = None


@app.post("/api/profile")
async def create_profile(request: ProfileCreateRequest):
    """Create a new user profile"""
    profile = app_state.context_manager.create_profile(
        name=request.name,
        headline=request.headline,
        summary=request.summary
    )
    return {"success": True, "profile": profile.model_dump(mode="json")}


@app.get("/api/profile")
async def get_profile():
    """Get current user profile"""
    profile = app_state.context_manager.current_profile
    if not profile:
        profile = app_state.context_manager.load_profile("default")

    if not profile:
        raise HTTPException(status_code=404, detail="No profile found")

    return profile.model_dump(mode="json")


@app.patch("/api/profile")
async def update_profile(updates: ProfileUpdate):
    """Update user profile"""
    profile = app_state.context_manager.update_profile(updates.model_dump(exclude_none=True))
    if not profile:
        raise HTTPException(status_code=404, detail="No profile to update")
    return {"success": True, "profile": profile.model_dump(mode="json")}


@app.post("/api/profile/resume")
async def upload_resume(file: UploadFile = File(...)):
    """Upload and parse a resume"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # Check file type
    allowed_extensions = [".pdf", ".docx", ".doc", ".txt"]
    ext = "." + file.filename.split(".")[-1].lower()
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
        )

    try:
        # Read file bytes
        content = await file.read()

        # Parse resume
        parsed = app_state.resume_parser.parse_bytes(content, file.filename)

        # Update profile with parsed data
        profile = app_state.context_manager.current_profile
        if not profile:
            profile = UserProfile(name=parsed.get("name") or "User")

        # Update profile fields
        if parsed.get("name"):
            profile.name = parsed["name"]
        if parsed.get("email"):
            profile.email = parsed["email"]
        if parsed.get("phone"):
            profile.phone = parsed["phone"]
        if parsed.get("summary"):
            profile.summary = parsed["summary"]

        # Update experiences
        if parsed.get("experiences"):
            profile.experiences = [
                Experience(
                    company=exp.get("company") or "Unknown",
                    title=exp.get("title") or "Unknown",
                    description=exp.get("description") or "",
                    start_date=exp.get("dates", "").split("-")[0].strip() if exp.get("dates") else None
                )
                for exp in parsed["experiences"]
            ]

        # Update skills
        if parsed.get("skills"):
            from .models import Skill, SkillLevel
            profile.skills = [
                Skill(name=skill, level=SkillLevel.INTERMEDIATE)
                for skill in parsed["skills"]
            ]

        # Store raw text
        profile.resume_text = parsed.get("raw_text")
        profile.resume_uploaded_at = datetime.now()

        # Save profile
        app_state.context_manager.save_profile(profile)

        return {
            "success": True,
            "parsed": {
                "name": parsed.get("name"),
                "email": parsed.get("email"),
                "skills_count": len(parsed.get("skills", [])),
                "experiences_count": len(parsed.get("experiences", [])),
            },
            "profile": profile.model_dump(mode="json")
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing resume: {str(e)}")


# ============================================================================
# Job Description Parsing
# ============================================================================

class JobDescriptionRequest(BaseModel):
    job_description: str


@app.post("/api/parse-job")
async def parse_job(request: JobDescriptionRequest):
    """Parse a job description to extract company, role, skills, etc."""
    try:
        parsed = parse_job_description(request.job_description)
        return {
            "success": True,
            "parsed": parsed
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing job description: {str(e)}")


# ============================================================================
# Stories (STAR format)
# ============================================================================

class StoryRequest(BaseModel):
    title: str
    category: str
    situation: str
    task: str
    action: str
    result: str
    keywords: List[str] = []


@app.post("/api/profile/stories")
async def add_story(story: StoryRequest):
    """Add a STAR format story"""
    profile = app_state.context_manager.current_profile
    if not profile:
        raise HTTPException(status_code=404, detail="No profile found")

    new_story = Story(**story.model_dump())
    profile.stories.append(new_story)
    app_state.context_manager.save_profile(profile)

    return {"success": True, "story": new_story.model_dump()}


@app.get("/api/profile/stories")
async def get_stories():
    """Get all stories"""
    profile = app_state.context_manager.current_profile
    if not profile:
        return {"stories": []}
    return {"stories": [s.model_dump() for s in profile.stories]}


@app.delete("/api/profile/stories/{index}")
async def delete_story(index: int):
    """Delete a story by index"""
    profile = app_state.context_manager.current_profile
    if not profile or index >= len(profile.stories):
        raise HTTPException(status_code=404, detail="Story not found")

    profile.stories.pop(index)
    app_state.context_manager.save_profile(profile)
    return {"success": True}


# ============================================================================
# Session Management
# ============================================================================

class SessionStartRequest(BaseModel):
    company_name: str
    role_title: str
    job_description: Optional[str] = None
    company_info: Optional[str] = None
    interview_type: str = "phone"
    industry: Optional[str] = None
    role_type: Optional[str] = None


@app.post("/api/session/start")
async def start_session(request: SessionStartRequest):
    """Start a new interview session"""
    session = app_state.context_manager.start_session(
        company_name=request.company_name,
        role_title=request.role_title,
        job_description=request.job_description,
        company_info=request.company_info,
        interview_type=request.interview_type,
        industry=request.industry,
        role_type=request.role_type
    )

    # Create interview session for tracking
    interview_session = InterviewSession(
        company=request.company_name,
        role=request.role_title,
        interview_type=request.interview_type
    )
    app_state.active_sessions[interview_session.id] = interview_session

    # Analyze job description if provided
    analysis = None
    if request.job_description:
        analysis = app_state.context_manager.analyze_job_description(request.job_description)

    return {
        "success": True,
        "session_id": interview_session.id,
        "session": session.model_dump(mode="json"),
        "job_analysis": analysis
    }


@app.get("/api/session/{session_id}")
async def get_session(session_id: str):
    """Get session details"""
    if session_id not in app_state.active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return app_state.active_sessions[session_id].model_dump(mode="json")


@app.post("/api/session/{session_id}/end")
async def end_session(session_id: str):
    """End an interview session"""
    if session_id in app_state.active_sessions:
        session = app_state.active_sessions[session_id]
        session.is_active = False
        session.ended_at = datetime.now()
        return {"success": True, "session": session.model_dump(mode="json")}
    raise HTTPException(status_code=404, detail="Session not found")


# ============================================================================
# Settings
# ============================================================================

@app.get("/api/settings")
async def get_settings():
    """Get user settings"""
    settings = app_state.user_settings.get("default", UserSettings())
    return settings.model_dump()


@app.patch("/api/settings")
async def update_settings(settings: Dict):
    """Update user settings"""
    current = app_state.user_settings.get("default", UserSettings())

    # Update nested settings
    if "answer" in settings:
        for key, value in settings["answer"].items():
            if hasattr(current.answer, key):
                setattr(current.answer, key, value)

    if "audio" in settings:
        for key, value in settings["audio"].items():
            if hasattr(current.audio, key):
                setattr(current.audio, key, value)

    if "display" in settings:
        for key, value in settings["display"].items():
            if hasattr(current.display, key):
                setattr(current.display, key, value)

    app_state.user_settings["default"] = current
    return {"success": True, "settings": current.model_dump()}


@app.get("/api/settings/presets")
async def get_presets():
    """Get all available presets"""
    return {
        "tones": TONE_PRESETS,
        "lengths": LENGTH_PRESETS,
        "industries": INDUSTRY_PRESETS,
        "roles": ROLE_PRESETS
    }


# ============================================================================
# Answer Generation
# ============================================================================

class GenerateAnswerRequest(BaseModel):
    question: str
    category: Optional[str] = None
    tone: Optional[str] = None
    length: Optional[str] = None
    format: Optional[str] = None
    technical_depth: Optional[int] = None


@app.post("/api/answer/generate")
async def generate_answer(request: GenerateAnswerRequest):
    """Generate an answer for a question"""
    profile = app_state.context_manager.current_profile
    if not profile:
        raise HTTPException(status_code=400, detail="No profile loaded. Please upload your resume first.")

    # Create detected question
    question = DetectedQuestion(
        text=request.question,
        category=request.category,
        keywords=app_state.question_detector.extract_keywords(request.question)
    )

    # Build answer settings
    settings = app_state.user_settings.get("default", UserSettings()).answer
    if request.tone:
        settings.tone = request.tone
    if request.length:
        settings.length = request.length
    if request.format:
        settings.format = request.format
    if request.technical_depth:
        settings.technical_depth = request.technical_depth

    # Generate answer
    answer = await app_state.answer_generator.generate(
        question=question,
        profile=profile,
        session=app_state.context_manager.current_session,
        answer_settings=settings
    )

    # Humanize the answer
    answer.text = app_state.humanizer.humanize(answer.text)

    return answer.model_dump(mode="json")


class RegenerateRequest(BaseModel):
    question_id: str
    question: str
    previous_answer: str
    adjustment: str  # "shorter", "longer", "simpler", "more_technical"


@app.post("/api/answer/regenerate")
async def regenerate_answer(request: RegenerateRequest):
    """Regenerate an answer with adjustments"""
    profile = app_state.context_manager.current_profile
    if not profile:
        raise HTTPException(status_code=400, detail="No profile loaded")

    question = DetectedQuestion(
        id=request.question_id,
        text=request.question,
        keywords=app_state.question_detector.extract_keywords(request.question)
    )

    settings = app_state.user_settings.get("default", UserSettings()).answer

    answer = await app_state.answer_generator.regenerate(
        question=question,
        profile=profile,
        previous_answer=request.previous_answer,
        adjustment=request.adjustment,
        session=app_state.context_manager.current_session,
        answer_settings=settings
    )

    answer.text = app_state.humanizer.humanize(answer.text)
    return answer.model_dump(mode="json")


# ============================================================================
# Common Questions
# ============================================================================

@app.get("/api/common-questions")
async def get_common_questions():
    """Get list of common interview questions"""
    return {
        "questions": [
            {"type": "tell_me_about_yourself", "text": "Tell me about yourself"},
            {"type": "why_this_company", "text": "Why do you want to work here?"},
            {"type": "why_this_role", "text": "Why are you interested in this role?"},
            {"type": "greatest_strength", "text": "What is your greatest strength?"},
            {"type": "greatest_weakness", "text": "What is your greatest weakness?"},
            {"type": "where_see_yourself", "text": "Where do you see yourself in 5 years?"},
            {"type": "why_leaving", "text": "Why are you leaving your current position?"},
            {"type": "salary_expectations", "text": "What are your salary expectations?"},
        ]
    }


@app.post("/api/common-questions/{question_type}")
async def generate_common_answer(question_type: str):
    """Generate answer for a common question"""
    profile = app_state.context_manager.current_profile
    if not profile:
        raise HTTPException(status_code=400, detail="No profile loaded")

    settings = app_state.user_settings.get("default", UserSettings()).answer

    answer = await app_state.answer_generator.generate_for_common_question(
        question_type=question_type,
        profile=profile,
        session=app_state.context_manager.current_session,
        answer_settings=settings
    )

    answer.text = app_state.humanizer.humanize(answer.text)
    return answer.model_dump(mode="json")


# ============================================================================
# WebSocket for Real-time
# ============================================================================

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time audio streaming and answer generation.

    Message types:
    - audio: Audio chunk for transcription
    - transcript: Transcribed text
    - question: Detected question
    - answer: Generated answer
    - status: Status updates
    """
    await websocket.accept()
    app_state.websocket_connections[session_id] = websocket

    try:
        while True:
            # Receive message
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "audio":
                # Process audio chunk
                import base64
                audio_bytes = base64.b64decode(data.get("data", ""))
                source = data.get("source", "microphone")

                # Transcribe
                segment = await app_state.transcription_service.transcribe_audio(
                    audio_bytes, source=source
                )

                if segment:
                    # Send transcript
                    await websocket.send_json({
                        "type": "transcript",
                        "data": segment.model_dump(mode="json")
                    })

                    # Check for questions (only from interviewer/system audio)
                    if segment.speaker == SpeakerType.INTERVIEWER:
                        question = app_state.question_detector.detect(segment)

                        if question:
                            # Send detected question
                            await websocket.send_json({
                                "type": "question",
                                "data": question.model_dump(mode="json")
                            })

                            # Generate answer
                            profile = app_state.context_manager.current_profile
                            if profile:
                                settings = app_state.user_settings.get("default", UserSettings()).answer
                                answer = await app_state.answer_generator.generate(
                                    question=question,
                                    profile=profile,
                                    session=app_state.context_manager.current_session,
                                    answer_settings=settings
                                )
                                answer.text = app_state.humanizer.humanize(answer.text)

                                # Send answer
                                await websocket.send_json({
                                    "type": "answer",
                                    "data": answer.model_dump(mode="json")
                                })

            elif msg_type == "text_input":
                # Manual text input (for testing or typing questions)
                text = data.get("text", "")
                source = data.get("source", "interviewer")

                segment = TranscriptSegment(
                    text=text,
                    speaker=SpeakerType.INTERVIEWER if source == "interviewer" else SpeakerType.CANDIDATE
                )

                await websocket.send_json({
                    "type": "transcript",
                    "data": segment.model_dump(mode="json")
                })

                if source == "interviewer":
                    question = app_state.question_detector.detect(segment)
                    if question:
                        await websocket.send_json({
                            "type": "question",
                            "data": question.model_dump(mode="json")
                        })

                        profile = app_state.context_manager.current_profile
                        if profile:
                            settings = app_state.user_settings.get("default", UserSettings()).answer
                            answer = await app_state.answer_generator.generate(
                                question=question,
                                profile=profile,
                                session=app_state.context_manager.current_session,
                                answer_settings=settings
                            )
                            answer.text = app_state.humanizer.humanize(answer.text)

                            await websocket.send_json({
                                "type": "answer",
                                "data": answer.model_dump(mode="json")
                            })

            elif msg_type == "adjust":
                # Adjust previous answer
                adjustment = data.get("adjustment")
                question_data = data.get("question")
                previous_answer = data.get("previous_answer")

                if question_data and previous_answer and adjustment:
                    question = DetectedQuestion(**question_data)
                    profile = app_state.context_manager.current_profile

                    if profile:
                        settings = app_state.user_settings.get("default", UserSettings()).answer
                        answer = await app_state.answer_generator.regenerate(
                            question=question,
                            profile=profile,
                            previous_answer=previous_answer,
                            adjustment=adjustment,
                            session=app_state.context_manager.current_session,
                            answer_settings=settings
                        )
                        answer.text = app_state.humanizer.humanize(answer.text)

                        await websocket.send_json({
                            "type": "answer",
                            "data": answer.model_dump(mode="json")
                        })

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        if session_id in app_state.websocket_connections:
            del app_state.websocket_connections[session_id]
    except Exception as e:
        print(f"WebSocket error: {e}")
        await websocket.send_json({
            "type": "error",
            "data": {"message": str(e)}
        })


# ============================================================================
# Run server
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
