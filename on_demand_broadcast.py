import os
import requests
from datetime import datetime, timezone
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "").strip()
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "").strip()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

FALLBACK_IMAGE = "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=800"


def force_broadcast_next():
    print("Checking for pending products to broadcast on demand...")

    response = supabase.table("marketplace_products") \
        .select("*") \
        .eq("broadcasted", False) \
        .limit(1) \
        .execute()

    if not response.data:
        print("No pending products found in queue to broadcast.")
        return

    product = response.data[0]
    prod_id = product["id"]
    title = str(product.get("title") or "Premium AI & SaaS Tool").strip()
    price = float(product.get("price_value") or 0)
    link = str(product.get("seller_contact") or "").strip()
    image_url = str(product.get("image_url") or "").strip()

    caption = (
        f"🚀 <b>ON-DEMAND DIGITAL DROP</b> 🚀\n\n"
        f"📦 <b>{title}</b>\n"
        f"💰 <b>Price:</b> ${price:,.2f} (Instant Digital Delivery)\n\n"
        f"🔥 Instant digital delivery. Scale your workflow or business instantly.\n\n"
        f"👉 <b>Get Access Here:</b> {link}\n\n"
        f"#DigitalProducts #AITools #USDeals #PassiveIncome"
    )

    photo_target = image_url if image_url.startswith("https://") else FALLBACK_IMAGE
    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    payload = {
        "chat_id": TELEGRAM_CHANNEL_ID,
        "photo": photo_target,
        "caption": caption,
        "parse_mode": "HTML",
    }

    res = requests.post(telegram_url, json=payload, timeout=20)
    if not res.ok and photo_target != FALLBACK_IMAGE:
        payload["photo"] = FALLBACK_IMAGE
        res = requests.post(telegram_url, json=payload, timeout=20)

    if res.ok:
        current_time = datetime.now(timezone.utc).isoformat()
        supabase.table("marketplace_products") \
            .update({
                "broadcasted": True,
                "last_broadcasted": current_time,
            }) \
            .eq("id", prod_id) \
            .execute()
        print(f"Successfully force-broadcasted product: {title}")
    else:
        print(f"Failed to broadcast ({res.status_code}): {res.text}")


if __name__ == "__main__":
    force_broadcast_next()
