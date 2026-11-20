"""
Phase 0 harness only - no application code is changed.

Serves the SAME sentence-transformer model the app uses today
(sentence-transformers/all-MiniLM-L6-v2) through ONNX Runtime via fastembed,
instead of PyTorch. install() swaps the loader of rag.embedding_engine.EmbeddingEngine,
so every RAG feature (assistant, resume analysis, job match, gap explanation,
knowledge base) uses ONNX MiniLM exactly where it would use PyTorch MiniLM.

fastembed uses the same tokenizer, 256-token truncation, mean pooling and L2
normalisation as sentence-transformers for this model.
"""
import os

import numpy as np

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


class FastEmbedMiniLM:
    """Duck-types the parts of SentenceTransformer that EmbeddingEngine uses."""

    def __init__(self):
        from fastembed import TextEmbedding
        self._model = TextEmbedding(MODEL_NAME, cache_dir=os.getenv("FASTEMBED_CACHE_PATH") or None,
                                    threads=int(os.getenv("ONNX_THREADS", "1")))

    @staticmethod
    def get_embedding_dimension():
        return 384

    def encode(self, texts, normalize_embeddings=True, show_progress_bar=False, convert_to_numpy=True, **_):
        single = isinstance(texts, str)
        batch = [texts] if single else list(texts)
        emb = np.array(list(self._model.embed(batch)), dtype="float32")
        if normalize_embeddings and len(emb):
            emb /= np.linalg.norm(emb, axis=1, keepdims=True) + 1e-12
        return emb[0] if single else emb


def install():
    import rag.embedding_engine as ee

    def _load_model(self):
        if self._model is not None or self._use_fallback:
            return
        with self._lock:
            if self._model is not None or self._use_fallback:
                return
            try:
                self._model = FastEmbedMiniLM()
                self._dim = 384
                print("PHASE0: ONNX MiniLM loaded (fastembed, all-MiniLM-L6-v2)", flush=True)
            except Exception as e:  # same behaviour as the original loader
                print(f"PHASE0: ONNX MiniLM FAILED to load ({e}); Falling back", flush=True)
                self._use_fallback = True

    ee.EmbeddingEngine._load_model = _load_model
    os.environ["PHASE0_EMBEDDER"] = "onnx-minilm"
