
CAREER_REQUIREMENTS = {

    "data scientist": {
        "required": [
            "python",
            "sql",
            "machine learning",
            "statistics",
            "pandas",
            "numpy"
        ],
        "nice_to_have": [
            "tensorflow",
            "pytorch",
            "tableau",
            "power bi"
        ]
    },

    "software engineer": {
        "required": [
            "python",
            "java",
            "sql",
            "git",
            "data structures",
            "algorithms"
        ],
        "nice_to_have": [
            "flask",
            "react",
            "docker",
            "aws"
        ]
    },

    "web developer": {
        "required": [
            "html",
            "css",
            "javascript",
            "react",
            "git"
        ],
        "nice_to_have": [
            "flask",
            "node.js",
            "mongodb"
        ]
    }

}

import os
import json
import logging
from google import genai


client = None

def get_client():
    global client
    if client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            client = genai.Client(api_key=api_key)
    return client


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
        ai_client = get_client()
        if not ai_client:
            return None
        response = ai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        data = json.loads(response.text)

        if "required" not in data or "nice_to_have" not in data:
            raise ValueError("Missing expected keys in Gemini response")

        return data

    except Exception as e:
        logging.error(f"Gemini career requirements error: {e}")
        return None