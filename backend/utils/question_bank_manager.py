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


def _curated_for(skill_name=None):
    from data.curated_questions import CURATED_QUESTIONS
    if skill_name is None:
        return list(CURATED_QUESTIONS)
    key = (skill_name or "").strip().lower()
    return [q for q in CURATED_QUESTIONS if q["skill_name"] == key]


def seed_curated_questions(skill_name=None):
    """
    Insert the reviewed questions from data/curated_questions.py that are not
    in the bank yet (for one skill, or every curated skill). Idempotent: a
    question whose normalized text already exists for that skill is skipped,
    and every question is validated with the same rules as AI output.
    Returns the number of rows added.
    """
    import logging
    items = _curated_for(skill_name)
    if not items:
        return 0
    skills = {q["skill_name"] for q in items}
    existing = {}
    for row in QuestionBank.query.filter(QuestionBank.skill_name.in_(skills)).all():
        existing.setdefault(row.skill_name, set()).add(normalize_question_text(row.question))
    added = 0
    for item in items:
        reason = validate_generated_question(item)
        if reason:
            logging.warning("Curated question rejected for %s: %s", item["skill_name"], reason)
            continue
        norm = normalize_question_text(item["question"])
        if norm in existing.setdefault(item["skill_name"], set()):
            continue
        db.session.add(QuestionBank(
            skill_name=item["skill_name"], question=item["question"].strip(),
            option_a=item["option_a"], option_b=item["option_b"],
            option_c=item["option_c"], option_d=item["option_d"],
            correct_answer=item["correct_answer"].upper()[:1],
            difficulty=item["difficulty"].title(),
        ))
        existing[item["skill_name"]].add(norm)
        added += 1
    if added:
        db.session.commit()
    return added


def curated_coverage():
    """Per-skill question counts in the bank (total / by difficulty) for every curated
    skill plus every skill a career requires - shows what can and cannot be verified."""
    from data.career_requirements import CAREER_REQUIREMENTS
    skills = {q["skill_name"] for q in _curated_for()}
    for req in CAREER_REQUIREMENTS.values():
        skills |= {s.lower() for s in req.get("required", [])}
    out = {}
    for skill in sorted(skills):
        rows = QuestionBank.query.filter_by(skill_name=skill).all()
        by_level = {}
        for r in rows:
            lvl = (r.difficulty or "Medium").title()
            by_level[lvl] = by_level.get(lvl, 0) + 1
        out[skill] = {"total": len(rows), "by_difficulty": by_level,
                      "verifiable": len(rows) >= MIN_QUESTIONS_TO_VERIFY}
    return out


def ensure_minimum_questions(skill_name):
    """
    Ensures QuestionBank has at least MINIMUM_QUESTIONS_PER_SKILL
    questions for the given skill. Curated (hand-reviewed) questions for the
    skill are inserted first if missing; only then is the remaining gap
    generated via the AI provider (duplicates skipped, saved permanently).

    Returns the current total question count for this skill after
    top-up (whether or not generation was needed).
    """
    try:
        seed_curated_questions(skill_name)
    except Exception as e:  # curated data must never break quiz loading
        import logging
        logging.warning("Could not seed curated questions for %s: %s", skill_name, e)
        db.session.rollback()

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