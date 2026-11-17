import os
import requests
from datetime import datetime, timezone, timedelta
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def recycle_old_products():
    """Automatically resets products broadcasted over 7 days ago back into the queue."""
    seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    
    # Find products broadcasted more than 7 days ago
    expired_products = supabase.table("marketplace_products") \
        .select("id") \
        .eq("broadcasted", True) \
        .lt("last_broadcasted_at", seven_days_ago) \
        .execute()
    
    if expired_products.data:
        for item in expired_products.data:
            supabase.table("marketplace_products") \
                .update({"broadcasted": False}) \
                .eq("id", item["id"]) \
                .execute()
        print(f"Recycled {len(expired_products.data)} expired products back into rotation.")

def broadcast_pending_products():
    # First, check and recycle any products older than 7 days
    recycle_old_products()

    # Fetch the next unbroadcasted product from Supabase
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
        # Mark product as broadcasted and record the exact timestamp
        current_time = datetime.now(timezone.utc).isoformat()
        supabase.table("marketplace_products") \
            .update({
                "broadcasted": True,
                "last_broadcasted_at": current_time
            }) \
            .eq("id", prod_id) \
            .execute()
        print(f"Successfully broadcasted and timestamped product: {title}")
    else:
        print(f"Failed to broadcast: {res.text}")

if __name__ == "__main__":
    broadcast_pending_products()
