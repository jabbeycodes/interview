"""
User profile and resume data models
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum


class SkillLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class Skill(BaseModel):
    """Individual skill with proficiency level"""
    name: str
    level: SkillLevel = SkillLevel.INTERMEDIATE
    years_experience: Optional[float] = None
    keywords: List[str] = Field(default_factory=list)  # Related terms for matching


class Experience(BaseModel):
    """Work experience entry"""
    company: str
    title: str
    start_date: Optional[str] = None  # "Jan 2020"
    end_date: Optional[str] = None  # "Present" or "Dec 2023"
    description: str
    achievements: List[str] = Field(default_factory=list)
    technologies: List[str] = Field(default_factory=list)
    is_current: bool = False


class Education(BaseModel):
    """Education entry"""
    institution: str
    degree: str
    field_of_study: Optional[str] = None
    graduation_year: Optional[int] = None
    gpa: Optional[float] = None
    honors: List[str] = Field(default_factory=list)


class Project(BaseModel):
    """Project entry for portfolio"""
    name: str
    description: str
    role: Optional[str] = None
    technologies: List[str] = Field(default_factory=list)
    impact: Optional[str] = None  # Quantifiable results
    url: Optional[str] = None


class Story(BaseModel):
    """
    STAR format story for behavioral questions.
    These are pre-prepared stories that can be matched to questions.
    """
    title: str  # Brief identifier
    category: str  # "leadership", "conflict", "failure", "achievement", etc.
    situation: str
    task: str
    action: str
    result: str
    keywords: List[str] = Field(default_factory=list)  # For question matching
    follow_up_points: List[str] = Field(default_factory=list)


class TalkingPoint(BaseModel):
    """Quick talking points for specific topics"""
    topic: str
    points: List[str]
    keywords: List[str] = Field(default_factory=list)


class UserProfile(BaseModel):
    """Complete user profile with all interview preparation data"""
    id: str = Field(default_factory=lambda: datetime.now().strftime("%Y%m%d%H%M%S"))
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None

    # Professional summary
    headline: Optional[str] = None  # "Senior Software Engineer with 8 years experience"
    summary: Optional[str] = None  # Longer professional summary

    # Core profile data
    skills: List[Skill] = Field(default_factory=list)
    experiences: List[Experience] = Field(default_factory=list)
    education: List[Education] = Field(default_factory=list)
    projects: List[Project] = Field(default_factory=list)

    # Interview preparation
    stories: List[Story] = Field(default_factory=list)
    talking_points: List[TalkingPoint] = Field(default_factory=list)

    # Personal details for culture fit questions
    strengths: List[str] = Field(default_factory=list)
    areas_for_growth: List[str] = Field(default_factory=list)
    career_goals: Optional[str] = None
    why_leaving: Optional[str] = None  # Why leaving current/last job
    salary_expectations: Optional[str] = None

    # Resume file info
    resume_file_path: Optional[str] = None
    resume_text: Optional[str] = None  # Extracted text from resume
    resume_uploaded_at: Optional[datetime] = None

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def get_context_summary(self) -> str:
        """Generate a concise summary for AI context"""
        parts = []

        if self.headline:
            parts.append(f"Profile: {self.headline}")

        if self.experiences:
            current = next((e for e in self.experiences if e.is_current), None)
            if current:
                parts.append(f"Currently: {current.title} at {current.company}")

            parts.append(f"Experience: {len(self.experiences)} positions")

        if self.skills:
            top_skills = [s.name for s in self.skills[:10]]
            parts.append(f"Key skills: {', '.join(top_skills)}")

        if self.education:
            latest = self.education[0]
            parts.append(f"Education: {latest.degree} from {latest.institution}")

        return "\n".join(parts)


class SessionPrep(BaseModel):
    """Session-specific interview preparation"""
    id: str = Field(default_factory=lambda: datetime.now().strftime("%Y%m%d%H%M%S"))
    company_name: str
    role_title: str
    job_description: Optional[str] = None
    company_info: Optional[str] = None  # Research about the company
    interviewer_name: Optional[str] = None
    interviewer_role: Optional[str] = None
    interview_type: str = "phone"  # "phone", "video", "onsite", "technical"

    # Prepared questions and answers
    prepared_questions: List[Dict[str, str]] = Field(default_factory=list)
    questions_to_ask: List[str] = Field(default_factory=list)  # Questions for the interviewer

    # Session settings
    industry: Optional[str] = None
    role_type: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.now)


class ProfileUpdate(BaseModel):
    """Model for partial profile updates"""
    name: Optional[str] = None
    headline: Optional[str] = None
    summary: Optional[str] = None
    skills: Optional[List[Skill]] = None
    experiences: Optional[List[Experience]] = None
    education: Optional[List[Education]] = None
    projects: Optional[List[Project]] = None
    stories: Optional[List[Story]] = None
    talking_points: Optional[List[TalkingPoint]] = None
    strengths: Optional[List[str]] = None
    areas_for_growth: Optional[List[str]] = None
    career_goals: Optional[str] = None
    why_leaving: Optional[str] = None
    salary_expectations: Optional[str] = None
