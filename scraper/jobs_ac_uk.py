"""jobs.ac.uk scraper agent — large UK/international academic job board."""

from urllib.parse import quote_plus
from scraper.base import BaseSiteAgent


class JobsAcUkSiteAgent(BaseSiteAgent):
    source_name = "jobs.ac.uk"

    def build_search_url(self, keyword: str, page: int = 0) -> str:
        q = quote_plus(keyword)
        base = f"https://www.jobs.ac.uk/search/?keywords={q}&activeFacet=typeOfRoleFacet&typeOfRoleFacet=Research"
        if page > 0:
            base += f"&startIndex={page * 25}"
        return base

    def parse_listing(self, html: str) -> list[dict]:
        soup = self._soup(html)
        jobs = []

        # jobs.ac.uk uses structured search result cards
        cards = soup.select("div.j-search-result, div.search-result, li.j-search-result__item")
        if not cards:
            # Fallback: find job links
            for a_tag in soup.select("a[href*='/job/']"):
                title = a_tag.get_text(strip=True)
                href = a_tag.get("href", "")
                if href and not href.startswith("http"):
                    href = "https://www.jobs.ac.uk" + href
                if title and len(title) > 10:
                    jobs.append({
                        "title": title,
                        "url": href,
                        "institution": "",
                        "deadline": "",
                        "location": "",
                        "country": "United Kingdom",
                        "research_field": "",
                        "description": "",
                        "salary_info": "",
                        "external_id": "",
                    })
            return jobs

        for card in cards:
            link_el = card.select_one("a[href*='/job/']")
            if not link_el:
                link_el = card.select_one("a[href]")
            if not link_el:
                continue

            title = link_el.get_text(strip=True)
            href = link_el.get("href", "")
            if href and not href.startswith("http"):
                href = "https://www.jobs.ac.uk" + href

            institution = ""
            deadline = ""
            location = ""
            salary = ""

            for el in card.select("span, div, p"):
                cls = " ".join(el.get("class", []))
                text = el.get_text(strip=True)
                if "employer" in cls or "institution" in cls:
                    institution = text
                elif "closing" in cls or "deadline" in cls:
                    deadline = text
                elif "location" in cls:
                    location = text
                elif "salary" in cls:
                    salary = text

            if title:
                jobs.append({
                    "title": title,
                    "url": href,
                    "institution": institution,
                    "deadline": deadline,
                    "location": location,
                    "country": "United Kingdom",
                    "research_field": "",
                    "description": "",
                    "salary_info": salary,
                    "external_id": "",
                })

        return jobs

    def parse_detail(self, url: str) -> dict:
        try:
            html = self.fetch_page(url)
        except Exception:
            return {}
        soup = self._soup(html)
        content = soup.select_one("div.j-advert-details, div.job-description, article, main")
        description = content.get_text(separator="\n", strip=True) if content else ""
        return {"description": description[:5000]}
