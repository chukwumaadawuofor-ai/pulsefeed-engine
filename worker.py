import os
import requests
import feedparser
from datetime import datetime

# Load environment variables from GitHub Secrets
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL = os.environ.get("TELEGRAM_CHANNEL_ID")

# Supabase headers
headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# RSS Feed sources
FEEDS = {
    "Football": "http://feeds.bbci.co.uk/sport/football/rss.xml",
    "Business": "https://feeds.reuters.com/reuters/businessNews",
    "Crypto": "https://www.coindesk.com/arc/outboundfeeds/rss/"
}

def run_worker():
    print(f"--- Running Feed Fetcher at {datetime.now()} ---")
    
    for category, feed_url in FEEDS.items():
        print(f"Fetching {category}...")
        parsed_feed = feedparser.parse(feed_url)
        
        for entry in parsed_feed.entries[:5]: # Take top 5 entries per run
            title = entry.get("title")
            link = entry.get("link")
            published = entry.get("published", str(datetime.now()))
            
            # 1. Check if article already exists in Supabase (duplicate check)
            check_url = f"{SUPABASE_URL}/rest/v1/articles?link=eq.{link}"
            res = requests.get(check_url, headers=headers)
            
            if res.status_code == 200 and len(res.json()) > 0:
                # Article already exists, skip it
                continue
            
            # 2. Insert new article into Supabase
            payload = {
                "title": title,
                "link": link,
                "source": category,
                "category": category,
                "published_at": published
            }
            insert_res = requests.post(f"{SUPABASE_URL}/rest/v1/articles", headers=headers, json=payload)
            
            if insert_res.status_code in [200, 201]:
                print(f"Saved to Supabase: {title}")
                
                # 3. Broadcast teaser to Telegram Channel with logging
                telegram_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
                msg = f"*{category} Update*\n\n{title}\n\n🔗 {link}"
                tg_payload = {
                    "chat_id": TELEGRAM_CHANNEL,
                    "text": msg,
                    "parse_mode": "Markdown"
                }
                
                tg_res = requests.post(telegram_url, json=tg_payload)
                print(f"Telegram Status Code: {tg_res.status_code}")
                print(f"Telegram Response JSON: {tg_res.json()}")
                
    print("--- Feed processing complete ---")

if __name__ == "__main__":
    run_worker()
