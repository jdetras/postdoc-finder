"""John Innes Centre vacancies scraper agent."""

from scraper.base import BaseSiteAgent


class JicSiteAgent(BaseSiteAgent):
    source_name = "JIC"

    _BASE_URL = "https://www.jic.ac.uk/vacancies/"

    def build_search_url(self, keyword: str, page: int = 0) -> str:
        # JIC lists all vacancies on one page
        return self._BASE_URL

    def parse_listing(self, html: str) -> list[dict]:
        soup = self._soup(html)
        jobs = []

        # JIC renders vacancy cards as links within a list/grid
        for card in soup.select("div.vacancy, li.vacancy, article, div.card"):
            link_el = card.select_one("a[href]")
            if not link_el:
                continue
            title = link_el.get_text(strip=True)
            href = link_el.get("href", "")
            if href and not href.startswith("http"):
                href = "https://www.jic.ac.uk" + href

            if not title or len(title) < 5:
                continue

            deadline = ""
            department = ""
            for el in card.select("span, p, div.meta"):
                text = el.get_text(strip=True)
                text_lower = text.lower()
                if "deadline" in text_lower or "closing" in text_lower:
                    deadline = text
                elif "group" in text_lower or "department" in text_lower:
                    department = text

            jobs.append({
                "title": title,
                "url": href,
                "institution": "John Innes Centre",
                "deadline": deadline,
                "location": "Norwich, UK",
                "country": "United Kingdom",
                "research_field": department or "Plant & Microbial Sciences",
                "description": "",
                "external_id": "",
            })

        # Fallback: look for job-like links if no cards found
        if not jobs:
            for a_tag in soup.select("a[href*='vacanc'], a[href*='jobs'], a[href*='recruit']"):
                title = a_tag.get_text(strip=True)
                href = a_tag.get("href", "")
                if href and not href.startswith("http"):
                    href = "https://www.jic.ac.uk" + href
                if title and len(title) > 10 and href != self._BASE_URL:
                    jobs.append({
                        "title": title,
                        "url": href,
                        "institution": "John Innes Centre",
                        "deadline": "",
                        "location": "Norwich, UK",
                        "country": "United Kingdom",
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
        content = soup.select_one("div.entry-content, article, main")
        description = content.get_text(separator="\n", strip=True) if content else ""
        return {"description": description[:5000]}
