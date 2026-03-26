"""
Main orchestrator for Morning Pulse daily podcast pipeline.
Runs: Scrape → Generate Script → TTS → Send to Discord
"""
import os
import sys
import traceback
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Add src to path when running from project root
sys.path.insert(0, os.path.dirname(__file__))

from scrapers.nyt import fetch_nyt_news
from scrapers.indian_market import fetch_indian_market_news
from scrapers.indian_sports_business import fetch_indian_sports_news, fetch_indian_business_news
from scrapers.world_news import fetch_world_news
from scrapers.cnbc import fetch_cnbc_news
from scrapers.tech_news import fetch_tech_news
from script_generator import generate_podcast_script
from tts_engine import text_to_speech
from discord_sender import send_to_discord, send_error_notification
from researcher import ResearchAgent
from fact_checker import FactChecker


def get_date_strings() -> tuple[str, str]:
    """Return (display_date, file_date) for today in IST."""
    ist = timezone(timedelta(hours=5, minutes=30))
    now = datetime.now(ist)
    display = now.strftime("%B %d, %Y")   # e.g. "March 24, 2026"
    file_fmt = now.strftime("%Y-%m-%d")   # e.g. "2026-03-24"
    return display, file_fmt


def run_pipeline() -> None:
    display_date, file_date = get_date_strings()
    print(f"\n{'='*60}")
    print(f"  Morning Pulse -- {display_date}")
    print(f"{'='*60}\n")

    # -- Step 1: Scrape all news sources --------------------------
    print("Step 1/4 -- Scraping news sources...")

    print("  [1/6] NYT Front Page...")
    nyt = fetch_nyt_news()
    print(f"        - {len(nyt)} stories")

    print("  [2/6] Indian Markets...")
    indian_market = fetch_indian_market_news()
    print(f"        - {len(indian_market.get('articles', []))} articles + {len(indian_market.get('indices', {}))} indices")

    print("  [3/6] Indian Sports & Business...")
    indian_sports = fetch_indian_sports_news()
    indian_business = fetch_indian_business_news()
    print(f"        - {len(indian_sports)} sports | {len(indian_business)} business")

    print("  [4/6] World News...")
    world_news = fetch_world_news()
    print(f"        - {len(world_news)} stories")

    print("  [5/6] CNBC Markets...")
    cnbc = fetch_cnbc_news()
    print(f"        - {len(cnbc)} articles")

    print("  [6/6] Tech News...")
    tech_news = fetch_tech_news()
    print(f"        - {len(tech_news)} articles")

    all_news = {
        "nyt": nyt,
        "indian_market": indian_market,
        "indian_sports": indian_sports,
        "indian_business": indian_business,
        "world_news": world_news,
        "cnbc": cnbc,
        "tech_news": tech_news,
    }

    # -- Step 1.5: Fact-Checking & Deep Research -------------------
    print("\nStep 1.5 -- Fact-checking and Deep-dive research...")
    
    # 1. Fact Check (Verify consistency and remove non-genuine news)
    checker = FactChecker()
    all_news = checker.verify_news(all_news)
    
    # 2. Deep Dive Research (Perform background search for context)
    researcher = ResearchAgent()
    research_data = researcher.research_all(all_news)

    # -- Step 2: Generate AI podcast script -----------------------
    print(f"\nStep 2/4 -- Generating podcast script with Groq Llama-3.3-70B...")
    script = generate_podcast_script(all_news, display_date, research_data)
    word_count = len(script.split())
    duration_est = round(word_count / 130)
    print(f"   - Script ready: {word_count} words (~{duration_est} min)")

    # -- Step 3: Convert to audio ----------------------------------
    print(f"\nStep 3/4 -- Converting to audio (edge-tts neural voice)...")
    audio_path = text_to_speech(script, file_date)
    print(f"   - Audio: {audio_path}")

    # -- Step 4: Send to Discord ------------------------------------
    print(f"\nStep 4/4 -- Sending to Discord...")
    success = send_to_discord(audio_path, script, display_date, indian_market)

    if success:
        print(f"\nOK! Morning Pulse for {display_date} delivered to Discord!")
    else:
        print(f"\n[FAIL] Discord delivery failed. Audio saved at: {audio_path}")
        sys.exit(1)


if __name__ == "__main__":
    display_date, _ = get_date_strings()
    try:
        run_pipeline()
    except Exception as e:
        error_details = traceback.format_exc()
        print(f"\n[ERROR] Pipeline failed:\n{error_details}")
        try:
            send_error_notification(error_details, display_date)
        except Exception:
            pass
        sys.exit(1)
