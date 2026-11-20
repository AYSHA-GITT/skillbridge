"""
Phase 0 prototype (harness only): a minimal, dependency-free replacement for the
google-genai SDK covering exactly what SkillBridge uses:

    client = genai.Client(api_key=...)
    resp = client.models.generate_content(model="gemini-...", contents="<prompt>")
    resp.text

It calls the same public REST endpoint the SDK uses
(POST {base}/v1beta/models/{model}:generateContent) over HTTPS with `requests`,
sending the key in the x-goog-api-key header (never in the URL, so it cannot leak
into logs). GOOGLE_GEMINI_BASE_URL is honoured like the SDK does. Errors raise,
exactly where the SDK would raise, so every caller's existing fallback still runs.

Placed first on sys.path, this package shadows google.genai; `google` is a
namespace package, so google.protobuf and others are unaffected.
"""
import os

import requests

__all__ = ["Client"]
DEFAULT_BASE = "https://generativelanguage.googleapis.com"
TIMEOUT = float(os.getenv("GEMINI_HTTP_TIMEOUT", "60"))


class GenerateContentResponse:
    def __init__(self, payload):
        self.raw = payload
        parts = []
        for cand in (payload.get("candidates") or [])[:1]:
            for part in ((cand.get("content") or {}).get("parts") or []):
                if isinstance(part, dict) and isinstance(part.get("text"), str):
                    parts.append(part["text"])
        self.text = "".join(parts) if parts else None


class APIError(Exception):
    def __init__(self, status, message):
        super().__init__(f"Gemini API error {status}: {message}")
        self.status = status


class _Models:
    def __init__(self, client):
        self._client = client

    def generate_content(self, model, contents, config=None, **_):
        if isinstance(contents, str):
            body_contents = [{"role": "user", "parts": [{"text": contents}]}]
        elif isinstance(contents, list) and all(isinstance(c, str) for c in contents):
            body_contents = [{"role": "user", "parts": [{"text": c} for c in contents]}]
        else:
            body_contents = contents
        model_path = model if model.startswith("models/") else f"models/{model}"
        url = f"{self._client.base_url}/v1beta/{model_path}:generateContent"
        r = self._client.session.post(url, json={"contents": body_contents},
                                      headers={"x-goog-api-key": self._client.api_key,
                                               "Content-Type": "application/json"},
                                      timeout=TIMEOUT)
        if r.status_code >= 400:
            try:
                msg = (r.json().get("error") or {}).get("message") or r.text[:200]
            except ValueError:
                msg = r.text[:200]
            raise APIError(r.status_code, msg)
        return GenerateContentResponse(r.json())


class Client:
    def __init__(self, api_key=None, **_):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("No API key was provided.")   # same behaviour as the SDK
        self.base_url = (os.getenv("GOOGLE_GEMINI_BASE_URL") or DEFAULT_BASE).rstrip("/")
        self.session = requests.Session()
        self.models = _Models(self)
