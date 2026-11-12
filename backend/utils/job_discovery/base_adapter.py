"""
Base class and HTTP helpers for job source providers.

Every provider:
* declares whether it is configured (credentials present) - unconfigured
  providers are skipped and reported, never faked;
* raises typed ProviderError subclasses so the sync service can distinguish
  authentication failures (do not retry), rate limits (back off, stop for this
  run) and transient failures (retry with exponential backoff);
* counts every HTTP request it makes so per-run request budgets can be enforced
  (several providers have small daily quotas).
"""
import logging
import os
import random
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable, List, Optional

import requests

logger = logging.getLogger(__name__)

USER_AGENT = os.getenv(
    "JOB_SYNC_USER_AGENT",
    "SkillBridge-JobSync/2.0 (career guidance platform; contact via site admin)",
)


class ProviderError(Exception):
    """Base error raised by a provider."""
    retryable = False

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class ProviderNotConfigured(ProviderError):
    """Credentials are missing. Not an outage - the provider is simply disabled."""


class ProviderAuthError(ProviderError):
    """Credentials rejected (HTTP 401/403). Retrying will not help."""


class ProviderRateLimited(ProviderError):
    """HTTP 429 or quota exhausted. Stop calling this provider for the current run."""


class ProviderTransientError(ProviderError):
    """Timeouts, connection errors, HTTP 5xx. Safe to retry with backoff."""
    retryable = True


class ProviderBadResponse(ProviderError):
    """Response could not be parsed / failed schema validation."""


class RequestBudgetExceeded(ProviderError):
    """This run already used the provider's request budget."""


class JobSourceAdapter(ABC):
    """Abstract provider. Subclasses implement `fetch_jobs` and `is_configured`."""

    #: short stable id stored in JobListing.source_provider
    provider_key: str = "unknown"

    def __init__(self, max_requests_per_run: Optional[int] = None,
                 max_retries: int = 3, backoff_base_seconds: float = 2.0,
                 timeout_seconds: float = 15.0, session: Optional[requests.Session] = None):
        env_budget = os.getenv(f"JOB_{self.provider_key.upper()}_MAX_REQUESTS_PER_RUN")
        self.max_requests_per_run = (
            max_requests_per_run if max_requests_per_run is not None
            else int(env_budget) if env_budget else self.default_request_budget
        )
        self.max_retries = max_retries
        self.backoff_base_seconds = backoff_base_seconds
        self.timeout_seconds = timeout_seconds
        self.session = session or requests.Session()
        self.requests_made = 0
        self._sleep = time.sleep  # overridable in tests

    default_request_budget: int = 10

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Human-readable provider name shown to users for attribution."""

    @property
    def is_sample_source(self) -> bool:
        return False

    @abstractmethod
    def is_configured(self) -> bool:
        """True when the credentials / settings needed to call the provider exist."""

    @abstractmethod
    def fetch_jobs(self, searches: Iterable[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Fetch raw jobs for the given searches ({'what': role, 'where': location}).
        Returns provider-neutral raw dicts consumed by the normalizer."""

    def reset_run_state(self) -> None:
        self.requests_made = 0

    # ── HTTP with retry / backoff ──────────────────────────────────────────
    def _request(self, method: str, url: str, **kwargs) -> Any:
        """Perform an HTTP request with exponential backoff on transient errors.
        Returns parsed JSON. Raises typed ProviderError subclasses."""
        headers = dict(kwargs.pop("headers", None) or {})
        headers.setdefault("User-Agent", USER_AGENT)
        headers.setdefault("Accept", "application/json")
        attempt = 0
        while True:
            if self.requests_made >= self.max_requests_per_run:
                raise RequestBudgetExceeded(
                    f"{self.source_name}: request budget of {self.max_requests_per_run} per run reached")
            self.requests_made += 1
            try:
                resp = self.session.request(method, url, headers=headers,
                                            timeout=self.timeout_seconds, **kwargs)
            except requests.RequestException as e:
                # Never include the URL: it may contain API keys in the query string / path
                err: ProviderError = ProviderTransientError(
                    f"{self.source_name}: network error ({type(e).__name__})")
            else:
                status = resp.status_code
                if status in (401, 403):
                    raise ProviderAuthError(f"{self.source_name}: credentials rejected (HTTP {status})", status)
                if status == 429:
                    raise ProviderRateLimited(f"{self.source_name}: rate limited (HTTP 429)", status)
                if status >= 500:
                    err = ProviderTransientError(f"{self.source_name}: server error HTTP {status}", status)
                elif status >= 400:
                    raise ProviderBadResponse(f"{self.source_name}: HTTP {status}: {resp.text[:200]}", status)
                else:
                    try:
                        return resp.json()
                    except ValueError:
                        raise ProviderBadResponse(f"{self.source_name}: response was not valid JSON")

            attempt += 1
            if attempt > self.max_retries:
                raise err
            delay = self.backoff_base_seconds * (2 ** (attempt - 1)) + random.uniform(0, 0.5)
            logger.warning("%s (attempt %d/%d), retrying in %.1fs", err, attempt, self.max_retries, delay)
            self._sleep(delay)

    def health_snapshot(self) -> Dict[str, Any]:
        """Configuration status only - no network call (health is derived from real sync runs)."""
        return {
            "provider": self.provider_key,
            "source": self.source_name,
            "configured": self.is_configured(),
            "is_sample_source": self.is_sample_source,
            "max_requests_per_run": self.max_requests_per_run,
        }
