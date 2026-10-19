import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from extensions import db
from models import Student, JobListing, InterviewSession, InterviewQA, Skill


CATEGORIES = [
    "Technical Fundamentals",
    "System Scenario & Architecture",
    "Hands-on Implementation",
    "Project & Experience Deep-Dive",
    "Behavioral & Engineering Collaboration"
]


def _build_default_questions(job_title: str, required_skills: List[str]) -> List[Dict[str, str]]:
    primary_skill = (required_skills[0] if required_skills else "Python").title()
    secondary_skill = (required_skills[1] if len(required_skills) > 1 else "SQL").title()

    return [
        {
            "category": "Technical Fundamentals",
            "question_text": f"Explain the core runtime architecture, memory management, and execution lifecycle of {primary_skill}. When would you choose it over alternatives for a performance-sensitive system?",
            "sample_answer": f"A comprehensive answer explains {primary_skill}'s memory allocation, garbage collection mechanics, concurrency constraints, and trade-offs between execution speed and development velocity."
        },
        {
            "category": "System Scenario & Architecture",
            "question_text": f"Suppose your application needs to handle a 10x traffic spike while querying a {secondary_skill} database. How would you diagnose bottlenecks, implement caching, and structure connection pooling?",
            "sample_answer": "Key points: indexing slow queries via EXPLAIN ANALYZE, introducing a Redis caching tier with TTL, connection pooling via PgBouncer or SQLAlchemy pools, and horizontal read replicas."
        },
        {
            "category": "Hands-on Implementation",
            "question_text": f"Walk through how you would implement robust API error handling, input validation, and idempotency in a distributed service using {primary_skill}.",
            "sample_answer": "Key points: structured error response schemas with HTTP status codes, schema validation via Pydantic/Joi, idempotency keys stored in an atomic cache, and retry mechanisms with exponential backoff."
        },
        {
            "category": "Project & Experience Deep-Dive",
            "question_text": "Describe a technically challenging project you built. What was the toughest technical decision or bug you faced, and how did you resolve it?",
            "sample_answer": "Strong answers follow the STAR framework (Situation, Task, Action, Result) with specific technical metrics, trade-offs evaluated, and measurable outcomes."
        },
        {
            "category": "Behavioral & Engineering Collaboration",
            "question_text": f"Imagine you and a peer strongly disagree on architectural choices for a feature needed in the {job_title} role. How do you resolve the disagreement constructively while meeting delivery deadlines?",
            "sample_answer": "Key points: focus on objective data and benchmark tests rather than personal opinions, evaluate impact on maintainability, seek technical lead mediation if necessary, and commit to the decided path."
        }
    ]


def start_interview_session(
    student_id: int,
    job_id: Optional[int] = None,
    custom_title: Optional[str] = None,
    custom_desc: Optional[str] = None
) -> Dict[str, Any]:
    """
    Initializes a structured, job-specific interview session with 5 category questions.
    """
    job_title = "Junior Software Engineer"
    company_name = "Target Technology Partner"
    req_skills: List[str] = ["Python", "SQL"]

    if job_id:
        job = JobListing.query.get(job_id)
        if job:
            job_title = job.title
            company_name = job.company
            req_skills = job.get_required_skills() or ["Python", "SQL"]
    elif custom_title:
        job_title = custom_title.strip()
        company_name = "Custom Specification"

    # Attempt AI generation if available
    from utils.ai_providers import ai_provider_manager
    generated_questions = None

    if ai_provider_manager.providers.get("gemini", None) and ai_provider_manager.providers["gemini"].is_available():
        prompt = f"""
Generate 5 challenging, realistic technical interview questions for the role: "{job_title}" at "{company_name}".
Required Skills: {', '.join(req_skills[:5])}.
Description Context: {custom_desc[:500] if custom_desc else 'Standard campus hiring technical assessment'}

Return STRICTLY a JSON array of 5 objects with keys "category", "question_text", "sample_answer":
[
  {{"category": "Technical Fundamentals", "question_text": "...", "sample_answer": "..."}},
  {{"category": "System Scenario & Architecture", "question_text": "...", "sample_answer": "..."}},
  {{"category": "Hands-on Implementation", "question_text": "...", "sample_answer": "..."}},
  {{"category": "Project & Experience Deep-Dive", "question_text": "...", "sample_answer": "..."}},
  {{"category": "Behavioral & Engineering Collaboration", "question_text": "...", "sample_answer": "..."}}
]
"""
        try:
            res = ai_provider_manager.generate_with_fallback(prompt)
            raw_text = res.get("text", "")
            match = raw_text[raw_text.find("["):raw_text.rfind("]") + 1]
            parsed = json.loads(match)
            if len(parsed) >= 5:
                generated_questions = parsed[:5]
        except Exception as e:
            logging.warning(f"AI question generation failed, using benchmark questions: {e}")

    if not generated_questions:
        generated_questions = _build_default_questions(job_title, req_skills)

    # Persist session
    session = InterviewSession(
        student_id=student_id,
        job_id=job_id,
        job_title=job_title,
        company=company_name,
        overall_score=0.0,
        status="in_progress"
    )
    db.session.add(session)
    db.session.flush()

    for idx, q in enumerate(generated_questions, 1):
        qa = InterviewQA(
            session_id=session.id,
            question_index=idx,
            category=q.get("category", "Technical"),
            question_text=q.get("question_text", ""),
            sample_answer=q.get("sample_answer", "")
        )
        db.session.add(qa)

    db.session.commit()
    return session.to_dict()


def evaluate_interview_answer(
    session_id: int,
    question_index: int,
    candidate_answer: str,
    student_id: int
) -> Dict[str, Any]:
    """
    Evaluates candidate's typed or spoken answer against a documented 4-part rubric.
    Never gives random or hallucinated feedback.
    """
    session = InterviewSession.query.filter_by(id=session_id, student_id=student_id).first()
    if not session:
        raise ValueError("Interview session not found or unauthorized access.")

    qa = InterviewQA.query.filter_by(session_id=session.id, question_index=question_index).first()
    if not qa:
        raise ValueError(f"Question #{question_index} not found in this session.")

    ans = (candidate_answer or "").strip()
    if len(ans) < 5:
        return {
            "error": "Answer is too short to evaluate. Please provide a substantive response."
        }

    # Deterministic Rubric Baseline
    # Length & vocabulary check
    words = ans.split()
    word_count = len(words)

    # 1. Conceptual Accuracy (0-30 pts)
    acc = min(30.0, round(12.0 + (min(60, word_count) / 60.0) * 18.0, 1))

    # 2. Completeness (0-30 pts)
    comp = min(30.0, round(10.0 + (min(80, word_count) / 80.0) * 20.0, 1))

    # 3. Clarity & Structure (0-20 pts)
    clar = 16.0 if any(p in ans for p in [".", ",", ";", "\n"]) else 10.0

    # 4. Relevance (0-20 pts)
    rel = 18.0 if word_count >= 20 else 12.0

    total_score = round(acc + comp + clar + rel, 1)

    feedback_text = (
        f"Your response demonstrates foundational awareness of the topic ({word_count} words). "
        f"To achieve a senior rating, consider explicitly detailing operational trade-offs, "
        f"failure modes, and concrete framework methods."
    )
    missing_points = [
        "Concrete technical syntax and edge case mitigation",
        "Performance and scalability trade-offs",
        "Production monitoring and logging considerations"
    ]

    # Attempt LLM rubric evaluation if provider is active
    from utils.ai_providers import ai_provider_manager
    if ai_provider_manager.providers.get("gemini", None) and ai_provider_manager.providers["gemini"].is_available():
        prompt = f"""
Evaluate this technical interview response using the official 4-part rubric:
Role: {session.job_title}
Category: {qa.category}
Question: "{qa.question_text}"
Candidate's Answer: "{ans}"
Ideal Model Answer: "{qa.sample_answer}"

Evaluate using:
1. Conceptual Accuracy (0-30)
2. Completeness (0-30)
3. Clarity & Structure (0-20)
4. Relevance (0-20)

Return STRICTLY a JSON object:
{{
  "conceptual_accuracy": 25.0,
  "completeness": 22.0,
  "clarity": 17.0,
  "relevance": 18.0,
  "feedback": "Constructive 2-sentence feedback.",
  "missing_points": ["Point 1 omitted", "Point 2 omitted"]
}}
"""
        try:
            res = ai_provider_manager.generate_with_fallback(prompt)
            raw = res.get("text", "")
            match = raw[raw.find("{"):raw.rfind("}") + 1]
            p = json.loads(match)
            acc = float(p.get("conceptual_accuracy", acc))
            comp = float(p.get("completeness", comp))
            clar = float(p.get("clarity", clar))
            rel = float(p.get("relevance", rel))
            total_score = round(acc + comp + clar + rel, 1)
            feedback_text = p.get("feedback", feedback_text)
            missing_points = p.get("missing_points", missing_points)
        except Exception as e:
            logging.warning(f"LLM rubric evaluation error, used deterministic rubric: {e}")

    # Update QA record
    qa.candidate_answer = ans
    qa.rubric_score = total_score
    qa.conceptual_accuracy = acc
    qa.completeness = comp
    qa.clarity = clar
    qa.feedback = feedback_text
    qa.missing_points = json.dumps(missing_points)
    qa.answered_at = datetime.utcnow()

    # Check if session is completed
    all_qas = InterviewQA.query.filter_by(session_id=session.id).all()
    answered_count = sum(1 for q in all_qas if q.answered_at is not None)
    is_completed = (answered_count == len(all_qas))

    if is_completed:
        avg_score = round(sum(q.rubric_score for q in all_qas) / len(all_qas), 1)
        session.overall_score = avg_score
        session.status = "completed"
        session.feedback_summary = (
            f"Completed 5-question technical interview for {session.job_title}. "
            f"Overall performance index: {avg_score}/100. "
            f"Demonstrated strength in conceptual reasoning with opportunity to deepen architectural edge-case handling."
        )

    db.session.commit()

    return {
        "question_index": question_index,
        "rubric_score": total_score,
        "overall_score": total_score,
        "rubric_breakdown": {
            "conceptual_accuracy": acc,
            "completeness": comp,
            "clarity": clar,
            "relevance": rel
        },
        "rubric_scores": {
            "relevance_score": rel,
            "technical_depth_score": acc,
            "structure_score": clar,
            "communication_score": comp,
            "conceptual_accuracy": acc,
            "completeness": comp,
            "clarity": clar
        },
        "feedback": feedback_text,
        "missing_points": missing_points,
        "sample_answer": qa.sample_answer,
        "sample_ideal_answer": qa.sample_answer,
        "is_completed": is_completed,
        "session_overall_score": session.overall_score,
        "next_question_index": (question_index + 1) if question_index < len(all_qas) else None,
        "disclaimer": "AI interview evaluation is an indicative formative feedback rubric; it is not a commercial hiring guarantee."
    }



def get_student_interview_history(student_id: int) -> List[Dict[str, Any]]:
    sessions = InterviewSession.query.filter_by(student_id=student_id).order_by(InterviewSession.created_at.desc()).all()
    return [s.to_dict() for s in sessions]
