"""
Context manager - manages user profile and session context for answer generation
"""
import json
import os
from typing import Optional, Dict, List
from datetime import datetime
from pathlib import Path
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import get_settings
from models import UserProfile, SessionPrep, Story, Experience, TalkingPoint


class ContextManager:
    """
    Manages all context for answer generation including:
    - User profile and resume data
    - Session-specific preparation (company, role, job description)
    - Conversation history
    - Cached relevant stories/experiences
    """

    def __init__(self, data_dir: Optional[str] = None):
        """
        Initialize context manager.

        Args:
            data_dir: Directory for storing profile data
        """
        settings = get_settings()
        self.data_dir = Path(data_dir or settings.data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.current_profile: Optional[UserProfile] = None
        self.current_session: Optional[SessionPrep] = None
        self._relevance_cache: Dict[str, List] = {}

    # Profile Management
    def load_profile(self, profile_id: str = "default") -> Optional[UserProfile]:
        """Load a user profile from disk"""
        profile_path = self.data_dir / f"profile_{profile_id}.json"

        if not profile_path.exists():
            return None

        try:
            with open(profile_path, "r") as f:
                data = json.load(f)
                self.current_profile = UserProfile(**data)
                return self.current_profile
        except Exception as e:
            print(f"Error loading profile: {e}")
            return None

    def save_profile(self, profile: UserProfile, profile_id: str = "default") -> bool:
        """Save a user profile to disk"""
        profile_path = self.data_dir / f"profile_{profile_id}.json"

        try:
            profile.updated_at = datetime.now()
            with open(profile_path, "w") as f:
                json.dump(profile.model_dump(mode="json"), f, indent=2, default=str)
            self.current_profile = profile
            return True
        except Exception as e:
            print(f"Error saving profile: {e}")
            return False

    def create_profile(self, name: str, **kwargs) -> UserProfile:
        """Create a new user profile"""
        profile = UserProfile(name=name, **kwargs)
        self.save_profile(profile)
        return profile

    def update_profile(self, updates: Dict) -> Optional[UserProfile]:
        """Update current profile with partial data"""
        if not self.current_profile:
            return None

        for key, value in updates.items():
            if hasattr(self.current_profile, key):
                setattr(self.current_profile, key, value)

        self.save_profile(self.current_profile)
        return self.current_profile

    # Session Management
    def start_session(
        self,
        company_name: str,
        role_title: str,
        job_description: Optional[str] = None,
        **kwargs
    ) -> SessionPrep:
        """Start a new interview preparation session"""
        self.current_session = SessionPrep(
            company_name=company_name,
            role_title=role_title,
            job_description=job_description,
            **kwargs
        )

        # Clear relevance cache for new session
        self._relevance_cache.clear()

        # Save session
        self._save_session()

        return self.current_session

    def update_session(self, updates: Dict) -> Optional[SessionPrep]:
        """Update current session"""
        if not self.current_session:
            return None

        for key, value in updates.items():
            if hasattr(self.current_session, key):
                setattr(self.current_session, key, value)

        self._save_session()
        return self.current_session

    def _save_session(self):
        """Save current session to disk"""
        if not self.current_session:
            return

        session_path = self.data_dir / f"session_{self.current_session.id}.json"
        with open(session_path, "w") as f:
            json.dump(self.current_session.model_dump(mode="json"), f, indent=2, default=str)

    def load_session(self, session_id: str) -> Optional[SessionPrep]:
        """Load a previous session"""
        session_path = self.data_dir / f"session_{session_id}.json"

        if not session_path.exists():
            return None

        try:
            with open(session_path, "r") as f:
                data = json.load(f)
                self.current_session = SessionPrep(**data)
                return self.current_session
        except Exception as e:
            print(f"Error loading session: {e}")
            return None

    # Story and Experience Matching
    def find_relevant_stories(
        self,
        keywords: List[str],
        category: Optional[str] = None,
        limit: int = 3
    ) -> List[Story]:
        """
        Find stories relevant to given keywords or category.

        Args:
            keywords: Keywords from the question
            category: Question category (behavioral, technical, etc.)
            limit: Maximum stories to return
        """
        if not self.current_profile or not self.current_profile.stories:
            return []

        # Check cache
        cache_key = f"stories_{'-'.join(sorted(keywords))}_{category}"
        if cache_key in self._relevance_cache:
            return self._relevance_cache[cache_key]

        scored_stories = []
        keywords_lower = {k.lower() for k in keywords}

        for story in self.current_profile.stories:
            score = 0

            # Category match (highest weight)
            if category and story.category.lower() == category.lower():
                score += 10

            # Keyword overlap
            story_keywords = {k.lower() for k in story.keywords}
            overlap = keywords_lower.intersection(story_keywords)
            score += len(overlap) * 3

            # Content keyword search
            story_content = (
                story.situation + story.task + story.action + story.result
            ).lower()
            for keyword in keywords_lower:
                if keyword in story_content:
                    score += 1

            if score > 0:
                scored_stories.append((score, story))

        # Sort by score and return top matches
        scored_stories.sort(key=lambda x: x[0], reverse=True)
        result = [story for score, story in scored_stories[:limit]]

        # Cache result
        self._relevance_cache[cache_key] = result
        return result

    def find_relevant_experiences(
        self,
        keywords: List[str],
        limit: int = 3
    ) -> List[Experience]:
        """Find experiences relevant to given keywords"""
        if not self.current_profile or not self.current_profile.experiences:
            return []

        scored_experiences = []
        keywords_lower = {k.lower() for k in keywords}

        for exp in self.current_profile.experiences:
            score = 0

            # Check title and company
            if any(k in exp.title.lower() for k in keywords_lower):
                score += 5
            if any(k in exp.company.lower() for k in keywords_lower):
                score += 3

            # Check description and achievements
            content = exp.description.lower()
            content += " ".join(exp.achievements).lower()
            for keyword in keywords_lower:
                if keyword in content:
                    score += 2

            # Check technologies
            exp_tech = {t.lower() for t in exp.technologies}
            tech_overlap = keywords_lower.intersection(exp_tech)
            score += len(tech_overlap) * 3

            # Boost current position
            if exp.is_current:
                score += 2

            if score > 0:
                scored_experiences.append((score, exp))

        scored_experiences.sort(key=lambda x: x[0], reverse=True)
        return [exp for score, exp in scored_experiences[:limit]]

    def find_talking_points(self, topic: str) -> List[TalkingPoint]:
        """Find talking points for a topic"""
        if not self.current_profile or not self.current_profile.talking_points:
            return []

        topic_lower = topic.lower()
        relevant = []

        for point in self.current_profile.talking_points:
            if topic_lower in point.topic.lower():
                relevant.append(point)
            elif any(topic_lower in k.lower() for k in point.keywords):
                relevant.append(point)

        return relevant

    # Context Building
    def build_answer_context(self, keywords: List[str], category: Optional[str] = None) -> Dict:
        """
        Build complete context for answer generation.

        Returns dict with relevant stories, experiences, and talking points.
        """
        context = {
            "profile_summary": None,
            "stories": [],
            "experiences": [],
            "talking_points": [],
            "session": None
        }

        if self.current_profile:
            context["profile_summary"] = self.current_profile.get_context_summary()
            context["stories"] = self.find_relevant_stories(keywords, category)
            context["experiences"] = self.find_relevant_experiences(keywords)

            # Find talking points for first keyword
            if keywords:
                context["talking_points"] = self.find_talking_points(keywords[0])

        if self.current_session:
            context["session"] = {
                "company": self.current_session.company_name,
                "role": self.current_session.role_title,
                "job_description": self.current_session.job_description,
                "company_info": self.current_session.company_info
            }

        return context

    # Job Description Analysis
    def analyze_job_description(self, job_description: str) -> Dict:
        """
        Analyze a job description to extract key requirements.

        Returns dict with extracted requirements and suggested focus areas.
        """
        # Keywords by category
        skill_patterns = [
            "python", "java", "javascript", "react", "node", "sql", "aws",
            "docker", "kubernetes", "git", "agile", "scrum"
        ]
        experience_patterns = [
            r"(\d+)\+?\s*years?",  # "5+ years"
        ]

        jd_lower = job_description.lower()

        analysis = {
            "required_skills": [],
            "years_experience": None,
            "key_responsibilities": [],
            "suggested_talking_points": []
        }

        # Extract skills
        for skill in skill_patterns:
            if skill in jd_lower:
                analysis["required_skills"].append(skill)

        # Extract years of experience
        import re
        for pattern in experience_patterns:
            match = re.search(pattern, jd_lower)
            if match:
                analysis["years_experience"] = match.group(1)
                break

        # Match against profile skills
        if self.current_profile:
            profile_skills = {s.name.lower() for s in self.current_profile.skills}
            matched_skills = set(analysis["required_skills"]).intersection(profile_skills)
            analysis["matched_skills"] = list(matched_skills)
            analysis["missing_skills"] = list(
                set(analysis["required_skills"]) - matched_skills
            )

        return analysis

    def get_session_context_summary(self) -> str:
        """Get a formatted summary of current session context"""
        if not self.current_session:
            return "No active session"

        parts = [
            f"Company: {self.current_session.company_name}",
            f"Role: {self.current_session.role_title}",
            f"Interview Type: {self.current_session.interview_type}"
        ]

        if self.current_session.interviewer_name:
            parts.append(f"Interviewer: {self.current_session.interviewer_name}")

        return "\n".join(parts)
