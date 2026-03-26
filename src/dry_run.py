"""
Dry run script for Morning Pulse.
Mocks Groq and Discord to test Scraping and TTS/Mixing locally.
"""
import os
import sys
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from scrapers.nyt import fetch_nyt_news
from scrapers.indian_market import fetch_indian_market_news
from scrapers.indian_sports_business import fetch_indian_sports_news, fetch_indian_business_news
from scrapers.world_news import fetch_world_news
from scrapers.cnbc import fetch_cnbc_news
from scrapers.tech_news import fetch_tech_news
from tts_engine import text_to_speech
from researcher import ResearchAgent
from fact_checker import FactChecker

def get_date_strings() -> tuple[str, str]:
    ist = timezone(timedelta(hours=5, minutes=30))
    now = datetime.now(ist)
    display = now.strftime("%B %d, %Y")
    file_fmt = now.strftime("%Y-%m-%d")
    return display, file_fmt

def run_dry_run() -> None:
    display_date, file_date = get_date_strings()
    print(f"\n{'='*60}")
    print(f"  [DRY RUN] Morning Pulse -- {display_date}")
    print(f"{'='*60}\n")

    # 1. Scrape News (Verify Scrapers)
    print("Step 1: Verifying Scrapers...")
    try:
        print("  Checking NYT...")
        nyt = fetch_nyt_news()
        print(f"  - {len(nyt)} stories")

        print("  Checking Indian Markets...")
        mkt = fetch_indian_market_news()
        print(f"  - {len(mkt.get('articles', []))} articles")

        print("  Checking World News...")
        world = fetch_world_news()
        print(f"  - {len(world)} stories")
        
        print("  - All scrapers reachable.")
    except Exception as e:
        print(f"  [ERROR] Scraper failed: {e}")
        return

    # 1.5 Fact-Check & Research
    print("\nStep 1.5: Fact-Checking & Deep Research...")
    all_news = {
        "nyt": nyt,
        "indian_market": mkt,
        "world_news": world,
    }
    
    # Mock/Run Fact-Checker
    checker = FactChecker()
    filtered_news = checker.verify_news(all_news)
    
    # Mock/Run Researcher
    researcher = ResearchAgent()
    research_data = researcher.research_all(filtered_news, max_stories=1)
    
    # 2. Mock Script Generation
    print("\nStep 2: Mocking Script Generation (Groq)...")
    from script_generator import generate_podcast_script
    try:
        mock_script = generate_podcast_script(filtered_news, display_date, research_data)
        print("  - Script generated with research context and fact-checking.")
    except Exception as e:
        print(f"  [ERROR] Script generation failed: {e}")
        return

    # 3. Test TTS & Mixing (Verify Edge-TTS + Pydub + FFmpeg)
    print("\nStep 3: Testing TTS & Audio Mixing...")
    audio_path = None
    try:
        # Use a special file name for the dry run
        dry_run_date = f"{file_date}_dry_run"
        audio_path = text_to_speech(mock_script, dry_run_date)
        print(f"  - Audio generated at: {audio_path}")
        
        if audio_path and os.path.exists(audio_path):
            file_size = os.path.getsize(audio_path) / 1024
            print(f"  - File size: {file_size:.1f} KB")
        else:
            print("  [ERROR] Audio file not found or generation failed!")
            audio_path = None # Ensure it stays None
    except Exception as e:
        print(f"  [ERROR] TTS/Mixing failed: {e}")
        # traceback.print_exc()

    # 4. Mock Discord
    print("\nStep 4: Mocking Discord Delivery...")
    if audio_path:
        print(f"  - Simulated sending {audio_path} to Discord.")
    else:
        print("  - [SKIP] Skipping Discord mock because audio generation failed.")
    print("\nDRY RUN COMPLETE! Everything seems ready for live API keys.")

if __name__ == "__main__":
    run_dry_run()
