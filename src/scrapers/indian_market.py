"""
Scraper for Indian Market news via Economic Times & MoneyControl RSS feeds.
Also fetches live NSE/BSE index data from Yahoo Finance.
"""
import feedparser
import requests

ET_MARKETS_RSS = "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"
MC_RSS = "https://www.moneycontrol.com/rss/latestnews.xml"
MAX_ITEMS = 6

# Yahoo Finance endpoints for live index prices
INDICES = {
    "NIFTY 50": "^NSEI",
    "SENSEX": "^BSESN",
    "BANK NIFTY": "^NSEBANK",
}


def fetch_index_data() -> dict:
    """Fetch live index data from Yahoo Finance (free, no API key)."""
    results = {}
    for name, symbol in INDICES.items():
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d"
            resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            data = resp.json()
            meta = data["chart"]["result"][0]["meta"]
            price = meta.get("regularMarketPrice", 0)
            prev_close = meta.get("chartPreviousClose", price)
            change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0
            results[name] = {
                "price": round(price, 2),
                "change_pct": round(change_pct, 2),
            }
        except Exception as e:
            print(f"[IndexData] Error for {name}: {e}")
            results[name] = {"price": 0, "change_pct": 0}
    return results


def fetch_indian_market_news() -> dict:
    """Return market news articles and live index snapshot."""
    articles = []
    for rss_url, source in [(ET_MARKETS_RSS, "ET Markets"), (MC_RSS, "MoneyControl")]:
        try:
            feed = feedparser.parse(rss_url)
            for entry in feed.entries[:MAX_ITEMS // 2]:
                articles.append({
                    "title": entry.get("title", ""),
                    "summary": entry.get("summary", entry.get("description", "")),
                    "source": source,
                    "link": entry.get("link", ""),
                })
        except Exception as e:
            print(f"[IndianMarket] Error fetching {source}: {e}")

    indices = fetch_index_data()
    return {"articles": articles, "indices": indices}


if __name__ == "__main__":
    data = fetch_indian_market_news()
    print("=== INDICES ===")
    for name, vals in data["indices"].items():
        arrow = "▲" if vals["change_pct"] >= 0 else "▼"
        print(f"  {name}: {vals['price']} {arrow} {vals['change_pct']}%")
    print("\n=== ARTICLES ===")
    for a in data["articles"]:
        print(f"• [{a['source']}] {a['title']}")
