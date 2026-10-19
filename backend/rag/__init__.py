"""
SkillBridge RAG (Retrieval-Augmented Generation) Package
Semantic retrieval engine using Sentence Transformers, FAISS / NumPy vector search,
and contextual Gemini grounding.
"""

from .vector_store import create_vector_store, FaissVectorStore, NumpyVectorStore
from .embedding_engine import get_embedding_engine
from .knowledge_manager import get_knowledge_manager
from .rag_pipeline import get_rag_pipeline

__all__ = [
    'create_vector_store',
    'FaissVectorStore',
    'NumpyVectorStore',
    'get_embedding_engine',
    'get_knowledge_manager',
    'get_rag_pipeline'
]
