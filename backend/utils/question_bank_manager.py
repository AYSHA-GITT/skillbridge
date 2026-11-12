from extensions import db
from models import QuestionBank
from utils.ai_question_generator import generate_questions, normalize_question_text

MINIMUM_QUESTIONS_PER_SKILL = 30
MIN_QUESTIONS_TO_VERIFY = 5   # a skill cannot be verified from fewer distinct questions

_WEAK_OPTION = {"all of the above", "none of the above", "both a and b", "all of these", "none of these"}


def validate_generated_question(item):
    """Reject malformed AI output before it can ever be stored. Returns a reason or None."""
    if not isinstance(item, dict):
        return "not an object"
    q = (item.get("question") or "").strip()
    if len(q) < 15:
        return "question too short"
    opts = [(item.get(f"option_{k}") or "").strip() for k in "abcd"]
    if any(not o for o in opts):
        return "missing option"
    if len({o.lower() for o in opts}) < 4:
        return "duplicate options"
    if any(o.lower().rstrip(".") in _WEAK_OPTION for o in opts):
        return "uses all/none-of-the-above"
    key = (item.get("correct_answer") or "").strip().upper()[:1]
    if key not in ("A", "B", "C", "D"):
        return "invalid answer key"
    if (item.get("difficulty") or "Medium").title() not in ("Easy", "Medium", "Hard"):
        return "invalid difficulty"
    return None


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
    num_to_gen = min(missing_count, 10)

    # Build a set of normalized existing question texts for
    # fast duplicate lookup
    existing_normalized = {
        normalize_question_text(q.question) for q in existing_questions
    }

    generated = generate_questions(skill_name, num_questions=num_to_gen)

    if not generated:
        # Gemini failed — return what we have, don't crash the caller
        return current_count

    added_count = 0

    import logging
    for item in generated:
        reason = validate_generated_question(item)
        if reason:
            logging.warning("Rejected generated question for %s: %s", skill_name, reason)
            continue
        question_text = item.get("question", "").strip()

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
            difficulty=(item.get("difficulty") or "Medium").title()
        )
        db.session.add(new_question)

        existing_normalized.add(normalized)  # prevent dupes within this same batch too
        added_count += 1

    db.session.commit()

    return current_count + added_count