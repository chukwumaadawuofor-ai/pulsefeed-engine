import os
import requests
from supabase import create_client

# Initialize Supabase connection using your existing GitHub secrets
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID")

# High-velocity impulse keywords for US & EU digital products / software
HIGH_VELOCITY_KEYWORDS = [
    "ai", "template", "bundle", "tracker", "automation", 
    "toolkit", "ebook", "creator", "software", "preset", "masterclass"
]

def run_marketplace_worker():
    """
    Fetches unbroadcasted products from Supabase, checks velocity, 
    and syndicates them to your Telegram channel and social feeds automatically.
    """
    try:
        # Fetch pending products from Supabase
        response = supabase.table("marketplace_products").select("*").eq("broadcasted", False).limit(5).execute()
        
        if not response.data:
            print("No new products in queue to broadcast.")
            return

        for product in response.data:
            title = product.get("title", "")
            title_lower = title.lower()
            price = float(product.get("price_value", 27.00))
            link = product.get("seller_contact", "")

            # Velocity Filter: Must be impulse-priced (<$60) and match high-demand keywords
            is_impulse = price <= 60.0
            has_winning_keyword = any(kw in title_lower for kw in HIGH_VELOCITY_KEYWORDS)

            if is_impulse and has_winning_keyword:
                message = (
                    f"🔥 **TOP US/EU DIGITAL DEAL** 🔥\n\n"
                    f"📌 **{title}**\n"
                    f"💵 **Price:** ${price:.2f} (Instant Digital Delivery)\n\n"
                    f"⚡ *Secure yours now:*\n"
                    f"👉 {link}\n\n"
                    f"#DigitalProducts #AITools #USDeals #PassiveIncome"
                )

                # Broadcast to your Telegram channel
                res = requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                    json={"chat_id": TELEGRAM_CHANNEL_ID, "text": message, "parse_mode": "Markdown"}
                )
                
                if res.status_code == 200:
                    # Mark as broadcasted so it doesn't duplicate
                    supabase.table("marketplace_products").update({"broadcasted": True}).eq("id", product['id']).execute()
                    print(f"Successfully syndicated: {title}")
                else:
                    print(f"Telegram broadcast failed: {res.text}")

    except Exception as e:
        print(f"Worker execution error: {e}")

if __name__ == "__main__":
    run_marketplace_worker()
