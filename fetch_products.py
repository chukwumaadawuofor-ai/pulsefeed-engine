import os
import requests
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Curated high-paying recurring SaaS & marketing software catalog
# (Replace these target links with your actual PartnerStack, JVZoo, or direct affiliate tracking links)
CURATED_SAAS_OFFERS = [
    {
        "title": "AI Marketing & Funnel Pro - SaaS Software",
        "seller_contact": "https://partnerstack.com/your-affiliate-link-1",
        "price_value": 49.00
    },
    {
        "title": "Automated Email CRM & Sales Suite",
        "seller_contact": "https://partnerstack.com/your-affiliate-link-2",
        "price_value": 79.00
    },
    {
        "title": "Advanced AI Copywriting & SEO Ranker",
        "seller_contact": "https://jvzoo.com/your-affiliate-link-3",
        "price_value": 39.00
    },
    {
        "title": "Cloud Video & Webinar Automation SaaS",
        "seller_contact": "https://partnerstack.com/your-affiliate-link-4",
        "price_value": 99.00
    }
]

def fetch_and_store_recurring_saas():
    print("Populating high-paying recurring SaaS & marketing software into Supabase...")
    
    for offer in CURATED_SAAS_OFFERS:
        title = offer["title"]
        seller_contact = offer["seller_contact"]
        price_value = offer["price_value"]

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
            "broadcasted": False
        }
        
        supabase.table("marketplace_products").insert(new_product).execute()
        print(f"Successfully added recurring SaaS offer: {title}")

if __name__ == "__main__":
    fetch_and_store_recurring_saas()
