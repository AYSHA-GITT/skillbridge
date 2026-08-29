import os
import json
import logging
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def generate_career_requirements(career_name):
    """
    Uses Gemini to generate a required/nice-to-have skill list for a
    career not present in our curated CAREER_REQUIREMENTS dict.
    Returns a dict: {"required": [...], "nice_to_have": [...]}
    or None on failure.
    """
    prompt = f"""
Generate a realistic list of skills needed for the career "{career_name}",
aimed at a student in India preparing to enter this field.

Rules:
- Return 5-8 "required" skills (must-have, core to the role)
- Return 3-5 "nice_to_have" skills (helpful but not essential)
- Use short, lowercase, commonly-known skill names only
  (e.g. "python", "sql", "communication" — not full sentences)

Return ONLY valid JSON in this exact format:

{{
  "required": ["skill1", "skill2", "..."],
  "nice_to_have": ["skill1", "skill2", "..."]
}}
"""

    try:
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt
        )
        data = json.loads(response.text)

        if "required" not in data or "nice_to_have" not in data:
            raise ValueError("Missing expected keys in Gemini response")

        return data

    except Exception as e:
        logging.error(f"Gemini career requirements error: {e}")
        return None