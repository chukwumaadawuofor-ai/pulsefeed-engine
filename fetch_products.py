import os
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Curated Tier-1 Software & AI Deals with your affiliate tracking
CURATED_SAAS_OFFERS = [
    {
        "title": "EverPitch Bundle — AI Pitch Deck & Sales Presentation Suite",
        "price_value": 47.00,
        "seller_contact": "https://www.jvzoo.com/c/3659489/459729",
        "image_url": "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=800"
    },
    {
        "title": "Social Media Traffic Bot & Scheduler Pro",
        "price_value": 59.00,
        "seller_contact": "https://www.jvzoo.com/c/3659489/459731",
        "image_url": "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=800"
    },
    {
        "title": "AI Voice & Video Automation Studio",
        "price_value": 67.00,
        "seller_contact": "https://www.jvzoo.com/c/3659489/459732",
        "image_url": "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=800"
    },
    {
        "title": "Omnichannel Lead Gen & Email Marketing Suite",
        "price_value": 97.00,
        "seller_contact": "https://www.jvzoo.com/c/3659489/459733",
        "image_url": "https://images.unsplash.com/photo-1533750349077-cdcd1ec5675f?w=800"
    }
]

def populate_products():
    for offer in CURATED_SAAS_OFFERS:
        existing = supabase.table("marketplace_products") \
            .select("id") \
            .eq("seller_contact", offer["seller_contact"]) \
            .execute()

        if existing.data:
            print(f"Offer already exists in queue: {offer['title']}")
        else:
            supabase.table("marketplace_products").insert({
                "title": offer["title"],
                "price_value": offer["price_value"],
                "seller_contact": offer["seller_contact"],
                "image_url": offer["image_url"],
                "broadcasted": False
            }).execute()
            print(f"Added new verified offer: {offer['title']}")

if __name__ == "__main__":
    populate_products()
