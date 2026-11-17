import os
import requests
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def broadcast_pending_products():
    # Fetch unbroadcasted products from Supabase
    response = supabase.table("marketplace_products") \
        .select("*") \
        .eq("broadcasted", False) \
        .limit(1) \
        .execute()
    
    if not response.data:
        print("No pending products to broadcast.")
        return

    product = response.data[0]
    prod_id = product["id"]
    title = product["title"]
    price = product["price_value"]
    link = product["seller_contact"]
    image_url = product.get("image_url")

    # Format the high-converting Telegram caption
    caption = (
        f"🚀 **NEW DIGITAL ASSET & SOFTWARE DROP** 🚀\n\n"
        f"📦 **{title}**\n"
        f"💰 **Price:** ${price:.2f} (Instant Digital Delivery)\n\n"
        f"🔥 Instant digital delivery. Scale your workflow or business instantly.\n\n"
        f"👉 **Get Access Here:** {link}\n\n"
        f"#DigitalProducts #AITools #USDeals #PassiveIncome"
    )

    # Send with Photo if image_url exists, otherwise fallback to text
    if image_url:
        telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        payload = {
            "chat_id": TELEGRAM_CHANNEL_ID,
            "photo": image_url,
            "caption": caption,
            "parse_mode": "Markdown"
        }
    else:
        telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHANNEL_ID,
            "text": caption,
            "parse_mode": "Markdown",
            "disable_web_page_preview": False
        }

    res = requests.post(telegram_url, json=payload)
    
    if res.status_code == 200:
        # Mark product as broadcasted so it doesn't repeat
        supabase.table("marketplace_products") \
            .update({"broadcasted": True}) \
            .eq("id", prod_id) \
            .execute()
        print(f"Successfully broadcasted product with image: {title}")
    else:
        print(f"Failed to broadcast: {res.text}")

if __name__ == "__main__":
    broadcast_pending_products()
