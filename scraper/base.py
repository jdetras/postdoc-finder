"""Base class for all site-specific scraper agents."""

import abc
import logging
import random
import time

import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]


class BaseSiteAgent(abc.ABC):
    """Abstract base for site-specific scraper agents."""

    source_name: str = "unknown"

    def __init__(self):
        self.session = requests.Session()
        self._rotate_ua()

    def _rotate_ua(self):
        self.session.headers.update({
            "User-Agent": random.choice(_USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=2, max=30))
    def fetch_page(self, url: str) -> str:
        """GET a URL and return the HTML body. Retries up to 3 times."""
        self._rotate_ua()
        resp = self.session.get(url, timeout=30)
        resp.raise_for_status()
        return resp.text

    def _soup(self, html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "html.parser")

    def _rate_limit(self):
        time.sleep(random.uniform(2, 4))

    # --- Abstract methods for subclasses ---

    @abc.abstractmethod
    def build_search_url(self, keyword: str, page: int = 0) -> str:
        ...

    @abc.abstractmethod
    def parse_listing(self, html: str) -> list[dict]:
        ...

    def parse_detail(self, url: str) -> dict:
        """Optionally override to fetch full job details from a detail page."""
        return {}

    # --- Main entry point ---

    def search(self, keywords: list[str], max_pages: int = 3) -> list[dict]:
        """Run search across keywords with pagination. Returns list of job dicts."""
        all_jobs: list[dict] = []
        seen_urls: set[str] = set()

        for kw in keywords:
            for page in range(max_pages):
                url = self.build_search_url(kw, page)
                try:
                    html = self.fetch_page(url)
                except Exception:
                    logger.warning("Failed to fetch %s page %d for '%s'", self.source_name, page, kw)
                    break

                listings = self.parse_listing(html)
                if not listings:
                    break

                for job in listings:
                    job["source"] = self.source_name
                    job_url = job.get("url", "")
                    if job_url and job_url in seen_urls:
                        continue
                    if job_url:
                        seen_urls.add(job_url)

                    # Optionally fetch detail page
                    if job_url and not job.get("description"):
                        try:
                            self._rate_limit()
                            detail = self.parse_detail(job_url)
                            job.update(detail)
                        except Exception:
                            logger.debug("Could not fetch detail for %s", job_url)

                    all_jobs.append(job)

                self._rate_limit()

        logger.info("%s: found %d jobs across %d keywords", self.source_name, len(all_jobs), len(keywords))
        return all_jobs
