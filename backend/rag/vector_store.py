import os
import logging
import numpy as np
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class VectorStore(ABC):
    """Abstract base class for vector storage and semantic similarity search."""

    @abstractmethod
    def add(self, embeddings: np.ndarray, documents: list[dict]):
        pass

    @abstractmethod
    def search(self, query_embedding: np.ndarray, top_k: int = 5, filter_fn=None) -> list[dict]:
        pass

    @abstractmethod
    def save(self, filepath_base: str):
        pass

    @abstractmethod
    def load(self, filepath_base: str) -> bool:
        pass

    @abstractmethod
    def size(self) -> int:
        pass


class FaissVectorStore(VectorStore):
    """FAISS-based vector index utilizing Inner Product on normalized vectors (Cosine Similarity)."""

    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self.documents = []
        import faiss
        self.faiss = faiss
        self.index: Any = faiss.IndexFlatIP(dimension)

    def add(self, embeddings: np.ndarray, documents: list[dict]):
        if len(embeddings) == 0:
            return
        embeddings = embeddings.astype('float32')
        # Ensure L2 normalized for cosine similarity
        self.faiss.normalize_L2(embeddings)
        self.index.add(embeddings)
        self.documents.extend(documents)

    def search(self, query_embedding: np.ndarray, top_k: int = 5, filter_fn=None) -> list[dict]:
        if self.index.ntotal == 0:
            return []
        q = np.array(query_embedding, dtype='float32').reshape(1, -1)
        self.faiss.normalize_L2(q)

        # Retrieve more candidates if a filter is applied
        fetch_k = min(self.index.ntotal, top_k * 4 if filter_fn else top_k)
        scores, indices = self.index.search(q, fetch_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.documents):
                continue
            doc = self.documents[idx].copy()
            doc['score'] = float(round(score, 4))
            if filter_fn and not filter_fn(doc):
                continue
            results.append(doc)
            if len(results) >= top_k:
                break
        return results

    def save(self, filepath_base: str):
        index_file = f"{filepath_base}.faiss"
        os.makedirs(os.path.dirname(index_file), exist_ok=True)
        self.faiss.write_index(self.index, index_file)

    def load(self, filepath_base: str) -> bool:
        index_file = f"{filepath_base}.faiss"
        if os.path.exists(index_file):
            try:
                self.index = self.faiss.read_index(index_file)
                self.dimension = self.index.d
                return True
            except Exception as e:
                logger.warning(f"Failed to load FAISS index from {index_file}: {e}")
                return False
        return False

    def size(self) -> int:
        return self.index.ntotal


class NumpyVectorStore(VectorStore):
    """Fallback NumPy vector store using vectorized matrix dot product for exact cosine similarity."""

    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self.documents = []
        self.embeddings = np.empty((0, dimension), dtype='float32')

    def add(self, embeddings: np.ndarray, documents: list[dict]):
        if len(embeddings) == 0:
            return
        embeddings = embeddings.astype('float32')
        # L2 normalize
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        embeddings = embeddings / norms

        if self.embeddings.shape[0] == 0:
            self.embeddings = embeddings
        else:
            self.embeddings = np.vstack([self.embeddings, embeddings])
        self.documents.extend(documents)

    def search(self, query_embedding: np.ndarray, top_k: int = 5, filter_fn=None) -> list[dict]:
        if self.embeddings.shape[0] == 0:
            return []
        q = np.array(query_embedding, dtype='float32').reshape(1, -1)
        q_norm = np.linalg.norm(q)
        if q_norm > 0:
            q = q / q_norm

        scores = np.dot(self.embeddings, q.T).flatten()
        ranked_indices = np.argsort(-scores)

        results = []
        for idx in ranked_indices:
            doc = self.documents[idx].copy()
            doc['score'] = float(round(scores[idx], 4))
            if filter_fn and not filter_fn(doc):
                continue
            results.append(doc)
            if len(results) >= top_k:
                break
        return results

    def save(self, filepath_base: str):
        np_file = f"{filepath_base}.npy"
        os.makedirs(os.path.dirname(np_file), exist_ok=True)
        np.save(np_file, self.embeddings)

    def load(self, filepath_base: str) -> bool:
        np_file = f"{filepath_base}.npy"
        if os.path.exists(np_file):
            try:
                self.embeddings = np.load(np_file).astype('float32')
                self.dimension = self.embeddings.shape[1] if self.embeddings.ndim > 1 else 384
                return True
            except Exception as e:
                logger.warning(f"Failed to load NumPy index from {np_file}: {e}")
                return False
        return False

    def size(self) -> int:
        return self.embeddings.shape[0]


def create_vector_store(dimension: int = 384) -> VectorStore:
    """Factory creating FAISS vector store if available, falling back smoothly to NumPy."""
    try:
        import faiss
        return FaissVectorStore(dimension=dimension)
    except Exception as e:
        logger.info(f"FAISS not available or failed to initialize ({e}). Using NumPyVectorStore.")
        return NumpyVectorStore(dimension=dimension)
