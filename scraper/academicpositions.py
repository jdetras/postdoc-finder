"""AcademicPositions.com scraper agent — international academic job board."""

from urllib.parse import quote_plus
from scraper.base import BaseSiteAgent


class AcademicPositionsSiteAgent(BaseSiteAgent):
    source_name = "AcademicPositions"

    def build_search_url(self, keyword: str, page: int = 0) -> str:
        q = quote_plus(keyword)
        base = f"https://academicpositions.com/jobs?query={q}&position-type=postdoc"
        if page > 0:
            base += f"&page={page + 1}"
        return base

    def parse_listing(self, html: str) -> list[dict]:
        soup = self._soup(html)
        jobs = []

        # AcademicPositions renders job cards in a list
        cards = soup.select("div.job-card, article.job, li.job-item, div.card, div.search-result")
        if not cards:
            for a_tag in soup.select("a[href*='/ad/']"):
                title = a_tag.get_text(strip=True)
                href = a_tag.get("href", "")
                if href and not href.startswith("http"):
                    href = "https://academicpositions.com" + href
                if title and len(title) > 10:
                    jobs.append({
                        "title": title,
                        "url": href,
                        "institution": "",
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
                href = "https://academicpositions.com" + href

            institution = ""
            deadline = ""
            location = ""
            country = ""

            for el in card.select("span, div, p"):
                cls = " ".join(el.get("class", []))
                text = el.get_text(strip=True)
                text_lower = text.lower()
                if "employer" in cls or "institution" in cls or "university" in text_lower:
                    institution = text
                elif "deadline" in cls or "closing" in cls or "deadline" in text_lower:
                    deadline = text
                elif "location" in cls or "country" in cls:
                    if not location:
                        location = text

            if title:
                jobs.append({
                    "title": title,
                    "url": href,
                    "institution": institution,
                    "deadline": deadline,
                    "location": location,
                    "country": country,
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
        content = soup.select_one("div.job-description, div.ad-content, article, main")
        description = content.get_text(separator="\n", strip=True) if content else ""
        return {"description": description[:5000]}
