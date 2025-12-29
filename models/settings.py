"""
User settings and preferences models
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from enum import Enum


class ToneType(str, Enum):
    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    CONFIDENT = "confident"
    HUMBLE = "humble"


class LengthType(str, Enum):
    BRIEF = "brief"
    STANDARD = "standard"
    DETAILED = "detailed"


class FormatType(str, Enum):
    CONVERSATIONAL = "conversational"
    STAR = "star"
    BULLET_POINTS = "bullet_points"


class IndustryType(str, Enum):
    TECH = "tech"
    FINANCE = "finance"
    HEALTHCARE = "healthcare"
    CONSULTING = "consulting"
    OTHER = "other"


class RoleType(str, Enum):
    ENGINEERING = "engineering"
    PRODUCT_MANAGEMENT = "product_management"
    DESIGN = "design"
    SALES = "sales"
    MANAGEMENT = "management"
    OTHER = "other"


class AnswerSettings(BaseModel):
    """Settings for answer generation"""
    tone: ToneType = ToneType.PROFESSIONAL
    length: LengthType = LengthType.STANDARD
    format: FormatType = FormatType.CONVERSATIONAL
    industry: Optional[IndustryType] = None
    role: Optional[RoleType] = None

    # Fine-tuning options
    technical_depth: int = Field(default=5, ge=1, le=10)  # 1=simple, 10=very technical
    include_metrics: bool = True  # Include numbers/metrics when possible
    include_examples: bool = True  # Include concrete examples
    use_stories: bool = True  # Use STAR stories when relevant

    # Custom personality guidelines
    custom_instructions: Optional[str] = None


class AudioSettings(BaseModel):
    """Audio capture and processing settings"""
    input_device: Optional[str] = None  # System audio device
    mic_device: Optional[str] = None  # Microphone device
    noise_reduction: bool = True
    auto_detect_questions: bool = True
    silence_threshold: float = Field(default=0.01, ge=0, le=1)
    min_question_length: int = Field(default=5, ge=1)  # Minimum words to be a question


class DisplaySettings(BaseModel):
    """UI display settings"""
    theme: str = "dark"  # "dark" or "light"
    font_size: str = "medium"  # "small", "medium", "large"
    show_transcript: bool = True
    show_confidence: bool = True
    auto_scroll: bool = True
    mini_mode_opacity: float = Field(default=0.9, ge=0.3, le=1.0)


class HotkeySettings(BaseModel):
    """Keyboard shortcuts"""
    toggle_recording: str = "Ctrl+Shift+R"
    shorter_answer: str = "Ctrl+Shift+S"
    longer_answer: str = "Ctrl+Shift+L"
    more_technical: str = "Ctrl+Shift+T"
    less_technical: str = "Ctrl+Shift+E"
    copy_answer: str = "Ctrl+Shift+C"
    toggle_mini_mode: str = "Ctrl+Shift+M"
    regenerate_answer: str = "Ctrl+Shift+G"


class NotificationSettings(BaseModel):
    """Notification preferences"""
    sound_on_answer: bool = False
    vibrate_on_answer: bool = False  # For mobile
    desktop_notifications: bool = True


class UserSettings(BaseModel):
    """Complete user settings"""
    answer: AnswerSettings = Field(default_factory=AnswerSettings)
    audio: AudioSettings = Field(default_factory=AudioSettings)
    display: DisplaySettings = Field(default_factory=DisplaySettings)
    hotkeys: HotkeySettings = Field(default_factory=HotkeySettings)
    notifications: NotificationSettings = Field(default_factory=NotificationSettings)

    # Quick presets
    active_preset: Optional[str] = None  # Name of active preset
    saved_presets: Dict[str, AnswerSettings] = Field(default_factory=dict)


class QuickAdjustment(BaseModel):
    """Model for real-time answer adjustments"""
    action: str  # "shorter", "longer", "simpler", "technical", "regenerate"
    question_id: Optional[str] = None  # Which question to adjust
