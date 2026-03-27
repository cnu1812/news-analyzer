"""
RSS Feed Generator for Morning Pulse.
Manages episode history and generates a standards-compliant RSS feed.
"""
import os
import json
import uuid
import time
from datetime import datetime
from pathlib import Path
from pydub import AudioSegment
from xml.sax.saxutils import escape

# Configuration (Change via .env)
BASE_URL = os.getenv("PODCAST_BASE_URL", "https://cnu1812.github.io/news-analyzer")
PODCAST_TITLE = "Morning Pulse"
PODCAST_DESC = "Wake up to the smartest 10 minutes of your day. Your daily AI-powered news briefing, delivering high-value insights from the NYT, global markets, CNBC, and tech breakthroughs. Fact-checked and research-backed by advanced AI for deep context."
PODCAST_AUTHOR = "Morning Pulse AI"
PODCAST_EMAIL = "cnu1812@gmail.com"
PODCAST_IMAGE = f"{BASE_URL}/assets/logo.png"
PODCAST_CATEGORY = "News"

def update_feed(mp3_path: str, title: str, description: str, image_url: str = None):
    """Adds a new episode and regenerates the RSS feed."""
    data_dir = Path("data")
    episodes_file = data_dir / "episodes.json"
    
    # 1. Load history
    if episodes_file.exists():
        with open(episodes_file, "r") as f:
            episodes = json.load(f)
    else:
        episodes = []

    # 2. Extract metadata
    file_size = os.path.getsize(mp3_path)
    audio = AudioSegment.from_mp3(mp3_path)
    duration_sec = int(len(audio) / 1000)
    
    # 3. Create new episode entry
    file_name = os.path.basename(mp3_path)
    new_episode = {
        "guid": str(uuid.uuid4()),
        "title": title,
        "description": description,
        "pub_date": datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000"),
        "url": f"{BASE_URL}/podcasts/{file_name}",
        "length": file_size,
        "duration": duration_sec,
        "type": "audio/mpeg",
        "image": image_url if image_url else PODCAST_IMAGE
    }
    
    # 4. Save history (newest first)
    episodes.insert(0, new_episode)
    with open(episodes_file, "w") as f:
        json.dump(episodes, f, indent=2)

    # 5. Generate XML
    return generate_xml(episodes)


def generate_xml(episodes):
    """Generates the RSS XML file."""
    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" 
    xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" 
    xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel>
    <title>{PODCAST_TITLE}</title>
    <description>{PODCAST_DESC}</description>
    <link>{BASE_URL}</link>
    <language>en-us</language>
    <itunes:author>{PODCAST_AUTHOR}</itunes:author>
    <itunes:type>episodic</itunes:type>
    <itunes:owner>
      <itunes:name>{PODCAST_AUTHOR}</itunes:name>
      <itunes:email>{PODCAST_EMAIL}</itunes:email>
    </itunes:owner>
    <itunes:image href="{escape(PODCAST_IMAGE)}"/>
    <itunes:category text="{escape(PODCAST_CATEGORY)}"/>
    <itunes:explicit>no</itunes:explicit>
"""

    for ep in episodes:
        # Convert duration to HH:MM:SS
        h = ep['duration'] // 3600
        m = (ep['duration'] % 3600) // 60
        s = ep['duration'] % 60
        duration_fmt = f"{h:02}:{m:02}:{s:02}"

        rss += f"""
    <item>
      <title>{escape(ep['title'])}</title>
      <description>{escape(ep['description'])}</description>
      <pubDate>{ep['pub_date']}</pubDate>
      <guid isPermaLink="false">{ep['guid']}</guid>
      <enclosure url="{escape(ep['url'])}" length="{ep['length']}" type="{ep['type']}"/>
      <itunes:image href="{escape(ep.get('image', PODCAST_IMAGE))}"/>
      <itunes:duration>{duration_fmt}</itunes:duration>
      <itunes:explicit>no</itunes:explicit>
    </item>"""

    rss += """
  </channel>
</rss>"""

    with open("index.xml", "w", encoding="utf-8") as f:
        f.write(rss)
    
    print(f"[RSS] Updated index.xml with {len(episodes)} episodes.")
    return "index.xml"

if __name__ == "__main__":
    # Test generation
    if os.path.exists("data/episodes.json"):
        with open("data/episodes.json", "r") as f:
            data = json.load(f)
            generate_xml(data)
