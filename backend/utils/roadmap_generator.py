import os
import json
import logging
from google import genai
from extensions import db
from models import RoadmapTemplate

client = None

def get_genai_client():
    global client
    if client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            client = genai.Client(api_key=api_key)
    return client

DAYS_BY_IMPORTANCE = {
    'High': 7,
    'Medium': 4,
}


def get_fallback_roadmap(skill_name, num_days):
    """
    Curated fallback curriculum in case Gemini API is unavailable or rate limited.
    """
    clean_skill = skill_name.strip().title()
    templates_7_days = [
        {"day_number": 1, "topic": f"Introduction to {clean_skill} & Environment Setup", "description": f"Understand core concepts, basic architecture, and set up the local tooling and environment for {clean_skill}.", "resource_hint": f"YouTube: {clean_skill} tutorial for beginners", "duration_hours": 1.5},
        {"day_number": 2, "topic": f"{clean_skill} Fundamentals & Syntax", "description": f"Learn foundational syntax, standard conventions, data handling, and essential operations in {clean_skill}.", "resource_hint": f"YouTube: {clean_skill} syntax and fundamentals crash course", "duration_hours": 2.0},
        {"day_number": 3, "topic": f"Intermediate Concepts & Core Operations", "description": f"Dive into functions, control flow, modules, and standard patterns used in real {clean_skill} projects.", "resource_hint": f"YouTube: {clean_skill} practical hands on guide", "duration_hours": 2.0},
        {"day_number": 4, "topic": f"Hands-on Mini Project with {clean_skill}", "description": f"Build a practical starter project applying what you have learned and solidify core competencies.", "resource_hint": f"YouTube: {clean_skill} beginner project step by step", "duration_hours": 2.5},
        {"day_number": 5, "topic": f"Debugging, Testing & Common Pitfalls", "description": f"Learn common error messages in {clean_skill}, debugging workflows, and basic unit testing.", "resource_hint": f"YouTube: {clean_skill} debugging and best practices", "duration_hours": 1.5},
        {"day_number": 6, "topic": f"Optimization, Tooling & Ecosystem", "description": f"Explore popular libraries, packages, performance optimization tips, and package managers for {clean_skill}.", "resource_hint": f"YouTube: {clean_skill} ecosystem and tools", "duration_hours": 2.0},
        {"day_number": 7, "topic": f"Capstone Project & Interview Prep", "description": f"Complete a portfolio-ready project showcasing {clean_skill} and review top technical interview questions.", "resource_hint": f"YouTube: {clean_skill} interview questions and answers", "duration_hours": 3.0}
    ]
    templates_4_days = [
        {"day_number": 1, "topic": f"{clean_skill} Fundamentals & Setup", "description": f"Understand core principles, basic terminology, and install necessary development tools for {clean_skill}.", "resource_hint": f"YouTube: {clean_skill} tutorial for beginners", "duration_hours": 1.5},
        {"day_number": 2, "topic": f"Key Concepts & Practical Exercises", "description": f"Practice primary syntax, data patterns, and common operations with hands-on coding exercises.", "resource_hint": f"YouTube: {clean_skill} crash course", "duration_hours": 2.0},
        {"day_number": 3, "topic": f"Working with Real-world Data & Libraries", "description": f"Learn how {clean_skill} integrates with real-world workflows, third-party libraries, and APIs.", "resource_hint": f"YouTube: {clean_skill} practical guide", "duration_hours": 2.0},
        {"day_number": 4, "topic": f"Mini Project & Skill Validation", "description": f"Complete a portfolio-level exercise to validate your skills and test your understanding.", "resource_hint": f"YouTube: {clean_skill} project tutorial", "duration_hours": 2.5}
    ]
    if num_days <= 4:
        return templates_4_days[:num_days]
    return templates_7_days[:num_days]


def generate_roadmap_days(skill_name, num_days):
    prompt = f"""
Create a {num_days}-day beginner learning plan for the skill "{skill_name}",
aimed at an Indian college student with no prior experience in it.

Rules:
- One entry per day, {num_days} entries total
- Each entry needs: a short topic title, a 1-2 sentence description of what
  to learn/practice that day, a resource_hint (a short phrase describing what
  to search for online, e.g. "YouTube: SQL joins explained"), and a realistic
  duration_hours (number, e.g. 1.5)
- Keep it practical and beginner-friendly, building up gradually

Return ONLY valid JSON in this exact format:

[
  {{"day_number": 1, "topic": "...", "description": "...",
    "resource_hint": "...", "duration_hours": 1.5}}
]
"""
    ai_client = get_genai_client()
    if not ai_client:
        return get_fallback_roadmap(skill_name, num_days)

    for model_name in ["gemini-3.6-flash", "gemini-flash-latest"]:
        try:
            response = ai_client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            text = (response.text or "").strip()
            if text.startswith("```json"):
                text = text[7:]
            elif text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            data = json.loads(text)
            if isinstance(data, list) and len(data) > 0:
                return data
        except Exception as e:
            logging.warning(f"Gemini model {model_name} error: {e}")

    # If all AI models failed, return curated fallback
    return get_fallback_roadmap(skill_name, num_days)


def ensure_roadmap_template(skill_name, importance):
    """
    Hybrid cache: check RoadmapTemplate for this skill first. If missing,
    generate via Gemini (day count based on importance) and cache
    permanently. Returns list of RoadmapTemplate rows for this skill.
    """
    existing = RoadmapTemplate.query.filter_by(skill_name=skill_name).all()
    if existing:
        return existing

    num_days = DAYS_BY_IMPORTANCE.get(importance, 4)
    generated = generate_roadmap_days(skill_name, num_days)

    if not generated:
        generated = get_fallback_roadmap(skill_name, num_days)

    saved = []
    for item in generated:
        entry = RoadmapTemplate(
            skill_name=skill_name,
            day_number=item.get('day_number'),
            topic=item.get('topic'),
            description=item.get('description'),
            resource_hint=item.get('resource_hint'),
            duration_hours=item.get('duration_hours', 1.5)
        )
        db.session.add(entry)
        saved.append(entry)

    db.session.commit()
    return saved