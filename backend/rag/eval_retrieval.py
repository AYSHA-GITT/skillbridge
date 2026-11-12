"""
Retrieval evaluation: compares the retrieval methods available in SkillBridge
on a fixed, hand-written test set (rag/eval_queries.json) over the curated
career documents (data/knowledge_base/careers/*.json).

Methods
  hash128     utils/rag_engine.DeterministicEmbeddingEngine (signed MD5 word + trigram hashing)
  bow_crc     rag/embedding_engine fallback (hashed bag-of-words)
  bm25        Okapi BM25 keyword retrieval (k1=1.5, b=0.75)
  minilm      sentence-transformers/all-MiniLM-L6-v2 (pretrained semantic embeddings)
  hybrid      reciprocal-rank fusion of minilm + bm25 (k=60)

Metrics: Recall@1, Recall@3, MRR - overall and per query type.

Run:  cd backend && python -m rag.eval_retrieval
"""
import glob
import json
import math
import os
import re
from collections import Counter
from typing import Callable, Dict, List

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)


def load_docs() -> Dict[str, str]:
    docs = {}
    for path in sorted(glob.glob(os.path.join(BACKEND, "data", "knowledge_base", "careers", "*.json"))):
        d = json.load(open(path, encoding="utf-8"))
        parts = [d.get("title", ""), d.get("industry_domain", ""), d.get("description", ""),
                 "Required skills: " + ", ".join(d.get("required_skills", [])),
                 "Nice to have: " + ", ".join(d.get("nice_to_have_skills", [])),
                 " ".join(d.get("responsibilities", []) if isinstance(d.get("responsibilities"), list)
                          else [str(d.get("responsibilities", ""))])]
        docs[d.get("career_id") or os.path.basename(path)[:-5]] = "\n".join(p for p in parts if p)
    return docs


def _tok(text: str) -> List[str]:
    return re.findall(r"[a-z0-9+#.]+", text.lower())


def dense_ranker(encode: Callable[[List[str]], np.ndarray], docs: Dict[str, str]):
    ids = list(docs)
    mat = encode([docs[i] for i in ids])
    mat = mat / (np.linalg.norm(mat, axis=1, keepdims=True) + 1e-9)

    def rank(q: str) -> List[str]:
        v = encode([q])[0]
        v = v / (np.linalg.norm(v) + 1e-9)
        return [ids[i] for i in np.argsort(-(mat @ v))]
    return rank


def bm25_ranker(docs: Dict[str, str], k1=1.5, b=0.75):
    ids = list(docs)
    toks = [_tok(docs[i]) for i in ids]
    avgdl = sum(len(t) for t in toks) / len(toks)
    df = Counter(w for t in toks for w in set(t))
    n = len(ids)
    tfs = [Counter(t) for t in toks]

    def rank(q: str) -> List[str]:
        scores = []
        for tf, t in zip(tfs, toks):
            s = 0.0
            for w in _tok(q):
                if w not in tf:
                    continue
                idf = math.log(1 + (n - df[w] + 0.5) / (df[w] + 0.5))
                s += idf * tf[w] * (k1 + 1) / (tf[w] + k1 * (1 - b + b * len(t) / avgdl))
            scores.append(s)
        return [ids[i] for i in np.argsort(-np.array(scores), kind="stable")]
    return rank


def rrf(*rankers, k=60):
    def rank(q: str) -> List[str]:
        score: Dict[str, float] = {}
        for r in rankers:
            for pos, d in enumerate(r(q)):
                score[d] = score.get(d, 0.0) + 1.0 / (k + pos + 1)
        return sorted(score, key=score.get, reverse=True)
    return rank


def evaluate(rank, queries) -> Dict[str, Dict[str, float]]:
    out = {}
    for group in ("all", "keyword", "paraphrase"):
        qs = [q for q in queries if group == "all" or q["type"] == group]
        r1 = r3 = mrr = 0.0
        for q in qs:
            ranking = rank(q["q"])
            pos = ranking.index(q["expected"]) + 1 if q["expected"] in ranking else None
            r1 += pos == 1
            r3 += pos is not None and pos <= 3
            mrr += 1.0 / pos if pos else 0.0
        out[group] = {"recall@1": round(r1 / len(qs), 3), "recall@3": round(r3 / len(qs), 3),
                      "mrr": round(mrr / len(qs), 3), "n": len(qs)}
    return out


def build_methods(docs):
    from utils.rag_engine import DeterministicEmbeddingEngine
    from rag.embedding_engine import EmbeddingEngine

    h = DeterministicEmbeddingEngine()
    methods = {
        "hash128": dense_ranker(lambda ts: np.stack([h.embed_text(t) for t in ts]), docs),
        "bow_crc": dense_ranker(lambda ts: EmbeddingEngine()._fallback_encode(ts), docs),
        "bm25": bm25_ranker(docs),
    }
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        minilm = dense_ranker(lambda ts: model.encode(ts, convert_to_numpy=True), docs)
        methods["minilm"] = minilm
        methods["hybrid_minilm_bm25"] = rrf(minilm, methods["bm25"])
    except Exception as e:  # model unavailable offline
        print(f"[skip] sentence-transformers unavailable: {e}")
    return methods


def main():
    import sys
    if BACKEND not in sys.path:
        sys.path.insert(0, BACKEND)
    docs = load_docs()
    queries = json.load(open(os.path.join(HERE, "eval_queries.json"), encoding="utf-8"))["queries"]
    results = {name: evaluate(rank, queries) for name, rank in build_methods(docs).items()}
    report = {"documents": len(docs), "queries": len(queries), "results": results}
    with open(os.path.join(HERE, "eval_results.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"{'method':22} {'R@1':>6} {'R@3':>6} {'MRR':>6} | paraphrase R@1  MRR")
    for name, r in results.items():
        a, p = r["all"], r["paraphrase"]
        print(f"{name:22} {a['recall@1']:>6} {a['recall@3']:>6} {a['mrr']:>6} | {p['recall@1']:>14} {p['mrr']:>5}")


if __name__ == "__main__":
    main()
