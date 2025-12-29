"""
Answer humanizer - makes AI responses sound more natural and human
"""
import re
import random
from typing import List, Optional


class AnswerHumanizer:
    """
    Transforms AI-generated answers to sound more natural and human.
    Adds conversational elements, removes robotic patterns, and introduces
    natural speech patterns.
    """

    # Robotic phrases to remove or replace
    ROBOTIC_PATTERNS = [
        (r"^As an? \w+,?\s*", ""),  # "As a software engineer, "
        (r"^In my role as,?\s*", ""),
        (r"^I would say that\s*", ""),
        (r"^To answer your question,?\s*", ""),
        (r"^That's a great question\.?\s*", ""),  # Optional to keep
        (r"^Great question\.?\s*", ""),
        (r"\bIn terms of\b", "regarding"),
        (r"\bIn order to\b", "to"),
        (r"\bDue to the fact that\b", "because"),
        (r"\bAt the end of the day\b", "ultimately"),
        (r"\bMoving forward\b", "going forward"),
        (r"\bI would be happy to\b", "I'd love to"),
        (r"\bI am confident that\b", "I'm confident"),
        (r"\bIt is important to note that\b", "notably"),
        (r"\bI believe that\b", "I think"),
    ]

    # Natural conversation starters
    NATURAL_STARTERS = [
        "So, ",
        "Well, ",
        "Honestly, ",
        "Actually, ",
        "",  # Sometimes no starter is most natural
        "",
        "",  # Weight toward no starter
    ]

    # Thoughtful pauses/acknowledgments for complex questions
    THOUGHTFUL_PAUSES = [
        "That's actually something I've thought about a lot. ",
        "Hmm, let me think about the best example. ",
        "You know, that reminds me of ",
        "That's a really good question - ",
        "I love this question because ",
    ]

    # Natural transition phrases
    TRANSITIONS = [
        "And then ",
        "So ",
        "From there, ",
        "That led to ",
        "Which meant ",
        "The result was ",
    ]

    # Filler phrases (use sparingly)
    FILLERS = [
        ", you know,",
        ", I think,",
        ", honestly,",
        ", to be honest,",
        ", actually,",
    ]

    # Enthusiasm markers
    ENTHUSIASM = [
        "I really enjoyed ",
        "I'm particularly proud of ",
        "What excited me most was ",
        "I was really passionate about ",
        "The coolest part was ",
    ]

    def __init__(self, intensity: float = 0.5):
        """
        Initialize humanizer.

        Args:
            intensity: How much to humanize (0.0 = minimal, 1.0 = maximum)
        """
        self.intensity = max(0.0, min(1.0, intensity))

    # Key points to bold (achievements, metrics, strong actions)
    BOLD_PATTERNS = [
        # Metrics and numbers
        r'(\d+%)',  # percentages
        r'(\d+x)',  # multipliers
        r'(\$[\d,]+[KMB]?)',  # dollar amounts
        r'(\d+\+?\s*(?:years?|months?|weeks?))',  # time periods
        r'(\d+\s*(?:team members?|people|users?|customers?))',  # people counts
        # Strong action verbs with results
        r'(led|spearheaded|drove|delivered|achieved|built|launched|created|designed|implemented|optimized|increased|reduced|improved|scaled|grew|saved)',
        # Impact words
        r'(significant|substantial|major|critical|key|core|primary|essential)',
    ]

    def humanize(self, text: str, question_complexity: str = "medium") -> str:
        """
        Humanize an AI-generated answer.

        Args:
            text: The AI-generated answer
            question_complexity: "simple", "medium", or "complex"

        Returns:
            More natural-sounding text
        """
        if not text:
            return text

        # Step 1: Remove robotic patterns
        result = self._remove_robotic_patterns(text)

        # Step 2: Add natural starter (occasionally)
        if random.random() < self.intensity * 0.3:
            if question_complexity == "complex":
                result = random.choice(self.THOUGHTFUL_PAUSES) + result
            else:
                starter = random.choice(self.NATURAL_STARTERS)
                if starter and not result.startswith(tuple("AEIOU")):
                    result = starter + result[0].lower() + result[1:]

        # Step 3: Add occasional fillers (very sparingly)
        if random.random() < self.intensity * 0.15:
            result = self._add_filler(result)

        # Step 4: Improve transitions
        result = self._improve_transitions(result)

        # Step 5: Vary sentence structure
        result = self._vary_structure(result)

        # Step 6: Contract formal phrases
        result = self._add_contractions(result)

        # Step 7: Add enthusiasm for achievement mentions
        result = self._add_enthusiasm(result)

        # Step 8: Bold key points
        result = self._bold_key_points(result)

        return result.strip()

    def _remove_robotic_patterns(self, text: str) -> str:
        """Remove or replace robotic-sounding phrases"""
        for pattern, replacement in self.ROBOTIC_PATTERNS:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        return text

    def _add_filler(self, text: str) -> str:
        """Add a natural filler phrase somewhere in the middle"""
        sentences = text.split(". ")
        if len(sentences) < 3:
            return text

        # Add filler to a random middle sentence
        insert_idx = random.randint(1, len(sentences) - 2)
        sentence = sentences[insert_idx]

        # Find a good insertion point (after a comma or at word boundary)
        words = sentence.split()
        if len(words) > 4:
            insert_word_idx = random.randint(2, len(words) - 2)
            filler = random.choice(self.FILLERS)
            words.insert(insert_word_idx, filler)
            sentences[insert_idx] = " ".join(words)

        return ". ".join(sentences)

    def _improve_transitions(self, text: str) -> str:
        """Replace generic transitions with more natural ones"""
        # Replace "Additionally" type transitions
        formal_transitions = [
            (r"\bAdditionally,?\s*", lambda: random.choice(["Also, ", "Plus, ", "And "])),
            (r"\bFurthermore,?\s*", lambda: random.choice(["Beyond that, ", "Also, ", "What's more, "])),
            (r"\bMoreover,?\s*", lambda: random.choice(["On top of that, ", "Also, ", ""])),
            (r"\bSubsequently,?\s*", lambda: random.choice(["Then ", "After that, ", "Next, "])),
            (r"\bConsequently,?\s*", lambda: random.choice(["So ", "As a result, ", "That meant "])),
        ]

        for pattern, replacement_func in formal_transitions:
            if re.search(pattern, text, re.IGNORECASE):
                text = re.sub(pattern, replacement_func(), text, count=1, flags=re.IGNORECASE)

        return text

    def _vary_structure(self, text: str) -> str:
        """Vary sentence structure to avoid monotony"""
        sentences = text.split(". ")

        # Check for repeated starts
        for i in range(1, len(sentences)):
            if sentences[i].split()[0:2] == sentences[i-1].split()[0:2]:
                # Add variation
                variations = ["In that case, ", "There, ", "At that point, ", ""]
                sentences[i] = random.choice(variations) + sentences[i]

        return ". ".join(sentences)

    def _add_contractions(self, text: str) -> str:
        """Convert formal phrases to contractions for natural speech"""
        contractions = [
            (r"\bI am\b", "I'm"),
            (r"\bI have\b", "I've"),
            (r"\bI would\b", "I'd"),
            (r"\bI will\b", "I'll"),
            (r"\bI had\b", "I'd"),
            (r"\bwe have\b", "we've"),
            (r"\bwe are\b", "we're"),
            (r"\bwe would\b", "we'd"),
            (r"\bthat is\b", "that's"),
            (r"\bthere is\b", "there's"),
            (r"\bit is\b", "it's"),
            (r"\bwould not\b", "wouldn't"),
            (r"\bcould not\b", "couldn't"),
            (r"\bdo not\b", "don't"),
            (r"\bdoes not\b", "doesn't"),
            (r"\bdid not\b", "didn't"),
            (r"\bcan not\b", "can't"),
            (r"\bcannot\b", "can't"),
        ]

        for pattern, replacement in contractions:
            # Apply most but not all contractions to seem natural
            if random.random() < 0.85:
                text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        return text

    def _add_enthusiasm(self, text: str) -> str:
        """Add enthusiasm markers for achievements"""
        achievement_words = ["achieved", "accomplished", "delivered", "launched", "built", "created"]

        # Only add enthusiasm once
        for word in achievement_words:
            if word in text.lower() and random.random() < self.intensity * 0.3:
                # Find the sentence with the achievement
                sentences = text.split(". ")
                for i, sentence in enumerate(sentences):
                    if word in sentence.lower() and not any(e in sentence for e in self.ENTHUSIASM):
                        enthusiasm = random.choice(self.ENTHUSIASM)
                        # Only modify if it makes sense
                        if sentence.lower().startswith("i "):
                            sentences[i] = enthusiasm + sentence[2:].lower()
                            text = ". ".join(sentences)
                            break
                break

        return text

    def _bold_key_points(self, text: str) -> str:
        """Add **bold** markers around key points like metrics, achievements, action verbs"""
        bolded = set()  # Track what we've already bolded to avoid duplicates
        result = text

        for pattern in self.BOLD_PATTERNS:
            matches = re.finditer(pattern, result, re.IGNORECASE)
            for match in matches:
                word = match.group(1)
                # Don't bold the same word twice or very short words
                if word.lower() not in bolded and len(word) > 2:
                    # Don't bold if already inside bold markers
                    start = match.start()
                    # Check if there's already a ** before this match
                    prefix = result[max(0, start-2):start]
                    if '**' not in prefix:
                        result = result[:start] + f"**{word}**" + result[start + len(word):]
                        bolded.add(word.lower())
                        # Only bold first 4-5 key items to avoid over-bolding
                        if len(bolded) >= 5:
                            return result

        return result

    def batch_humanize(self, texts: List[str]) -> List[str]:
        """Humanize multiple texts"""
        return [self.humanize(text) for text in texts]


def humanize_answer(text: str, intensity: float = 0.5) -> str:
    """Convenience function to humanize a single answer"""
    humanizer = AnswerHumanizer(intensity=intensity)
    return humanizer.humanize(text)
