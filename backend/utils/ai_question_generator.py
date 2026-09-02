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
    if ai_client:
        for model_name in ["gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.6-flash", "gemini-flash-latest"]:
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

    # Fallback to curated templates if AI is rate-limited or unavailable
    return get_fallback_questions(skill_name, num_questions)


def get_fallback_questions(skill_name, num_questions=5):
    """Provides standard fallback questions if Gemini API is unavailable or rate limited."""
    clean = skill_name.strip().title()
    templates = [
        {
            "question": f"What is the primary role of {clean} in modern software workflows?",
            "option_a": f"Developing applications, services, or solutions using {clean}",
            "option_b": "Replacing hardware and cooling systems",
            "option_c": "Serving static non-interactive styling exclusively",
            "option_d": "None of the above",
            "correct_answer": "A",
            "difficulty": "Easy"
        },
        {
            "question": f"Which of the following is considered a best practice when working with {clean}?",
            "option_a": "Writing modular, readable, and well-tested code",
            "option_b": "Skipping all error handling and logging",
            "option_c": "Hardcoding credentials and sensitive secrets",
            "option_d": "Avoiding documentation completely",
            "correct_answer": "A",
            "difficulty": "Easy"
        },
        {
            "question": f"When troubleshooting an issue in {clean}, what is the recommended first step?",
            "option_a": "Inspect logs and understand the stack trace or error message",
            "option_b": "Randomly delete dependencies and files",
            "option_c": "Reinstall the operating system",
            "option_d": "Ignore the problem",
            "correct_answer": "A",
            "difficulty": "Medium"
        },
        {
            "question": f"How does {clean} typically achieve reusability and maintainability?",
            "option_a": "Through modular functions, libraries, packages, or components",
            "option_b": "By copy-pasting code blocks repeatedly",
            "option_c": "By putting all code in a single unorganized script",
            "option_d": "Reusability is not supported",
            "correct_answer": "A",
            "difficulty": "Medium"
        },
        {
            "question": f"Which tool or practice is essential for collaborating effectively on {clean} projects?",
            "option_a": "Version control systems like Git alongside code reviews",
            "option_b": "Sharing zipped code over email without versioning",
            "option_c": "Directly modifying files on production servers",
            "option_d": "Avoiding version control completely",
            "correct_answer": "A",
            "difficulty": "Medium"
        }
    ]
    return templates[:num_questions]


def normalize_question_text(text):
    """Lowercase, strip whitespace/punctuation for duplicate comparison."""
    import re
    return re.sub(r'[^a-z0-9\s]', '', text.lower()).strip()