"""
Configuration management for Interview Assistant
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # API Keys
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")

    # Server settings
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    debug: bool = Field(default=False)

    # OpenAI settings
    gpt_model: str = Field(default="gpt-4-turbo-preview")
    whisper_model: str = Field(default="whisper-1")
    max_tokens: int = Field(default=1000)
    temperature: float = Field(default=0.7)

    # Audio settings
    audio_sample_rate: int = Field(default=16000)
    audio_chunk_duration: float = Field(default=3.0)  # seconds
    silence_threshold: float = Field(default=0.01)

    # Answer generation settings
    default_tone: str = Field(default="professional")
    default_length: str = Field(default="standard")
    default_format: str = Field(default="conversational")

    # Data paths
    data_dir: str = Field(default="data")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Answer tone presets
TONE_PRESETS = {
    "professional": {
        "description": "Polished and business-appropriate",
        "modifiers": ["articulate", "measured", "confident"],
        "avoid": ["slang", "overly casual language", "filler words"]
    },
    "friendly": {
        "description": "Warm and approachable while remaining professional",
        "modifiers": ["personable", "engaging", "relatable"],
        "avoid": ["being too formal", "cold language"]
    },
    "confident": {
        "description": "Self-assured without being arrogant",
        "modifiers": ["assertive", "decisive", "clear"],
        "avoid": ["hedging", "uncertainty markers", "self-deprecation"]
    },
    "humble": {
        "description": "Modest while still showcasing achievements",
        "modifiers": ["thoughtful", "collaborative", "learning-focused"],
        "avoid": ["bragging", "overconfidence"]
    }
}

# Answer length presets (in approximate speaking time)
LENGTH_PRESETS = {
    "brief": {
        "tokens": 150,
        "speaking_time": "30 seconds",
        "sentences": "2-3"
    },
    "standard": {
        "tokens": 300,
        "speaking_time": "1 minute",
        "sentences": "4-6"
    },
    "detailed": {
        "tokens": 500,
        "speaking_time": "2 minutes",
        "sentences": "8-12"
    }
}

# Industry presets with common questions and terminology
INDUSTRY_PRESETS = {
    "tech": {
        "keywords": ["scalability", "architecture", "agile", "sprint", "deployment"],
        "common_questions": [
            "Tell me about a challenging technical problem you solved",
            "How do you stay updated with new technologies",
            "Describe your experience with [technology]"
        ]
    },
    "finance": {
        "keywords": ["ROI", "compliance", "risk management", "stakeholder", "due diligence"],
        "common_questions": [
            "Describe a time you identified a financial risk",
            "How do you ensure accuracy in your work",
            "Tell me about your experience with financial modeling"
        ]
    },
    "healthcare": {
        "keywords": ["patient outcomes", "compliance", "HIPAA", "care coordination"],
        "common_questions": [
            "How do you handle high-pressure situations",
            "Describe your approach to patient communication",
            "Tell me about a time you improved a process"
        ]
    },
    "consulting": {
        "keywords": ["stakeholder management", "deliverables", "scope", "engagement"],
        "common_questions": [
            "Tell me about a difficult client situation",
            "How do you structure your problem-solving approach",
            "Describe a project where you drove significant impact"
        ]
    }
}

# Role-specific presets
ROLE_PRESETS = {
    "engineering": {
        "focus_areas": ["technical skills", "problem-solving", "system design", "collaboration"],
        "answer_style": "Include specific technical details and metrics when relevant"
    },
    "product_management": {
        "focus_areas": ["user empathy", "prioritization", "cross-functional leadership", "metrics"],
        "answer_style": "Frame answers around user impact and business outcomes"
    },
    "design": {
        "focus_areas": ["user research", "design process", "iteration", "collaboration"],
        "answer_style": "Walk through design thinking and decision rationale"
    },
    "sales": {
        "focus_areas": ["relationship building", "quota achievement", "negotiation", "pipeline"],
        "answer_style": "Use numbers and concrete results, tell compelling stories"
    },
    "management": {
        "focus_areas": ["team development", "strategic thinking", "conflict resolution", "results"],
        "answer_style": "Focus on leadership approach and team outcomes"
    }
}
