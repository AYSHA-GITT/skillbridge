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

    try:
        ai_client = get_genai_client()
        if not ai_client:
            return None
        response = ai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        questions = json.loads(response.text)

        if not isinstance(questions, list):
            raise ValueError("Gemini did not return a list.")

        logging.info(f"Generated {len(questions)} questions for {skill_name}")

        return questions

    except Exception as e:
        logging.error(f"Gemini Error: {e}")
        return None


def normalize_question_text(text):
    """Lowercase, strip whitespace/punctuation for duplicate comparison."""
    import re
    return re.sub(r'[^a-z0-9\s]', '', text.lower()).strip()