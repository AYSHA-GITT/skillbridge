# Phase 0 result: **FAIL**

Render free-tier conditions: `--memory=512m --memory-swap=512m --cpus=0.1`, gunicorn 1 worker x 8 threads, PostgreSQL 16, real job providers, Gemini via the real google-genai SDK against a local stub.

| Criterion | Result |
|---|---|
| No OOM kill (cgroup oom_kill, OOMKilled flag, worker SIGKILL) | FAIL |
| Peak anonymous memory <= 450 MB (measured 508.9 MB) | FAIL |
| ONNX MiniLM actually served RAG (log line present, no fallback) | PASS |
| No HTTP 5xx / dropped connection under concurrent load | FAIL |
| End-to-end: no failures except harness-only (7 real) | FAIL |
| Retrieval quality equivalent to PyTorch MiniLM | PASS |
| Backend unit tests in slim image (229 run) | PASS |

## Image: onnx (candidate, ONNX MiniLM)
- Time to healthy at 0.1 CPU: 46 s
- Peak anonymous memory: **508.9 MB**; peak charged incl. page cache: 512.0 MB; kernel memory.peak: 512.0 MB; limit 536870912
- OOM: oom_kill=10, oom events=17, worker SIGKILL=20, OOMKilled=True

| Phase | Peak anon MB | Peak charged MB |
|---|---|---|
| startup | 230.0 | 238.7 |
| idle | 230.2 | 238.9 |
| e2e | 508.9 | 512.0 |
| setup | 344.2 | 353.5 |
| stress | 508.2 | 512.0 |
| after | 184.7 | 191.9 |

- End-to-end check: 184 pass, 3 warn, 8 fail (harness-only: ['Cleanup e2e organisation']; real: [('RAG assistant', 'RAG resume analysis', 'HTTP 599'), ('RAG assistant', 'RAG job match', 'HTTP 599'), ('RAG assistant', 'RAG explain gap', 'HTTP 599'), ('RAG assistant', 'RAG catalog', ''), ('Jobs', 'Search + pagination', 'total=0 pages=0'), ('Account', 'Delete account e2e_a_f11ed0ad', ''), ('Account', 'Deleted account cannot log in', '')])
- Load test: 131 ok / 48 failed in 300 s, 8 concurrent students + recruiter + FL + job sync

| Feature | ok | failed | p50 s | p95 s | first error |
|---|---|---|---|---|---|
| RAG assistant (Gemini) | 5 | 7 | 15.0 | 66.1 | ConnectionError: ('Connection aborted.', ConnectionResetError(104, 'Co |
| RAG explain gap | 0 | 7 | 16.43 | 61.0 | ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote en |
| RAG job match | 0 | 15 | 21.52 | 66.11 | ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote en |
| RAG resume analysis | 0 | 7 | 19.82 | 61.01 | ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote en |
| career recommendations | 11 | 0 | 0.9 | 45.36 |  |
| federated learning round | 6 | 0 | 45.4 | 45.89 |  |
| interview start (Gemini) | 3 | 0 | 45.76 | 45.76 |  |
| job match breakdown | 13 | 1 | 1.64 | 47.27 | ConnectionError: ('Connection aborted.', ConnectionResetError(104, 'Co |
| job sync (live providers) | 0 | 1 | 21.51 | 21.51 | ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote en |
| jobs by match | 6 | 0 | 5.35 | 46.07 |  |
| quiz | 6 | 0 | 24.93 | 45.08 |  |
| readiness breakdown | 7 | 0 | 2.7 | 46.18 |  |
| recruiter candidate search | 1 | 0 | 4.09 | 4.09 |  |
| recruiter match report | 8 | 4 | 2.45 | 8.03 | ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote en |
| recruiter search | 12 | 0 | 5.2 | 48.16 |  |
| recruiter verification request | 4 | 1 | 2.5 | 3.0 | ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote en |
| resume export DOCX | 4 | 1 | 5.63 | 47.86 | ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote en |
| resume export PDF | 6 | 0 | 3.15 | 44.07 |  |
| resume optimizer analyze | 3 | 0 | 1.6 | 1.6 |  |
| resume parse | 10 | 0 | 2.75 | 4.1 |  |
| resume upload | 10 | 0 | 1.75 | 44.47 |  |
| skill extraction | 8 | 2 | 2.2 | 3.6 | ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote en |
| skill gap analysis | 2 | 2 | 2.12 | 2.94 | ConnectionError: ('Connection aborted.', ConnectionResetError(104, 'Co |
| skill passport PDF | 6 | 0 | 3.34 | 45.16 |  |

## Image: torch (current, PyTorch MiniLM)
- Time to healthy at 0.1 CPU: 32 s
- Peak anonymous memory: **508.4 MB**; peak charged incl. page cache: 512.0 MB; kernel memory.peak: 512.0 MB; limit 536870912
- OOM: oom_kill=9, oom events=13, worker SIGKILL=18, OOMKilled=True

| Phase | Peak anon MB | Peak charged MB |
|---|---|---|
| startup | 229.9 | 238.1 |
| idle | 230.0 | 238.6 |
| e2e | 508.4 | 512.0 |
| setup | 344.1 | 353.2 |
| stress | 508.4 | 512.0 |
| after-stress | 172.5 | 178.7 |
| after | 230.0 | 238.2 |

- End-to-end check: 182 pass, 3 warn, 10 fail (harness-only: ['Cleanup e2e organisation']; real: [('Career guidance', 'Readiness breakdown', '{}'), ('Career guidance', 'Readiness links to a jobs domain', 'None'), ('RAG assistant', 'RAG resume analysis', 'HTTP 599'), ('RAG assistant', 'RAG job match', 'HTTP 599'), ('RAG assistant', 'RAG explain gap', 'HTTP 599'), ('RAG assistant', 'RAG catalog', ''), ('Jobs', 'Search + pagination', 'total=0 pages=0'), ('Account', 'Delete account e2e_a_20862317', ''), ('Account', 'Deleted account cannot log in', '')])
- Load test: 132 ok / 51 failed in 300 s, 8 concurrent students + recruiter + FL + job sync

| Feature | ok | failed | p50 s | p95 s | first error |
|---|---|---|---|---|---|
| RAG assistant (Gemini) | 0 | 12 | 35.11 | 66.7 | ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote en |
| RAG explain gap | 0 | 12 | 34.06 | 70.88 | ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote en |
| RAG job match | 0 | 6 | 66.85 | 70.88 | ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote en |
| RAG resume analysis | 0 | 9 | 37.31 | 67.01 | ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote en |
| career recommendations | 12 | 0 | 0.6 | 30.27 |  |
| federated learning round | 5 | 5 | 12.45 | 18.6 | ConnectionError: ('Connection aborted.', ConnectionResetError(104, 'Co |
| interview start (Gemini) | 1 | 0 | 29.38 | 29.38 |  |
| job match breakdown | 14 | 0 | 1.35 | 29.98 |  |
| job sync (live providers) | 0 | 1 | 33.91 | 33.91 | ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote en |
| jobs by match | 11 | 1 | 2.05 | 29.08 | ConnectionError: ('Connection aborted.', ConnectionResetError(104, 'Co |
| quiz | 1 | 0 | 29.58 | 29.58 |  |
| recruiter candidate search | 1 | 0 | 2.39 | 2.39 |  |
| recruiter match report | 10 | 2 | 1.9 | 31.27 | ConnectionError: ('Connection aborted.', ConnectionResetError(104, 'Co |
| recruiter search | 9 | 3 | 4.85 | 31.61 | ConnectionError: ('Connection aborted.', ConnectionResetError(104, 'Co |
| recruiter verification request | 6 | 0 | 1.0 | 1.4 |  |
| resume export DOCX | 4 | 0 | 31.03 | 31.78 |  |
| resume optimizer analyze | 4 | 0 | 1.7 | 2.5 |  |
| resume parse | 16 | 0 | 1.25 | 4.1 |  |
| resume upload | 16 | 0 | 0.95 | 30.97 |  |
| skill extraction | 16 | 0 | 1.1 | 2.3 |  |
| skill gap analysis | 2 | 0 | 15.5 | 1.03 |  |
| skill passport PDF | 4 | 0 | 15.74 | 29.18 |  |

## Retrieval quality (rag/eval_retrieval.py benchmark + app knowledge-base search)
| Engine | R@1 all | R@3 all | MRR all | R@1 paraphrase | R@3 paraphrase |
|---|---|---|---|---|---|
| torch | 0.852 | 1.0 | 0.926 | 0.778 | 1.0 |
| onnx | 0.852 | 1.0 | 0.926 | 0.778 | 1.0 |
- Vector cosine PyTorch vs ONNX: {'min': 1.0, 'mean': 1.0, 'texts': 36}
- Full benchmark rankings identical: 27/27; knowledge-base top-5 identical: 27/27; max score difference: 0.0

## Unit tests in slim image: 229 run, 0 failures, 0 errors

Gemini stub requests served: {'onnx': {'requests': 32, 'by_kind': {'quiz': 8, 'roadmap': 12, 'text': 12}}, 'torch': {'requests': 19, 'by_kind': {'quiz': 3, 'roadmap': 12, 'text': 4}}}
