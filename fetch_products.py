import os
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Add only real, verified affiliate links from JVZoo (Approved Products) or Selar below
CURATED_SAAS_OFFERS = [
    {
        "title": "EverPitch Bundle — AI Pitch Deck & Sales Presentation Suite",
        "price_value": 47.00,
        "seller_contact": "https://www.jvzoo.com/c/3659489/459729",
        "image_url": "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=800"
    }
]

def populate_products():
    for offer in CURATED_SAAS_OFFERS:
        # Check if this exact affiliate link is already in the database
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
