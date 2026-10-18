# 🎙️ Morning Pulse — AI Daily News Podcast

Your personal AI news radio show. Every morning at **6:00 AM IST**, it scrapes top headlines (**strictly filtering for high-value macro news**), writes a dynamic dual-host banter script with Groq AI, converts it to two ultra-realistic voices via ElevenLabs, mixes in an ambient background beat, and drops the finished MP3 straight into your Discord server.

---

## ✨ What You Get

A **~15-minute MP3** sent to Discord every morning covering:

| Section | Sources |
|---------|---------|
| 🗞️ New York Times Front Page | NYT RSS |
| 📈 Indian Market Analysis | ET Markets + MoneyControl + Yahoo Finance (live indices) |
| 🏏 Indian Sports | Times of India + Cricbuzz |
| 💼 Indian Business | Economic Times + Business Standard |
| 🌍 World News | BBC World + Reuters |
| 💹 CNBC Market Analytics | CNBC RSS |
| 💻 Tech News | TechCrunch + The Verge + Ars Technica |

### 🔥 Advanced v2 Features Included:
- **Strict News Filtering**: Automatically discards celebrity gossip and fluff; focuses strictly on market-moving, geopolitical, and high-impact macro news.
- **Dual-Host Banter**: Script is dynamically written and voiced as a dialogue between Host A (Adam) and Host B (Rachel).
- **Background Music Mixing**: Automatically downloads and seamlessly mixes a lo-fi background beat underneath the podcast using `pydub`.

---

## 🛠️ Setup (One-Time)

### 1. Fork / Clone this repo to GitHub

### 2. Get your free API keys

**Groq API** (free, no credit card needed beyond signup):
1. Go to [console.groq.com](https://console.groq.com)
2. Sign up → API Keys → Create key
3. Copy the key starting with `gsk_...`

**ElevenLabs API** (free 10,000 chars/month):
1. Go to [elevenlabs.io](https://elevenlabs.io)
2. Sign up → Profile → API Keys
3. Copy the API key

**Discord Webhook**:
1. Open your Discord server
2. Go to the channel where you want the podcast
3. Click ⚙️ Edit Channel → Integrations → Webhooks → New Webhook
4. Copy the Webhook URL

**Twitter (X) API** (for automated posting):
1. Go to [developer.x.com](https://developer.x.com) and sign up for a **Free Developer Account**.
2. Create a new **Project** and **App**.
3. In **App Settings** -> **User authentication settings**:
   - Set App permissions to **Read and Write**.
   - Type of App: **Web App, Android, iOS**.
   - Callback URL / Website URL: Use your GitHub repo URL (required field, but not used for this bot).
4. Go to **Keys and Tokens**:
   - **API Key and Secret** -> Regenerate to get `TWITTER_API_KEY` and `TWITTER_API_SECRET`.
   - **Access Token and Secret** -> Generate to get `TWITTER_ACCESS_TOKEN` and `TWITTER_ACCESS_SECRET`.

### 3. Add GitHub Secrets

In your GitHub repo → **Settings → Secrets and variables → Actions → New repository secret**:

| Secret Name | Value |
|-------------|-------|
| `GROQ_API_KEY` | Your Groq key (`gsk_...`) |
| `ELEVENLABS_API_KEY` | Your ElevenLabs key |
| `DISCORD_WEBHOOK_URL` | Your Discord webhook URL |
| `TWITTER_API_KEY` | Your X (Twitter) API Key |
| `TWITTER_API_SECRET` | Your X (Twitter) API Secret |
| `TWITTER_ACCESS_TOKEN` | Your X (Twitter) Access Token |
| `TWITTER_ACCESS_SECRET` | Your X (Twitter) Access Token Secret |

### 4. Enable GitHub Actions

Go to your repo → **Actions tab** → Enable workflows (if prompted).

That's it! 🎉 The podcast runs automatically every morning.

---

## 🚀 Test It Right Now

**Trigger manually** (without waiting for 6 AM):
1. GitHub repo → Actions → "Morning Pulse — Daily Podcast"
2. Click **Run workflow** → Run

Or run locally:
```bash
pip install -r requirements.txt

# Note: FFmpeg must be installed on your system for audio mixing to work locally!
# (FFmpeg is automatically installed on the GitHub Actions runner)

# Copy and fill in your keys
copy .env.example .env
# edit .env with your actual keys

# Windows (PowerShell)
$env:GROQ_API_KEY="gsk_..."
$env:DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
python src/main.py
```

---

## 📁 Project Structure

```
morning-pulse/
├── .github/workflows/
│   └── daily_podcast.yml   ← GitHub Actions (runs 6AM IST daily)
├── src/
│   ├── scrapers/
│   │   ├── nyt.py
│   │   ├── indian_market.py
│   │   ├── indian_sports_business.py
│   │   ├── world_news.py
│   │   ├── cnbc.py
│   │   └── tech_news.py
│   ├── script_generator.py  ← Groq / Gemini with automatic model fallback
│   ├── tts_engine.py        ← Microsoft Edge Neural TTS
│   ├── discord_sender.py    ← Webhook delivery
│   └── main.py              ← Orchestrator
├── output/                  ← Generated MP3s (gitignored)
├── requirements.txt
└── .env.example
```

---

## 💰 Cost Breakdown

| Service | Plan | Cost |
|---------|------|------|
| GitHub Actions | Free tier (2000 min/month) | **Free** |
| Groq API | Free tier | **Free** |
| ElevenLabs | Free tier (10k chars/month) | **Free** |
| News sources | RSS feeds | **Free** |
| Discord | Webhooks | **Free** |
| **Total** | | **$0/month** |

---

## 🎨 Customization

- **Change TTS voice**: Edit `VOICE` in `src/tts_engine.py`
- **Change schedule**: Edit the cron in `.github/workflows/daily_podcast.yml`  
  (`"30 0 * * *"` = 6:00 AM IST | `"0 2 * * *"` = 7:30 AM IST)
- **Add/remove news sources**: Edit any file in `src/scrapers/`


## Automatic model recovery

All script, fact-checking, artwork-prompt and social-hook requests share
`src/llm_utils.py`. Gemini now defaults to `gemini-flash-latest` (Google's rolling
Flash alias), and Groq defaults to `openai/gpt-oss-120b`.

For each request, the app queries the provider's model catalog, then tries:

1. An optional `GEMINI_MODEL` / `GROQ_MODEL` override.
2. Optional comma-separated `GEMINI_FALLBACK_MODELS` / `GROQ_FALLBACK_MODELS`.
3. Built-in alternatives, followed by compatible models from the live catalog.
4. The other provider, if its API key is configured.

Discovery prefers newer Gemini Flash versions and orders Groq discoveries by
creation time. It excludes specialized models and restricts automatic discovery
to recognized general-purpose text model families. Gemini discovery requires
`generateContent` support and excludes previews; the rolling latest alias itself
may point to a preview, according to Google's release policy. Explicit overrides
can select other models. A future model with a different naming/API contract may
still need a code update; no fallback can guarantee access, quota, or compatibility.

404/410 and Groq retirement errors suppress that model for one hour in the current
process. Every scheduled run starts fresh and discovers available replacements;
no source-code edits or commits are needed for ordinary model retirements. If the
catalog is unavailable, configured models and built-in defaults are still tried.
401/403 errors move to the other provider rather than misclassifying an API key
problem as retirement. Rate limits and server failures try the next candidate.
Each provider has a maximum of eight generation attempts with connection/read
timeouts of 10/90 seconds. Logs identify the selected model without printing keys,
prompts, or raw provider error bodies. Empty, truncated and invalid JSON responses
are rejected instead of being published as successful generations.

In GitHub Actions, set the optional model overrides under **Settings → Secrets and
variables → Actions → Variables**. Existing API key secrets and `PREFER_GEMINI`
continue to work. Models can have different costs and quotas; selection does not
change billing settings or guarantee free-tier availability.

The integration uses the providers' documented REST APIs through the existing
`requests` dependency, replacing the old Groq and Gemini SDK pins.

Run offline regression tests (no API keys or publishing):

```bash
python -m unittest discover -s tests -v
```

Model/API references: [Gemini models](https://ai.google.dev/gemini-api/docs/models),
[Gemini model discovery](https://ai.google.dev/api/models),
[Groq models](https://console.groq.com/docs/models),
[Groq API](https://console.groq.com/docs/api-reference).
