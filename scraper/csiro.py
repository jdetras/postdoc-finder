"""CSIRO jobs scraper agent."""

from urllib.parse import quote_plus
from scraper.base import BaseSiteAgent


class CsiroSiteAgent(BaseSiteAgent):
    source_name = "CSIRO"

    def build_search_url(self, keyword: str, page: int = 0) -> str:
        q = quote_plus(keyword)
        if page > 0:
            return f"https://jobs.csiro.au/search/?q={q}&startrow={page * 10}"
        return f"https://jobs.csiro.au/search/?q={q}"

    def parse_listing(self, html: str) -> list[dict]:
        soup = self._soup(html)
        jobs = []

        # CSIRO typically renders job results in a table or list
        rows = soup.select("tr.data-row, div.job-result, li.search-result, div.card")
        if not rows:
            # Fallback: find links that look like job detail pages
            for a_tag in soup.select("a[href*='/job/'], a[href*='/cw/en/job/']"):
                title = a_tag.get_text(strip=True)
                href = a_tag.get("href", "")
                if href and not href.startswith("http"):
                    href = "https://jobs.csiro.au" + href
                if title and len(title) > 5:
                    jobs.append({
                        "title": title,
                        "url": href,
                        "institution": "CSIRO",
                        "deadline": "",
                        "location": "",
                        "country": "Australia",
                        "research_field": "",
                        "description": "",
                        "external_id": "",
                    })
            return jobs

        for row in rows:
            link_el = row.select_one("a[href]")
            if not link_el:
                continue
            title = link_el.get_text(strip=True)
            href = link_el.get("href", "")
            if href and not href.startswith("http"):
                href = "https://jobs.csiro.au" + href

            # Extract location from sibling cells/spans
            location = ""
            for cell in row.select("td, span.location, div.location"):
                text = cell.get_text(strip=True)
                if text != title and len(text) > 2:
                    location = text
                    break

            if title:
                jobs.append({
                    "title": title,
                    "url": href,
                    "institution": "CSIRO",
                    "deadline": "",
                    "location": location,
                    "country": "Australia",
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
        desc_el = soup.select_one("div.job-description, div.ats-description, main")
        description = desc_el.get_text(separator="\n", strip=True) if desc_el else ""
        return {"description": description[:5000]}
