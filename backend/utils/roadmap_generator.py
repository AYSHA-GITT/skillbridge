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
    try:
        ai_client = get_genai_client()
        if not ai_client:
            return None
        response = ai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        data = json.loads(response.text)
        if not isinstance(data, list):
            raise ValueError("Expected a list")
        return data
    except Exception as e:
        logging.error(f"Gemini roadmap generation error: {e}")
        return None


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
        return []

    saved = []
    for item in generated:
        entry = RoadmapTemplate(
            skill_name=skill_name,
            day_number=item.get('day_number'),
            topic=item.get('topic'),
            description=item.get('description'),
            resource_hint=item.get('resource_hint'),
            duration_hours=item.get('duration_hours')
        )
        db.session.add(entry)
        saved.append(entry)

    db.session.commit()
    return saved