"""
Data models for Interview Assistant
"""
from .profile import (
    UserProfile,
    Experience,
    Education,
    Skill,
    SkillLevel,
    Project,
    Story,
    TalkingPoint,
    SessionPrep,
    ProfileUpdate
)

from .settings import (
    UserSettings,
    AnswerSettings,
    AudioSettings,
    DisplaySettings,
    HotkeySettings,
    ToneType,
    LengthType,
    FormatType,
    IndustryType,
    RoleType,
    QuickAdjustment
)

from .conversation import (
    TranscriptSegment,
    DetectedQuestion,
    GeneratedAnswer,
    ConversationTurn,
    InterviewSession,
    WebSocketMessage,
    AudioChunk,
    SpeakerType
)

__all__ = [
    # Profile
    "UserProfile",
    "Experience",
    "Education",
    "Skill",
    "SkillLevel",
    "Project",
    "Story",
    "TalkingPoint",
    "SessionPrep",
    "ProfileUpdate",
    # Settings
    "UserSettings",
    "AnswerSettings",
    "AudioSettings",
    "DisplaySettings",
    "HotkeySettings",
    "ToneType",
    "LengthType",
    "FormatType",
    "IndustryType",
    "RoleType",
    "QuickAdjustment",
    # Conversation
    "TranscriptSegment",
    "DetectedQuestion",
    "GeneratedAnswer",
    "ConversationTurn",
    "InterviewSession",
    "WebSocketMessage",
    "AudioChunk",
    "SpeakerType",
]
