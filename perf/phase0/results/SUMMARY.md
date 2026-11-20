# Phase 0 result: **FAIL**

Render free-tier conditions: `--memory=512m --memory-swap=512m --cpus=0.1`, gunicorn 1 worker x 8 threads, PostgreSQL 16, real job providers, Gemini via the real google-genai SDK against a local stub.

| Criterion | Result |
|---|---|
| Candidate image measured | FAIL |
| Retrieval quality equivalent to PyTorch MiniLM | FAIL |
| Backend unit tests in slim image (0 run) | FAIL |

Gemini stub requests served: {'onnx': None, 'torch': None}
