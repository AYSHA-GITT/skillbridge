"""
gunicorn entry point for the Phase 0 measurement (harness only).

PHASE0_VARIANT=onnx   -> MiniLM served by ONNX Runtime (onnx_shim)
PHASE0_VARIANT=torch  -> the app exactly as it is today (PyTorch sentence-transformers)

Rate limiting is switched off ONLY because every request in the load test comes
from one IP (127.0.0.1); it has no measurable memory cost either way.
"""
import os

import onnx_shim  # noqa: E402

if os.getenv("PHASE0_VARIANT", "onnx").startswith("onnx"):
    onnx_shim.install()
else:
    onnx_shim.install_torch_batch()

from app import app  # noqa: E402

app.config["RATELIMIT_ENABLED"] = False
