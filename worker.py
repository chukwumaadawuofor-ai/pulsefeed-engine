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

# Define RSS feeds
FEEDS = {
    "Football": "https://rss.app/feeds/v1.1/wtuh7e98a5d3f23a.json", # Replace or keep your feed URLs
    "Business": "https://news.google.com/rss/search?q=business+nigeria&hl=en-NG&gl=NG&ceid=NG:en",
    "Crypto": "https://cointelegraph.com/rss"
}

def send_to_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHANNEL_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    response = requests.post(url, json=payload)
    print(f"Telegram Status Code: {response.status_code}")
    print(f"Telegram Response: {response.text}")
    return response

def main():
    print("--- Starting Feed Fetcher ---")
    
    for category, url in FEEDS.items():
        print(f"Fetching {category} from {url}...")
        parsed = feedparser.parse(url)
        print(f"Found {len(parsed.entries)} entries in {category}")
        
        for entry in parsed.entries[:3]: # Limit to top 3 for testing
            title = entry.get("title", "No Title")
            link = entry.get("link", "")
            
            # Check if article already exists in Supabase
            existing = supabase.table("articles").select("id").eq("link", link).execute()
            if existing.data:
                print(f"Skipping duplicate: {title}")
                continue
                
            print(f"New article found: {title}")
            
            # Insert into Supabase
            insert_res = supabase.table("articles").insert({"title": title, "link": link, "category": category}).execute()
            print(f"Supabase Insert Response: {insert_res}")
            
            # Format and send to Telegram
            message = f"*{category} Update*\n\n{title}\n\n[Read More]({link})"
            send_to_telegram(message)

    print("--- Feed processing complete ---")

if __name__ == "__main__":
    main()
