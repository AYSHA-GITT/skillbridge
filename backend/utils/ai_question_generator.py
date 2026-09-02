import os
import json
import logging
from dotenv import load_dotenv
from google import genai

load_dotenv()

logging.basicConfig(level=logging.INFO)

client = None

def get_genai_client():
    global client
    if client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            client = genai.Client(api_key=api_key)
    return client


def generate_questions(skill_name, num_questions=5):
    """
    Generate MCQ questions using Google Gemini.
    Returns:
        list of questions on success
        None on failure
    """

    prompt = f"""
Generate exactly {num_questions} multiple-choice questions for the skill "{skill_name}".

Rules:
- Beginner to Intermediate level
- Exactly 4 options
- One correct answer
- Difficulty should be Easy or Medium

Return ONLY valid JSON.

Example:

[
 {{
   "question":"...",
   "option_a":"...",
   "option_b":"...",
   "option_c":"...",
   "option_d":"...",
   "correct_answer":"A",
   "difficulty":"Easy"
 }}
]
"""

    ai_client = get_genai_client()
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
            questions = json.loads(text)

            if isinstance(questions, list) and len(questions) > 0:
                logging.info(f"Generated {len(questions)} questions for {skill_name}")
                return questions
        except Exception as e:
            logging.warning(f"Gemini Question Error with {model_name}: {e}")

    return None


def normalize_question_text(text):
    """Lowercase, strip whitespace/punctuation for duplicate comparison."""
    import re
    return re.sub(r'[^a-z0-9\s]', '', text.lower()).strip()