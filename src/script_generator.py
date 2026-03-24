"""
AI Podcast Script Generator using Groq API (free tier, Llama-3.3-70B).
Transforms raw news data into an engaging, natural podcast script (~15 min).
"""
import os
from groq import Groq
from datetime import datetime

# Target word count for ~20 min podcast (safely hits 10+ min at 64k bitrate)
TARGET_WORDS = 3000


def _format_market_section(market_data: dict) -> str:
    """Format market index data into readable text for the AI prompt."""
    indices = market_data.get("indices", {})
    lines = []
    for name, vals in indices.items():
        arrow = "UP" if vals["change_pct"] >= 0 else "DOWN"
        lines.append(f"  {name}: {vals['price']} ({arrow} {abs(vals['change_pct'])}%)")
    articles = market_data.get("articles", [])
    for a in articles:
        lines.append(f"  • [{a['source']}] {a['title']}: {a['summary'][:200]}")
    return "\n".join(lines)


def _format_articles(articles: list[dict], max_per_source: int = 3) -> str:
    """Format a list of articles into a compact text block."""
    lines = []
    for a in articles[:max_per_source * 3]:
        title = a.get("title", "")
        summary = a.get("summary", "")[:250]
        source = a.get("source", "")
        lines.append(f"  • [{source}] {title}: {summary}")
    return "\n".join(lines)


def generate_podcast_script(all_news: dict, date_str: str) -> str:
    """
    Call Groq API to generate the full podcast script.
    
    all_news keys:
        nyt, indian_market, indian_sports, indian_business,
        world_news, cnbc, tech_news
    """
    client = Groq(api_key=os.environ["GROQ_API_KEY"])

    # Build the context for the AI
    news_context = f"""
=== NEW YORK TIMES — FRONT PAGE ===
{_format_articles(all_news.get('nyt', []))}

=== INDIAN MARKETS — LIVE DATA & ANALYSIS ===
{_format_market_section(all_news.get('indian_market', {}))}

=== INDIAN SPORTS ===
{_format_articles(all_news.get('indian_sports', []))}

=== INDIAN BUSINESS ===
{_format_articles(all_news.get('indian_business', []))}

=== WORLD NEWS ===
{_format_articles(all_news.get('world_news', []))}

=== CNBC — MARKET ANALYTICS ===
{_format_articles(all_news.get('cnbc', []))}

=== TECH NEWS ===
{_format_articles(all_news.get('tech_news', []))}
"""

    system_prompt = """You are the writing team for "Morning Pulse", the most high-energy, engaging, and dynamic news podcast on the internet.
The podcast is hosted by two people:
- HOST_A (Sreenivas): A deep-voiced, professional, but highly enthusiastic anchor.
- HOST_B (Deepika): A warm, brilliant co-host who chimes in with great insights and reactions.

RULES:
- CREATE INCREDIBLE HOOKS: Start strong and keep the listener glued!
- MULTI-HOST BANTER: Write the script as a dynamic conversation. Every line MUST be prefixed with either [HOST_A] or [HOST_B].
- STRICT NEWS FILTERING: You MUST act as a ruthless editor. Discard celebrity gossip, vague PR pieces, or low-impact news. ONLY discuss macro-economic shifts, major tech breakthroughs, geopolitical events, and hard market-moving news.
- LONG-FORM SHOW: We need a MASSIVE 15-to-20 MINUTE EPISODE. The script MUST be AT LEAST 2,500 words. Dive DEEP into the news items. Do not just read headlines; have Adam and Sarah debate the implications of the most critical news.
- NO BORING LISTS: Seamlessly weave the NYT, Markets, Tech, and World news together as a conversation.
- WRITE ONLY SPOKEN TEXT: NO stage directions, NO headers, NO extra text. Just pure dialogue.
- END WITH A BANG: Host A and Host B should sign off leaving the listener motivated for the day!"""

    user_prompt = f"""Today is {date_str}. This is not a regular news update; this is a 20-MINUTE MASTERCLASS. 
The script MUST be AT LEAST 3,000 words. You MUST discuss each of the news categories below (NYT, Markets, Tech, World) for AT LEAST 4-5 minutes each.
DO NOT move to the next topic until Sreenivas and Deepika have had a deep, multi-paragraph debate about the long-term geopolitical and economic implications of the current topic.
If the script is less than 3,000 words, you have failed the assignment.

{news_context}

Start with a massive hook, like: 
[HOST_A] Welcome back to Morning Pulse! It is {date_str}, and today we've got a crazy lineup...
[HOST_B] Exactly, Sreenivas! We are tracking major shifts in...

DO NOT output any intro/outro text outside of the dialogue itself. Every single line MUST start with [HOST_A] or [HOST_B]."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
        max_tokens=6000,
    )

    script = response.choices[0].message.content.strip()
    print(f"[ScriptGen] Generated {len(script.split())} words")
    return script


if __name__ == "__main__":
    # Quick test with dummy data
    import json
    dummy = {
        "nyt": [{"title": "Test NYT Story", "summary": "Summary here", "source": "NYT", "link": ""}],
        "indian_market": {"indices": {"NIFTY 50": {"price": 22000, "change_pct": 0.5}}, "articles": []},
        "indian_sports": [],
        "indian_business": [],
        "world_news": [],
        "cnbc": [],
        "tech_news": [],
    }
    script = generate_podcast_script(dummy, "March 24, 2026")
    print(script[:500])
