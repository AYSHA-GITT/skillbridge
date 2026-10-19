import os
import time
import json
import logging
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List


class AIProvider(ABC):
    """
    Shared AI Provider Interface.
    Enables pluggable switching between Google Gemini, Ollama (Qwen), and xAI Grok.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass

    @abstractmethod
    def generate_text(self, prompt: str, system_instruction: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes text generation. Returns dictionary:
        {
            'text': str,
            'provider': str,
            'model': str,
            'latency_ms': float,
            'is_local': bool
        }
        """
        pass


class GeminiProvider(AIProvider):
    """
    Google GenAI provider (Gemini 3.5 / 3.6 Flash).
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-3.5-flash"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self._model = model
        self._client = None

    @property
    def provider_name(self) -> str:
        return "Google Gemini"

    @property
    def model_name(self) -> str:
        return self._model

    def _get_client(self):
        if self._client is None and self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logging.warning(f"Could not initialize Gemini Client: {e}")
                self._client = None
        return self._client

    def is_available(self) -> bool:
        return bool(self.api_key and self.api_key != "your_gemini_api_key_here")

    def generate_text(self, prompt: str, system_instruction: Optional[str] = None) -> Dict[str, Any]:
        client = self._get_client()
        if not client:
            raise RuntimeError("Gemini API key is not configured or client initialization failed.")

        full_prompt = f"{system_instruction}\n\n{prompt}" if system_instruction else prompt
        candidate_models = [self._model, "gemini-3.5-flash-lite", "gemini-3.6-flash", "gemini-flash-latest"]
        last_err = None

        start = time.time()
        for m in candidate_models:
            try:
                resp = client.models.generate_content(model=m, contents=full_prompt)
                text = (resp.text or "").strip()
                if text:
                    latency = round((time.time() - start) * 1000, 1)
                    return {
                        "text": text,
                        "provider": self.provider_name,
                        "model": m,
                        "latency_ms": latency,
                        "is_local": False
                    }
            except Exception as e:
                last_err = e
                logging.warning(f"Gemini call failed on {m}: {e}")

        raise RuntimeError(f"All Gemini models failed: {last_err}")


class OllamaProvider(AIProvider):
    """
    Local Ollama Provider (Qwen 2.5 / configured local LLM).
    100% private, runs entirely on-premise without external network requests.
    """

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434").rstrip("/")
        self._model = model or os.getenv("OLLAMA_MODEL") or "qwen2.5:latest"

    @property
    def provider_name(self) -> str:
        return "Ollama (Local Qwen)"

    @property
    def model_name(self) -> str:
        return self._model

    def is_available(self) -> bool:
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags", headers={"User-Agent": "SkillBridge"})
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                return resp.status == 200
        except Exception:
            return False

    def generate_text(self, prompt: str, system_instruction: Optional[str] = None) -> Dict[str, Any]:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self._model,
            "prompt": prompt,
            "system": system_instruction or "You are SkillBridge AI, a helpful and precise career mentor.",
            "stream": False,
            "options": {"temperature": 0.3}
        }

        start = time.time()
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=20) as resp:
                res_json = json.loads(resp.read().decode("utf-8"))
                text = res_json.get("response", "").strip()
                latency = round((time.time() - start) * 1000, 1)
                return {
                    "text": text,
                    "provider": self.provider_name,
                    "model": self._model,
                    "latency_ms": latency,
                    "is_local": True
                }
        except Exception as e:
            raise RuntimeError(f"Ollama local execution failed: {e}")


class GrokProvider(AIProvider):
    """
    xAI Grok Provider.
    Calls official xAI OpenAI-compatible endpoints with backend-only key protection.
    """

    API_URL = "https://api.x.ai/v1/chat/completions"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("GROK_API_KEY")
        self._model = model or os.getenv("GROK_MODEL") or "grok-2-latest"

    @property
    def provider_name(self) -> str:
        return "xAI Grok"

    @property
    def model_name(self) -> str:
        return self._model

    def is_available(self) -> bool:
        return bool(self.api_key and self.api_key != "your_grok_api_key_here")

    def generate_text(self, prompt: str, system_instruction: Optional[str] = None) -> Dict[str, Any]:
        if not self.is_available():
            raise RuntimeError("Grok API key is not configured in backend environment.")

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": 0.3
        }

        start = time.time()
        try:
            data = json.dumps(payload).encode("utf-8")
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": "SkillBridge-Backend"
            }
            req = urllib.request.Request(self.API_URL, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=15) as resp:
                res_json = json.loads(resp.read().decode("utf-8"))
                choices = res_json.get("choices", [])
                if not choices:
                    raise ValueError("No choices returned in Grok response")
                text = choices[0].get("message", {}).get("content", "").strip()
                latency = round((time.time() - start) * 1000, 1)
                return {
                    "text": text,
                    "provider": self.provider_name,
                    "model": self._model,
                    "latency_ms": latency,
                    "is_local": False
                }
        except Exception as e:
            raise RuntimeError(f"Grok API call failed: {e}")


class AIProviderManager:
    """
    Manages provider selection, health telemetry, and automated fallback cascade.
    """

    def __init__(self):
        self.providers: Dict[str, AIProvider] = {
            "gemini": GeminiProvider(),
            "ollama": OllamaProvider(),
            "grok": GrokProvider()
        }
        self.active_provider_key = os.getenv("ACTIVE_AI_PROVIDER", "gemini").lower()

    def set_active_provider(self, key: str) -> bool:
        k = key.lower()
        if k in self.providers:
            self.active_provider_key = k
            return True
        return False

    def get_providers_status(self) -> List[Dict[str, Any]]:
        status_list = []
        for k, p in self.providers.items():
            status_list.append({
                "key": k,
                "name": p.provider_name,
                "provider_key": k,
                "model": p.model_name,
                "is_available": p.is_available(),
                "is_active": (k == self.active_provider_key),
                "is_local": getattr(p, "is_sample_source", False) or k == "ollama"
            })
        return status_list

    def get_available_providers(self) -> Dict[str, Any]:
        providers = []
        for k, p in self.providers.items():
            providers.append({
                "key": k,
                "name": k,
                "provider_name": p.provider_name,
                "model": p.model_name,
                "is_available": p.is_available(),
                "is_active": (k == self.active_provider_key)
            })
        return {
            "providers": providers,
            "active_provider": self.active_provider_key
        }


    def generate_with_fallback(self, prompt: str, system_instruction: Optional[str] = None) -> Dict[str, Any]:
        """
        Attempts execution using active provider.
        If active provider fails, cascades down available providers gracefully.
        """
        # Try active provider first
        order = [self.active_provider_key] + [k for k in ["gemini", "ollama", "grok"] if k != self.active_provider_key]
        last_error = None

        for k in order:
            provider = self.providers.get(k)
            if not provider or not provider.is_available():
                continue
            try:
                res = provider.generate_text(prompt, system_instruction)
                res["requested_provider"] = self.active_provider_key
                res["fallback_used"] = (k != self.active_provider_key)
                return res
            except Exception as e:
                last_error = e
                logging.warning(f"Provider {k} failed: {e}. Trying next...")

        # If all providers fail or none configured, return structured failure
        return {
            "text": "",
            "provider": "None Available",
            "model": "Fallback",
            "latency_ms": 0.0,
            "is_local": True,
            "error": str(last_error) if last_error else "No AI provider configured."
        }


ai_provider_manager = AIProviderManager()
