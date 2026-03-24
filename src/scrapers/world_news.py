"""
Scraper for World News via BBC and Reuters RSS feeds.
"""
import feedparser

WORLD_FEEDS = [
    ("http://feeds.bbci.co.uk/news/world/rss.xml", "BBC World"),
    ("https://feeds.reuters.com/reuters/topNews", "Reuters"),
    ("https://rss.app/feeds/tvqRMa0oMFBqNSUO.xml", "Reuters World"),  # Reuters alt
]

MAX_ITEMS_PER_FEED = 4


def fetch_world_news() -> list[dict]:
    articles = []
    seen_titles = set()
    for url, source in WORLD_FEEDS:
        try:
            feed = feedparser.parse(url)
            count = 0
            for entry in feed.entries:
                if count >= MAX_ITEMS_PER_FEED:
                    break
                title = entry.get("title", "")
                if title in seen_titles:
                    continue
                seen_titles.add(title)
                articles.append({
                    "title": title,
                    "summary": entry.get("summary", entry.get("description", "")),
                    "source": source,
                    "link": entry.get("link", ""),
                })
                count += 1
        except Exception as e:
            print(f"[WorldNews] Error fetching {source}: {e}")
    return articles[:10]  # Cap at 10 total


if __name__ == "__main__":
    for a in fetch_world_news():
        print(f"• [{a['source']}] {a['title']}")
