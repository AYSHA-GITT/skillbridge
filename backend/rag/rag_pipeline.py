import os
import logging
import json
from typing import Optional, List, Dict, Any
from .knowledge_manager import get_knowledge_manager
from .embedding_engine import get_embedding_engine
try:
    from utils.skill_extractor import extract_skills
except ImportError:
    from backend.utils.skill_extractor import extract_skills

logger = logging.getLogger(__name__)

class RAGPipeline:
    """
    Retrieval-Augmented Generation (RAG) Orchestrator for SkillBridge.
    Blends SentenceTransformer semantic retrieval, deterministic NLP extraction,
    and grounded Gemini generative synthesis.
    """

    _instance = None

    def __init__(self, base_dir: Optional[str] = None):
        self.km = get_knowledge_manager(base_dir)
        self.embedding_engine = get_embedding_engine()

    @classmethod
    def get_instance(cls, base_dir: Optional[str] = None):
        if cls._instance is None:
            cls._instance = cls(base_dir)
        return cls._instance

    def _get_gemini_client(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return None
        try:
            from google import genai
            return genai.Client(api_key=api_key)
        except Exception as e:
            logger.warning(f"Could not initialize Google GenAI Client: {e}")
            return None

    def analyze_resume_rag(
        self,
        resume_text: str,
        target_career: Optional[str] = None,
        top_k: int = 4
    ) -> Dict[str, Any]:
        """
        Runs complete RAG analysis on resume text:
        1. Semantic retrieval of matched careers, benchmark JDs, and skill definitions.
        2. Rule-based explicit skill extraction with textual evidence.
        3. Segregation of explicit vs. inferred vs. missing skills without hallucination.
        4. Grounded generative assessment with source citations.
        """
        if not resume_text or not resume_text.strip():
            return {
                "error": "Empty resume text provided",
                "semantic_match_score": 0.0,
                "explicit_skills": [],
                "inferred_skills": [],
                "missing_skills": [],
                "retrieved_context": [],
                "explanation": "No resume text was provided for analysis."
            }

        # 1. Deterministic NLP extraction (Ground Truth Evidence)
        extracted_rule_skills = extract_skills(resume_text)
        explicit_skills_map = {item['skill_name'].lower().strip(): item['extraction_confidence'] for item in extracted_rule_skills}
        explicit_skill_names = set(explicit_skills_map.keys())

        # 2. Semantic retrieval against knowledge base
        # Search using resume summary / primary technical content
        resume_snippet = resume_text[:1500]
        retrieved_docs = self.km.search(resume_snippet, top_k=top_k, min_score=0.20)

        # If a specific target career was requested, guarantee its benchmark is included
        target_benchmark = None
        if target_career:
            target_benchmark = self.km.get_career_benchmark(target_career)
            if target_benchmark and not any(d.get('chunk_id') == target_benchmark.get('chunk_id') for d in retrieved_docs):
                retrieved_docs.insert(0, target_benchmark)

        # 3. Identify best matching career & relevant job postings
        matched_careers = []
        matched_jobs = []
        target_req_skills = set()
        target_nice_skills = set()

        for doc in retrieved_docs:
            if doc.get('type') in ('career_benchmark', 'career_requirements'):
                matched_careers.append({
                    "career": doc.get('career'),
                    "title": doc.get('title'),
                    "domain": doc.get('domain'),
                    "similarity_score": doc.get('score', 0.0),
                    "source": doc.get('source'),
                    "required_skills": doc.get('required_skills', [])
                })
                target_req_skills.update(s.lower() for s in doc.get('required_skills', []))
                target_nice_skills.update(s.lower() for s in doc.get('nice_to_have_skills', []))
            elif doc.get('type') == 'job_description':
                matched_jobs.append({
                    "role": doc.get('role'),
                    "company": doc.get('company'),
                    "location": doc.get('location'),
                    "salary_range": doc.get('salary_range'),
                    "similarity_score": doc.get('score', 0.0),
                    "source": doc.get('source'),
                    "required_skills": doc.get('required_skills', [])
                })
                target_req_skills.update(s.lower() for s in doc.get('required_skills', []))

        # Default career if none retrieved
        effective_career = target_career or (matched_careers[0]['career'] if matched_careers else "software engineer")
        top_match_score = retrieved_docs[0].get('score', 0.5) if retrieved_docs else 0.5

        # 4. Strict segregation: Explicit vs Inferred vs Missing
        explicit_list = [
            {
                "skill_name": s,
                "confidence": explicit_skills_map[s],
                "status": "explicitly_supported",
                "evidence": f"Mentioned in resume with {int(explicit_skills_map[s]*100)}% section confidence"
            }
            for s in sorted(explicit_skill_names)
        ]

        # Inferred: Required by matched roles or knowledge base, connected to candidate's domain, but NOT in resume
        missing_required = sorted(list(target_req_skills - explicit_skill_names))
        missing_nice = sorted(list(target_nice_skills - explicit_skill_names))

        # Inferred domain competencies (associated skills with partial context)
        inferred_list = [
            {
                "skill_name": s,
                "status": "inferred_need",
                "relevance": "Industry standard for matched roles",
                "verification_required": True
            }
            for s in missing_nice[:5]
        ]

        # 5. Calculate semantic match percentage
        # Combine cosine similarity (40%) and explicit skill coverage (60%)
        req_coverage = (len(target_req_skills & explicit_skill_names) / len(target_req_skills)) if target_req_skills else 0.5
        composite_score = round(((top_match_score * 0.4) + (req_coverage * 0.6)) * 100, 1)

        # 6. Grounded Gemini synthesis citing retrieved context
        explanation = self._synthesize_rag_explanation(
            resume_text=resume_snippet,
            career_name=effective_career,
            explicit_skills=sorted(list(explicit_skill_names)),
            missing_skills=missing_required,
            retrieved_docs=retrieved_docs,
            match_score=composite_score
        )

        return {
            "target_career": effective_career,
            "semantic_match_score": composite_score,
            "cosine_similarity": round(float(top_match_score), 4),
            "explicit_skills": explicit_list,
            "inferred_skills": inferred_list,
            "missing_skills": missing_required,
            "missing_nice_to_have": missing_nice,
            "matched_careers": matched_careers,
            "matched_job_postings": matched_jobs,
            "retrieved_sources": [
                {
                    "title": d.get('title'),
                    "type": d.get('type'),
                    "source": d.get('source'),
                    "score": d.get('score')
                }
                for d in retrieved_docs
            ],
            "explanation": explanation
        }

    def match_job_rag(
        self,
        resume_text: str,
        job_description_text: str,
        student_skills: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Evaluates a candidate's resume/skills against a custom or specific job posting.
        """
        if not job_description_text or not job_description_text.strip():
            return {"error": "Job description cannot be empty"}

        # Extract skills from JD
        jd_skills_raw = extract_skills(job_description_text)
        jd_skill_names = set(item['skill_name'].lower().strip() for item in jd_skills_raw)

        # Extract skills from resume
        if student_skills is not None:
            candidate_skills = set(s.lower().strip() for s in student_skills)
        else:
            cand_extracted = extract_skills(resume_text or "")
            candidate_skills = set(item['skill_name'].lower().strip() for item in cand_extracted)

        # Compute semantic similarity via Sentence Transformers
        emb_resume = self.embedding_engine.encode(resume_text[:1200] if resume_text else " ".join(candidate_skills), normalize=True)
        emb_jd = self.embedding_engine.encode(job_description_text[:1200], normalize=True)
        cosine_sim = float(round(float(sum(emb_resume * emb_jd)), 4)) if len(emb_resume) and len(emb_jd) else 0.5
        cosine_sim = max(0.0, min(1.0, cosine_sim))

        # Skill overlap
        matched_skills = sorted(list(jd_skill_names & candidate_skills))
        missing_skills = sorted(list(jd_skill_names - candidate_skills))

        skill_coverage = (len(matched_skills) / len(jd_skill_names)) if jd_skill_names else cosine_sim
        overall_match_pct = round(((cosine_sim * 0.45) + (skill_coverage * 0.55)) * 100, 1)

        # Semantic retrieval to find similar benchmark standards
        benchmarks = self.km.search(job_description_text[:500], top_k=2, min_score=0.25)
        source_citations = [b.get('source') for b in benchmarks if b.get('source')]

        # Grounded generative synthesis
        advice = self._synthesize_job_match_advice(
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            match_pct=overall_match_pct,
            jd_snippet=job_description_text[:400],
            citations=source_citations
        )

        return {
            "overall_match_percent": overall_match_pct,
            "semantic_similarity_score": round(cosine_sim, 3),
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "total_jd_skills_detected": len(jd_skill_names),
            "citations": source_citations,
            "actionable_advice": advice
        }

    def explain_skill_gap_rag(
        self,
        student_verified_skills: List[str],
        career_name: str
    ) -> Dict[str, Any]:
        """
        Produces an explainable skill gap report grounded in authoritative benchmark requirements.
        """
        benchmark = self.km.get_career_benchmark(career_name)
        if not benchmark:
            from data.career_requirements import CAREER_REQUIREMENTS
            norm = career_name.strip().lower()
            reqs = CAREER_REQUIREMENTS.get(norm, {"required": ["python", "sql", "git"], "nice_to_have": ["docker"]})
            benchmark = {
                "title": career_name.title(),
                "career": norm,
                "required_skills": reqs.get("required", []),
                "nice_to_have_skills": reqs.get("nice_to_have", []),
                "source": "SkillBridge Curated Benchmark"
            }

        verified_lower = set(s.lower().strip() for s in student_verified_skills)
        required = benchmark.get("required_skills", [])
        nice = benchmark.get("nice_to_have_skills", [])

        missing_required = [s for s in required if s.lower() not in verified_lower]
        matched_required = [s for s in required if s.lower() in verified_lower]

        req_cov = (len(matched_required) / len(required)) if required else 1.0
        readiness_est = round(req_cov * 100, 1)

        # Retrieve relevant job descriptions for this role
        related_jds = self.km.search(f"{career_name} job requirements", top_k=2, doc_type="job_description")

        # Grounded synthesis
        explanation = self._synthesize_gap_explanation(
            career_name=career_name,
            matched=matched_required,
            missing=missing_required,
            readiness_pct=readiness_est,
            source=str(benchmark.get("source") or "Industry Knowledge Base"),
            related_jds=related_jds
        )

        return {
            "career": career_name,
            "benchmark_source": benchmark.get("source"),
            "readiness_estimate_percent": readiness_est,
            "matched_required_skills": matched_required,
            "missing_required_skills": missing_required,
            "nice_to_have_skills": nice,
            "related_postings_sample": [
                {
                    "company": jd.get("company"),
                    "role": jd.get("role"),
                    "salary_range": jd.get("salary_range"),
                    "source": jd.get("source")
                }
                for jd in related_jds
            ],
            "grounded_explanation": explanation
        }

    # =========================================================================
    # GROUNDED GENERATIVE SYNTHESIS (WITH DETERMINISTIC FALLBACK)
    # =========================================================================

    def _synthesize_rag_explanation(
        self,
        resume_text: str,
        career_name: str,
        explicit_skills: List[str],
        missing_skills: List[str],
        retrieved_docs: List[dict],
        match_score: float
    ) -> str:
        client = self._get_gemini_client()
        context_blocks = []
        for i, doc in enumerate(retrieved_docs[:3], 1):
            context_blocks.append(f"[{i}] {doc.get('title')} (Source: {doc.get('source')}):\n{doc.get('text')}")
        context_str = "\n\n".join(context_blocks)

        prompt = f"""
You are the SkillLens RAG Career Evaluator.
Analyze the candidate's resume match against the target career '{career_name.title()}'.

CRITICAL CONSTRAINTS:
1. Base your statements strictly on the retrieved industry context and explicit resume skills below.
2. Never invent qualifications, projects, certifications, or work experience that do not exist in the resume.
3. Explicitly reference the retrieved sources (e.g. "[Source: ...]").
4. Distinguish between skills proven by resume evidence and missing/inferred requirements.

RETRIEVED INDUSTRY BENCHMARK CONTEXT:
{context_str}

CANDIDATE FACTS:
- Target Career: {career_name.title()}
- Overall Composite Match: {match_score}%
- Explicit Skills with Resume Evidence: {', '.join(explicit_skills) if explicit_skills else 'None detected'}
- Missing Industry Requirements: {', '.join(missing_skills[:5]) if missing_skills else 'None'}

Provide a concise, 3-paragraph executive summary:
Paragraph 1: Assessment of candidate's proven strengths with specific resume evidence.
Paragraph 2: Analysis of critical missing requirements referencing the industry benchmark sources.
Paragraph 3: Exact 2-3 step priority action plan to bridge the gap.
"""

        if client:
            for model_name in ["gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.6-flash"]:
                try:
                    resp = client.models.generate_content(model=model_name, contents=prompt)
                    if resp.text and len(resp.text.strip()) > 30:
                        return resp.text.strip()
                except Exception as e:
                    logger.warning(f"Gemini RAG synthesis error with {model_name}: {e}")

        # Deterministic Grounded Fallback
        top_source = retrieved_docs[0].get('source', 'Industry Career Benchmark 2026') if retrieved_docs else 'SkillBridge Benchmark'
        skills_str = ", ".join(s.title() for s in explicit_skills[:4]) if explicit_skills else "fundamental abilities"
        missing_str = ", ".join(s.title() for s in missing_skills[:3]) if missing_skills else "advanced deployment tools"

        return (
            f"**Candidate Strengths & Evidence**: The resume demonstrates verified competence in {skills_str}, "
            f"aligning with baseline standards for {career_name.title()} (Match Score: {match_score}%).\n\n"
            f"**Industry Benchmark Gaps**: According to {top_source}, candidates entering this track are expected "
            f"to demonstrate proven capabilities in {missing_str}. These competencies were not supported by direct textual evidence in the submitted resume.\n\n"
            f"**Action Plan**: Prioritize mastering {missing_skills[0].title() if missing_skills else 'system design'} "
            f"and verify it through the adaptive technical quiz to substantially boost your career readiness profile."
        )

    def _synthesize_job_match_advice(
        self,
        matched_skills: List[str],
        missing_skills: List[str],
        match_pct: float,
        jd_snippet: str,
        citations: List[str]
    ) -> str:
        client = self._get_gemini_client()
        citation_str = ", ".join(citations) if citations else "Enterprise Hiring Standards"

        prompt = f"""
You are the SkillLens Job Match Advisor.
Advise a candidate whose profile was matched against a job description.
Overall Match: {match_pct}%.
Matched Skills: {', '.join(matched_skills) if matched_skills else 'None'}
Missing Requirements: {', '.join(missing_skills) if missing_skills else 'None'}
Benchmark Citation: {citation_str}
Job Description Excerpt: {jd_snippet}

Write 2 crisp, actionable paragraphs:
1. Candid evaluation of how ready the candidate is for this role.
2. Concrete interview talking points for their matched skills and a fast preparation roadmap for their missing skills.
"""
        if client:
            for model_name in ["gemini-3.5-flash", "gemini-3.5-flash-lite"]:
                try:
                    resp = client.models.generate_content(model=model_name, contents=prompt)
                    if resp.text and len(resp.text.strip()) > 20:
                        return resp.text.strip()
                except Exception as e:
                    logger.warning(f"Job match Gemini synthesis error: {e}")

        matched_str = ", ".join(s.title() for s in matched_skills[:3]) if matched_skills else "general profile background"
        missing_str = ", ".join(s.title() for s in missing_skills[:3]) if missing_skills else "niche toolsets"
        return (
            f"You match **{match_pct}%** of the technical qualifications specified in this posting (Benchmark: {citation_str}). "
            f"Your strongest assets for this interview are your verified competencies in **{matched_str}**.\n\n"
            f"To maximize your interview conversion rate, be prepared to address the employer's need for **{missing_str}** by building a hands-on GitHub project demonstrating these tools."
        )

    def _synthesize_gap_explanation(
        self,
        career_name: str,
        matched: List[str],
        missing: List[str],
        readiness_pct: float,
        source: str,
        related_jds: List[dict]
    ) -> str:
        client = self._get_gemini_client()
        jd_examples = "; ".join(f"{jd.get('role')} at {jd.get('company')} ({jd.get('salary_range')})" for jd in related_jds)

        prompt = f"""
Explain the skill gap for a student preparing for '{career_name.title()}' (Estimated Readiness: {readiness_pct}%).
Verified Competencies: {', '.join(matched) if matched else 'None'}
Missing Core Requirements: {', '.join(missing) if missing else 'None'}
Source Standard: {source}
Current Hiring Benchmarks: {jd_examples}

Write a direct 2-paragraph career guidance summary grounded strictly in the provided sources:
1. Explain why the missing competencies ({', '.join(missing[:3])}) are critical prerequisites for hiring.
2. Reference the current market expectations from {source} and the projected career return on investment.
"""
        if client:
            for model_name in ["gemini-3.5-flash", "gemini-3.5-flash-lite"]:
                try:
                    resp = client.models.generate_content(model=model_name, contents=prompt)
                    if resp.text and len(resp.text.strip()) > 20:
                        return resp.text.strip()
                except Exception as e:
                    logger.warning(f"Skill gap Gemini synthesis error: {e}")

        missing_str = ", ".join(s.title() for s in missing[:3]) if missing else "specialized domain tools"
        return (
            f"Based on **{source}**, candidate readiness for **{career_name.title()}** currently stands at **{readiness_pct}%**. "
            f"The primary bottleneck is the absence of verified competence in **{missing_str}**, which are standard prerequisites across current market postings ({jd_examples or 'industry benchmarks'}).\n\n"
            f"Targeting these specific missing skills will directly close your gap, elevate your profile into the High-Readiness tier, and qualify you for entry-level compensation brackets."
        )


def get_rag_pipeline(base_dir: Optional[str] = None) -> RAGPipeline:
    return RAGPipeline.get_instance(base_dir)
