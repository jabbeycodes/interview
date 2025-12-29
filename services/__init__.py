"""
Service modules for Interview Assistant
"""
from .transcription import TranscriptionService, DualStreamTranscriber
from .question_detector import QuestionDetector
from .answer_generator import AnswerGenerator
from .humanizer import AnswerHumanizer, humanize_answer
from .context_manager import ContextManager

__all__ = [
    "TranscriptionService",
    "DualStreamTranscriber",
    "QuestionDetector",
    "AnswerGenerator",
    "AnswerHumanizer",
    "humanize_answer",
    "ContextManager",
]
