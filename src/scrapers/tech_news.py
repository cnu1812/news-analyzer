"""
Scraper for Tech News via TechCrunch, The Verge, and Hacker News RSS feeds.
"""
import feedparser

TECH_FEEDS = [
    ("https://techcrunch.com/feed/", "TechCrunch"),
    ("https://www.theverge.com/rss/index.xml", "The Verge"),
    ("https://feeds.arstechnica.com/arstechnica/index", "Ars Technica"),
]

MAX_ITEMS_PER_FEED = 3


def fetch_tech_news() -> list[dict]:
    articles = []
    seen = set()
    for url, source in TECH_FEEDS:
        try:
            feed = feedparser.parse(url)
            count = 0
            for entry in feed.entries:
                if count >= MAX_ITEMS_PER_FEED:
                    break
                title = entry.get("title", "")
                if title in seen:
                    continue
                seen.add(title)
                # Strip HTML from summary if present
                summary = entry.get("summary", entry.get("description", ""))
                if summary and "<" in summary:
                    import re
                    summary = re.sub(r"<[^>]+>", "", summary)
                articles.append({
                    "title": title,
                    "summary": summary[:500],
                    "source": source,
                    "link": entry.get("link", ""),
                })
                count += 1
        except Exception as e:
            print(f"[TechNews] Error fetching {source}: {e}")
    return articles


if __name__ == "__main__":
    for a in fetch_tech_news():
        print(f"• [{a['source']}] {a['title']}")
