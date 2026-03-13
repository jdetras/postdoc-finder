"""EURAXESS job board scraper agent."""

from urllib.parse import quote_plus
from scraper.base import BaseSiteAgent


class EuraxessSiteAgent(BaseSiteAgent):
    source_name = "EURAXESS"

    def build_search_url(self, keyword: str, page: int = 0) -> str:
        q = quote_plus(keyword)
        return f"https://euraxess.ec.europa.eu/jobs/search?keywords={q}&page={page}"

    def parse_listing(self, html: str) -> list[dict]:
        soup = self._soup(html)
        jobs = []
        # EURAXESS uses article or div.views-row for job cards
        cards = soup.select("div.views-row, article.node--type-job-offer")
        if not cards:
            cards = soup.select("tr.views-row, li.views-row")

        for card in cards:
            link_el = card.select_one("a[href*='/jobs/']")
            if not link_el:
                link_el = card.select_one("a")
            if not link_el:
                continue

            title = link_el.get_text(strip=True)
            href = link_el.get("href", "")
            if href and not href.startswith("http"):
                href = "https://euraxess.ec.europa.eu" + href

            # Try to extract metadata from the card
            institution = ""
            deadline = ""
            location = ""
            research_field = ""

            for field_el in card.select(".field, .views-field"):
                text = field_el.get_text(strip=True)
                label_el = field_el.select_one(".field__label, .views-label")
                label = label_el.get_text(strip=True).lower() if label_el else ""

                if "deadline" in label or "closing" in label:
                    deadline = text.replace(label_el.get_text(), "").strip() if label_el else text
                elif "organisation" in label or "institution" in label or "employer" in label:
                    institution = text.replace(label_el.get_text(), "").strip() if label_el else text
                elif "country" in label or "location" in label:
                    location = text.replace(label_el.get_text(), "").strip() if label_el else text
                elif "research" in label and "field" in label:
                    research_field = text.replace(label_el.get_text(), "").strip() if label_el else text

            if title:
                jobs.append({
                    "title": title,
                    "url": href,
                    "institution": institution,
                    "deadline": deadline,
                    "location": location,
                    "country": "",
                    "research_field": research_field,
                    "description": "",
                    "external_id": href.split("/")[-1] if href else "",
                })
        return jobs

    def parse_detail(self, url: str) -> dict:
        try:
            html = self.fetch_page(url)
        except Exception:
            return {}
        soup = self._soup(html)
        desc_el = soup.select_one(".field--name-body, .node__content, .job-description")
        description = desc_el.get_text(separator="\n", strip=True) if desc_el else ""
        return {"description": description[:5000]}
