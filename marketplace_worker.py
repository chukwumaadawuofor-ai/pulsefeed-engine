import os
import requests
from datetime import datetime, timezone, timedelta
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

FALLBACK_IMAGE = "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=800"

def get_next_product():
    # 1. Look for products that have NEVER been broadcasted
    unbroadcasted = supabase.table("marketplace_products") \
        .select("*") \
        .eq("broadcasted", False) \
        .limit(1) \
        .execute()

    if unbroadcasted.data:
        return unbroadcasted.data[0]

    # 2. If all products have been posted once, recycle the oldest one ONLY if > 7 days old
    seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    recyclable = supabase.table("marketplace_products") \
        .select("*") \
        .lt("last_broadcasted", seven_days_ago) \
        .order("last_broadcasted", desc=False) \
        .limit(1) \
        .execute()

    if recyclable.data:
        return recyclable.data[0]

    return None

def send_telegram_drop(product):
    title = product.get("title", "Premium AI & SaaS Tool")
    price = float(product.get("price_value", 0))
    link = product.get("seller_contact", "")
    image_url = product.get("image_url") or FALLBACK_IMAGE

    caption = (
        f"🚀 <b>NEW DIGITAL ASSET & SOFTWARE DROP</b> 🚀\n\n"
        f"📦 <b>{title}</b>\n"
        f"💰 <b>Price:</b> ${price:,.2f} (Instant Digital Delivery)\n\n"
        f"🔥 Instant digital delivery. Scale your workflow or business instantly.\n\n"
        f"👉 <b>Get Access Here:</b> {link}\n\n"
        f"#DigitalProducts #AITools #USDeals #SaaS"
    )

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    payload = {
        "chat_id": TELEGRAM_CHANNEL_ID,
        "photo": image_url,
        "caption": caption,
        "parse_mode": "HTML"
    }

    response = requests.post(url, json=payload, timeout=20)

    # Fallback if image URL fails to load on Telegram servers
    if not response.ok:
        payload["photo"] = FALLBACK_IMAGE
        response = requests.post(url, json=payload, timeout=20)

    response.raise_for_status()
    return response.json()

def run():
    product = get_next_product()
    if not product:
        print("No eligible products due for broadcast right now (all active items posted within 7 days). Skipping.")
        return

    product_id = product["id"]
    print(f"Broadcasting: {product['title']} (ID: {product_id})")

    # Mark as broadcasted BEFORE/WITH strict verification
    now_iso = datetime.now(timezone.utc).isoformat()
    update_res = supabase.table("marketplace_products") \
        .update({
            "broadcasted": True,
            "last_broadcasted": now_iso
        }) \
        .eq("id", product_id) \
        .execute()

    if not update_res.data:
        raise RuntimeError(f"CRITICAL: Failed to update broadcast status in Supabase for ID {product_id}. Aborting send to prevent duplicates.")

    send_telegram_drop(product)
    print("Broadcast sent and locked in Supabase successfully.")

if __name__ == "__main__":
    run()
