"""Orchestrator that runs all site agents and deduplicates results."""

import logging
from rapidfuzz import fuzz

from scraper import keywords as kw_gen
from scraper.euraxess import EuraxessSiteAgent
from scraper.academictransfer import AcademicTransferSiteAgent
from scraper.csiro import CsiroSiteAgent
from scraper.ipk import IpkSiteAgent
from scraper.jic import JicSiteAgent
from scraper.embl import EmblSiteAgent
from scraper.jobs_ac_uk import JobsAcUkSiteAgent
from scraper.academicpositions import AcademicPositionsSiteAgent

logger = logging.getLogger(__name__)

_SITE_AGENTS = [
    EuraxessSiteAgent,
    AcademicTransferSiteAgent,
    CsiroSiteAgent,
    IpkSiteAgent,
    JicSiteAgent,
    EmblSiteAgent,
    JobsAcUkSiteAgent,
    AcademicPositionsSiteAgent,
]


def _is_duplicate(job: dict, existing: list[dict], threshold: int = 90) -> bool:
    """Check if a job is a fuzzy duplicate of any in existing list."""
    title = job.get("title", "")
    inst = job.get("institution", "")
    combined = f"{title} {inst}".strip()
    if not combined:
        return False
    for e in existing:
        e_combined = f"{e.get('title', '')} {e.get('institution', '')}".strip()
        if fuzz.token_sort_ratio(combined, e_combined) >= threshold:
            return True
    return False


class ScraperAgent:
    """Orchestrates scraping across all job boards."""

    def run_all(self, user_profile: dict, status_callback=None) -> list[dict]:
        """Run all site agents with keywords generated from the user profile.

        Args:
            user_profile: dict with research_fields, interests, skills, etc.
            status_callback: optional callable(site_name, count, error_msg)
                for progress reporting in Streamlit.

        Returns:
            Deduplicated list of job dicts.
        """
        search_terms = kw_gen.generate(user_profile)
        if not search_terms:
            search_terms = ["academic position"]

        all_jobs: list[dict] = []
        stats: dict[str, dict] = {}

        for AgentCls in _SITE_AGENTS:
            agent = AgentCls()
            name = agent.source_name
            try:
                jobs = agent.search(search_terms)
                # Deduplicate against already-collected jobs
                new_jobs = [j for j in jobs if not _is_duplicate(j, all_jobs)]
                all_jobs.extend(new_jobs)
                stats[name] = {"found": len(jobs), "new": len(new_jobs), "error": None}
                if status_callback:
                    status_callback(name, len(new_jobs), None)
            except Exception as exc:
                logger.error("Agent %s failed: %s", name, exc)
                stats[name] = {"found": 0, "new": 0, "error": str(exc)}
                if status_callback:
                    status_callback(name, 0, str(exc))

        logger.info(
            "ScraperAgent finished: %d total jobs from %d sites",
            len(all_jobs), len(_SITE_AGENTS),
        )
        return all_jobs

    def run_site(self, site_name: str, search_terms: list[str]) -> list[dict]:
        """Run a single site agent by name."""
        for AgentCls in _SITE_AGENTS:
            agent = AgentCls()
            if agent.source_name == site_name:
                return agent.search(search_terms)
        raise ValueError(f"Unknown site: {site_name}")
