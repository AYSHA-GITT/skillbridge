import os
import json
import hashlib
import logging
from typing import Optional, List, Dict, Any
from .embedding_engine import get_embedding_engine
from .vector_store import create_vector_store, VectorStore

logger = logging.getLogger(__name__)

class KnowledgeManager:
    """
    Manages knowledge base ingestion, chunking, embedding generation,
    persistent vector caching, and semantic retrieval.
    """

    _instance = None

    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.base_dir = base_dir
        self.kb_dir = os.path.join(base_dir, 'data', 'knowledge_base')
        self.cache_dir = os.path.join(base_dir, 'data', 'cache')
        os.makedirs(self.cache_dir, exist_ok=True)

        self.embedding_engine = get_embedding_engine()
        self.vector_store: VectorStore = create_vector_store(self.embedding_engine.dimension)
        self.documents: List[Dict[str, Any]] = []
        self._initialized = False

    @classmethod
    def get_instance(cls, base_dir: Optional[str] = None):
        if cls._instance is None:
            cls._instance = cls(base_dir)
        return cls._instance

    def initialize(self, force_rebuild: bool = False):
        """Initializes or loads cached index."""
        if self._initialized and not force_rebuild:
            return

        cache_base = os.path.join(self.cache_dir, 'rag_index')
        meta_file = os.path.join(self.cache_dir, 'rag_metadata.json')
        hash_file = os.path.join(self.cache_dir, 'rag_hash.txt')

        current_hash = self._compute_kb_hash()

        # Try to load existing cache if valid
        if not force_rebuild and os.path.exists(meta_file) and os.path.exists(hash_file):
            try:
                with open(hash_file, 'r', encoding='utf-8') as f:
                    cached_hash = f.read().strip()
                if cached_hash == current_hash and self.vector_store.load(cache_base):
                    with open(meta_file, 'r', encoding='utf-8') as f:
                        self.documents = json.load(f)
                    self.vector_store.documents = self.documents
                    self._initialized = True
                    logger.info(f"Loaded RAG vector cache successfully: {len(self.documents)} knowledge chunks.")
                    return
            except Exception as e:
                logger.warning(f"Failed to load cached RAG index: {e}. Rebuilding...")

        # Rebuild index from knowledge base files
        self.rebuild_index()

    def _compute_kb_hash(self) -> str:
        """Computes hash of all knowledge files to detect updates."""
        hasher = hashlib.md5()
        if os.path.exists(self.kb_dir):
            for root, _, files in sorted(os.walk(self.kb_dir)):
                for file in sorted(files):
                    if file.endswith('.json'):
                        filepath = os.path.join(root, file)
                        hasher.update(file.encode('utf-8'))
                        hasher.update(str(os.path.getmtime(filepath)).encode('utf-8'))

        # Also incorporate curated career requirements file
        cr_path = os.path.join(self.base_dir, 'data', 'career_requirements.py')
        if os.path.exists(cr_path):
            hasher.update(str(os.path.getmtime(cr_path)).encode('utf-8'))

        return hasher.hexdigest()

    def rebuild_index(self):
        """Builds knowledge chunks, encodes them, and saves cache."""
        logger.info("Building RAG Knowledge Base index...")
        chunks = self._load_and_chunk_all()
        if not chunks:
            logger.warning("No knowledge chunks found to index.")
            self._initialized = True
            return

        texts = [chunk['text'] for chunk in chunks]
        logger.info(f"Encoding {len(texts)} knowledge chunks using Sentence Transformers...")
        embeddings = self.embedding_engine.encode(texts, normalize=True)

        self.vector_store = create_vector_store(self.embedding_engine.dimension)
        self.vector_store.add(embeddings, chunks)
        self.documents = chunks

        # Save to disk cache
        cache_base = os.path.join(self.cache_dir, 'rag_index')
        meta_file = os.path.join(self.cache_dir, 'rag_metadata.json')
        hash_file = os.path.join(self.cache_dir, 'rag_hash.txt')

        try:
            self.vector_store.save(cache_base)
            with open(meta_file, 'w', encoding='utf-8') as f:
                json.dump(self.documents, f, indent=2)
            with open(hash_file, 'w', encoding='utf-8') as f:
                f.write(self._compute_kb_hash())
            logger.info(f"Saved RAG index cache with {len(self.documents)} chunks.")
        except Exception as e:
            logger.warning(f"Could not write RAG cache to disk: {e}")

        self._initialized = True

    def _load_and_chunk_all(self) -> List[Dict[str, Any]]:
        chunks = []

        # 1. Load Career Benchmarks from JSON files
        careers_dir = os.path.join(self.kb_dir, 'careers')
        indexed_careers = set()
        if os.path.exists(careers_dir):
            for file in os.listdir(careers_dir):
                if file.endswith('.json'):
                    path = os.path.join(careers_dir, file)
                    try:
                        with open(path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        chunks.extend(self._chunk_career_doc(data))
                        indexed_careers.add(data.get('title', '').strip().lower())
                    except Exception as e:
                        logger.warning(f"Error reading career file {path}: {e}")

        # 2. Sync with CAREER_REQUIREMENTS from career_requirements.py to guarantee coverage
        try:
            try:
                from data.career_requirements import CAREER_REQUIREMENTS
            except ImportError:
                from backend.data.career_requirements import CAREER_REQUIREMENTS
            for c_name, reqs in CAREER_REQUIREMENTS.items():
                if c_name.lower() not in indexed_careers:
                    career_doc = {
                        "career_id": c_name.replace(" ", "_"),
                        "title": c_name.title(),
                        "industry_domain": "Information Technology & Software",
                        "description": f"Professional industry role for {c_name.title()} focusing on modern enterprise software and engineering standards.",
                        "experience_level": "Entry to Mid Level",
                        "required_skills": reqs.get("required", []),
                        "nice_to_have_skills": reqs.get("nice_to_have", []),
                        "responsibilities": [
                            f"Apply core competencies in {', '.join(reqs.get('required', [])[:4])}.",
                            f"Participate in agile sprint delivery and code reviews.",
                            f"Deliver verified solutions meeting production quality standards."
                        ],
                        "source": f"SkillBridge Curated Industry Benchmark - {c_name.title()} (2026)"
                    }
                    chunks.extend(self._chunk_career_doc(career_doc))
        except Exception as e:
            logger.warning(f"Could not load CAREER_REQUIREMENTS: {e}")

        # 3. Load Job Descriptions
        jd_dir = os.path.join(self.kb_dir, 'job_descriptions')
        if os.path.exists(jd_dir):
            for file in os.listdir(jd_dir):
                if file.endswith('.json'):
                    path = os.path.join(jd_dir, file)
                    try:
                        with open(path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        chunks.extend(self._chunk_job_description(data))
                    except Exception as e:
                        logger.warning(f"Error reading JD file {path}: {e}")

        # 4. Load Skill Definitions
        skills_file = os.path.join(self.kb_dir, 'skills', 'skill_definitions.json')
        if os.path.exists(skills_file):
            try:
                with open(skills_file, 'r', encoding='utf-8') as f:
                    skills_dict = json.load(f)
                for s_key, s_data in skills_dict.items():
                    chunks.extend(self._chunk_skill_definition(s_data))
            except Exception as e:
                logger.warning(f"Error reading skills definition file: {e}")

        return chunks

    def _chunk_career_doc(self, data: dict) -> List[Dict[str, Any]]:
        title = data.get('title', 'Unknown Role')
        domain = data.get('industry_domain', 'Technology')
        req = data.get('required_skills', [])
        nice = data.get('nice_to_have_skills', [])
        desc = data.get('description', '')
        resp = " ".join(data.get('responsibilities', []))
        source = data.get('source', 'SkillBridge Industry Career Benchmark')

        # Primary composite chunk
        text = (
            f"Career Role: {title}. Domain: {domain}. Overview: {desc} "
            f"Required Core Skills: {', '.join(req)}. Preferred Skills: {', '.join(nice)}. "
            f"Key Responsibilities: {resp}"
        )

        chunk1 = {
            "chunk_id": f"career_{data.get('career_id', title.lower())}_overview",
            "type": "career_benchmark",
            "title": title,
            "career": title.lower(),
            "domain": domain,
            "required_skills": req,
            "nice_to_have_skills": nice,
            "source": source,
            "text": text,
            "raw_data": data
        }

        # Requirement-focused chunk for granular query matching
        req_text = (
            f"Industry Standard Requirements for {title} in {domain}: "
            f"Must-have technical competencies include {', '.join(req)}. "
            f"Complementary technologies: {', '.join(nice)}."
        )
        chunk2 = {
            "chunk_id": f"career_{data.get('career_id', title.lower())}_reqs",
            "type": "career_requirements",
            "title": f"{title} Requirements",
            "career": title.lower(),
            "domain": domain,
            "required_skills": req,
            "nice_to_have_skills": nice,
            "source": source,
            "text": req_text,
            "raw_data": data
        }

        return [chunk1, chunk2]

    def _chunk_job_description(self, data: dict) -> List[Dict[str, Any]]:
        role = data.get('role', 'Job Opening')
        company = data.get('company', 'Hiring Organization')
        career = data.get('career_category', role).lower()
        req = data.get('required_skills', [])
        pref = data.get('preferred_skills', [])
        desc = data.get('description', '')
        resp = data.get('responsibilities', '')
        loc = data.get('location', 'Remote')
        sal = data.get('salary_range', 'Competitive')
        source = data.get('source', f"{company} Job Requisition")

        text = (
            f"Job Opening: {role} at {company} ({loc}). Category: {career.title()}. "
            f"Salary Range: {sal}. Job Description: {desc} "
            f"Required Technical Skills: {', '.join(req)}. Preferred Skills: {', '.join(pref)}. "
            f"Key Responsibilities: {resp}"
        )

        return [{
            "chunk_id": f"jd_{data.get('job_id', company.lower())}",
            "type": "job_description",
            "title": f"{role} ({company})",
            "company": company,
            "role": role,
            "location": loc,
            "salary_range": sal,
            "career": career,
            "required_skills": req,
            "nice_to_have_skills": pref,
            "source": source,
            "text": text,
            "raw_data": data
        }]

    def _chunk_skill_definition(self, data: dict) -> List[Dict[str, Any]]:
        name = data.get('canonical_name', 'Skill')
        category = data.get('category', 'Technical')
        defin = data.get('definition', '')
        syns = data.get('synonyms', [])
        eco = data.get('key_ecosystem', [])
        source = f"SkillLens Knowledge Taxonomy: {name.title()}"

        text = (
            f"Skill Definition: {name.title()} ({category}). Definition: {defin} "
            f"Common Aliases: {', '.join(syns)}. Related Tools & Ecosystem: {', '.join(eco)}."
        )

        return [{
            "chunk_id": f"skill_{name.replace(' ', '_')}",
            "type": "skill_definition",
            "title": f"Skill: {name.title()}",
            "skill_name": name.lower(),
            "category": category,
            "source": source,
            "text": text,
            "raw_data": data
        }]

    def search(
        self,
        query: str,
        top_k: int = 5,
        doc_type: Optional[str] = None,
        career_filter: Optional[str] = None,
        min_score: float = 0.15
    ) -> List[Dict[str, Any]]:
        """
        Executes semantic search against the knowledge vector index.
        """
        self.initialize()
        if not query or not query.strip():
            return []

        q_clean = query.strip()
        query_emb = self.embedding_engine.encode(q_clean, normalize=True)

        def filter_fn(doc):
            if doc_type and doc.get('type') != doc_type:
                return False
            if career_filter:
                doc_career = doc.get('career', '').lower()
                c_clean = career_filter.strip().lower()
                if doc_career and c_clean not in doc_career and doc_career not in c_clean:
                    return False
            return True

        raw_results = self.vector_store.search(query_emb, top_k=top_k, filter_fn=filter_fn)

        filtered = [r for r in raw_results if r.get('score', 0) >= min_score]
        return filtered

    def get_career_benchmark(self, career_name: str) -> Optional[Dict[str, Any]]:
        """Returns the benchmark standard for a specific career."""
        self.initialize()
        c_clean = career_name.strip().lower()
        for doc in self.documents:
            if doc.get('type') in ('career_benchmark', 'career_requirements') and doc.get('career') == c_clean:
                return doc
        # Fuzzy match
        for doc in self.documents:
            if doc.get('type') in ('career_benchmark', 'career_requirements'):
                if c_clean in doc.get('career', '') or doc.get('career', '') in c_clean:
                    return doc
        return None

    def get_all_careers(self) -> List[Dict[str, Any]]:
        """Returns catalog of all available careers."""
        self.initialize()
        seen = set()
        careers = []
        for doc in self.documents:
            if doc.get('type') == 'career_benchmark':
                c = doc.get('career')
                if c and c not in seen:
                    seen.add(c)
                    careers.append({
                        'career_id': doc.get('chunk_id'),
                        'career': c,
                        'title': doc.get('title'),
                        'domain': doc.get('domain'),
                        'required_skills': doc.get('required_skills', []),
                        'nice_to_have_skills': doc.get('nice_to_have_skills', []),
                        'source': doc.get('source')
                    })
        return careers

    def get_all_job_descriptions(self) -> List[Dict[str, Any]]:
        """Returns catalog of all real-world job descriptions in knowledge base."""
        self.initialize()
        seen = set()
        jds = []
        for doc in self.documents:
            if doc.get('type') == 'job_description':
                jid = doc.get('chunk_id')
                if jid and jid not in seen:
                    seen.add(jid)
                    jds.append({
                        'job_id': jid,
                        'title': doc.get('title'),
                        'company': doc.get('company'),
                        'role': doc.get('role'),
                        'location': doc.get('location'),
                        'salary_range': doc.get('salary_range'),
                        'career': doc.get('career'),
                        'required_skills': doc.get('required_skills', []),
                        'nice_to_have_skills': doc.get('nice_to_have_skills', []),
                        'source': doc.get('source')
                    })
        return jds

    def add_custom_job_description(self, jd_data: dict) -> Dict[str, Any]:
        """Allows dynamically adding a new job description to the knowledge base."""
        self.initialize()
        chunks = self._chunk_job_description(jd_data)
        if not chunks:
            raise ValueError("Invalid job description payload")

        texts = [c['text'] for c in chunks]
        embeddings = self.embedding_engine.encode(texts, normalize=True)
        self.vector_store.add(embeddings, chunks)
        self.documents.extend(chunks)

        # Save to disk
        cache_base = os.path.join(self.cache_dir, 'rag_index')
        meta_file = os.path.join(self.cache_dir, 'rag_metadata.json')
        try:
            self.vector_store.save(cache_base)
            with open(meta_file, 'w', encoding='utf-8') as f:
                json.dump(self.documents, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not update RAG cache on disk: {e}")

        # Also save JSON in job_descriptions dir for persistence
        job_id = jd_data.get('job_id', f"custom_jd_{hashlib.md5(jd_data.get('role', '').encode()).hexdigest()[:8]}")
        jd_file = os.path.join(self.kb_dir, 'job_descriptions', f"{job_id}.json")
        try:
            with open(jd_file, 'w', encoding='utf-8') as f:
                json.dump(jd_data, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not persist custom JD to file: {e}")

        return chunks[0]


def get_knowledge_manager(base_dir: Optional[str] = None) -> KnowledgeManager:
    return KnowledgeManager.get_instance(base_dir)
