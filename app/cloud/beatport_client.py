"""
Simple Beatport charts fetcher using requests + BeautifulSoup.
This is a best-effort scraper for public chart pages; for production use,
prefer an official API or licensing.
"""

import requests
from bs4 import BeautifulSoup
import time


class BeatportClient:
    BASE = "https://www.beatport.com"

    def __init__(self, session=None, rate_limit_seconds=1.0):
        self.session = session or requests.Session()
        self.rate_limit = rate_limit_seconds

    def fetch_charts(self, chart_path="charts/top-100"):
        url = f"{self.BASE}/{chart_path}"
        resp = self.session.get(url, timeout=15)
        resp.raise_for_status()
        time.sleep(self.rate_limit)
        return self.parse_chart_html(resp.text)

    def parse_chart_html(self, html):
        soup = BeautifulSoup(html, "html.parser")
        results = []

        # Beatport's markup may change; this parser is defensive
        for item in soup.select(".buk-track-meta"):
            try:
                title_tag = item.select_one(".buk-track-meta__title a")
                artist_tag = item.select_one(".buk-track-meta__artists a")
                release_tag = item.select_one(".buk-track-meta__label a")

                title = title_tag.get_text(strip=True) if title_tag else ""
                artist = artist_tag.get_text(strip=True) if artist_tag else ""
                release = release_tag.get_text(strip=True) if release_tag else ""

                results.append({
                    "title": title,
                    "artist": artist,
                    "release": release,
                })
            except Exception:
                continue

        # Fallback: try rows
        if not results:
            for row in soup.select(".bucket-track"):
                t = row.select_one(".buk-track-title")
                a = row.select_one(".buk-track-artists")
                if t:
                    results.append({
                        "title": t.get_text(strip=True),
                        "artist": (a.get_text(strip=True) if a else ""),
                    })

        return results

    def top_100(self):
        try:
            return self.fetch_charts("charts/top-100")
        except Exception as exc:
            return {"error": str(exc)}


if __name__ == "__main__":
    c = BeatportClient()
    print(c.top_100()[:10])
