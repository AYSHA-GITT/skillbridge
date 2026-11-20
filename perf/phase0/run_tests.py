"""
Runs the backend unit-test suite inside the slim (no-PyTorch) image with ONNX MiniLM
installed, and writes a JSON summary (Phase 0 harness only).
Usage (in the container, cwd /app): python /phase0/run_tests.py /out/unit_tests.json
"""
import json
import sys
import unittest

sys.path[:0] = ["/phase0", "/app"]
import onnx_shim  # noqa: E402

onnx_shim.install()

suite = unittest.defaultTestLoader.discover("tests")
result = unittest.TextTestRunner(verbosity=1).run(suite)
summary = {
    "ran": result.testsRun,
    "failures": len(result.failures),
    "errors": len(result.errors),
    "skipped": len(result.skipped),
    "ok": result.wasSuccessful(),
    "failed_tests": [str(t) for t, _ in result.failures + result.errors][:50],
    "details": [tb[-1500:] for _, tb in (result.failures + result.errors)][:10],
}
json.dump(summary, open(sys.argv[1], "w"), indent=1)
print(json.dumps({k: summary[k] for k in ("ran", "failures", "errors", "ok")}))
sys.exit(0 if result.wasSuccessful() else 1)
