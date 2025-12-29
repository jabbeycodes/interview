"""
Conversation and transcript models
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum


class SpeakerType(str, Enum):
    INTERVIEWER = "interviewer"
    CANDIDATE = "candidate"
    UNKNOWN = "unknown"


class TranscriptSegment(BaseModel):
    """Single segment of transcribed speech"""
    id: str = Field(default_factory=lambda: datetime.now().strftime("%Y%m%d%H%M%S%f"))
    text: str
    speaker: SpeakerType = SpeakerType.UNKNOWN
    timestamp: datetime = Field(default_factory=datetime.now)
    duration: Optional[float] = None  # seconds
    confidence: float = Field(default=1.0, ge=0, le=1)
    is_question: bool = False
    is_final: bool = True  # False for partial/streaming transcripts


class DetectedQuestion(BaseModel):
    """A question detected from the transcript"""
    id: str = Field(default_factory=lambda: datetime.now().strftime("%Y%m%d%H%M%S%f"))
    text: str
    category: Optional[str] = None  # "behavioral", "technical", "situational", etc.
    keywords: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)
    confidence: float = Field(default=1.0, ge=0, le=1)
    segment_ids: List[str] = Field(default_factory=list)  # Related transcript segments


class GeneratedAnswer(BaseModel):
    """An answer generated for a question"""
    id: str = Field(default_factory=lambda: datetime.now().strftime("%Y%m%d%H%M%S%f"))
    question_id: str
    text: str
    speaking_time: Optional[str] = None  # Estimated time to speak
    key_points: List[str] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)  # Which profile elements were used
    confidence: float = Field(default=1.0, ge=0, le=1)
    timestamp: datetime = Field(default_factory=datetime.now)

    # Settings used to generate this answer
    tone: str = "professional"
    length: str = "standard"
    format: str = "conversational"

    # Alternative versions
    alternatives: List[str] = Field(default_factory=list)

    # Follow-up suggestions
    likely_follow_ups: List[str] = Field(default_factory=list)
    questions_to_ask: List[str] = Field(default_factory=list)


class ConversationTurn(BaseModel):
    """A complete Q&A turn in the conversation"""
    question: DetectedQuestion
    answer: Optional[GeneratedAnswer] = None
    user_feedback: Optional[str] = None  # "used", "skipped", "modified"


class InterviewSession(BaseModel):
    """Complete interview session"""
    id: str = Field(default_factory=lambda: datetime.now().strftime("%Y%m%d%H%M%S"))
    started_at: datetime = Field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None

    # Session context
    company: Optional[str] = None
    role: Optional[str] = None
    interview_type: str = "phone"

    # Transcript and conversation
    transcript: List[TranscriptSegment] = Field(default_factory=list)
    turns: List[ConversationTurn] = Field(default_factory=list)

    # Session stats
    questions_detected: int = 0
    answers_generated: int = 0
    answers_used: int = 0

    # Status
    is_active: bool = True
    is_recording: bool = False


class WebSocketMessage(BaseModel):
    """Message format for WebSocket communication"""
    type: str  # "transcript", "question", "answer", "status", "error"
    data: Dict
    timestamp: datetime = Field(default_factory=datetime.now)


class AudioChunk(BaseModel):
    """Audio data chunk for processing"""
    data: bytes
    sample_rate: int = 16000
    channels: int = 1
    source: str = "microphone"  # "microphone" or "system"
    timestamp: datetime = Field(default_factory=datetime.now)
