"""
Question detection service - identifies interview questions from transcript
"""
import re
from typing import List, Optional, Tuple
from datetime import datetime
from models import TranscriptSegment, DetectedQuestion, SpeakerType


class QuestionDetector:
    """
    Detects and categorizes interview questions from transcript segments.
    Uses pattern matching and heuristics to identify questions.
    """

    # Common interview question starters
    QUESTION_STARTERS = [
        # Direct questions
        r"^(can you|could you|would you|will you|do you|did you|have you|are you|were you)",
        r"^(what|when|where|why|how|which|who|whose)",
        r"^(tell me|describe|explain|walk me through|give me)",
        r"^(have you ever|has there been|was there)",

        # Behavioral question patterns
        r"(tell me about a time|describe a situation|give an example)",
        r"(how would you handle|how do you approach|how did you)",
        r"(what would you do if|what did you do when)",

        # Situational patterns
        r"(imagine|suppose|let's say|hypothetically)",

        # Follow-up patterns
        r"^(and |so |but )?(what|how|why|can you)",
        r"(can you elaborate|tell me more|explain further)",
    ]

    # Question categories and their patterns
    QUESTION_CATEGORIES = {
        "behavioral": [
            r"tell me about a time",
            r"describe a situation",
            r"give me an example",
            r"have you ever",
            r"how did you handle",
            r"what did you do when",
        ],
        "technical": [
            r"explain (how|what|why)",
            r"what is (your experience with|your approach to)",
            r"how would you (implement|design|build|solve)",
            r"what (technologies|tools|frameworks)",
            r"describe (your|the) (architecture|system|process)",
        ],
        "situational": [
            r"what would you do if",
            r"how would you handle",
            r"imagine|suppose|hypothetically",
            r"if you (were|had to)",
        ],
        "background": [
            r"tell me about yourself",
            r"walk me through your (resume|background|experience)",
            r"why (did you|are you|do you want)",
            r"what (interests you|attracted you|motivates you)",
        ],
        "culture_fit": [
            r"what kind of (environment|culture|team)",
            r"how do you (work with|collaborate|communicate)",
            r"what (values|matters|is important) to you",
            r"describe your (ideal|perfect|preferred)",
        ],
        "strengths_weaknesses": [
            r"(strength|weakness|improvement|growth)",
            r"what are you (good at|best at|proud of)",
            r"where do you (struggle|need improvement)",
            r"what would (colleagues|managers) say about you",
        ],
        "goals_motivation": [
            r"where do you see yourself",
            r"what are your (goals|aspirations|plans)",
            r"why (this role|this company|us)",
            r"what do you want to (achieve|accomplish|learn)",
        ],
        "salary_logistics": [
            r"(salary|compensation|benefits|pay)",
            r"when can you (start|begin)",
            r"are you (interviewing|considering|talking to)",
            r"(notice period|availability|relocation)",
        ],
    }

    # Phrases that indicate NOT a question (small talk, statements)
    NON_QUESTION_PATTERNS = [
        r"^(thanks|thank you|great|good|okay|alright|perfect|wonderful|excellent)",
        r"^(let me|i'll|i will|i'm going to)",
        r"^(before we|moving on|next|so now)",
        r"(does that make sense|do you have any questions)",  # Interviewer checking understanding
    ]

    def __init__(self, min_words: int = 5):
        """
        Initialize the question detector.

        Args:
            min_words: Minimum number of words for a segment to be considered
        """
        self.min_words = min_words
        self._compiled_patterns = self._compile_patterns()

    def _compile_patterns(self) -> dict:
        """Pre-compile regex patterns for efficiency"""
        return {
            "starters": [re.compile(p, re.IGNORECASE) for p in self.QUESTION_STARTERS],
            "categories": {
                cat: [re.compile(p, re.IGNORECASE) for p in patterns]
                for cat, patterns in self.QUESTION_CATEGORIES.items()
            },
            "non_questions": [re.compile(p, re.IGNORECASE) for p in self.NON_QUESTION_PATTERNS]
        }

    def is_question(self, text: str) -> Tuple[bool, float]:
        """
        Determine if text is likely a question.

        Args:
            text: The text to analyze

        Returns:
            Tuple of (is_question, confidence)
        """
        text = text.strip()

        # Too short
        if len(text.split()) < self.min_words:
            return False, 0.0

        # Check for non-question patterns first
        for pattern in self._compiled_patterns["non_questions"]:
            if pattern.search(text):
                return False, 0.1

        confidence = 0.0

        # Check for question mark
        if text.endswith("?"):
            confidence += 0.4

        # Check for question starters
        for pattern in self._compiled_patterns["starters"]:
            if pattern.search(text):
                confidence += 0.4
                break

        # Check for category-specific patterns
        for patterns in self._compiled_patterns["categories"].values():
            for pattern in patterns:
                if pattern.search(text):
                    confidence += 0.2
                    break
            if confidence >= 0.8:
                break

        # Threshold for considering it a question
        is_question = confidence >= 0.4
        return is_question, min(confidence, 1.0)

    def categorize_question(self, text: str) -> Optional[str]:
        """
        Categorize a question by type.

        Args:
            text: The question text

        Returns:
            Category name or None if no category matches
        """
        text = text.lower()

        best_category = None
        best_score = 0

        for category, patterns in self._compiled_patterns["categories"].items():
            score = 0
            for pattern in patterns:
                if pattern.search(text):
                    score += 1
            if score > best_score:
                best_score = score
                best_category = category

        return best_category

    def extract_keywords(self, text: str) -> List[str]:
        """
        Extract relevant keywords from a question for answer matching.

        Args:
            text: The question text

        Returns:
            List of keywords
        """
        # Remove common words
        stop_words = {
            "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "must", "can", "to", "of", "in", "for",
            "on", "with", "at", "by", "from", "about", "into", "through", "during",
            "before", "after", "above", "below", "between", "under", "again",
            "further", "then", "once", "here", "there", "when", "where", "why",
            "how", "all", "each", "few", "more", "most", "other", "some", "such",
            "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very",
            "just", "you", "your", "me", "my", "i", "we", "us", "our", "tell",
            "describe", "explain", "give", "example", "time", "situation"
        }

        # Extract words
        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())

        # Filter and return unique keywords
        keywords = []
        for word in words:
            if word not in stop_words and len(word) > 2:
                if word not in keywords:
                    keywords.append(word)

        return keywords[:10]  # Limit to top 10 keywords

    def detect(self, segment: TranscriptSegment) -> Optional[DetectedQuestion]:
        """
        Detect if a transcript segment contains a question.

        Args:
            segment: TranscriptSegment to analyze

        Returns:
            DetectedQuestion if a question is detected, None otherwise
        """
        # Only analyze interviewer speech
        if segment.speaker != SpeakerType.INTERVIEWER:
            return None

        text = segment.text.strip()
        is_q, confidence = self.is_question(text)

        if not is_q:
            return None

        category = self.categorize_question(text)
        keywords = self.extract_keywords(text)

        return DetectedQuestion(
            text=text,
            category=category,
            keywords=keywords,
            confidence=confidence,
            segment_ids=[segment.id]
        )

    def detect_multi_part(
        self,
        segments: List[TranscriptSegment],
        time_threshold: float = 5.0
    ) -> List[DetectedQuestion]:
        """
        Detect questions that may span multiple segments.

        Args:
            segments: List of transcript segments to analyze
            time_threshold: Max seconds between segments to consider them related

        Returns:
            List of detected questions
        """
        questions = []
        interviewer_segments = [
            s for s in segments if s.speaker == SpeakerType.INTERVIEWER
        ]

        if not interviewer_segments:
            return questions

        # Group consecutive interviewer segments
        groups = []
        current_group = [interviewer_segments[0]]

        for i in range(1, len(interviewer_segments)):
            prev = current_group[-1]
            curr = interviewer_segments[i]

            # Check if timestamps are close enough (if available)
            time_diff = (curr.timestamp - prev.timestamp).total_seconds()
            if time_diff <= time_threshold:
                current_group.append(curr)
            else:
                groups.append(current_group)
                current_group = [curr]

        groups.append(current_group)

        # Analyze each group
        for group in groups:
            combined_text = " ".join(s.text for s in group)
            is_q, confidence = self.is_question(combined_text)

            if is_q:
                category = self.categorize_question(combined_text)
                keywords = self.extract_keywords(combined_text)

                questions.append(DetectedQuestion(
                    text=combined_text,
                    category=category,
                    keywords=keywords,
                    confidence=confidence,
                    segment_ids=[s.id for s in group]
                ))

        return questions
