import os
import tweepy
import requests
from pathlib import Path

def post_episode_to_twitter(text: str, image_url: str = None):
    """
    Posts a daily update to Twitter (X) using API v2.
    Includes an image if image_url is provided.
    """
    # 1. Load Credentials
    api_key = os.getenv("TWITTER_API_KEY")
    api_secret = os.getenv("TWITTER_API_SECRET")
    access_token = os.getenv("TWITTER_ACCESS_TOKEN")
    access_token_secret = os.getenv("TWITTER_ACCESS_SECRET")

    if not all([api_key, api_secret, access_token, access_token_secret]):
        print("[Twitter] Missing credentials. Skipping social post.")
        return False

    try:
        # 2. Authentication (V2 Client for Tweeting, V1.1 for Media)
        client = tweepy.Client(
            consumer_key=api_key, consumer_secret=api_secret,
            access_token=access_token, access_token_secret=access_token_secret
        )
        
        auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_token_secret)
        api_v1 = tweepy.API(auth)

        media_ids = []
        # 3. Handle Image (Download and Upload)
        if image_url:
            print(f"[Twitter] Downloading artwork for tweet: {image_url}")
            temp_img = "temp_tweet_art.jpg"
            response = requests.get(image_url, stream=True)
            if response.status_code == 200:
                with open(temp_img, 'wb') as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
                
                # Upload to Twitter v1.1 (Required for media)
                media = api_v1.media_upload(filename=temp_img)
                media_ids.append(media.media_id)
                os.remove(temp_img)
            else:
                print(f"[Twitter] Failed to download image: {response.status_code}")

        # 4. Post Tweet
        response = client.create_tweet(text=text, media_ids=media_ids if media_ids else None)
        print(f"[Twitter] Success! Tweet ID: {response.data['id']}")
        return True

    except Exception as e:
        print(f"[Twitter] Error posting to Twitter: {e}")
        return False

if __name__ == "__main__":
    # Test (requires .env)
    post_episode_to_twitter("Hello from Morning Pulse! 🎙️ #AI #News", "https://cnu1812.github.io/news-analyzer/assets/logo.png")
