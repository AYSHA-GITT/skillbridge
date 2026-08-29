from data.career_requirements import CAREER_REQUIREMENTS
from utils.career_requirements_generator import generate_career_requirements


def get_career_requirements(career_name):
    """
    Hybrid lookup: check curated dict first, fall back to Gemini
    if the career isn't in our list. Returns the requirements dict,
    or None if both fail.
    """
    normalized = career_name.strip().lower()

    if normalized in CAREER_REQUIREMENTS:
        return CAREER_REQUIREMENTS[normalized]

    # Not in curated list — ask Gemini
    return generate_career_requirements(normalized)


def analyze_skill_gap(student_verified_skills, career_name):
    """
    student_verified_skills: list of skill_name strings the student
    has actually verified (passed quiz on) — NOT just extracted/claimed.

    Returns a dict with matched required/nice_to_have skills, and
    what's missing from each category.
    """
    requirements = get_career_requirements(career_name)

    if requirements is None:
        return None

    student_skills_lower = set(s.lower() for s in student_verified_skills)

    required = requirements.get("required", [])
    nice_to_have = requirements.get("nice_to_have", [])

    matched_required = [s for s in required if s in student_skills_lower]
    missing_required = [s for s in required if s not in student_skills_lower]

    matched_nice = [s for s in nice_to_have if s in student_skills_lower]
    missing_nice = [s for s in nice_to_have if s not in student_skills_lower]

    # Coverage score: weighted more heavily toward required skills
    required_coverage = (len(matched_required) / len(required)) if required else 1.0
    nice_coverage = (len(matched_nice) / len(nice_to_have)) if nice_to_have else 1.0

    overall_coverage = round(
        (required_coverage * 0.75) + (nice_coverage * 0.25), 2
    )

    return {
        "career": career_name,
        "matched_required": matched_required,
        "missing_required": missing_required,
        "matched_nice_to_have": matched_nice,
        "missing_nice_to_have": missing_nice,
        "required_coverage": round(required_coverage, 2),
        "nice_to_have_coverage": round(nice_coverage, 2),
        "overall_coverage": overall_coverage,
    }