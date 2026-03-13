"""EMBL-EBI jobs scraper agent."""

from urllib.parse import quote_plus
from scraper.base import BaseSiteAgent


class EmblSiteAgent(BaseSiteAgent):
    source_name = "EMBL-EBI"

    def build_search_url(self, keyword: str, page: int = 0) -> str:
        q = quote_plus(keyword)
        return f"https://www.embl.org/jobs/searchjobs/?q={q}&location=&position_type=Postdoctoral+Fellow"

    def parse_listing(self, html: str) -> list[dict]:
        soup = self._soup(html)
        jobs = []

        # EMBL renders job listings — try multiple selectors
        cards = soup.select("div.job-listing, li.job-item, article.job, div.card, div.views-row")
        if not cards:
            # Fallback: find any links to job detail pages
            for a_tag in soup.select("a[href*='/jobs/'], a[href*='job']"):
                title = a_tag.get_text(strip=True)
                href = a_tag.get("href", "")
                if href and not href.startswith("http"):
                    href = "https://www.embl.org" + href
                if title and len(title) > 10 and "search" not in href:
                    jobs.append({
                        "title": title,
                        "url": href,
                        "institution": "EMBL-EBI",
                        "deadline": "",
                        "location": "",
                        "country": "",
                        "research_field": "",
                        "description": "",
                        "external_id": "",
                    })
            return jobs

        for card in cards:
            link_el = card.select_one("a[href]")
            if not link_el:
                continue
            title = link_el.get_text(strip=True)
            href = link_el.get("href", "")
            if href and not href.startswith("http"):
                href = "https://www.embl.org" + href

            deadline = ""
            location = ""
            for span in card.select("span, div.meta, p"):
                text = span.get_text(strip=True).lower()
                if "deadline" in text or "closing" in text:
                    deadline = span.get_text(strip=True)
                elif "location" in text or any(c in text for c in ["heidelberg", "hinxton", "hamburg", "barcelona", "rome"]):
                    location = span.get_text(strip=True)

            if title:
                jobs.append({
                    "title": title,
                    "url": href,
                    "institution": "EMBL-EBI",
                    "deadline": deadline,
                    "location": location,
                    "country": "",
                    "research_field": "",
                    "description": "",
                    "external_id": "",
                })

        return jobs

    def parse_detail(self, url: str) -> dict:
        try:
            html = self.fetch_page(url)
        except Exception:
            return {}
        soup = self._soup(html)
        content = soup.select_one("div.job-description, article, main, div.entry-content")
        description = content.get_text(separator="\n", strip=True) if content else ""
        return {"description": description[:5000]}
