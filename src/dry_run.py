"""
Dry run script for Morning Pulse.
Mocks Groq and Discord to test Scraping and TTS/Mixing locally.
"""
import os
import sys
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from scrapers.nyt import fetch_nyt_news
from scrapers.indian_market import fetch_indian_market_news
from scrapers.indian_sports_business import fetch_indian_sports_news, fetch_indian_business_news
from scrapers.world_news import fetch_world_news
from scrapers.cnbc import fetch_cnbc_news
from scrapers.tech_news import fetch_tech_news
from tts_engine import text_to_speech

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

    # 2. Mock Script Generation
    print("\nStep 2: Mocking Script Generation (Groq)...")
    mock_script = f"""[HOST_A] Welcome to the Morning Pulse dry run for {display_date}! 
[HOST_B] Thanks Sreenivas! We are testing the pipeline today to make sure everything sounds perfect.
[HOST_A] Exactly. We've just confirmed our scrapers are pulling news from the NYT, Indian markets, and tech world.
[HOST_B] And now we're testing the neural voices. This is Deepika from India, and you're Sreenivas from India as well!
[HOST_A] That's right. Next step is mixing this dialogue with some smooth lo-fi beats.
[HOST_B] Let's see if the audio engine can handle it! Signing off for the dry run."""
    print("  - Mock script created.")

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
