"""
Scraper for Indian Sports and Business news via RSS feeds.
"""
import feedparser

SPORTS_FEEDS = [
    ("https://timesofindia.indiatimes.com/rss/sports.cms", "Times of India Sports"),
    ("https://www.cricbuzz.com/rss/cricket-news", "Cricbuzz"),
]

BUSINESS_FEEDS = [
    ("https://economictimes.indiatimes.com/industry/rssfeeds/13352306.cms", "ET Business"),
    ("https://www.business-standard.com/rss/home_page_top_stories.rss", "Business Standard"),
]

MAX_ITEMS_PER_FEED = 3


def fetch_feed(feeds: list[tuple]) -> list[dict]:
    articles = []
    for url, source in feeds:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:MAX_ITEMS_PER_FEED]:
                articles.append({
                    "title": entry.get("title", ""),
                    "summary": entry.get("summary", entry.get("description", "")),
                    "source": source,
                    "link": entry.get("link", ""),
                })
        except Exception as e:
            print(f"[{source}] Error: {e}")
    return articles


def fetch_indian_sports_news() -> list[dict]:
    return fetch_feed(SPORTS_FEEDS)


def fetch_indian_business_news() -> list[dict]:
    return fetch_feed(BUSINESS_FEEDS)


if __name__ == "__main__":
    print("=== SPORTS ===")
    for a in fetch_indian_sports_news():
        print(f"• [{a['source']}] {a['title']}")
    print("\n=== BUSINESS ===")
    for a in fetch_indian_business_news():
        print(f"• [{a['source']}] {a['title']}")
