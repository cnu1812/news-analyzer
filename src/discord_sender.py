"""
Discord sender — delivers the Morning Pulse podcast to your Discord channel
via a webhook. Sends a rich embed + the MP3 audio file attachment.
"""
import os
import json
import requests
from datetime import datetime
from pathlib import Path


def _build_embed(date_str: str, script: str, market_data: dict) -> dict:
    """Build a rich Discord embed with today's highlights."""
    # Extract market snapshot lines
    indices = market_data.get("indices", {})
    market_lines = []
    for name, vals in indices.items():
        arrow = "📈" if vals["change_pct"] >= 0 else "📉"
        sign = "+" if vals["change_pct"] >= 0 else ""
        market_lines.append(f"{arrow} **{name}**: {vals['price']:,.2f} ({sign}{vals['change_pct']}%)")

    # Word count → estimated duration
    word_count = len(script.split())
    duration_min = round(word_count / 130)

    embed = {
        "title": f"🎙️ Morning Pulse — {date_str}",
        "description": (
            f"Your daily **{duration_min}-minute** news briefing is ready!\n\n"
            + ("**📊 Indian Markets**\n" + "\n".join(market_lines) if market_lines else "")
        ),
        "color": 0x5865F2,  # Discord blurple
        "fields": [
            {
                "name": "📰 Sections Covered",
                "value": (
                    "🗞️ New York Times Front Page\n"
                    "📈 Indian Market Analysis\n"
                    "🏏 Indian Sports & Business\n"
                    "🌍 World News\n"
                    "💹 CNBC Market Analytics\n"
                    "💻 Tech News"
                ),
                "inline": True,
            },
            {
                "name": "⏱️ Details",
                "value": (
                    f"Duration: ~{duration_min} min\n"
                    f"Words: {word_count:,}\n"
                    f"Voice: Andrew (Neural)\n"
                    f"Generated: 6:00 AM IST"
                ),
                "inline": True,
            },
        ],
        "footer": {"text": "Morning Pulse • Powered by Groq Llama-3.3-70B + Edge TTS"},
        "timestamp": datetime.utcnow().isoformat(),
    }
    return embed


def send_to_discord(
    audio_path: str,
    script: str,
    date_str: str,
    market_data: dict,
) -> bool:
    """
    Send the podcast to Discord via webhook.
    
    Returns True on success, False on failure.
    """
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        raise ValueError("DISCORD_WEBHOOK_URL environment variable not set!")

    audio_file = Path(audio_path)
    if not audio_file.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    embed = _build_embed(date_str, script, market_data)

    # Discord webhook with file attachment uses multipart form
    payload = {
        "username": "Morning Pulse 🎙️",
        "avatar_url": "https://i.imgur.com/4M34hi2.png",
        "embeds": [embed],
    }

    print(f"[Discord] Sending podcast to webhook...")

    with open(audio_path, "rb") as f:
        response = requests.post(
            webhook_url,
            data={"payload_json": __import__("json").dumps(payload)},
            files={"file": (audio_file.name, f, "audio/mpeg")},
            timeout=120,
        )

    if response.status_code in (200, 204):
        print(f"[Discord] (OK) Podcast sent successfully!")
        return True
    else:
        print(f"[Discord] (Failed) Failed: {response.status_code} — {response.text[:300]}")
        return False


def send_error_notification(error_msg: str, date_str: str) -> None:
    """Send an error notification to Discord if the pipeline fails."""
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        return

    embed = {
        "title": f"⚠️ Morning Pulse Failed — {date_str}",
        "description": f"The daily podcast generation encountered an error:\n```\n{error_msg[:1000]}\n```",
        "color": 0xFF0000,
        "footer": {"text": "Morning Pulse • Error Report"},
    }

    requests.post(
        webhook_url,
        json={"username": "Morning Pulse 🎙️", "embeds": [embed]},
        timeout=30,
    )


if __name__ == "__main__":
    # Test embed preview (won't actually send without webhook URL)
    dummy_embed = _build_embed(
        "March 24, 2026",
        "test " * 1800,
        {"indices": {"NIFTY 50": {"price": 22000, "change_pct": 0.5}}},
    )
    import json
    print(json.dumps(dummy_embed, indent=2))
