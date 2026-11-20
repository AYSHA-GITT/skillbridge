# Phase 0 result: **FAIL** (candidate image: onnx-rest)

Render free-tier conditions: `--memory=512m --memory-swap=512m --cpus=0.1`, gunicorn 1 worker x 8 threads, PostgreSQL 16, real job providers; Gemini answered by a local stub (SDK in runs 2-3, REST client in run 4).

| Criterion | Result |
|---|---|
| No OOM kill (cgroup oom_kill, OOMKilled flag, worker SIGKILL) | PASS |
| Peak anonymous memory <= 450 MB (measured 505.2 MB) | FAIL |
| ONNX MiniLM actually served RAG (log line present, no fallback) | PASS |
| No HTTP 5xx / dropped connection under concurrent load | PASS |
| End-to-end: no failures except harness-only (4 real) | FAIL |
| Retrieval quality equivalent to PyTorch MiniLM | PASS |
| Backend unit tests in slim image (229 run) | PASS |

## Image: onnx-rest (CANDIDATE: tuned ONNX MiniLM + REST Gemini client (no google-genai SDK), 8 threads (run 4))
- Time to healthy at 0.1 CPU: 34 s
- Peak anonymous memory: **505.2 MB**; peak charged incl. page cache: 511.2 MB; kernel memory.peak: 513.0 MB; limit 536870912
- OOM: oom_kill=0, oom events=0, worker SIGKILL=0, OOMKilled=False

| Phase | Peak anon MB | Peak charged MB |
|---|---|---|
| startup | 184.2 | 191.9 |
| idle | 184.4 | 191.9 |
| e2e | 413.4 | 422.8 |
| setup | 415.3 | 424.9 |
| stress | 505.2 | 511.2 |
| after | 505.2 | 509.9 |

- End-to-end check: 199 pass, 2 warn, 5 fail (harness-only: ['Cleanup e2e organisation']; real: [('Career guidance', 'Readiness breakdown', '{}'), ('Career guidance', 'Readiness links to a jobs domain', 'None'), ('Account', 'Delete account e2e_a_201e3a66', ''), ('Account', 'Deleted account cannot log in', '')])
- Load test: 1187 ok / 0 failed in 300 s, 8 concurrent students + recruiter + FL + job sync

| Feature | ok | failed | p50 s | p95 s | first error |
|---|---|---|---|---|---|
| RAG assistant (Gemini) | 105 | 0 | 1.5 | 3.1 |  |
| RAG explain gap | 64 | 0 | 1.35 | 3.3 |  |
| RAG job match | 66 | 0 | 1.45 | 3.09 |  |
| RAG resume analysis | 82 | 0 | 1.25 | 2.8 |  |
| career recommendations | 77 | 0 | 1.09 | 2.3 |  |
| federated learning round | 13 | 0 | 3.01 | 4.6 |  |
| interview start (Gemini) | 36 | 0 | 1.4 | 3.0 |  |
| job match breakdown | 60 | 0 | 2.2 | 3.9 |  |
| job sync (live providers) | 1 | 0 | 448.28 | 448.28 |  |
| jobs by match | 67 | 0 | 3.4 | 5.4 |  |
| quiz | 34 | 0 | 1.54 | 3.2 |  |
| readiness breakdown | 41 | 0 | 1.99 | 3.39 |  |
| recruiter candidate search | 1 | 0 | 8.89 | 8.89 |  |
| recruiter match report | 23 | 0 | 2.9 | 5.0 |  |
| recruiter search | 23 | 0 | 8.2 | 11.9 |  |
| recruiter verification request | 8 | 0 | 3.65 | 4.3 |  |
| resume export DOCX | 34 | 0 | 6.15 | 8.7 |  |
| resume export PDF | 47 | 0 | 0.7 | 1.7 |  |
| resume optimizer analyze | 45 | 0 | 0.9 | 2.4 |  |
| resume parse | 97 | 0 | 3.3 | 7.1 |  |
| resume upload | 97 | 0 | 1.39 | 3.2 |  |
| skill extraction | 97 | 0 | 2.9 | 5.49 |  |
| skill gap analysis | 35 | 0 | 1.79 | 3.1 |  |
| skill passport PDF | 34 | 0 | 1.6 | 3.21 |  |

## Image: onnx-rest-t4 (same as onnx-rest with 4 gunicorn threads (run 4))
- Time to healthy at 0.1 CPU: 35 s
- Peak anonymous memory: **452.7 MB**; peak charged incl. page cache: 463.8 MB; kernel memory.peak: 464.1 MB; limit 536870912
- OOM: oom_kill=0, oom events=0, worker SIGKILL=0, OOMKilled=False

| Phase | Peak anon MB | Peak charged MB |
|---|---|---|
| startup | 184.2 | 191.6 |
| idle | 184.4 | 191.6 |
| e2e | 414.3 | 423.3 |
| setup | 416.2 | 425.5 |
| stress | 452.7 | 463.8 |
| after | 448.1 | 459.1 |

- End-to-end check: 199 pass, 2 warn, 5 fail (harness-only: ['Cleanup e2e organisation']; real: [('Career guidance', 'Readiness breakdown', '{}'), ('Career guidance', 'Readiness links to a jobs domain', 'None'), ('Account', 'Delete account e2e_a_2ee5d9b4', ''), ('Account', 'Deleted account cannot log in', '')])
- Load test: 671 ok / 0 failed in 300 s, 8 concurrent students + recruiter + FL + job sync

| Feature | ok | failed | p50 s | p95 s | first error |
|---|---|---|---|---|---|
| RAG assistant (Gemini) | 47 | 0 | 3.3 | 7.1 |  |
| RAG explain gap | 33 | 0 | 3.2 | 5.6 |  |
| RAG job match | 44 | 0 | 2.65 | 6.71 |  |
| RAG resume analysis | 34 | 0 | 3.15 | 6.0 |  |
| career recommendations | 45 | 0 | 2.7 | 7.4 |  |
| federated learning round | 12 | 0 | 5.4 | 7.71 |  |
| interview start (Gemini) | 27 | 0 | 2.99 | 5.39 |  |
| job match breakdown | 39 | 0 | 3.5 | 7.8 |  |
| job sync (live providers) | 1 | 0 | 344.19 | 344.19 |  |
| jobs by match | 38 | 0 | 4.1 | 7.2 |  |
| quiz | 21 | 0 | 3.7 | 6.21 |  |
| readiness breakdown | 10 | 0 | 2.99 | 5.6 |  |
| recruiter candidate search | 1 | 0 | 6.09 | 6.09 |  |
| recruiter match report | 22 | 0 | 4.35 | 6.51 |  |
| recruiter search | 22 | 0 | 9.2 | 11.99 |  |
| recruiter verification request | 8 | 0 | 2.9 | 6.2 |  |
| resume export DOCX | 25 | 0 | 6.6 | 11.6 |  |
| resume export PDF | 19 | 0 | 2.3 | 5.21 |  |
| resume optimizer analyze | 13 | 0 | 2.31 | 6.2 |  |
| resume parse | 62 | 0 | 5.35 | 9.6 |  |
| resume upload | 62 | 0 | 3.75 | 6.3 |  |
| skill extraction | 62 | 0 | 4.75 | 8.2 |  |
| skill gap analysis | 10 | 0 | 3.7 | 5.9 |  |
| skill passport PDF | 14 | 0 | 2.56 | 5.1 |  |

## Image: onnx-tuned (candidate: ONNX MiniLM, batch 8, ONNX arena off, MALLOC_ARENA_MAX=2, prebuilt KB index)
- Time to healthy at 0.1 CPU: 32 s
- Peak anonymous memory: **505.3 MB**; peak charged incl. page cache: 512.8 MB; kernel memory.peak: 513.2 MB; limit 536870912
- OOM: oom_kill=1, oom events=1, worker SIGKILL=2, OOMKilled=True

| Phase | Peak anon MB | Peak charged MB |
|---|---|---|
| startup | 230.1 | 238.7 |
| idle | 230.2 | 239.0 |
| e2e | 427.2 | 437.6 |
| setup | 429.0 | 439.8 |
| stress | 505.3 | 512.8 |
| after | 461.2 | 472.3 |

- End-to-end check: 201 pass, 2 warn, 3 fail (harness-only: ['Cleanup e2e organisation']; real: [('Account', 'Delete account e2e_a_a2d39e24', ''), ('Account', 'Deleted account cannot log in', '')])
- Load test: 1387 ok / 10 failed in 300 s, 8 concurrent students + recruiter + FL + job sync

| Feature | ok | failed | p50 s | p95 s | first error |
|---|---|---|---|---|---|
| RAG assistant (Gemini) | 125 | 1 | 1.16 | 3.91 | ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote en |
| RAG explain gap | 72 | 0 | 1.51 | 2.3 |  |
| RAG job match | 71 | 0 | 1.6 | 2.5 |  |
| RAG resume analysis | 70 | 0 | 1.4 | 2.3 |  |
| career recommendations | 75 | 0 | 0.7 | 1.2 |  |
| federated learning round | 14 | 0 | 1.75 | 2.9 |  |
| interview start (Gemini) | 49 | 0 | 1.1 | 2.0 |  |
| job match breakdown | 86 | 2 | 1.5 | 2.8 | ConnectionError: ('Connection aborted.', ConnectionResetError(104, 'Co |
| job sync (live providers) | 0 | 1 | 159.32 | 159.32 | ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote en |
| jobs by match | 84 | 2 | 2.25 | 3.7 | ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote en |
| quiz | 49 | 0 | 1.2 | 2.5 |  |
| readiness breakdown | 39 | 0 | 1.4 | 2.7 |  |
| recruiter candidate search | 1 | 0 | 5.9 | 5.9 |  |
| recruiter match report | 33 | 0 | 1.91 | 3.4 |  |
| recruiter search | 32 | 1 | 5.5 | 7.71 | ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote en |
| recruiter verification request | 8 | 0 | 2.6 | 2.89 |  |
| resume export DOCX | 33 | 2 | 4.3 | 6.29 | ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote en |
| resume export PDF | 29 | 0 | 0.7 | 1.5 |  |
| resume optimizer analyze | 33 | 0 | 1.2 | 2.4 |  |
| resume parse | 135 | 0 | 1.9 | 4.8 |  |
| resume upload | 135 | 0 | 0.99 | 1.81 |  |
| skill extraction | 134 | 1 | 2.0 | 3.1 | ConnectionError: ('Connection aborted.', ConnectionResetError(104, 'Co |
| skill gap analysis | 33 | 0 | 1.2 | 2.6 |  |
| skill passport PDF | 47 | 0 | 1.19 | 2.0 |  |

## Image: torch-tuned (PyTorch MiniLM with the same tuning (batch 8, MALLOC_ARENA_MAX=2, prebuilt KB index))
- Time to healthy at 0.1 CPU: 62 s
- Peak anonymous memory: **508.7 MB**; peak charged incl. page cache: 512.0 MB; kernel memory.peak: 512.0 MB; limit 536870912
- OOM: oom_kill=8, oom events=8, worker SIGKILL=16, OOMKilled=True

| Phase | Peak anon MB | Peak charged MB |
|---|---|---|
| startup | 460.2 | 476.0 |
| idle | 460.3 | 476.2 |
| e2e | 508.7 | 511.9 |
| setup | 505.0 | 510.7 |
| stress | 507.7 | 512.0 |
| after | 316.0 | 327.3 |

- End-to-end check: 196 pass, 3 warn, 7 fail (harness-only: ['Cleanup e2e organisation']; real: [('Career guidance', 'Readiness breakdown', '{}'), ('Career guidance', 'Readiness links to a jobs domain', 'None'), ('Admin', 'Manual sync', '1.0s status=None new=None upd=None'), ('Admin', 'Audit log records manual sync', ''), ('Account', 'Delete account e2e_a_e5d5ef22', ''), ('Account', 'Deleted account cannot log in', '')])
- Load test: 145 ok / 40 failed in 300 s, 8 concurrent students + recruiter + FL + job sync

| Feature | ok | failed | p50 s | p95 s | first error |
|---|---|---|---|---|---|
| RAG assistant (Gemini) | 0 | 12 | 10.47 | 73.49 | ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote en |
| RAG explain gap | 2 | 5 | 14.3 | 69.11 | ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote en |
| RAG job match | 0 | 7 | 11.14 | 69.11 | ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote en |
| RAG resume analysis | 0 | 7 | 10.73 | 73.5 | ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote en |
| career recommendations | 12 | 0 | 1.9 | 60.78 |  |
| federated learning round | 5 | 0 | 55.0 | 55.2 |  |
| interview start (Gemini) | 4 | 1 | 1.31 | 1.9 | ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote en |
| job match breakdown | 8 | 1 | 2.99 | 62.77 | ConnectionError: ('Connection aborted.', ConnectionResetError(104, 'Co |
| job sync (live providers) | 0 | 1 | 2.19 | 2.19 | HTTP 409 {"run":{"alerts_created":0,"duplicate_count":0,"error":"Anoth |
| jobs by match | 9 | 0 | 2.3 | 3.3 |  |
| quiz | 3 | 0 | 1.4 | 1.4 |  |
| readiness breakdown | 5 | 1 | 3.01 | 60.47 | ConnectionError: ('Connection aborted.', ConnectionResetError(104, 'Co |
| recruiter candidate search | 1 | 0 | 3.8 | 3.8 |  |
| recruiter match report | 12 | 1 | 1.4 | 61.57 | ConnectionError: ('Connection aborted.', ConnectionResetError(104, 'Co |
| recruiter search | 10 | 3 | 2.11 | 4.42 | ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote en |
| recruiter verification request | 6 | 0 | 1.1 | 1.7 |  |
| resume export DOCX | 1 | 0 | 62.48 | 62.48 |  |
| resume export PDF | 5 | 0 | 2.3 | 59.17 |  |
| resume optimizer analyze | 3 | 0 | 1.8 | 1.8 |  |
| resume parse | 17 | 0 | 1.4 | 3.69 |  |
| resume upload | 17 | 0 | 1.51 | 60.98 |  |
| skill extraction | 17 | 0 | 1.19 | 2.5 |  |
| skill gap analysis | 4 | 0 | 0.5 | 0.5 |  |
| skill passport PDF | 4 | 1 | 1.5 | 2.03 | ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote en |

## Image: onnx (ONNX MiniLM, untuned (run 2))
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

## Image: torch (current PyTorch image, untuned (run 2))
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

## Step-by-step peak memory, onnx image (fresh process each, no limit)
| Configuration | Peak RSS MB |
|---|---|
| python only | 13.5 |
| google-genai SDK import only | 96.1 |
| app import (incl. genai, sklearn, flwr, pandas) | 300.4 |
| app + MiniLM + one query | 473.5 |
| app + build KB index: batch 256, arena on (as tested) | 684.8 |
| app + build KB index: batch 8, arena on | 532.9 |
| app + build KB index: batch 8, arena off | 513.0 |
| app + build KB index: batch 8, arena off, MALLOC_ARENA_MAX=2 | 538.2 |
| app + LOAD prebuilt KB index (no re-encoding), tuned | 480.2 |
| REST Gemini client: app import | 250.1 |
| REST Gemini client: app + LOAD prebuilt KB index, tuned | 440.6 |

## Step-by-step peak memory, torch image (fresh process each, no limit)
| Configuration | Peak RSS MB |
|---|---|
| python only | 14.1 |
| google-genai SDK import only | 95.3 |
| app import (incl. genai, sklearn, flwr, pandas) | 301.2 |
| app + MiniLM + one query | 713.2 |
| app + build KB index: batch 32 (as tested) | 905.1 |
| app + build KB index: batch 8, MALLOC_ARENA_MAX=2 | 804.6 |
| app + LOAD prebuilt KB index (no re-encoding), tuned | 733.7 |

## Unit tests in slim image: 229 run, 0 failures, 0 errors

Gemini stub requests served: {'onnx': {'requests': 32, 'by_kind': {'quiz': 8, 'roadmap': 12, 'text': 12}}, 'torch': {'requests': 19, 'by_kind': {'quiz': 3, 'roadmap': 12, 'text': 4}}}
