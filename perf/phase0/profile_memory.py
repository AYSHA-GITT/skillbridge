"""
Step-by-step memory profile inside a candidate image (Phase 0 harness, no memory limit).

Every configuration runs in a FRESH Python process; the number reported is that
process's peak resident memory (VmHWM) and its resident memory at the end (VmRSS).
This separates the cost of: the Gemini SDK import, the app import, loading MiniLM,
encoding one query, (re)building the knowledge-base index with different batch /
arena / allocator settings, and loading a prebuilt index instead.

Usage (in the container, cwd /app): python /phase0/profile_memory.py <variant> <out_json>
  variant: onnx | torch
"""
import json
import os
import subprocess
import sys

STEPS_CODE = r'''
import os, sys, json
sys.path[:0] = ["/phase0", "/app"]
def status():
    d = {}
    for line in open("/proc/self/status"):
        k, _, v = line.partition(":")
        if k in ("VmHWM", "VmRSS"):
            d[k] = round(int(v.split()[0]) / 1024, 1)
    return d
steps = [x for x in sys.argv[1].split(",") if x]
variant = sys.argv[2]
marks = {"start": status()}
if "genai" in steps:
    from google import genai  # noqa
    marks["after_genai_import"] = status()
if "app" in steps:
    import onnx_shim
    if variant.startswith("onnx"):
        onnx_shim.install()
    else:
        onnx_shim.install_torch_batch()
    from app import app  # noqa
    marks["after_app_import"] = status()
if "query" in steps:
    from rag.embedding_engine import get_embedding_engine
    e = get_embedding_engine()
    e.encode("Which skills does a data analyst need?")
    marks["after_model_and_one_query"] = status()
if "kb_build" in steps or "kb_load" in steps:
    from rag.knowledge_manager import KnowledgeManager
    km = KnowledgeManager(base_dir="/app")
    km.initialize(force_rebuild=("kb_build" in steps))
    km.search("career designing AWS cloud infrastructure", top_k=5)
    marks["after_kb_" + ("build" if "kb_build" in steps else "load")] = {**status(), "chunks": len(km.documents)}
print(json.dumps(marks))
'''

CONFIGS = {
    "onnx": [
        ("python only", "", {}),
        ("google-genai SDK import only", "genai", {}),
        ("app import (incl. genai, sklearn, flwr, pandas)", "app", {}),
        ("app + MiniLM + one query", "app,query", {}),
        ("app + build KB index: batch 256, arena on (as tested)", "app,query,kb_build", {}),
        ("app + build KB index: batch 8, arena on", "app,query,kb_build", {"ONNX_BATCH_SIZE": "8"}),
        ("app + build KB index: batch 8, arena off", "app,query,kb_build",
         {"ONNX_BATCH_SIZE": "8", "ONNX_CPU_ARENA": "0"}),
        ("app + build KB index: batch 8, arena off, MALLOC_ARENA_MAX=2", "app,query,kb_build",
         {"ONNX_BATCH_SIZE": "8", "ONNX_CPU_ARENA": "0", "MALLOC_ARENA_MAX": "2"}),
        ("app + LOAD prebuilt KB index (no re-encoding), tuned", "app,query,kb_load",
         {"ONNX_BATCH_SIZE": "8", "ONNX_CPU_ARENA": "0", "MALLOC_ARENA_MAX": "2"}),
    ],
    "torch": [
        ("python only", "", {}),
        ("google-genai SDK import only", "genai", {}),
        ("app import (incl. genai, sklearn, flwr, pandas)", "app", {}),
        ("app + MiniLM + one query", "app,query", {}),
        ("app + build KB index: batch 32 (as tested)", "app,query,kb_build", {}),
        ("app + build KB index: batch 8, MALLOC_ARENA_MAX=2", "app,query,kb_build",
         {"TORCH_BATCH_SIZE": "8", "MALLOC_ARENA_MAX": "2"}),
        ("app + LOAD prebuilt KB index (no re-encoding), tuned", "app,query,kb_load",
         {"TORCH_BATCH_SIZE": "8", "MALLOC_ARENA_MAX": "2"}),
    ],
}


def main():
    variant, out = sys.argv[1], sys.argv[2]
    results = []
    for name, steps, env in CONFIGS[variant]:
        r = subprocess.run([sys.executable, "-c", STEPS_CODE, steps, variant], capture_output=True, text=True,
                           env={**os.environ, **env}, cwd="/app", timeout=900)
        line = (r.stdout.strip().splitlines() or ["{}"])[-1]
        try:
            marks = json.loads(line)
        except ValueError:
            marks = {"error": (r.stderr or r.stdout)[-600:]}
        peak = max((m.get("VmHWM", 0) for m in marks.values() if isinstance(m, dict)), default=None)
        results.append({"config": name, "env": env, "peak_rss_mb": peak, "marks": marks})
        print(f"{name:70s} peak {peak} MB", flush=True)
    json.dump({"variant": variant, "results": results}, open(out, "w"), indent=1)


if __name__ == "__main__":
    main()
