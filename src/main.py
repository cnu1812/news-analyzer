"""
Main orchestrator for Morning Pulse daily podcast pipeline.
Runs: Scrape → Generate Script → TTS → Send to Discord
"""
import os
import sys
import traceback
from datetime import datetime, timezone, timedelta

# Try loading environment variables from .env if python-dotenv is available (for local dev)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Add src to path when running from project root
sys.path.insert(0, os.path.dirname(__file__))

from scrapers.nyt import fetch_nyt_news
from scrapers.indian_market import fetch_indian_market_news
from scrapers.indian_sports_business import fetch_indian_sports_news, fetch_indian_business_news
from scrapers.world_news import fetch_world_news
from scrapers.cnbc import fetch_cnbc_news
from scrapers.tech_news import fetch_tech_news
from script_generator import generate_podcast_script, generate_image_prompt, generate_social_hook
from tts_engine import text_to_speech
from discord_sender import send_to_discord, send_error_notification
from researcher import ResearchAgent
from fact_checker import FactChecker
from rss_generator import update_feed
from twitter_sender import post_episode_to_twitter
import shutil
import random
from urllib.parse import quote


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
        
        # Step 5: Update RSS Feed for Spotify/Apple/Amazon (Zero-Cost Hosting)
        print(f"\nStep 5/4 -- Updating Automated RSS Feed...")
        try:
            # Move to permanent storage for RSS host (GitHub Pages)
            project_root = os.path.dirname(os.path.dirname(__file__))
            podcasts_dir = os.path.join(project_root, "podcasts")
            os.makedirs(podcasts_dir, exist_ok=True)
            
            permanent_file_name = f"morning_pulse_{file_date}.mp3"
            permanent_path = os.path.join(podcasts_dir, permanent_file_name)
            shutil.copy(audio_path, permanent_path)
            
            # Generate Dynamic Episode Artwork (Pro Upgrade)
            print("   - Generating dynamic episode artwork prompt...")
            image_prompt = generate_image_prompt(all_news)
            
            # 1. Try Pollinations AI (Requires API Key in 2026)
            pollinations_key = os.getenv("POLLINATIONS_API_KEY")
            seed = random.randint(0, 1000000)
            encoded_prompt = quote(image_prompt)
            
            if pollinations_key:
                image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1400&height=1400&nologo=true&seed={seed}&key={pollinations_key}"
                print(f"   - AI Artwork (Pollinations) generated: {image_url}")
            else:
                # 2. Fallback to Unsplash (Zero-Cost, No Key High-Quality Photos)
                # We use the top keywords for the search
                keywords = quote(image_prompt.split(",")[1].strip() if "," in image_prompt else "news")
                image_url = f"https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&w=1400&h=1400&q=80&keywords={keywords}"
                print(f"   - [INFO] No Pollinations key. Falling back to Unsplash: {image_url}")

            description = f"Morning Pulse for {display_date}. Top stories from NYT, Markets, Tech, and more - fact-checked and research-backed."
            update_feed(permanent_path, f"Morning Pulse - {display_date}", description, image_url=image_url)
            print(f"   - RSS updated! MP3 saved to: {permanent_path}")

            # Step 6: Social Media Blast (X/Twitter)
            print(f"\nStep 6/4 -- Blasting to Social Media (X)...")
            try:
                tweet_text = generate_social_hook(all_news)
                # Link to Spotify
                link = "Listen now: https://open.spotify.com/show/57JysTl6fZwvGBFC4KBeux"
                full_tweet = f"{tweet_text}\n\n{link}"
                post_episode_to_twitter(full_tweet, image_url=image_url)
            except Exception as e:
                print(f"   - [WARNING] Twitter post failed: {e}")
        except Exception as e:
            print(f"   - [WARNING] RSS update failed: {e}")

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
