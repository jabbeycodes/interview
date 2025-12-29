"""
Job description parser - extracts company, role, requirements from job postings
"""
import re
from typing import Dict, List, Optional


class JobDescriptionParser:
    """
    Parses job descriptions to extract structured information.
    """

    # Common company name patterns
    COMPANY_PATTERNS = [
        r"(?:at|@|join|with)\s+([A-Z][A-Za-z0-9\s&]+?)(?:\s+as|\s+is|\s*[,\.])",
        r"^([A-Z][A-Za-z0-9\s&]+?)\s+is\s+(?:looking|seeking|hiring)",
        r"(?:About|Company:?)\s*([A-Z][A-Za-z0-9\s&]+?)(?:\n|\.)",
        r"([A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+)?)\s+(?:Inc|LLC|Corp|Ltd|Company)",
    ]

    # Role/title patterns
    ROLE_PATTERNS = [
        r"(?:Position|Role|Title|Job Title):?\s*([^\n]+)",
        r"(?:hiring|seeking|looking for)(?: an?)?\s+([A-Z][A-Za-z\s]+?)(?:\s+to|\s+who|\s*[,\.])",
        r"^([A-Z][A-Za-z\s]+(?:Engineer|Developer|Manager|Designer|Analyst|Scientist|Lead|Director|Architect))",
        r"(?:join .+ as .+?|as a)\s+([A-Z][A-Za-z\s]+?)(?:\s+to|\s+and|\s*[,\.\n])",
    ]

    # Skills/requirements patterns
    SKILL_PATTERNS = [
        # Programming languages
        r"\b(Python|Java|JavaScript|TypeScript|C\+\+|C#|Ruby|Go|Rust|Swift|Kotlin|PHP|Scala|R)\b",
        # Frameworks
        r"\b(React|Angular|Vue|Node\.?js|Django|Flask|FastAPI|Spring|Rails|\.NET|Express)\b",
        # Databases
        r"\b(SQL|MySQL|PostgreSQL|MongoDB|Redis|Elasticsearch|DynamoDB|Cassandra|Oracle)\b",
        # Cloud/DevOps
        r"\b(AWS|Azure|GCP|Docker|Kubernetes|CI/CD|Jenkins|Terraform|Ansible)\b",
        # Data/ML
        r"\b(Machine Learning|ML|AI|TensorFlow|PyTorch|Pandas|NumPy|Spark|Hadoop|ETL)\b",
        # General tech
        r"\b(REST|GraphQL|Microservices|Agile|Scrum|Git|Linux|API|OAuth)\b",
    ]

    # Experience patterns
    EXPERIENCE_PATTERNS = [
        r"(\d+)\+?\s*(?:years?|yrs?)(?:\s+of)?\s+(?:experience|exp)",
        r"(?:minimum|at least|requires?)\s+(\d+)\+?\s*(?:years?|yrs?)",
    ]

    def parse(self, job_description: str) -> Dict:
        """
        Parse a job description and extract structured information.

        Args:
            job_description: Raw job description text

        Returns:
            Dictionary with extracted fields
        """
        result = {
            "company_name": None,
            "role_title": None,
            "skills": [],
            "years_experience": None,
            "requirements": [],
            "responsibilities": [],
        }

        if not job_description:
            return result

        # Clean text
        text = job_description.strip()

        # Extract company name
        result["company_name"] = self._extract_company(text)

        # Extract role/title
        result["role_title"] = self._extract_role(text)

        # Extract skills
        result["skills"] = self._extract_skills(text)

        # Extract years of experience
        result["years_experience"] = self._extract_experience(text)

        # Extract requirements (bullet points under Requirements/Qualifications)
        result["requirements"] = self._extract_section(text, ["requirements", "qualifications", "what you need", "must have"])

        # Extract responsibilities
        result["responsibilities"] = self._extract_section(text, ["responsibilities", "what you'll do", "your role", "duties"])

        return result

    def _extract_company(self, text: str) -> Optional[str]:
        """Extract company name from job description"""
        for pattern in self.COMPANY_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                company = match.group(1).strip()
                # Clean up
                company = re.sub(r'\s+', ' ', company)
                if len(company) > 2 and len(company) < 50:
                    return company
        return None

    def _extract_role(self, text: str) -> Optional[str]:
        """Extract role/title from job description"""
        # Check first few lines for title
        first_lines = text[:500]

        for pattern in self.ROLE_PATTERNS:
            match = re.search(pattern, first_lines, re.IGNORECASE | re.MULTILINE)
            if match:
                role = match.group(1).strip()
                role = re.sub(r'\s+', ' ', role)
                if len(role) > 3 and len(role) < 60:
                    return role

        # Fallback: look for common job title words
        title_words = ["Engineer", "Developer", "Manager", "Designer", "Analyst",
                       "Scientist", "Lead", "Director", "Architect", "Specialist"]
        for word in title_words:
            pattern = rf"([A-Z][a-z]+\s+)*{word}"
            match = re.search(pattern, first_lines)
            if match:
                return match.group(0).strip()

        return None

    def _extract_skills(self, text: str) -> List[str]:
        """Extract technical skills from job description"""
        skills = set()

        for pattern in self.SKILL_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Normalize skill name
                skill = match.strip()
                if skill.lower() == "node.js":
                    skill = "Node.js"
                elif skill.lower() == "nodejs":
                    skill = "Node.js"
                skills.add(skill)

        return sorted(list(skills))

    def _extract_experience(self, text: str) -> Optional[str]:
        """Extract years of experience requirement"""
        for pattern in self.EXPERIENCE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return f"{match.group(1)}+ years"
        return None

    def _extract_section(self, text: str, section_keywords: List[str]) -> List[str]:
        """Extract bullet points from a section"""
        items = []

        # Find section
        for keyword in section_keywords:
            pattern = rf"(?:{keyword})[:\s]*\n((?:[\s]*[-•*]\s*[^\n]+\n?)+)"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                section_text = match.group(1)
                # Extract bullet points
                bullets = re.findall(r"[-•*]\s*([^\n]+)", section_text)
                items.extend([b.strip() for b in bullets if len(b.strip()) > 10])
                break

        return items[:10]  # Limit to 10 items


def parse_job_description(text: str) -> Dict:
    """Convenience function to parse a job description"""
    parser = JobDescriptionParser()
    return parser.parse(text)
