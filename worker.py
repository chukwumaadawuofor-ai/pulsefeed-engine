import os
import feedparser
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

# Supabase Headers
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates"
}

# RSS Feeds to monitor (Football & Finance)
FEEDS = [
    {"name": "BBC Sport Football", "category": "Football", "url": "https://feeds.bbci.co.uk/sport/football/rss.xml"},
    {"name": "Reuters Business", "category": "Finance", "url": "https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best"},
    {"name": "CoinDesk Crypto", "category": "Crypto", "url": "https://www.coindesk.com/arc/outboundrss/?outputType=xml"}
]

def send_telegram_alert(title, link, category):
    """Sends formatted teaser to your Telegram channel"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL_ID:
        print("Telegram credentials missing. Skipping notification.")
        return

    emoji = "⚽" if category == "Football" else "📈" if category == "Finance" else "🚀"
    
    message = (
        f"{emoji} **{category} Update**\n\n"
        f"*{title}*\n\n"
        f"🔗 [Read Full Update]({link})"
    )

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHANNEL_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            print(f"Telegram Error: {response.text}")
    except Exception as e:
        print(f"Failed to send Telegram alert: {e}")

def save_to_supabase(article):
    """Upserts article to Supabase table 'articles' using 'link' as unique constraint"""
    url = f"{SUPABASE_URL}/rest/v1/articles"
    try:
        response = requests.post(url, headers=HEADERS, json=article, timeout=10)
        if response.status_code in [200, 201]:
            return True
        else:
            print(f"Supabase Error: {response.text}")
            return False
    except Exception as e:
        print(f"Database connection error: {e}")
        return False

def process_feeds():
    print(f"--- Running Feed Fetcher at {datetime.now()} ---")
    
    for feed_info in FEEDS:
        print(f"Fetching {feed_info['name']}...")
        parsed_feed = feedparser.parse(feed_info["url"])
        
        for entry in parsed_feed.entries[:5]:
            title = entry.get("title", "No Title")
            link = entry.get("link", "")
            published = entry.get("published", datetime.now().isoformat())
            
            if not link:
                continue

            article_data = {
                "title": title,
                "link": link,
                "source": feed_info["name"],
                "category": feed_info["category"],
                "published_at": published
            }

            url_check = f"{SUPABASE_URL}/rest/v1/articles?link=eq.{requests.utils.quote(link, safe='')}"
            check_res = requests.get(url_check, headers=HEADERS).json()

            if not check_res:
                success = save_to_supabase(article_data)
                if success:
                    print(f"New item saved & broadcasting: {title}")
                    send_telegram_alert(title, link, feed_info["category"])
            else:
                continue

    print("--- Feed processing complete ---")

if __name__ == "__main__":
    process_feeds()
