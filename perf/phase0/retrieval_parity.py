"""
Retrieval-quality parity: current PyTorch MiniLM vs ONNX MiniLM (Phase 0 harness).

Three comparisons, each engine in its own process and its own copy of the
knowledge base (so no cached index is shared between them):

 1. The project's own retrieval benchmark (rag/eval_retrieval.py: 27 hand-written
    queries, keyword + paraphrase) - Recall@1, Recall@3, MRR.
 2. Vector agreement: cosine(PyTorch vector, ONNX vector) for every benchmark
    document and query.
 3. The app's real knowledge-base search (rag.knowledge_manager.search, as used by
    the assistant): top-5 results and scores for every benchmark query.

Usage: python retrieval_parity.py <backend_dir> <out_json>
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def run_engine(engine, backend, workdir, out):
    """Child process: score one engine."""
    sys.path.insert(0, backend)
    sys.path.insert(0, HERE)
    import numpy as np
    if engine == "onnx":
        import onnx_shim
        onnx_shim.install()
        model = onnx_shim.FastEmbedMiniLM()
    else:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")

    def encode(texts):
        return np.asarray(model.encode(list(texts), normalize_embeddings=True), dtype="float32")

    from rag.eval_retrieval import load_docs, dense_ranker, evaluate
    docs = load_docs()
    queries = json.load(open(os.path.join(backend, "rag", "eval_queries.json"), encoding="utf-8"))["queries"]
    rank = dense_ranker(encode, docs)
    rankings = {q["q"]: rank(q["q"]) for q in queries}
    vectors = encode(list(docs.values()) + [q["q"] for q in queries])

    # the app's knowledge-base search, on a private copy of the knowledge base
    from rag.embedding_engine import EmbeddingEngine
    from rag.knowledge_manager import KnowledgeManager
    km = KnowledgeManager(base_dir=workdir)
    if hasattr(km, "initialize"):
        km.initialize()
    kb = {}
    for q in queries:
        hits = km.search(q["q"], top_k=5, min_score=0.0)
        kb[q["q"]] = [{"source": h.get("source") or h.get("title") or "", "text": (h.get("text") or "")[:80],
                       "score": round(float(h.get("score", 0.0)), 4)} for h in hits]
    json.dump({"engine": engine, "embedding_engine": EmbeddingEngine.get_instance().engine_name,
               "benchmark": evaluate(rank, queries), "rankings": rankings, "kb_search": kb}, open(out, "w"))
    np.save(out + ".npy", vectors)


def main():
    backend, out = os.path.abspath(sys.argv[1]), sys.argv[2]
    import numpy as np
    res = {}
    for engine in ("torch", "onnx"):
        work = tempfile.mkdtemp(prefix=f"kb_{engine}_")
        shutil.copytree(os.path.join(backend, "data", "knowledge_base"), os.path.join(work, "data", "knowledge_base"))
        part = os.path.join(work, "result.json")
        python = os.getenv(f"PHASE0_PYTHON_{engine.upper()}") or sys.executable   # optional per-engine interpreter
        subprocess.run([python, __file__, "--child", engine, backend, work, part], check=True)
        res[engine] = json.load(open(part))
        res[engine]["vectors"] = np.load(part + ".npy")

    t, o = res["torch"], res["onnx"]
    cos = (t["vectors"] * o["vectors"]).sum(axis=1)
    same_rank = sum(t["rankings"][q] == o["rankings"][q] for q in t["rankings"])
    same_top1 = sum(t["rankings"][q][0] == o["rankings"][q][0] for q in t["rankings"])
    kb_same_top5 = sum([(h["source"], h["text"]) for h in t["kb_search"][q]] ==
                       [(h["source"], h["text"]) for h in o["kb_search"][q]] for q in t["kb_search"])
    kb_score_diff = max((abs(a["score"] - b["score"]) for q in t["kb_search"]
                         for a, b in zip(t["kb_search"][q], o["kb_search"][q])), default=0.0)
    n = len(t["rankings"])
    report = {
        "engines": {"torch": t["embedding_engine"], "onnx": o["embedding_engine"]},
        "benchmark": {"torch": t["benchmark"], "onnx": o["benchmark"]},
        "vector_cosine": {"min": round(float(cos.min()), 6), "mean": round(float(cos.mean()), 6),
                          "texts": int(len(cos))},
        "benchmark_full_ranking_identical": f"{same_rank}/{n}",
        "benchmark_top1_identical": f"{same_top1}/{n}",
        "kb_search_top5_identical": f"{kb_same_top5}/{len(t['kb_search'])}",
        "kb_search_max_score_difference": round(kb_score_diff, 4),
        "kb_search_examples": {q: {"torch": t["kb_search"][q][:3], "onnx": o["kb_search"][q][:3]}
                               for q in list(t["kb_search"])[:3]},
    }
    report["equivalent"] = (report["benchmark"]["torch"] == report["benchmark"]["onnx"]
                            and report["vector_cosine"]["min"] >= 0.999
                            and kb_same_top5 == len(t["kb_search"]))
    json.dump(report, open(out, "w"), indent=1)
    print(json.dumps({k: report[k] for k in ("benchmark_full_ranking_identical", "benchmark_top1_identical",
                                             "kb_search_top5_identical", "vector_cosine", "equivalent")}))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--child":
        run_engine(*sys.argv[2:6])
    else:
        main()
