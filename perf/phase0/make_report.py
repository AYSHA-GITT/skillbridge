"""
Builds perf/phase0/results/SUMMARY.md and verdict.json from the CI artifacts.

PASS requires, for the candidate (onnx) image under --memory=512m --memory-swap=512m --cpus=0.1:
  * no OOM kill (cgroup oom_kill == 0, container not OOMKilled, no gunicorn worker SIGKILL)
  * peak anonymous (non-reclaimable) memory <= 450 MB, i.e. >= 62 MB headroom
  * ONNX retrieval equivalent to PyTorch MiniLM (identical benchmark, vectors, KB search)
  * every backend unit test passing in the slim image
  * no end-to-end failure except the known harness-only check(s) listed below
  * no server error (HTTP 5xx) or dropped connection in the concurrent load test
Usage: python make_report.py <results_dir>
"""
import glob
import json
import os
import sys

R = sys.argv[1]
LIMIT_ANON_MB = 450
# e2e checks that cannot pass in CI for reasons unrelated to the app under test
HARNESS_ONLY = {"Cleanup e2e organisation"}   # imports the app on the CI runner itself (no Flask there)


def load(name, default=None):
    p = os.path.join(R, name)
    try:
        return json.load(open(p))
    except (OSError, ValueError):
        return default


def e2e(variant):
    rows = load(f"e2e_{variant}.json", []) or []
    fails = [r for r in rows if r[2] == "FAIL"]
    real = [r for r in fails if r[1] not in HARNESS_ONLY]
    return {"pass": sum(r[2] == "PASS" for r in rows), "warn": sum(r[2] == "WARN" for r in rows),
            "fail": len(fails), "real_fail": real, "harness_fail": [r for r in fails if r[1] in HARNESS_ONLY],
            "total": len(rows)}


def variant_block(v):
    mem, load_, state = load(f"memory_{v}.json", {}), load(f"load_{v}.json", {}), load(f"state_{v}.json", {})
    log = open(os.path.join(R, f"app_log_{v}.txt"), encoding="utf-8", errors="replace").read() \
        if os.path.exists(os.path.join(R, f"app_log_{v}.txt")) else ""
    startup = (open(os.path.join(R, f"startup_{v}.txt")).read().strip()
               if os.path.exists(os.path.join(R, f"startup_{v}.txt")) else "?")
    ev = mem.get("events", {})
    sigkill = log.count("SIGKILL") + log.count("out of memory")
    by = load_.get("by_feature", {})
    dropped = sum(1 for f in by.values() for e in f.get("errors", []) if not e.startswith("HTTP 4"))
    five_xx = sum(1 for f in by.values() for e in f.get("errors", []) if e.startswith("HTTP 5"))
    return {"variant": v, "mem": mem, "load": load_, "state": state, "startup_s": startup,
            "oom_kill": ev.get("oom_kill", 0), "oom_events": ev.get("oom", 0), "worker_sigkill": sigkill,
            "oom_killed_flag": state.get("OOMKilled"), "dropped_or_5xx": dropped, "http_5xx": five_xx,
            "engine_line": "PHASE0: ONNX MiniLM loaded" in log, "fallback_line": "Falling back" in log,
            "e2e": e2e(v)}


def main():
    parity = load("retrieval_parity.json", {})
    tests = load("unit_tests.json", {})
    order = ("onnx-rest-ext", "onnx-rest-ext-t4", "onnx-rest", "onnx-rest-t4", "onnx-tuned", "torch-tuned",
             "onnx", "torch")
    variants = [variant_block(v) for v in order if os.path.exists(os.path.join(R, f"memory_{v}.json"))]
    # candidate = the most complete measured configuration, in this order of preference
    cand = next((v for name in ("onnx-rest-ext", "onnx-rest", "onnx-tuned", "onnx")
                 for v in variants if v["variant"] == name), None)

    checks = []
    if cand:
        checks += [
            ("No OOM kill (cgroup oom_kill, OOMKilled flag, worker SIGKILL)",
             cand["oom_kill"] == 0 and not cand["oom_killed_flag"] and cand["worker_sigkill"] == 0),
            (f"Peak anonymous memory <= {LIMIT_ANON_MB} MB (measured {cand['mem'].get('overall_max_anon_mb')} MB)",
             (cand["mem"].get("overall_max_anon_mb") or 9999) <= LIMIT_ANON_MB),
            ("ONNX MiniLM actually served RAG (log line present, no fallback)",
             cand["engine_line"] and not cand["fallback_line"]),
            ("No HTTP 5xx / dropped connection under concurrent load", cand["dropped_or_5xx"] == 0),
            (f"End-to-end: no failures except harness-only ({len(cand['e2e']['real_fail'])} real)",
             len(cand["e2e"]["real_fail"]) == 0 and cand["e2e"]["total"] > 0),
        ]
    else:
        checks.append(("Candidate image measured", False))
    checks += [("Retrieval quality equivalent to PyTorch MiniLM", bool(parity.get("equivalent"))),
               (f"Backend unit tests in slim image ({tests.get('ran', 0)} run)", bool(tests.get("ok")))]
    verdict = "PASS" if all(ok for _, ok in checks) else "FAIL"

    L = [f"# Phase 0 result: **{verdict}** (candidate image: {cand['variant'] if cand else 'none'})", "",
         "Render free-tier conditions: `--memory=512m --memory-swap=512m --cpus=0.1`, gunicorn 1 worker x 8 threads, "
         "PostgreSQL 16, real job providers; Gemini answered by a local stub (SDK in runs 2-3, REST client in run 4).", "",
         "| Criterion | Result |", "|---|---|"] + [f"| {c} | {'PASS' if ok else 'FAIL'} |" for c, ok in checks]
    labels = {"onnx-rest-ext": "CANDIDATE: tuned ONNX + REST Gemini client, 8 threads, job sync in a separate process (run 5)",
              "onnx-rest-ext-t4": "same as onnx-rest-ext with 4 gunicorn threads (run 5)",
              "onnx-rest": "tuned ONNX MiniLM + REST Gemini client (no google-genai SDK), 8 threads (run 4)",
              "onnx-rest-t4": "same as onnx-rest with 4 gunicorn threads (run 4)",
              "onnx-tuned": "candidate: ONNX MiniLM, batch 8, ONNX arena off, MALLOC_ARENA_MAX=2, prebuilt KB index",
              "torch-tuned": "PyTorch MiniLM with the same tuning (batch 8, MALLOC_ARENA_MAX=2, prebuilt KB index)",
              "onnx": "ONNX MiniLM, untuned (run 2)", "torch": "current PyTorch image, untuned (run 2)"}
    for v in variants:
        m = v["mem"]
        L += ["", f"## Image: {v['variant']} ({labels.get(v['variant'], '')})",
              f"- Time to healthy at 0.1 CPU: {v['startup_s']} s",
              f"- Peak anonymous memory: **{m.get('overall_max_anon_mb')} MB**; peak charged incl. page cache: "
              f"{m.get('overall_max_current_mb')} MB; kernel memory.peak: {m.get('memory_peak_mb')} MB; limit {m.get('memory_max')}",
              f"- OOM: oom_kill={v['oom_kill']}, oom events={v['oom_events']}, worker SIGKILL={v['worker_sigkill']}, "
              f"OOMKilled={v['oom_killed_flag']}",
              "", "| Phase | Peak anon MB | Peak charged MB |", "|---|---|---|"]
        L += [f"| {p} | {d['max_anon_mb']} | {d['max_current_mb']} |" for p, d in m.get("phases", {}).items()]
        e = v["e2e"]
        L += ["", f"- End-to-end check: {e['pass']} pass, {e['warn']} warn, {e['fail']} fail "
                  f"(harness-only: {[r[1] for r in e['harness_fail']]}; real: {[(r[0], r[1], r[3][:80]) for r in e['real_fail']]})"]
        ld = v["load"]
        if ld:
            L += [f"- Load test: {ld.get('requests_ok')} ok / {ld.get('requests_failed')} failed in {ld.get('seconds')} s, "
                  f"{ld.get('concurrent_students')} concurrent students + recruiter + FL + job sync", "",
                  "| Feature | ok | failed | p50 s | p95 s | first error |", "|---|---|---|---|---|---|"]
            L += [f"| {k} | {f['ok']} | {f['fail']} | {f['p50_s']} | {f['p95_s']} | {(f['errors'] or [''])[0][:70]} |"
                  for k, f in ld.get("by_feature", {}).items()]
    if parity:
        L += ["", "## Retrieval quality (rag/eval_retrieval.py benchmark + app knowledge-base search)",
              "| Engine | R@1 all | R@3 all | MRR all | R@1 paraphrase | R@3 paraphrase |", "|---|---|---|---|---|---|"]
        for eng, b in parity.get("benchmark", {}).items():
            L.append(f"| {eng} | {b['all']['recall@1']} | {b['all']['recall@3']} | {b['all']['mrr']} | "
                     f"{b['paraphrase']['recall@1']} | {b['paraphrase']['recall@3']} |")
        L += [f"- Vector cosine PyTorch vs ONNX: {parity.get('vector_cosine')}",
              f"- Full benchmark rankings identical: {parity.get('benchmark_full_ranking_identical')}; "
              f"knowledge-base top-5 identical: {parity.get('kb_search_top5_identical')}; "
              f"max score difference: {parity.get('kb_search_max_score_difference')}"]
    for pv in ("onnx", "torch"):
        prof = load(f"profile_{pv}.json")
        if prof:
            L += ["", f"## Step-by-step peak memory, {pv} image (fresh process each, no limit)",
                  "| Configuration | Peak RSS MB |", "|---|---|"]
            L += [f"| {r['config']} | {r['peak_rss_mb']} |" for r in prof["results"]]
    if tests:
        L += ["", f"## Unit tests in slim image: {tests.get('ran')} run, {tests.get('failures')} failures, "
                  f"{tests.get('errors')} errors", *[f"- {t}" for t in tests.get("failed_tests", [])]]
    stub = {v: load(f"gemini_stub_{v}.json") for v in ("onnx", "torch")}
    L += ["", f"Gemini stub requests served: {stub}"]
    open(os.path.join(R, "SUMMARY.md"), "w").write("\n".join(L) + "\n")
    json.dump({"verdict": verdict, "checks": checks}, open(os.path.join(R, "verdict.json"), "w"), indent=1)
    print("\n".join(L))


if __name__ == "__main__":
    main()
