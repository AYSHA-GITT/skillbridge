import re
import hashlib
from typing import List, Dict, Any, Optional
import numpy as np


class DocumentChunk:
    def __init__(
        self,
        chunk_id: str,
        document_id: str,
        title: str,
        source_type: str,
        text: str,
        user_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.chunk_id = chunk_id
        self.document_id = document_id
        self.title = title
        self.source_type = source_type  # 'career_guide', 'job_description', 'user_profile', 'learning_resource'
        self.text = text
        self.user_id = user_id  # None for public documents; student_id for private documents
        self.metadata = metadata or {}
        self.embedding: Optional[np.ndarray] = None


class DeterministicEmbeddingEngine:
    """
    High-performance, pure-Python/NumPy dense embedding engine.
    Computes normalized 128-dimensional term-frequency and subword hash projection.
    Provides robust, deterministic semantic and keyword matching without requiring
    external model downloads or unstable C++ extensions on Windows.
    """

    DIM = 128

    def embed_text(self, text: str) -> np.ndarray:
        vec = np.zeros(self.DIM, dtype=np.float32)
        words = re.findall(r'\b[a-zA-Z0-9_\-\+\#\.]+\b', text.lower())
        if not words:
            return vec

        for word in words:
            # Word-level hash bin
            h = int(hashlib.md5(word.encode('utf-8')).hexdigest(), 16)
            idx = h % self.DIM
            sign = 1.0 if ((h >> 8) & 1) else -1.0
            vec[idx] += sign

            # Character 3-gram subword hashing for typo and inflection tolerance
            if len(word) >= 3:
                for i in range(len(word) - 2):
                    sub = word[i:i+3]
                    sh = int(hashlib.md5(sub.encode('utf-8')).hexdigest()[:8], 16)
                    s_idx = sh % self.DIM
                    s_sign = 0.5 if (sh & 1) else -0.5
                    vec[s_idx] += s_sign

        norm = np.linalg.norm(vec)
        if norm > 1e-7:
            vec /= norm
        return vec


class LocalVectorStore:
    """
    In-memory vector store enforcing strict tenant isolation.
    Guarantees user A can never retrieve documents belonging to user B.
    """

    def __init__(self):
        self.chunks: List[DocumentChunk] = []
        self.embedder = DeterministicEmbeddingEngine()

    def add_document(
        self,
        document_id: str,
        title: str,
        source_type: str,
        text: str,
        user_id: Optional[int] = None,
        chunk_size: int = 400,
        chunk_overlap: int = 80,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Splits text into overlapping chunks, computes dense embeddings, and stores them.
        """
        # Clean text
        cleaned = re.sub(r'\s+', ' ', text).strip()
        if not cleaned:
            return 0

        # Remove existing chunks for this document_id to allow clean updates
        self.chunks = [c for c in self.chunks if c.document_id != document_id]

        # Chunking
        words = cleaned.split(' ')
        chunk_count = 0
        step = max(1, chunk_size - chunk_overlap)

        for i in range(0, len(words), step):
            chunk_words = words[i:i + chunk_size]
            chunk_text = ' '.join(chunk_words).strip()
            if len(chunk_text) < 15:
                continue

            cid = f"{document_id}_chk_{chunk_count}"
            chunk = DocumentChunk(
                chunk_id=cid,
                document_id=document_id,
                title=title,
                source_type=source_type,
                text=chunk_text,
                user_id=user_id,
                metadata=metadata
            )
            chunk.embedding = self.embedder.embed_text(chunk_text)
            self.chunks.append(chunk)
            chunk_count += 1

        return chunk_count

    def search(
        self,
        query: str,
        requesting_user_id: Optional[int],
        top_k: int = 4,
        similarity_threshold: float = 0.22,
        source_type_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieves top-k relevant chunks respecting user access control.
        """
        query_vec = self.embedder.embed_text(query)
        if np.linalg.norm(query_vec) < 1e-7:
            return []

        candidates = []
        for chunk in self.chunks:
            # STRICT ACCESS CONTROL:
            # A chunk is ONLY accessible if it is public (user_id is None)
            # OR belongs strictly to the requesting user.
            if chunk.user_id is not None and chunk.user_id != requesting_user_id:
                continue

            if source_type_filter and chunk.source_type != source_type_filter:
                continue

            if chunk.embedding is None:
                continue

            similarity = float(np.dot(query_vec, chunk.embedding))
            if similarity >= similarity_threshold:
                candidates.append((similarity, chunk))

        # Sort descending by similarity
        candidates.sort(key=lambda x: x[0], reverse=True)

        results = []
        for rank, (score, chunk) in enumerate(candidates[:top_k], 1):
            results.append({
                "citation_tag": f"[Source {rank}: {chunk.title}]",
                "similarity_score": round(score, 3),
                "title": chunk.title,
                "source_type": chunk.source_type,
                "document_id": chunk.document_id,
                "text": chunk.text,
                "is_user_private": chunk.user_id is not None,
                "metadata": chunk.metadata
            })

        return results


class RAGCareerOrchestrator:
    """
    End-to-end RAG orchestrator for grounded career advisory.
    Integrates knowledge ingestion, retrieval, prompt synthesis, and LLM answer generation.
    """

    def __init__(self):
        self.vector_store = LocalVectorStore()
        self._knowledge_seeded = False

    def seed_default_knowledge(self) -> None:
        """
        Ingests default career guides, requirements, and best practices.
        """
        if self._knowledge_seeded:
            return
        self._knowledge_seeded = True

        from data.career_requirements import CAREER_REQUIREMENTS
        for career_name, reqs in CAREER_REQUIREMENTS.items():
            req_list = ", ".join(reqs.get("required", []))
            nth_list = ", ".join(reqs.get("nice_to_have", []))
            doc_text = (
                f"Career Specification for {career_name.title()}.\n"
                f"Core Required Competencies (Mandatory): {req_list}.\n"
                f"Preferred Nice-to-Have Technologies: {nth_list}.\n"
                f"Industry benchmark: To achieve job-readiness in {career_name.title()}, candidates must demonstrate "
                f"verified active competence in core languages, relational querying (SQL), and domain tooling. "
                f"Hands-on portfolio projects and active problem solving significantly enhance hiring potential."
            )
            self.vector_store.add_document(
                document_id=f"guide_{career_name.replace(' ', '_')}",
                title=f"{career_name.title()} Industry Competency Standard",
                source_type="career_guide",
                text=doc_text,
                user_id=None
            )

    def ingest_job_listing(self, job_dict: Dict[str, Any]) -> None:
        """
        Ingests a specific job opportunity into the RAG vector store as public knowledge.
        """
        jid = job_dict.get("id")
        title = job_dict.get("title", "Position")
        company = job_dict.get("company", "Company")
        desc = job_dict.get("description", "")
        reqs = ", ".join(job_dict.get("required_skills", []))
        prefs = ", ".join(job_dict.get("preferred_skills", []))
        eligibility = job_dict.get("eligibility", "")

        doc_text = (
            f"Job Opening: {title} at {company}.\n"
            f"Employment Type: {job_dict.get('job_type', 'Full-time')}. Work Arrangement: {job_dict.get('work_arrangement', 'Remote')}.\n"
            f"Required Mandatory Skills: {reqs}.\n"
            f"Preferred Additional Skills: {prefs}.\n"
            f"Eligibility Criteria: {eligibility}.\n"
            f"Detailed Role Description:\n{desc}"
        )

        self.vector_store.add_document(
            document_id=f"job_{jid}",
            title=f"{title} ({company})",
            source_type="job_description",
            text=doc_text,
            user_id=None,
            metadata={"job_id": jid, "company": company, "application_url": job_dict.get("application_url")}
        )

    def ingest_student_profile(self, student_id: int, profile: Dict[str, Any]) -> None:
        """
        Ingests user-authorized student profile data under strict user_id isolation.
        Never accessible to any other user.
        """
        verified = ", ".join(profile.get("verified_skills", []))
        missing = ", ".join(profile.get("missing_skills", []))
        career = profile.get("target_career", "Software Engineering")
        readiness = profile.get("readiness_score", 0.0)

        doc_text = (
            f"Student Profile Data (Authorized Private Record for Student #{student_id}):\n"
            f"Target Career Focus: {career}.\n"
            f"Current Verified Career Readiness: {readiness}%.\n"
            f"Verified Skills (Proven via Adaptive Assessments): {verified if verified else 'None verified yet'}.\n"
            f"Identified Missing Skill Gaps: {missing if missing else 'None (All core verified)'}."
        )

        self.vector_store.add_document(
            document_id=f"student_profile_{student_id}",
            title="My Verified Profile & Skill Status",
            source_type="user_profile",
            text=doc_text,
            user_id=student_id
        )

    def ask(
        self,
        question: str,
        student_id: int,
        student_profile: Dict[str, Any],
        selected_job_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Executes genuine RAG retrieval and answer generation.
        """
        self.seed_default_knowledge()
        self.ingest_student_profile(student_id, student_profile)

        # Retrieve relevant chunks with strict user_id boundary
        chunks = self.vector_store.search(
            query=question,
            requesting_user_id=student_id,
            top_k=4,
            similarity_threshold=0.20
        )

        from utils.ai_providers import ai_provider_manager

        if not chunks:
            # Graceful empty retrieval state
            return {
                "answer": (
                    "I searched the career guidance knowledge base and your authorized profile, "
                    "but could not find direct factual evidence matching your specific query. "
                    "You may want to rephrase your question or specify a particular skill or job role."
                ),
                "is_rag": True,
                "empty_retrieval": True,
                "citations": [],
                "retrieved_sources": [],
                "provider": "SkillBridge RAG Engine (Empty Retrieval Handled)",
                "confidence": "Low (No Grounding Chunks Found)"
            }

        # Build grounded context with numbered citations
        context_blocks = []
        citations_summary = []
        for i, c in enumerate(chunks, 1):
            tag = f"[Source {i}: {c['title']}]"
            context_blocks.append(f"{tag}\n{c['text']}")
            citations_summary.append({
                "tag": f"[Source {i}]",
                "title": c["title"],
                "source_type": c["source_type"],
                "similarity_score": c["similarity_score"]
            })

        grounded_context = "\n\n".join(context_blocks)

        system_instruction = (
            "You are the SkillBridge RAG Career Mentor. "
            "You MUST answer strictly using the retrieved factual sources provided below. "
            "For every key factual claim, cite the source using [Source 1], [Source 2], etc. "
            "Clearly distinguish retrieved facts from helpful suggestions. "
            "If the retrieved context does not contain enough evidence to answer part of the question, "
            "explicitly state that the evidence is missing rather than guessing."
        )

        user_prompt = f"""
RETRIEVED KNOWLEDGE SOURCES:
{grounded_context}

STUDENT QUESTION:
"{question}"

INSTRUCTIONS:
1. Provide a concise, clear answer (3-5 sentences).
2. Explicitly cite the sources (e.g., "...as specified in [Source 1]").
3. Conclude with one actionable next step.
"""

        generation_res = ai_provider_manager.generate_with_fallback(user_prompt, system_instruction)
        answer_text = generation_res.get("text", "").strip()

        if not answer_text:
            # Fallback to local synthesis if LLM unavailable
            top_source = chunks[0]
            answer_text = (
                f"Based on retrieved documentation from **{top_source['title']}**: "
                f"{top_source['text'][:250]}... "
                f"Address your identified gaps to improve qualification alignment."
            )

        return {
            "answer": answer_text,
            "is_rag": True,
            "empty_retrieval": False,
            "citations": citations_summary,
            "retrieved_sources": [c["title"] for c in chunks],
            "provider": generation_res.get("provider", "Local Grounded Engine"),
            "model": generation_res.get("model", "Deterministic"),
            "latency_ms": generation_res.get("latency_ms", 0.0),
            "is_local": generation_res.get("is_local", False)
        }

    def answer_query(
        self,
        query: str,
        student_id: int,
        student_profile: Optional[Dict[str, Any]] = None,
        selected_job_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Alias for ask() providing flexible signature compatibility.
        """
        profile = student_profile or {
            "target_career": "Full Stack Developer",
            "readiness_score": 75.0,
            "verified_skills": ["Python", "React", "Git"],
            "missing_skills": ["Docker", "Kubernetes"]
        }
        return self.ask(question=query, student_id=student_id, student_profile=profile, selected_job_id=selected_job_id)


rag_engine = RAGCareerOrchestrator()

