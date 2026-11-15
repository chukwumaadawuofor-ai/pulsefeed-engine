```python
import os
import feedparser
import requests
from supabase import create_client, Client

# Load environment variables
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID")

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Define RSS feeds with emojis for clean channel branding
FEEDS = {
    "⚽ FOOTBALL": "https://feeds.bbci.co.uk/sport/football/rss.xml",
    "💼 BUSINESS": "https://news.google.com/rss/search?q=business+nigeria&hl=en-NG&gl=NG&ceid=NG:en",
    "🪙 CRYPTO": "https://cointelegraph.com/rss"
}

def send_to_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHANNEL_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    response = requests.post(url, json=payload)
    print(f"Telegram Status Code: {response.status_code}")
    print(f"Telegram Response: {response.text}")
    return response

def main():
    print("--- Starting Feed Fetcher ---")
    for category, feed_url in FEEDS.items():
        print(f"Fetching {category} from {feed_url}...")
        parsed = feedparser.parse(feed_url)
        print(f"Found {len(parsed.entries)} entries in {category}")
        
        # Post top 2 newest articles per category to keep the feed balanced
        for entry in parsed.entries[:2]:
            link = entry.link
            title = entry.title
            
            # Check if article already exists in Supabase
            existing = supabase.table("articles").select("id").eq("link", link).execute()
            
            if not existing.data:
                # Escape any accidental Markdown underscores or asterisks in headlines
                clean_title = title.replace("_", "\\_").replace("*", "\\*")
                
                message = (
                    f"*{category} UPDATE*\n\n"
                    f"{clean_title}\n\n"
                    f"🔗 [Read Full Story]({link})\n"
                    f"📲 Follow @PulseFeedNG"
                )
                
                res = send_to_telegram(message)
                
                if res.status_code == 200:
                    supabase.table("articles").insert({
                        "title": title,
                        "link": link,
                        "category": category
                    }).execute()
                    print(f"Saved & Sent: {title}")
                else:
                    print(f"Failed to send: {title}")

if __name__ == "__main__":
    main()
```
