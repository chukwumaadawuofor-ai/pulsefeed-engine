import os
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 100% Verified & Approved JVZoo Affiliate Offers (ID: 3659489)
CURATED_SAAS_OFFERS = [
    {
        "title": "EverPitch Bundle — AI Pitch Deck & Sales Presentation Suite",
        "price_value": 197.00,
        "seller_contact": "https://www.jvzoo.com/c/3659489/459729",
        "image_url": "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=800"
    },
    {
        "title": "EverPitch Commercial — AI Business Presentation Creator",
        "price_value": 47.00,
        "seller_contact": "https://www.jvzoo.com/c/3659489/461141",
        "image_url": "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=800"
    },
    {
        "title": "EverPitch Mega Bundle Gold — Enterprise AI Presentation & Agency Kit",
        "price_value": 297.00,
        "seller_contact": "https://www.jvzoo.com/c/3659489/462283",
        "image_url": "https://images.unsplash.com/photo-1504868584819-f8e8b4b6d7e3?w=800"
    },
    {
        "title": "Click Action AI Premium Bundle — All-in-One AI Automation Suite",
        "price_value": 97.00,
        "seller_contact": "https://www.jvzoo.com/c/3659489/458332",
        "image_url": "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=800"
    },
    {
        "title": "ReferralNow Bundle — Automated Viral Referral & Growth Engine",
        "price_value": 147.00,
        "seller_contact": "https://www.jvzoo.com/c/3659489/461379",
        "image_url": "https://images.unsplash.com/photo-1551434678-e076c223a692?w=800"
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
