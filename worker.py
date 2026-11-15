
import os
import random
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
    "⚽ FOOTBALL": "https://feeds.bbci.co.uk/sport/football/rss.xml",
    "💼 BUSINESS": "https://news.google.com/rss/search?q=business+nigeria&hl=en-NG&gl=NG&ceid=NG:en",
    "🪙 CRYPTO": "https://cointelegraph.com/rss"
}

# Sample accumulator match predictions & mock booking codes for Nigerian bookmakers (SportyBet / Bet9ja style)
BETTING_ACCUMULATORS = [
    {
        "title": "Weekend Banker Accumulator (3 Odds)",
        "games": [
            "1. Manchester City vs Wolves — Home Win & Over 1.5",
            "2. Real Madrid vs Valencia — Real Madrid Win",
            "3. Napoli vs Monza — Over 2.5 Goals"
        ],
        "booking_code": "SP9J" + str(random.randint(100000, 999999)),
        "bookmaker": "SportyBet / Bet9ja"
    },
    {
        "title": "Super Value Multi-Bet (5 Odds)",
        "games": [
            "1. Arsenal vs Crystal Palace — Arsenal Clean Sheet (No)",
            "2. Bayern Munich vs Augsburg — Over 3.5 Goals",
            "3. Inter Milan vs Empoli — Home Win in Both Halves"
        ],
        "booking_code": "B9JA" + str(random.randint(100000, 999999)),
        "bookmaker": "Bet9ja / 1xBet"
    },
    {
        "title": "Mega Goal Rush Slip (8+ Odds)",
        "games": [
            "1. Barcelona vs Villarreal — Both Teams to Score & Over 2.5",
            "2. Liverpool vs Aston Villa — Over 2.5 Goals",
            "3. PSG vs Marseille — Both Teams to Score"
        ],
        "booking_code": "RET" + str(random.randint(100000, 999999)),
        "bookmaker": "NairaBet / SportyBet"
    }
]

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

def post_betting_slip():
    # Pick a random accumulator slip to post
    slip = random.choice(BETTING_ACCUMULATORS)
    
    # Create a unique link/identifier key for Supabase to prevent duplicate posting
    slip_id_key = f"betting_slip_{slip['booking_code']}"
    
    existing = supabase.table("articles").select("id").eq("link", slip_id_key).execute()
    
    if not existing.data:
        games_text = "\n".join(slip["games"])
        message = (
            f"🎯 *DAILY BOOKING CODE UPDATE*\n\n"
            f"*{slip['title']}*\n\n"
            f"{games_text}\n\n"
            f"🔖 *Booking Code:* `{slip['booking_code']}`\n"
            f"🏦 *Recommended App/Shop:* {slip['bookmaker']}\n\n"
            f"⚠️ *Play Responsibly (18+)*\n"
            f"📲 Follow @PulseFeedNG"
        )
        
        res = send_to_telegram(message)
        if res.status_code == 200:
            supabase.table("articles").insert({
                "title": slip["title"],
                "link": slip_id_key,
                "category": "🎯 BETTING TIPS"
            }).execute()
            print(f"Successfully posted betting slip: {slip['booking_code']}")

def main():
    print("--- Starting Feed Fetcher & Betting Bot ---")
    
    # 1. Fetch normal RSS news feeds
    for category, feed_url in FEEDS.items():
        print(f"Fetching {category} from {feed_url}...")
        parsed = feedparser.parse(feed_url)
        print(f"Found {len(parsed.entries)} entries in {category}")
        
        for entry in parsed.entries[:2]:
            link = entry.link
            title = entry.title
            
            existing = supabase.table("articles").select("id").eq("link", link).execute()
            
            if not existing.data:
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

    # 2. Automatically generate and post a betting slip with booking code
    post_betting_slip()

if __name__ == "__main__":
    main()
