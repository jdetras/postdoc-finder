"""IPK Gatersleben job board scraper agent."""

from scraper.base import BaseSiteAgent


class IpkSiteAgent(BaseSiteAgent):
    source_name = "IPK Gatersleben"

    _BASE_URL = "https://www.ipk-gatersleben.de/en/career/job-offers"

    def build_search_url(self, keyword: str, page: int = 0) -> str:
        # IPK doesn't have a search parameter — we scrape the full listing page
        return self._BASE_URL

    def parse_listing(self, html: str) -> list[dict]:
        soup = self._soup(html)
        jobs = []

        # IPK renders job offers as links in a content area
        for a_tag in soup.select("a[href*='career'], a[href*='job'], a[href*='stelle']"):
            title = a_tag.get_text(strip=True)
            href = a_tag.get("href", "")
            if href and not href.startswith("http"):
                href = "https://www.ipk-gatersleben.de" + href

            # Skip navigation/menu links — only keep meaningful titles
            if not title or len(title) < 10:
                continue
            # Skip if it's just a menu link back to job-offers
            if href.rstrip("/") == self._BASE_URL.rstrip("/"):
                continue

            jobs.append({
                "title": title,
                "url": href,
                "institution": "IPK Gatersleben",
                "deadline": "",
                "location": "Gatersleben, Germany",
                "country": "Germany",
                "research_field": "Plant Sciences",
                "description": "",
                "external_id": "",
            })

        # Also look for structured listings (div/li with links)
        for item in soup.select("div.ce-bodytext li, div.content li, article"):
            link_el = item.select_one("a[href]")
            if not link_el:
                continue
            title = link_el.get_text(strip=True)
            href = link_el.get("href", "")
            if href and not href.startswith("http"):
                href = "https://www.ipk-gatersleben.de" + href
            if not title or len(title) < 10:
                continue
            # Avoid duplicates
            if any(j["url"] == href for j in jobs):
                continue
            jobs.append({
                "title": title,
                "url": href,
                "institution": "IPK Gatersleben",
                "deadline": "",
                "location": "Gatersleben, Germany",
                "country": "Germany",
                "research_field": "Plant Sciences",
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
        main = soup.select_one("div.ce-bodytext, main, article")
        description = main.get_text(separator="\n", strip=True) if main else ""

        # Try to extract deadline from text
        deadline = ""
        import re
        match = re.search(r"(?:deadline|closing|application.*?date)[:\s]*([A-Za-z0-9\s,\.]+\d{4})", description, re.IGNORECASE)
        if match:
            deadline = match.group(1).strip()

        return {"description": description[:5000], "deadline": deadline}
