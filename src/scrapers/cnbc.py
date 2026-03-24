"""
Scraper for CNBC Market Analytics and Finance news via RSS feeds.
"""
import feedparser

CNBC_FEEDS = [
    ("https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114", "CNBC Markets"),
    ("https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664", "CNBC Business"),
    ("https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=15839135", "CNBC US Economy"),
]

MAX_ITEMS_PER_FEED = 3


def fetch_cnbc_news() -> list[dict]:
    articles = []
    seen = set()
    for url, source in CNBC_FEEDS:
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
                articles.append({
                    "title": title,
                    "summary": entry.get("summary", entry.get("description", "")),
                    "source": source,
                    "link": entry.get("link", ""),
                })
                count += 1
        except Exception as e:
            print(f"[CNBC] Error fetching {source}: {e}")
    return articles


if __name__ == "__main__":
    for a in fetch_cnbc_news():
        print(f"• [{a['source']}] {a['title']}")
