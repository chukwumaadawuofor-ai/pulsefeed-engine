import os
import requests
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Curated high-paying SaaS & AI software catalog with your real JVZoo affiliate link
CURATED_SAAS_OFFERS = [
    {
        "title": "EverPitch Bundle - AI Software Deal",
        "seller_contact": "https://www.jvzoo.com/c/3659489/459729",
        "price_value": 197.46,
        "image_url": "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=800"
    }
]

def fetch_and_store_recurring_saas():
    print("Populating high-paying recurring SaaS & marketing software into Supabase...")
    
    for offer in CURATED_SAAS_OFFERS:
        title = offer["title"]
        seller_contact = offer["seller_contact"]
        price_value = offer["price_value"]
        image_url = offer.get("image_url")

        # Check if this specific SaaS product already exists in Supabase
        existing = supabase.table("marketplace_products") \
            .select("id") \
            .eq("title", title) \
            .execute()
        
        if existing.data:
            print(f"SaaS offer already exists: {title}")
            continue

        # Insert new recurring software offer into Supabase with broadcasted = False
        new_product = {
            "title": title,
            "seller_contact": seller_contact,
            "price_value": price_value,
            "image_url": image_url,
            "broadcasted": False
        }
        
        supabase.table("marketplace_products").insert(new_product).execute()
        print(f"Successfully added recurring SaaS offer: {title}")

if __name__ == "__main__":
    fetch_and_store_recurring_saas()
