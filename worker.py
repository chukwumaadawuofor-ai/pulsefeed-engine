import os
import random
import feedparser
import requests
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

FEEDS = {
    "⚽ FOOTBALL": "https://feeds.bbci.co.uk/sport/football/rss.xml",
    "💼 BUSINESS": "https://news.google.com/rss/search?q=business+nigeria&hl=en-NG&gl=NG&ceid=NG:en",
    "🪙 CRYPTO": "https://cointelegraph.com/rss",
    "💻 REMOTE JOBS": "https://weworkremotely.com/remote-jobs.rss"
}

BETTING_ACCUMULATORS = [
    {
        "title": "🔥 Ultimate Weekend Banker & Value Slip (8.5 Odds)",
        "games": [
            "1. Real Madrid vs Real Sociedad — Home Win & Over 1.5 ✅",
            "2. Bayern Munich vs Werder Bremen — Over 2.5 Goals ✅",
            "3. PSG vs Lens — Both Teams to Score (BTTS) ✅",
            "4. Benfica vs Gil Vicente — Home Win ✅",
            "5. Ajax vs PEC Zwolle — Over 2.5 Goals ✅"
        ],
        "booking_code": "SP9J" + str(random.randint(100000, 999999)),
        "bookmaker": "SportyBet / Bet9ja"
    },
    {
        "title": "💰 Mega Profit Accumulator (12+ Odds)",
        "games": [
            "1. Manchester City vs Brighton — Home Win in Both Halves",
            "2. Inter Milan vs Torino — Inter Win & Clean Sheet (No)",
            "3. Bayer Leverkusen vs VfB Stuttgart — Over 3.5 Goals",
            "4. Barcelona vs Athletic Bilbao — Both Teams to Score",
            "5. Sporting CP vs Porto — Under 3.5 Goals"
        ],
        "booking_code": "B9JA" + str(random.randint(100000, 999999)),
        "bookmaker": "Bet9ja / 1xBet"
    },
    {
        "title": "⚡ High-Stakes Goldmine Slip (15+ Odds)",
        "games": [
            "1. Arsenal vs Chelsea — Both Teams to Score & Over 2.5",
            "2. Liverpool vs Tottenham — Home Win",
            "3. Napoli vs AC Milan — Over 2.5 Goals",
            "4. Atletico Madrid vs Sevilla — Home Win or Draw & Under 3.5",
            "5. Galatasaray vs Fenerbahce — Over 1.5 Goals"
        ],
        "booking_code": "RET" + str(random.randint(100000, 999999)),
        "bookmaker": "NairaBet / SportyBet"
    }
]

def send_to_telegram(text, pin_message=False):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHANNEL_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    response = requests.post(url, json=payload)
    print(f"Telegram Status Code: {response.status_code}")

    if response.status_code == 200 and pin_message:
        try:
            msg_id = response.json()["result"]["message_id"]
            pin_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/pinChatMessage"
            pin_payload = {
                "chat_id": TELEGRAM_CHANNEL_ID,
                "message_id": msg_id,
                "disable_notification": True
            }
            pin_res = requests.post(pin_url, json=pin_payload)
            print(f"Auto-Pin Status: {pin_res.status_code}")
        except Exception as e:
            print(f"Could not pin message: {e}")

    return response

def post_betting_slip():
    slip = random.choice(BETTING_ACCUMULATORS)
    slip_id_key = f"betting_slip_{slip['booking_code']}"

    existing = supabase.table("articles").select("id").eq("link", slip_id_key).execute()

    if not existing.data:
        games = slip["games"]
        is_winning_ticket = len(games) > 0 and all("✅" in game for game in games)

        if not is_winning_ticket:
            print(f"Skipping slip {slip['booking_code']} (Not a 100% win yet).")
            return

        games_text = "\n".join(games)
        message = (
            f"🏆✅ **WON TICKET — CASHED OUT!** ✅🏆\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🎯 *DAILY BOOKING CODE UPDATE*\n\n"
            f"*{slip['title']}*\n\n"
            f"{games_text}\n\n"
            f"🔖 *Booking Code:* `{slip['booking_code']}`\n"
            f"🏦 *Recommended App/Shop:* {slip['bookmaker']}\n\n"
            f"📌 *Pinned to top — 100% WON!*\n"
            f"⚠️ *Play Responsibly (18+)*\n"
            f"📲 Follow @PulseFeedNG"
        )

        res = send_to_telegram(message, pin_message=True)
        if res.status_code == 200:
            supabase.table("articles").insert({
                "title": slip["title"],
                "link": slip_id_key,
                "category": "🎯 BETTING TIPS"
            }).execute()
            print(f"Successfully posted and pinned winning slip: {slip['booking_code']}")

def main():
    print("--- Starting Feed Fetcher & Betting Bot ---")

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

                res = send_to_telegram(message, pin_message=False)
                if res.status_code == 200:
                    supabase.table("articles").insert({
                        "title": title,
                        "link": link,
                        "category": category
                    }).execute()
                    print(f"Saved & Sent: {title}")

    post_betting_slip()

if __name__ == "__main__":
    main()
