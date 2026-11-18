import os
import html
import requests
from datetime import datetime, timezone, timedelta
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def broadcast_next_product():
    seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

    # 1. Look for any unbroadcasted product first
    response = supabase.table("marketplace_products") \
        .select("*") \
        .eq("broadcasted", False) \
        .limit(1) \
        .execute()

    products = response.data

    # 2. If all products have been posted, recycle only offers older than 7 days
    if not products:
        recycle_response = supabase.table("marketplace_products") \
            .select("*") \
            .lt("last_broadcasted_at", seven_days_ago) \
            .order("last_broadcasted_at", desc=False) \
            .limit(1) \
            .execute()
        products = recycle_response.data

    if not products:
        print("All active offers have been broadcasted within the last 7 days. Skipping.")
        return

    product = products[0]
    product_id = product["id"]
    title = html.escape(str(product.get("title", "AI & SaaS Software Deal")))
    price = float(product.get("price_value", 0))
    link = str(product.get("seller_contact", "")).strip()
    image_url = str(product.get("image_url") or "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=800").strip()

    caption = (
        f"🚀 <b>NEW DIGITAL ASSET &amp; SOFTWARE DROP</b> 🚀\n\n"
        f"📦 <b>{title}</b>\n"
        f"💰 <b>Price: ${price:.2f} (Instant Digital Delivery)</b>\n\n"
        f"🔥 Instant digital delivery. Scale your workflow or business instantly.\n\n"
        f"👉 <b>Get Access Here:</b> {link}\n\n"
        f"#DigitalProducts #AITools #USDeals #PassiveIncome"
    )

    tg_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    payload = {
        "chat_id": TELEGRAM_CHANNEL_ID,
        "photo": image_url,
        "caption": caption,
        "parse_mode": "HTML"
    }

    res = requests.post(tg_url, json=payload, timeout=20)
    if res.status_code != 200:
        raise RuntimeError(f"Telegram API error ({res.status_code}): {res.text}")

    # Mark as broadcasted immediately so it never repeats on the next run
    now_iso = datetime.now(timezone.utc).isoformat()
    supabase.table("marketplace_products") \
        .update({"broadcasted": True, "last_broadcasted_at": now_iso}) \
        .eq("id", product_id) \
        .execute()

    print(f"Successfully broadcasted and locked product ID {product_id}: {title}")

if __name__ == "__main__":
    broadcast_next_product()
