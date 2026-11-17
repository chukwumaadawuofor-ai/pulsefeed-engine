import os
import requests
from supabase import create_client, Client

# Initialize Supabase credentials from environment secrets
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_and_broadcast_products():
    print("Checking Supabase for unbroadcasted marketplace products...")
    
    # Query unbroadcasted digital products from marketplace_products
    response = supabase.table("marketplace_products") \
        .select("*") \
        .eq("broadcasted", False) \
        .limit(1) \
        .execute()
    
    products = response.data
    
    if not products:
        print("No new products to broadcast.")
        return

    for prod in products:
        prod_id = prod["id"]
        title = prod["title"]
        seller_contact = prod.get("seller_contact", "https://t.me/")
        price = prod.get("price_value", "0.00")
        
        # Format a high-converting, impulse-buy message for Tier-1 buyers
        message = (
            f"🚀 **NEW DIGITAL ASSET & SOFTWARE DROP** 🚀\n\n"
            f"📦 **{title}**\n"
            f"💰 **Price:** ${price}\n\n"
            f"🔥 Instant digital delivery. Scale your workflow or business instantly.\n\n"
            f"👉 **Get Access Here:** {seller_contact}"
        )
        
        # Send via Telegram Bot API
        telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHANNEL_ID,
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": False
        }
        
        res = requests.post(telegram_url, json=payload)
        
        if res.status_code == 200:
            print(f"Successfully broadcasted product: {title}")
            # Mark as broadcasted so it doesn't repeat
            supabase.table("marketplace_products") \
                .update({"broadcasted": True}) \
                .eq("id", prod_id) \
                .execute()
        else:
            print(f"Failed to send Telegram message: {res.text}")

if __name__ == "__main__":
    fetch_and_broadcast_products()
