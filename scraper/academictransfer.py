"""AcademicTransfer job board scraper agent."""

from urllib.parse import quote_plus
from scraper.base import BaseSiteAgent


class AcademicTransferSiteAgent(BaseSiteAgent):
    source_name = "AcademicTransfer"

    def build_search_url(self, keyword: str, page: int = 0) -> str:
        q = quote_plus(keyword)
        # AcademicTransfer first page is server-rendered; no reliable pagination via URL
        return f"https://www.academictransfer.com/en/jobs/?q={q}"

    def parse_listing(self, html: str) -> list[dict]:
        soup = self._soup(html)
        jobs = []
        cards = soup.select("div.job-item, article.job, li.search-result, div.card")
        if not cards:
            # Fallback: look for any links to job detail pages
            cards = soup.select("a[href*='/en/job/'], a[href*='/en/jobs/']")
            for a_tag in cards:
                title = a_tag.get_text(strip=True)
                href = a_tag.get("href", "")
                if href and not href.startswith("http"):
                    href = "https://www.academictransfer.com" + href
                if title and href:
                    jobs.append({
                        "title": title,
                        "url": href,
                        "institution": "",
                        "deadline": "",
                        "location": "",
                        "country": "Netherlands",
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
                href = "https://www.academictransfer.com" + href

            institution = ""
            deadline = ""
            location = ""
            for meta in card.select("span, div.meta, p"):
                text = meta.get_text(strip=True).lower()
                if "university" in text or "institute" in text:
                    institution = meta.get_text(strip=True)
                elif "deadline" in text or "closing" in text:
                    deadline = meta.get_text(strip=True)

            if title:
                jobs.append({
                    "title": title,
                    "url": href,
                    "institution": institution,
                    "deadline": deadline,
                    "location": location,
                    "country": "Netherlands",
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
        desc_el = soup.select_one("div.job-description, div.vacancy-text, article, main")
        description = desc_el.get_text(separator="\n", strip=True) if desc_el else ""
        return {"description": description[:5000]}
