import logging
import threading
import numpy as np

logger = logging.getLogger(__name__)

class EmbeddingEngine:
    """
    Embedding Engine using Sentence Transformers ('all-MiniLM-L6-v2')
    with lazy initialization, in-memory caching, and fallback support.
    """

    _instance = None
    _lock = threading.Lock()

    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        self.model_name = model_name
        self._model = None
        self._dim = 384
        self._cache = {}
        self._cache_lock = threading.Lock()
        self._use_fallback = False

    @classmethod
    def get_instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    @property
    def dimension(self) -> int:
        return self._dim

    def _load_model(self):
        if self._model is not None or self._use_fallback:
            return
        with self._lock:
            if self._model is not None or self._use_fallback:
                return
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"Loading SentenceTransformer model '{self.model_name}'...")
                self._model = SentenceTransformer(self.model_name)
                dim = None
                if hasattr(self._model, 'get_embedding_dimension'):
                    dim = self._model.get_embedding_dimension()
                elif hasattr(self._model, 'get_sentence_embedding_dimension'):
                    dim = self._model.get_sentence_embedding_dimension()
                if dim is not None:
                    self._dim = int(dim)
                logger.info(f"SentenceTransformer loaded successfully (dim={self._dim}).")
            except Exception as e:
                logger.warning(f"Could not load SentenceTransformer '{self.model_name}': {e}. Falling back to TF-IDF.")
                self._use_fallback = True

    def encode(self, texts: list[str] | str, normalize: bool = True) -> np.ndarray:
        """
        Encode single text or list of texts into L2-normalized float32 embeddings.
        """
        is_single = isinstance(texts, str)
        text_list = [texts] if is_single else list(texts)

        if not text_list:
            return np.empty((0, self._dim), dtype='float32')

        self._load_model()

        # Check cache for single queries
        if is_single:
            cache_key = (text_list[0].strip().lower(), normalize)
            with self._cache_lock:
                if cache_key in self._cache:
                    return self._cache[cache_key].copy()

        if self._model is not None and not self._use_fallback:
            try:
                embeddings = self._model.encode(
                    text_list,
                    normalize_embeddings=normalize,
                    show_progress_bar=False,
                    convert_to_numpy=True
                ).astype('float32')
            except Exception as e:
                logger.warning(f"Error during SentenceTransformer encode: {e}. Using deterministic fallback.")
                embeddings = self._fallback_encode(text_list)
        else:
            embeddings = self._fallback_encode(text_list)

        if is_single and len(embeddings) > 0:
            cache_key = (text_list[0].strip().lower(), normalize)
            with self._cache_lock:
                if len(self._cache) > 2000:
                    # Clear half the cache if it gets too large
                    self._cache.clear()
                self._cache[cache_key] = embeddings[0].copy()
            return embeddings[0]

        return embeddings

    def _fallback_encode(self, texts: list[str]) -> np.ndarray:
        """
        Deterministic word-hash bag-of-words projection for zero-downtime fallback.
        """
        embeddings = np.zeros((len(texts), self._dim), dtype='float32')
        for i, text in enumerate(texts):
            words = text.lower().replace(",", " ").replace(".", " ").split()
            for w in words:
                h = abs(hash(w)) % self._dim
                embeddings[i, h] += 1.0
            norm = np.linalg.norm(embeddings[i])
            if norm > 0:
                embeddings[i] /= norm
        return embeddings


def get_embedding_engine() -> EmbeddingEngine:
    return EmbeddingEngine.get_instance()
