"""
Answer generation service using GPT-4
"""
import json
from typing import Optional, List, Dict
import openai
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import get_settings, TONE_PRESETS, LENGTH_PRESETS, INDUSTRY_PRESETS, ROLE_PRESETS
from models import (
    DetectedQuestion, GeneratedAnswer, UserProfile, SessionPrep,
    AnswerSettings, Story
)


class AnswerGenerator:
    """
    Generates human-sounding interview answers using GPT-4.
    Personalizes responses based on user profile, resume, and settings.
    """

    def __init__(self):
        self.settings = get_settings()
        self.client = openai.AsyncOpenAI(api_key=self.settings.openai_api_key)

    def _build_system_prompt(
        self,
        profile: UserProfile,
        session: Optional[SessionPrep],
        answer_settings: AnswerSettings
    ) -> str:
        """Build the system prompt with all context"""

        tone_config = TONE_PRESETS.get(answer_settings.tone.value, TONE_PRESETS["professional"])
        length_config = LENGTH_PRESETS.get(answer_settings.length.value, LENGTH_PRESETS["standard"])

        prompt = f"""You are helping a job candidate prepare authentic, human-sounding interview answers.

## YOUR ROLE
Generate answers that sound like they're coming from the actual candidate - natural, genuine, and conversational.
NOT robotic. NOT overly polished. Include natural speech patterns like "honestly," "I think," "you know," occasional pauses, and authentic enthusiasm.

## CANDIDATE PROFILE
{profile.get_context_summary()}

{f"Professional Summary: {profile.summary}" if profile.summary else ""}

## EXPERIENCE HIGHLIGHTS
"""
        # Add top experiences
        for exp in profile.experiences[:3]:
            prompt += f"""
### {exp.title} at {exp.company}
{exp.description}
Key achievements: {', '.join(exp.achievements[:3]) if exp.achievements else 'N/A'}
Technologies: {', '.join(exp.technologies[:5]) if exp.technologies else 'N/A'}
"""

        # Add skills
        if profile.skills:
            skill_names = [s.name for s in profile.skills[:15]]
            prompt += f"\n## KEY SKILLS\n{', '.join(skill_names)}\n"

        # Add session context (company, role, job description)
        if session:
            prompt += f"""
## INTERVIEW CONTEXT
Company: {session.company_name}
Role: {session.role_title}
Interview Type: {session.interview_type}
"""
            # Add custom industry context
            if session.industry:
                prompt += f"Industry: {session.industry}\n"

            # Add custom role type context
            if session.role_type:
                prompt += f"Role Function: {session.role_type}\n"

            if session.job_description:
                prompt += f"""
## JOB DESCRIPTION
{session.job_description[:2000]}

Use the job description above to tailor your answers. Reference specific requirements, technologies, or responsibilities mentioned when relevant.
"""
            if session.company_info:
                prompt += f"""
## ABOUT THE COMPANY
{session.company_info[:1000]}
"""

        # Add tone and style instructions
        prompt += f"""
## ANSWER STYLE
- Tone: {tone_config['description']}
- Be: {', '.join(tone_config['modifiers'])}
- Avoid: {', '.join(tone_config['avoid'])}
- Target length: {length_config['speaking_time']} ({length_config['sentences']} sentences)
- Technical depth: {answer_settings.technical_depth}/10
"""

        # Add industry/role context from session (custom text) or settings (presets)
        industry_context = session.industry if session and session.industry else None
        role_context = session.role_type if session and session.role_type else None

        if industry_context:
            # Use custom industry - generate appropriate guidance
            prompt += f"\n- Industry context: {industry_context}. Tailor language and examples to this industry."
            # Also check if it matches a preset for additional keywords
            industry_key = industry_context.lower()
            for preset_key, preset_config in INDUSTRY_PRESETS.items():
                if preset_key in industry_key or industry_key in preset_key:
                    prompt += f"\n- Relevant industry terms: {', '.join(preset_config.get('keywords', [])[:5])}"
                    break
        elif answer_settings.industry:
            industry_config = INDUSTRY_PRESETS.get(answer_settings.industry.value, {})
            if industry_config:
                prompt += f"\n- Industry keywords to incorporate naturally: {', '.join(industry_config.get('keywords', [])[:5])}"

        if role_context:
            # Use custom role type - generate appropriate guidance
            prompt += f"\n- Role focus: {role_context}. Frame answers around this specific function and its priorities."
            # Check for matching presets
            role_key = role_context.lower()
            for preset_key, preset_config in ROLE_PRESETS.items():
                if preset_key.replace("_", " ") in role_key or any(word in role_key for word in preset_key.split("_")):
                    prompt += f"\n- {preset_config.get('answer_style', '')}"
                    break
        elif answer_settings.role:
            role_config = ROLE_PRESETS.get(answer_settings.role.value, {})
            if role_config:
                prompt += f"\n- {role_config.get('answer_style', '')}"

        # Custom instructions
        if answer_settings.custom_instructions:
            prompt += f"""
## CUSTOM INSTRUCTIONS
{answer_settings.custom_instructions}
"""

        prompt += """
## CRITICAL RULES
1. Sound HUMAN - use natural language, not corporate speak
2. Be SPECIFIC - use real details from the candidate's experience
3. Show PERSONALITY - candidates should stand out, not sound generic
4. Include RESULTS - quantify impact whenever possible
5. Be AUTHENTIC - it's okay to show thoughtfulness ("That's a great question, let me think...")
6. NEVER fabricate experiences or skills not in the profile
7. When unsure, give a framework answer the candidate can adapt
"""

        return prompt

    def _find_relevant_stories(
        self,
        question: DetectedQuestion,
        profile: UserProfile
    ) -> List[Story]:
        """Find STAR stories relevant to the question"""
        if not profile.stories:
            return []

        relevant = []
        question_keywords = set(question.keywords)
        question_category = question.category

        for story in profile.stories:
            # Match by category
            if question_category and story.category.lower() == question_category.lower():
                relevant.append(story)
                continue

            # Match by keywords
            story_keywords = set(story.keywords)
            overlap = question_keywords.intersection(story_keywords)
            if len(overlap) >= 1:
                relevant.append(story)

        return relevant[:3]  # Return top 3 relevant stories

    async def generate(
        self,
        question: DetectedQuestion,
        profile: UserProfile,
        session: Optional[SessionPrep] = None,
        answer_settings: Optional[AnswerSettings] = None
    ) -> GeneratedAnswer:
        """
        Generate an answer for a detected question.

        Args:
            question: The detected interview question
            profile: User's profile with resume data
            session: Optional session-specific context
            answer_settings: Answer customization settings

        Returns:
            GeneratedAnswer with the generated response
        """
        if answer_settings is None:
            answer_settings = AnswerSettings()

        system_prompt = self._build_system_prompt(profile, session, answer_settings)

        # Find relevant stories
        relevant_stories = self._find_relevant_stories(question, profile)

        # Build user message
        user_message = f"Question: {question.text}"

        if relevant_stories:
            user_message += "\n\n## Relevant experiences you can draw from:"
            for story in relevant_stories:
                user_message += f"""
### {story.title}
- Situation: {story.situation}
- Task: {story.task}
- Action: {story.action}
- Result: {story.result}
"""

        # Add format instruction
        format_instruction = {
            "conversational": "Respond in a natural, conversational way.",
            "star": "Structure your answer using the STAR method (Situation, Task, Action, Result) but present it naturally, not as a rigid format.",
            "bullet_points": "Provide key points that can be delivered naturally, not as a literal list."
        }
        user_message += f"\n\n{format_instruction.get(answer_settings.format.value, format_instruction['conversational'])}"

        # Get length settings
        length_config = LENGTH_PRESETS.get(answer_settings.length.value, LENGTH_PRESETS["standard"])

        try:
            response = await self.client.chat.completions.create(
                model=self.settings.gpt_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=length_config["tokens"] + 100,  # Buffer for variation
                temperature=self.settings.temperature
            )

            answer_text = response.choices[0].message.content.strip()

            # Estimate speaking time (avg 150 words per minute)
            word_count = len(answer_text.split())
            speaking_time = f"{int(word_count / 2.5)} seconds"

            # Extract key points
            key_points = self._extract_key_points(answer_text)

            # Predict follow-ups
            follow_ups = await self._predict_follow_ups(question, answer_text)

            return GeneratedAnswer(
                question_id=question.id,
                text=answer_text,
                speaking_time=speaking_time,
                key_points=key_points,
                sources=[s.title for s in relevant_stories],
                confidence=question.confidence,
                tone=answer_settings.tone.value,
                length=answer_settings.length.value,
                format=answer_settings.format.value,
                likely_follow_ups=follow_ups
            )

        except Exception as e:
            # Return a fallback response
            return GeneratedAnswer(
                question_id=question.id,
                text=f"I apologize, I'm having trouble generating a response. Here's a framework: For this {question.category or 'question'}, consider discussing a specific example from your experience, what you did, and the outcome.",
                speaking_time="15 seconds",
                key_points=["Use a specific example", "Describe your actions", "Share the result"],
                confidence=0.3
            )

    def _extract_key_points(self, answer: str) -> List[str]:
        """Extract key talking points from an answer"""
        # Simple extraction - get sentences with impact words
        impact_words = ["achieved", "improved", "led", "created", "built", "reduced",
                       "increased", "saved", "delivered", "implemented", "managed"]

        sentences = answer.replace("\n", " ").split(". ")
        key_points = []

        for sentence in sentences:
            sentence_lower = sentence.lower()
            if any(word in sentence_lower for word in impact_words):
                if len(sentence) > 20:  # Skip very short sentences
                    key_points.append(sentence.strip()[:100])  # Limit length

        return key_points[:4]  # Max 4 key points

    async def _predict_follow_ups(
        self,
        question: DetectedQuestion,
        answer: str
    ) -> List[str]:
        """Predict likely follow-up questions"""
        try:
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",  # Use faster model for this
                messages=[
                    {
                        "role": "system",
                        "content": "You predict follow-up interview questions. Return exactly 2-3 short follow-up questions, one per line."
                    },
                    {
                        "role": "user",
                        "content": f"Question asked: {question.text}\n\nCandidate's answer: {answer[:500]}\n\nPredict follow-up questions:"
                    }
                ],
                max_tokens=150,
                temperature=0.7
            )

            follow_ups = response.choices[0].message.content.strip().split("\n")
            return [q.strip().lstrip("123.-) ") for q in follow_ups if q.strip()][:3]

        except:
            return []

    async def regenerate(
        self,
        question: DetectedQuestion,
        profile: UserProfile,
        previous_answer: str,
        adjustment: str,
        session: Optional[SessionPrep] = None,
        answer_settings: Optional[AnswerSettings] = None
    ) -> GeneratedAnswer:
        """
        Regenerate an answer with adjustments.

        Args:
            question: Original question
            profile: User profile
            previous_answer: The answer to adjust
            adjustment: What to change ("shorter", "longer", "simpler", "more_technical")
            session: Session context
            answer_settings: Settings (may be modified based on adjustment)
        """
        if answer_settings is None:
            answer_settings = AnswerSettings()

        # Modify settings based on adjustment
        adjustment_map = {
            "shorter": lambda s: setattr(s, 'length', 'brief'),
            "longer": lambda s: setattr(s, 'length', 'detailed'),
            "simpler": lambda s: setattr(s, 'technical_depth', max(1, s.technical_depth - 3)),
            "more_technical": lambda s: setattr(s, 'technical_depth', min(10, s.technical_depth + 3)),
        }

        if adjustment in adjustment_map:
            adjustment_map[adjustment](answer_settings)

        # Generate new answer
        return await self.generate(question, profile, session, answer_settings)

    async def generate_for_common_question(
        self,
        question_type: str,
        profile: UserProfile,
        session: Optional[SessionPrep] = None,
        answer_settings: Optional[AnswerSettings] = None
    ) -> GeneratedAnswer:
        """
        Generate answers for common questions using predefined templates.

        Args:
            question_type: Type like "tell_me_about_yourself", "why_this_company", etc.
            profile: User profile
            session: Session context
            answer_settings: Answer settings
        """
        common_questions = {
            "tell_me_about_yourself": "Tell me about yourself.",
            "why_this_company": f"Why do you want to work at {session.company_name if session else 'this company'}?",
            "why_this_role": f"Why are you interested in this {session.role_title if session else 'role'}?",
            "greatest_strength": "What is your greatest strength?",
            "greatest_weakness": "What is your greatest weakness?",
            "where_see_yourself": "Where do you see yourself in 5 years?",
            "why_leaving": "Why are you leaving your current position?",
            "salary_expectations": "What are your salary expectations?",
        }

        question_text = common_questions.get(question_type, "Tell me about yourself.")

        question = DetectedQuestion(
            text=question_text,
            category="background" if "yourself" in question_text else "goals_motivation",
            keywords=[]
        )

        return await self.generate(question, profile, session, answer_settings)
