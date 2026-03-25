"""
Text-to-Speech engine using Microsoft Edge Neural Voices (edge-tts).
100% Free, Zero Character Limits, Premium Neural Quality.
Supports MULTI-HOST banter and BACKGROUND MUSIC mixing via pydub.
"""
import os
import sys
import asyncio
import edge_tts
import requests
import time
import random
from gtts import gTTS
from pathlib import Path

# Explicitly ensure Pydub finds FFmpeg in the venv on Windows (for local dry-runs)
venv_scripts_path = Path("venv/Scripts").resolve()
os.environ["PATH"] = str(venv_scripts_path) + os.pathsep + os.environ.get("PATH", "")

from pydub import AudioSegment

# Free & Unlimited Neural Voices for Edge-TTS
HOST_A_VOICE_ID = "en-IN-PrabhatNeural"    # Sreenivas (Professional Indian Male)
HOST_B_VOICE_ID = "en-IN-NeerjaNeural"    # Deepika (Warm Indian Female)

OUTPUT_DIR = Path("output")
ASSETS_DIR = Path("src/assets")


async def _generate_speech_async(text: str, voice_id: str, output_file: str) -> None:
    """Generate audio for a single chunk of text using edge-tts asynchronously with retries."""
    max_retries = 3
    base_delay = 2
    
    for attempt in range(max_retries):
        try:
            communicate = edge_tts.Communicate(text, voice_id)
            await communicate.save(output_file)
            return
        except Exception as e:
            # Handle 503 (Service Unavailable) or handshake errors which are often transient
            error_msg = str(e)
            if "503" in error_msg or "Handshake" in error_msg or "Invalid response status" in error_msg:
                wait_time = base_delay * (2 ** attempt) + random.uniform(0, 1)
                print(f"      [TTS] Service busy (503), retrying in {wait_time:.1f}s... (Attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(wait_time)
            else:
                raise e
    
    # Final attempt without catching to let the exception bubble up if it still fails
    communicate = edge_tts.Communicate(text, voice_id)
    await communicate.save(output_file)


def _generate_speech_gtts(text: str, output_file: str) -> None:
    """Fallback: Generate audio using Google TTS (gTTS) if Edge-TTS fails."""
    try:
        # Use Indian English accent for consistency
        tts = gTTS(text=text, lang='en', tld='co.in')
        tts.save(output_file)
    except Exception as e:
        print(f"      [TTS] CRITICAL: Fallback gTTS also failed: {e}")
        raise e


def _generate_speech(text: str, voice_id: str) -> bytes:
    """Synchronous wrapper to generate audio with edge-tts and return bytes, with gTTS fallback."""
    temp_file = str(OUTPUT_DIR / f"temp_{abs(hash(text))}.mp3")
    
    try:
        # Primary: Microsoft Edge Neural TTS
        asyncio.run(_generate_speech_async(text, voice_id, temp_file))
    except Exception as e:
        print(f"      [TTS] Warning: Edge-TTS failed after retries ({e}). Switching to gTTS fallback...")
        try:
            # Secondary: Google TTS (gTTS)
            _generate_speech_gtts(text, temp_file)
        except Exception as fallback_err:
            # Last Resort: If even gTTS fails, we have to bubble up the error or return silent audio
            raise fallback_err
    
    with open(temp_file, "rb") as f:
        audio_bytes = f.read()
        
    os.remove(temp_file)
    return audio_bytes


def _download_sample_music() -> Path:
    """Download a royalty-free CC0 background track if one doesn't exist."""
    bg_music_path = ASSETS_DIR / "bg_music.mp3"
    if bg_music_path.exists():
        return bg_music_path
        
    print("[TTS] Background music not found. Downloading a sample CC0 track...")
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    # Direct URL to a public domain ambient/lo-fi track
    url = "https://cdn.pixabay.com/download/audio/2022/05/27/audio_1808fbf07a.mp3?filename=lofi-study-112191.mp3"
    try:
        r = requests.get(url, stream=True)
        with open(bg_music_path, "wb") as f:
            for chunk in r.iter_content(1024):
                f.write(chunk)
        return bg_music_path
    except Exception as e:
        print(f"[TTS] Warning: Could not download sample music ({e}). Proceeding without music.")
        return None


def text_to_speech(script: str, date_str: str) -> str:
    """
    Parse a dual-host script, generate MP3s via edge-tts, stitch them,
    add background music, and return the final MP3 path.
    """
    OUTPUT_DIR.mkdir(exist_ok=True)
    output_path = str(OUTPUT_DIR / f"morning_pulse_{date_str}.mp3")

    # 1. Parse Script Lines
    print("[TTS] Parsing dual-host script...")
    lines = script.split("\n")
    
    segments = [] # List of tuples: (text, voice_id)
    current_text = ""
    current_voice = HOST_A_VOICE_ID # Default

    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if line.startswith("[HOST_A]"):
            if current_text:
                segments.append((current_text, current_voice))
            current_text = line.replace("[HOST_A]", "").strip()
            current_voice = HOST_A_VOICE_ID
        elif line.startswith("[HOST_B]"):
            if current_text:
                segments.append((current_text, current_voice))
            current_text = line.replace("[HOST_B]", "").strip()
            current_voice = HOST_B_VOICE_ID
        else:
            current_text += " " + line

    if current_text:
        segments.append((current_text, current_voice))

    print(f"[TTS] Generated {len(segments)} distinct dialogue segments.")

    # 2. Fetch Audio for each segment
    print("[TTS] Calling Edge-TTS Azure API for audio segments...")
    master_audio = AudioSegment.empty()
    
    for i, (text, voice_id) in enumerate(segments):
        print(f"      -> Synthesizing segment {i+1}/{len(segments)} (Voice: {'Sreenivas' if voice_id == HOST_A_VOICE_ID else 'Deepika'})...")
        audio_bytes = _generate_speech(text, voice_id)
        
        # Pacing: small delay between segments to avoid aggressive rate limiting
        if i < len(segments) - 1:
            time.sleep(0.5)
        
        # Save temp file for pydub to read
        temp_file = OUTPUT_DIR / f"temp_chunk_{i}.mp3"
        with open(temp_file, "wb") as f:
            f.write(audio_bytes)
            
        try:
            segment_audio = AudioSegment.from_mp3(temp_file)
            # Add 250ms natural conversation pause between speakers
            pause = AudioSegment.silent(duration=250) 
            master_audio += segment_audio + pause
        except Exception as e:
            print(f"[TTS] Warning: Could not process audio chunk. Ensure ffmpeg is installed! ({e})")
            return str(temp_file) # Exit early with just the first chunk as fallback
            
        # Cleanup temp file
        os.remove(temp_file)

    # 3. Add Background Music
    bg_music_path = _download_sample_music()
    if bg_music_path:
        print("[TTS] Mixing background music...")
        try:
            bg_audio = AudioSegment.from_mp3(bg_music_path)
            # Reduce volume of background music by 20 dB so it sits nicely underneath
            bg_audio = bg_audio - 20  
            # Loop music if it's shorter than the podcast
            while len(bg_audio) < len(master_audio):
                bg_audio += bg_audio
                
            # Trim music to exact podcast length
            bg_audio = bg_audio[:len(master_audio)]
            # Add a 3 second fade-out to the music at the end
            bg_audio = bg_audio.fade_out(3000)
            # Overlay voices on top of the music
            master_audio = bg_audio.overlay(master_audio)
        except Exception as e:
            print(f"[TTS] Warning: Background music mixing failed (ensure ffmpeg is installed). {e}")

    # 4. Export Final MP3
    print(f"[TTS] Exporting final master track to {output_path}...")
    try:
        master_audio.export(output_path, format="mp3", bitrate="64k")
    except Exception as e:
        print(f"[TTS] Warning: Could not export final MP3 (ensure ffmpeg is installed). {e}")
        return str(OUTPUT_DIR / "temp_chunk_0.mp3") # Fallback

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"[TTS] Done! File size: {size_mb:.1f} MB")
    return output_path


if __name__ == "__main__":
    sample = "[HOST_A] Welcome to the Morning Pulse! \n[HOST_B] Wow, what a day in the markets!"
    path = text_to_speech(sample, "2026-03-24")
