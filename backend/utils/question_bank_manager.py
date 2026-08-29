from extensions import db
from models import QuestionBank
from utils.ai_question_generator import generate_questions, normalize_question_text

MINIMUM_QUESTIONS_PER_SKILL = 30


def ensure_minimum_questions(skill_name):
    """
    Ensures QuestionBank has at least MINIMUM_QUESTIONS_PER_SKILL
    questions for the given skill. Generates only the missing amount
    via Gemini, skips duplicates, and saves permanently.

    Returns the current total question count for this skill after
    top-up (whether or not generation was needed).
    """
    existing_questions = QuestionBank.query.filter_by(
        skill_name=skill_name
    ).all()

    current_count = len(existing_questions)

    if current_count >= MINIMUM_QUESTIONS_PER_SKILL:
        return current_count

    missing_count = MINIMUM_QUESTIONS_PER_SKILL - current_count

    # Build a set of normalized existing question texts for
    # fast duplicate lookup
    existing_normalized = {
        normalize_question_text(q.question) for q in existing_questions
    }

    generated = generate_questions(skill_name, num_questions=missing_count)

    if not generated:
        # Gemini failed — return what we have, don't crash the caller
        return current_count

    added_count = 0

    for item in generated:
        question_text = item.get("question", "").strip()
        if not question_text:
            continue

        normalized = normalize_question_text(question_text)

        if normalized in existing_normalized:
            continue  # skip duplicate, don't insert

        correct_answer = item.get("correct_answer", "").strip().upper()[:1]

        new_question = QuestionBank(
            skill_name=skill_name,
            question=question_text,
            option_a=item.get("option_a"),
            option_b=item.get("option_b"),
            option_c=item.get("option_c"),
            option_d=item.get("option_d"),
            correct_answer=correct_answer,
            difficulty=item.get("difficulty", "Medium")
        )
        db.session.add(new_question)

        existing_normalized.add(normalized)  # prevent dupes within this same batch too
        added_count += 1

    db.session.commit()

    return current_count + added_count