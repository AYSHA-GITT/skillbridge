import os
import json
import logging
from dotenv import load_dotenv
from google import genai

load_dotenv()

# Created on first use, like every other Gemini caller: creating it at import time made
# the whole app fail to start ("No API key was provided") when GEMINI_API_KEY was unset.
_client = None

FALLBACK_REQUIREMENTS = {
    "required": ["python", "sql", "git", "data structures"],
    "nice_to_have": ["docker", "cloud computing", "rest api"]
}


def _get_client():
    global _client
    if _client is None:
        api_key = (os.getenv("GEMINI_API_KEY") or "").strip()
        if not api_key:
            return None
        _client = genai.Client(api_key=api_key)
    return _client


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

    client = _get_client()
    if client is None:
        logging.warning("Gemini is not configured (GEMINI_API_KEY unset); using the default "
                        "skill list for career %r", career_name)
        return {k: list(v) for k, v in FALLBACK_REQUIREMENTS.items()}

    for model_name in ["gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.6-flash", "gemini-flash-latest"]:
        try:
            response = client.models.generate_content(
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

            if "required" in data and "nice_to_have" in data:
                return data
        except Exception as e:
            logging.warning(f"Gemini career requirements error with {model_name}: {e}")

    return {k: list(v) for k, v in FALLBACK_REQUIREMENTS.items()}