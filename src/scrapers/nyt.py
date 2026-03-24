"""
Scraper for New York Times Front Page via RSS.
"""
import feedparser
import requests
from datetime import datetime, timezone

NYT_RSS = "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml"
MAX_ITEMS = 7


def fetch_nyt_news() -> list[dict]:
    """Fetch top stories from NYT front page RSS feed."""
    try:
        feed = feedparser.parse(NYT_RSS)
        items = []
        for entry in feed.entries[:MAX_ITEMS]:
            items.append({
                "title": entry.get("title", ""),
                "summary": entry.get("summary", entry.get("description", "")),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
            })
        return items
    except Exception as e:
        print(f"[NYT] Error fetching: {e}")
        return []


if __name__ == "__main__":
    news = fetch_nyt_news()
    for n in news:
        print(f"• {n['title']}")
