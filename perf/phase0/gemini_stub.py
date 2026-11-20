"""
Local stand-in for the Gemini REST API (Phase 0 harness only).

The app keeps using the real google-genai SDK; GOOGLE_GEMINI_BASE_URL points it
here, so the SDK's full request/response path (and its memory) is exercised
without an API key, quota or network. Replies follow the formats the app asks
for (quiz questions, roadmap days); anything else gets a short grounded answer,
and callers with stricter formats use their existing fallbacks.

Also serves the built React app on another port (SPA fallback to index.html),
so e2e_check.py's "frontend serves" checks run as they do locally.

Usage: python gemini_stub.py <gemini_port> <frontend_build_dir> <frontend_port> <stats_json>
"""
import json
import os
import re
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer, BaseHTTPRequestHandler

STATS = {"requests": 0, "by_kind": {}}
LOCK = threading.Lock()


def _reply_text(prompt: str) -> tuple[str, str]:
    m = re.search(r"exactly\s+(\d+)\s+multiple-choice", prompt, re.I)
    if m:
        n = int(m.group(1))
        skill = (re.search(r'for the skill "([^"]+)"', prompt) or [None, "the skill"])[1]
        qs = [{"question": f"Phase 0 question {i + 1} about {skill}?",
               "option_a": "Correct statement", "option_b": "Distractor one",
               "option_c": "Distractor two", "option_d": "Distractor three",
               "correct_answer": "A", "difficulty": ["Easy", "Medium", "Hard"][i % 3]} for i in range(n)]
        return "quiz", json.dumps(qs)
    if '"day_number"' in prompt or "day_number" in prompt:
        days = [{"day_number": d, "topic": f"Day {d} topic", "description": "Study the core ideas and practise.",
                 "resource_hint": "YouTube: tutorial", "duration_hours": 1.5} for d in range(1, 5)]
        return "roadmap", json.dumps(days)
    return "text", ("Based on the retrieved SkillBridge context, focus on the required skills listed for the "
                    "career, verify them with assessments and build one project for each [1].")


class GeminiHandler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        try:
            req = json.loads(body or b"{}")
        except ValueError:
            req = {}
        parts = []
        for c in req.get("contents", []) or []:
            for p in (c.get("parts", []) if isinstance(c, dict) else []):
                if isinstance(p, dict) and p.get("text"):
                    parts.append(p["text"])
        kind, text = _reply_text("\n".join(parts))
        model = (re.search(r"models/([^:/]+)", self.path) or [None, "stub"])[1]
        out = json.dumps({
            "candidates": [{"content": {"parts": [{"text": text}], "role": "model"},
                            "finishReason": "STOP", "index": 0}],
            "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 10, "totalTokenCount": 20},
            "modelVersion": model}).encode()
        with LOCK:
            STATS["requests"] += 1
            STATS["by_kind"][kind] = STATS["by_kind"].get(kind, 0) + 1
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)


def spa_handler(root):
    class SPA(SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=root, **kw)

        def log_message(self, *a):
            pass

        def send_head(self):
            path = self.translate_path(self.path)
            if not os.path.exists(path):
                self.path = "/index.html"
            return super().send_head()
    return SPA


def main():
    g_port, build_dir, f_port, stats_path = int(sys.argv[1]), sys.argv[2], int(sys.argv[3]), sys.argv[4]
    threading.Thread(target=ThreadingHTTPServer(("0.0.0.0", f_port), spa_handler(build_dir)).serve_forever,
                     daemon=True).start()

    def dump():
        while True:
            threading.Event().wait(5)
            with LOCK:
                json.dump(STATS, open(stats_path, "w"))
    threading.Thread(target=dump, daemon=True).start()
    ThreadingHTTPServer(("0.0.0.0", g_port), GeminiHandler).serve_forever()


if __name__ == "__main__":
    main()
