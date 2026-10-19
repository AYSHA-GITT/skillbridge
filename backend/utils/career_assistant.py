import os
import logging
from dotenv import load_dotenv

load_dotenv()

client = None

def get_genai_client():
    global client
    if client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            try:
                from google import genai
                client = genai.Client(api_key=api_key)
            except Exception as e:
                logging.warning(f"Could not initialize Google GenAI: {e}")
                client = None
    return client


def generate_fallback_answer(profile, question):
    """
    Deterministic rule-based advisor answering strictly from profile facts
    if Gemini is unavailable, rate-limited, or quota-exhausted.
    """
    q = question.lower()
    target_career = profile.get("target_career") or "your target career"
    readiness = profile.get("readiness_score") or 0.0
    verified = profile.get("verified_skills") or []
    missing = profile.get("missing_skills") or []
    top_missing = missing[0] if missing else "a specialized skill"
    top_career = profile.get("top_recommended_career") or target_career
    top_match = profile.get("top_career_match_percent") or readiness
    salary = profile.get("predicted_salary_lpa") or 6.0

    if any(k in q for k in ["next", "first", "start", "what to learn"]):
        if missing:
            return (
                f"Based on your target career '{target_career.title()}', your highest priority skill to learn next is "
                f"**{top_missing.title()}**. Verifying this will give you the most direct boost to your readiness score (currently {readiness}%)."
            )
        return (
            f"You have verified all core required competencies for {target_career.title()}! "
            f"You can now focus on nice-to-have technologies like Cloud deployment or Docker to maximize your profile."
        )

    if any(k in q for k in ["why", "recommended", "recommendation"]):
        verified_str = ", ".join(s.title() for s in verified[:3]) if verified else "your active skills"
        return (
            f"**{top_career.title()}** was recommended as your top career track ({top_match}% match) because your "
            f"verified competencies ({verified_str}) strongly overlap with this role's industry standard. "
            f"Addressing your gap in **{top_missing.title()}** will push your readiness even higher."
        )

    if any(k in q for k in ["gap", "biggest gap", "missing", "weakness"]):
        if missing:
            missing_str = ", ".join(s.title() for s in missing[:3])
            return (
                f"Your primary skill gap for {target_career.title()} is **{top_missing.title()}**. "
                f"Your full list of missing required skills is: {missing_str}. "
                f"Check your learning roadmap for a day-by-day plan to address these."
            )
        return f"You currently have no unverified required skill gaps for {target_career.title()}."

    if any(k in q for k in ["salary", "earn", "lpa", "money", "pay"]):
        return (
            f"Your current skill set qualifies you for an estimated market compensation of **₹{salary} LPA**. "
            f"In our Salary Simulator, adding high-demand technologies like Docker or Cloud (AWS) can provide an incremental boost of +₹1.5 to ₹3.0 LPA."
        )

    if any(k in q for k in ["prepare", "readiness", "improve", "how to"]):
        return (
            f"To improve your readiness for {target_career.title()} (currently at {readiness}%): "
            f"1) Follow your generated learning roadmap targeting {top_missing.title()}; "
            f"2) Take the verification quiz in the Assessments tab once prepared; "
            f"3) Track your progress milestones to unlock achievement badges."
        )

    # General grounded response
    return (
        f"For your target track ({target_career.title()} · {readiness}% readiness), "
        f"your verified competencies are [{', '.join(s.title() for s in verified[:4]) if verified else 'None yet'}] and "
        f"your key remaining gap is **{top_missing.title()}**. "
        f"Follow your learning roadmap and complete verification quizzes to prove competency."
    )


def ask_career_assistant(profile, question, student_id=None, selected_job_id=None):
    """
    Answers student questions using genuine RAG retrieval when student context is available,
    or falls back to the deterministic profile-grounded rule engine.
    """
    sid = student_id or profile.get("student_id")
    target_career = profile.get("target_career") or "Unspecified"
    readiness = profile.get("readiness_score") or 0.0
    missing = profile.get("missing_skills") or []

    # Attempt genuine RAG retrieval pipeline first
    if sid:
        try:
            from utils.rag_engine import rag_engine
            rag_res = rag_engine.ask(
                question=question,
                student_id=int(sid),
                student_profile=profile,
                selected_job_id=selected_job_id
            )
            return {
                "answer": rag_res["answer"],
                "source": f"RAG ({rag_res.get('provider', 'AI')})",
                "is_rag": True,
                "empty_retrieval": rag_res.get("empty_retrieval", False),
                "citations": rag_res.get("citations", []),
                "retrieved_sources": rag_res.get("retrieved_sources", []),
                "provider": rag_res.get("provider"),
                "model": rag_res.get("model"),
                "grounded_on": {
                    "target_career": target_career,
                    "readiness_score": readiness,
                    "top_missing_skill": missing[0] if missing else None
                }
            }
        except Exception as e:
            logging.warning(f"RAG execution failed, falling back to grounded rule engine: {e}")

    # Retrieve RAG context from knowledge base
    rag_context_str = ""
    citations = []
    try:
        from rag.knowledge_manager import get_knowledge_manager
        km = get_knowledge_manager()
        retrieved_chunks = km.search(f"{target_career} {question}", top_k=2, min_score=0.20)
        if retrieved_chunks:
            rag_parts = []
            for c in retrieved_chunks:
                source_label = c.get('source', 'Industry Knowledge Base')
                citations.append(source_label)
                rag_parts.append(f"• From {source_label}:\n  {c.get('text')}")
            rag_context_str = "\nRETRIEVED INDUSTRY BENCHMARK CONTEXT:\n" + "\n".join(rag_parts) + "\n"
    except Exception as e:
        logging.warning(f"RAG context retrieval in career assistant skipped: {e}")

    prompt = f"""
You are the SkillBridge Career Assistant, an expert, encouraging, concise career advisor.
You MUST answer the student's question strictly grounded on the factual profile data and retrieved industry benchmarks provided below.
DO NOT hallucinate skills, scores, or careers not present in the profile.

STUDENT PROFILE DATA:
- Target Career: {target_career}
- Current Readiness Score: {readiness}%
- Verified Skills (Proven via assessment): {', '.join(verified) if verified else 'None yet'}
- Missing Required Skills (Gaps): {', '.join(missing) if missing else 'None (All core verified)'}
- Estimated Salary: {salary} LPA
- Top Recommended Career: {top_career} ({top_match}% match)
{rag_context_str}
STUDENT QUESTION:
"{question}"

INSTRUCTIONS:
- Keep the answer between 2 to 4 sentences.
- Be concrete, actionable, and reference their actual skills and target career.
- Format key skill names or metrics in bold.
- If relevant, cite the industry benchmark source.
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
                if text:
                    return {
                        "answer": text,
                        "source": "Gemini 3.6 Flash (RAG Grounded)",
                        "is_rag": True,
                        "citations": citations,
                        "retrieved_sources": citations,
                        "grounded_on": {
                            "target_career": target_career,
                            "readiness_score": readiness,
                            "top_missing_skill": missing[0] if missing else None
                        }
                    }
            except Exception as e:
                logging.warning(f"Assistant LLM call failed on {model_name}: {e}")

    # Fallback to deterministic grounded generator
    fallback_text = generate_fallback_answer(profile, question)
    return {
        "answer": fallback_text,
        "source": "Grounded Career Engine (Deterministic)",
        "is_rag": False,
        "empty_retrieval": False,
        "citations": citations if citations else [],
        "retrieved_sources": ["Student Verified Skill Profile"],
        "grounded_on": {
            "target_career": target_career,
            "readiness_score": readiness,
            "top_missing_skill": missing[0] if missing else None
        }
    }

