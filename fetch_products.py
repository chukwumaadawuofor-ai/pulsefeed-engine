import os
import requests
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Expanded catalog with multiple software categories (AI Software, Video Tools, Marketing SaaS)
CURATED_SAAS_OFFERS = [
    {
        "title": "EverPitch Bundle - AI Software Deal",
        "seller_contact": "https://www.jvzoo.com/c/3659489/459729",
        "price_value": 197.46,
        "image_url": "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=800",
        "category": "AI Software"
    },
    {
        "title": "Cinematic AI Video Studio Pro",
        "seller_contact": "https://www.jvzoo.com/c/3659489/YOUR_NEW_PRODUCT_ID",
        "price_value": 67.00,
        "image_url": "https://images.unsplash.com/photo-1574717024653-61fd2cf4d44d?w=800",
        "category": "Video Generation"
    }
]

def fetch_and_store_recurring_saas():
    print("Populating multi-category SaaS catalog into Supabase...")
    
    for offer in CURATED_SAAS_OFFERS:
        title = offer["title"]
        seller_contact = offer["seller_contact"]
        price_value = offer["price_value"]
        image_url = offer.get("image_url")

        # Check if this product already exists in Supabase
        existing = supabase.table("marketplace_products") \
            .select("id") \
            .eq("title", title) \
            .execute()
        
        if existing.data:
            print(f"Offer already exists in queue: {title}")
            continue

        # Insert new offer into Supabase with broadcasted = False
        new_product = {
            "title": title,
            "seller_contact": seller_contact,
            "price_value": price_value,
            "image_url": image_url,
            "broadcasted": False
        }
        
        supabase.table("marketplace_products").insert(new_product).execute()
        print(f"Successfully added to queue: {title}")

if __name__ == "__main__":
    fetch_and_store_recurring_saas()
