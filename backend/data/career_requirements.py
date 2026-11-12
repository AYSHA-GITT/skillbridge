# Career skill requirements - single source of truth for gap analysis, readiness,
# roadmaps, career recommendations and the resume optimizer.
#
# Reviewed 2026-11-13 against skills demanded in ~480 current India-based tech postings
# collected by SkillBridge (see utils/market_demand.py; `flask jobs market-demand`).
# Changes were made only where demand was strong (roughly >= 25% of postings):
#   ai engineer        + generative ai (required, 56%), + aws (nice, 39%)
#   data scientist     + spark (nice, 27%), + scikit-learn (nice)
#   software engineer  + ci/cd (nice, 34%)
#   full stack dev     + rest api (required, 52%)
#   devops engineer    aws nice -> required (70%), + gcp (nice, 57%)
#   cloud engineer     + azure (nice, 55%), + gcp (nice, 60%)
# Basics employers rarely write down (git, data structures, html/css) were kept.
# web developer was not changed: too few current postings to judge.

CAREER_REQUIREMENTS = {

    "data analyst": {
        "required": [
            "sql",
            "excel",
            "python",
            "power bi",
            "tableau",
            "statistics"
        ],
        "nice_to_have": [
            "pandas",
            "numpy",
            "data visualization",
            "r",
            "communication"
        ]
    },

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
            "power bi",
            "spark",
            "scikit-learn"
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
            "aws",
            "ci/cd"
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
    },

    "full stack developer": {
        "required": [
            "html",
            "css",
            "javascript",
            "react",
            "node.js",
            "sql",
            "git",
            "rest api"
        ],
        "nice_to_have": [
            "docker",
            "mongodb",
            "aws",
            "typescript"
        ]
    },

    "devops engineer": {
        "required": [
            "linux",
            "git",
            "docker",
            "kubernetes",
            "ci/cd",
            "bash",
            "aws"
        ],
        "nice_to_have": [
            "terraform",
            "python",
            "monitoring",
            "gcp"
        ]
    },

    "cloud engineer": {
        "required": [
            "aws",
            "docker",
            "linux",
            "python",
            "git"
        ],
        "nice_to_have": [
            "kubernetes",
            "terraform",
            "ci/cd",
            "sql",
            "azure",
            "gcp"
        ]
    },

    "ai engineer": {
        "required": [
            "python",
            "machine learning",
            "deep learning",
            "pytorch",
            "data structures",
            "generative ai"
        ],
        "nice_to_have": [
            "tensorflow",
            "nlp",
            "docker",
            "sql",
            "aws"
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

    ai_client = get_client()
    if not ai_client:
        return None

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

            if "required" in data and "nice_to_have" in data:
                return data
        except Exception as e:
            logging.warning(f"Gemini career requirements error with {model_name}: {e}")

    return None