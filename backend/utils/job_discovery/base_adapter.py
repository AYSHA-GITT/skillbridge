from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime


class JobSourceAdapter(ABC):
    """
    Abstract Base Class for opportunity discovery sources.
    Enables plug-and-play ingestion from official APIs, job boards,
    and curated indexes without modifying core matching logic.
    """

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Name of the data provider (e.g., 'Arbeitnow Jobs API', 'SkillBridge Curated Index')"""
        pass

    @property
    @abstractmethod
    def is_sample_source(self) -> bool:
        """True if source provides labeled demo/mock records, False for verified live data."""
        pass

    @abstractmethod
    def fetch_jobs(self, query: Optional[str] = None, limit: int = 25) -> List[Dict[str, Any]]:
        """
        Fetches job/internship listings from this source.
        Returns a list of raw or semi-structured dictionaries.
        """
        pass

    def health_check(self) -> Dict[str, Any]:
        """Returns availability status and response latency metric."""
        try:
            start = datetime.utcnow()
            jobs = self.fetch_jobs(limit=1)
            latency_ms = round((datetime.utcnow() - start).total_seconds() * 1000, 1)
            return {
                "source": self.source_name,
                "status": "healthy" if bool(jobs) else "empty_response",
                "latency_ms": latency_ms
            }
        except Exception as e:
            return {
                "source": self.source_name,
                "status": "error",
                "error": str(e)
            }
