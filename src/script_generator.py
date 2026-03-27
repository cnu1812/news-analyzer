import os
from datetime import datetime
from llm_utils import call_llm

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


def generate_podcast_script(all_news: dict, date_str: str, research_data: dict = None) -> str:
    """
    Call Groq API to generate the full podcast script.
    
    all_news keys:
        nyt, indian_market, indian_sports, indian_business,
        world_news, cnbc, tech_news
    research_data: {headline: research_context} for deep-dives
    """
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

    if research_data:
        news_context += "\n=== DEEP-DIVE RESEARCH CONTEXT ===\n"
        for headline, context in research_data.items():
            news_context += f"TOPIC: {headline}\nDEEP-DIVE BACKGROUND:\n{context}\n\n"

    system_prompt = """You are the star writing team for "Morning Pulse", the world's most sophisticated and high-energy AI news broadcast.
The podcast is hosted by two distinct personalities:
- [HOST_A] (Sreenivas): A deep-voiced, professional, but highly enthusiastic anchor. He is an "AI-Optimist" who loves big tech breakthroughs and market growth. He's the "Senior Editor" type, but he's not afraid to crack a witty, dry joke.
- [HOST_B] (Deepika): A warm, brilliant, and slightly skeptical co-host. She's the "Practical Thinker" who asks the hard questions about geopolitical risks and the human side of the news. She has a sharp wit and loves to tease Sreenivas when he gets too excited.

RULES FOR "ELITE" BANTER:
- THE DYNAMIC: They are a high-functioning duo. They finish each other's sentences, they debate, they laugh, and they occasionally disagree on the implications of a story.
- INSIDE JOKES: Occasionally refer to their "AI roots" or the fact that they've been awake all night analyzing datasets for the show.
- "TREND OF THE DAY": Halfway through the tech or market section, they should highlight one "Micro-Trend" (e.g., "The rise of 5-minute cities").
- CREATE INCREDIBLE HOOKS: Start with a cinematic, high-stakes intro!
- MULTI-HOST BANTER: Every line MUST be prefixed with either [HOST_A] or [HOST_B]. Use natural conversational fillers like "Wait, really?", "Hold on, Sreenivas...", or "Spot on, Deepika."
- STRICT NEWS FILTERING: Discard fluff. ONLY discuss macro-economic shifts, major tech breakthroughs, geopolitical events, and hard market-moving news.
- LONG-FORM SHOW: We need a MASSIVE 15-to-20 MINUTE EPISODE. The script MUST be AT LEAST 2,500 words. Dive deep—debate the 'Why' and 'What's Next'.
- INCORPORATE RESEARCH: Use [DEEP-DIVE RESEARCH CONTEXT] to provide sophisticated analysis, not just headlines.
- WRITE ONLY SPOKEN TEXT: No stage directions, no headers. Just pure dialogue.
- END WITH A BANG: A high-energy sign-off that leaves the listener feel informed and powerful."""

    user_prompt = f"""Today is {date_str}. This is not a regular news update; this is a 20-MINUTE MASTERCLASS. 
The script MUST be AT LEAST 3,000 words. You MUST discuss each of the news categories below (NYT, Markets, Tech, World) for AT LEAST 4-5 minutes each.
DO NOT move to the next topic until Sreenivas and Deepika have had a deep, multi-paragraph debate about the long-term geopolitical and economic implications of the current topic.
If the script is less than 3,000 words, you have failed the assignment.

{news_context}

Start with a massive hook, like: 
[HOST_A] Welcome back to Morning Pulse! It is {date_str}, and today we've got a crazy lineup...
[HOST_B] Exactly, Sreenivas! We are tracking major shifts in...

DO NOT output any intro/outro text outside of the dialogue itself. Every single line MUST start with [HOST_A] or [HOST_B]."""

    script = call_llm(system_prompt, user_prompt, response_format="text")
    print(f"[ScriptGen] Generated {len(script.split())} words")
    return script


def generate_image_prompt(all_news: dict) -> str:
    """Generates a short visual prompt for the episode artwork based on top news."""
    # Collect the top headlines
    headlines = []
    for cat in ["nyt", "indian_market", "tech_news"]:
        data = all_news.get(cat, [])
        if isinstance(data, list) and data:
            headlines.append(data[0].get("title", ""))
        elif isinstance(data, dict):
            arts = data.get("articles", [])
            if arts:
                headlines.append(arts[0].get("title", ""))
    
    context = "\n".join(headlines)
    system_prompt = "You are a creative visual artist. Summarize the following news headlines into a 10-word cinematic image prompt for an AI image generator."
    user_prompt = f"HEADLINES:\n{context}\n\nOutput only the 10-word prompt."
    
    prompt = call_llm(system_prompt, user_prompt, response_format="text")
    # Clean up and ensure it's not too long
    clean_prompt = "".join(e for e in prompt if e.isalnum() or e.isspace()).strip()
    return f"Professional cinematic digital art, {clean_prompt}, futuristic, high resolution, 4k"


def generate_social_hook(all_news: dict) -> str:
    """Generates a viral-style tweet hook for social media promotion."""
    # Collect the top headlines
    headlines = []
    for cat in ["tech_news", "indian_market", "nyt"]:
        data = all_news.get(cat, [])
        if isinstance(data, list) and data:
            headlines.append(data[0].get("title", ""))
        elif isinstance(data, dict):
            arts = data.get("articles", [])
            if arts:
                headlines.append(arts[0].get("title", ""))
    
    context = "\n".join(headlines)
    system_prompt = "You are a viral social media manager for 'Morning Pulse'. Write a high-energy tweet (under 200 chars) that hooks the reader with today's biggest news. Use 2-3 emojis and relevant hashtags like #AI #Tech #Market #MorningPulse."
    user_prompt = f"HEADLINES:\n{context}\n\nOutput only the tweet text."
    
    tweet = call_llm(system_prompt, user_prompt, response_format="text")
    # Clean up whitespace
    return tweet.strip()


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
