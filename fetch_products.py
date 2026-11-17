import os
import requests
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_and_store_trending_software():
    print("Fetching trending software products for the marketplace...")
    
    # Example using a public developer/tech dataset or API endpoint
    # You can plug in Product Hunt API, RapidAPI, or an RSS tech feed parser here.
    api_url = "https://api.github.com/search/repositories?q=topic:ai-tools+sort:stars&per_page=5"
    headers = {"Accept": "application/vnd.github.v3+json"}
    
    response = requests.get(api_url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to fetch data: {response.text}")
        return

    items = response.json().get("items", [])
    
    for item in items:
        title = f"{item['name'].replace('-', ' ').title()} - AI Toolkit"
        repo_url = item['html_url']
        description = item.get('description', 'High-velocity digital software tool.')
        
        # Construct your affiliate or direct product landing page link
        # (You can map this dynamically to your PartnerStack/JVZoo affiliate links)
        seller_contact = repo_url 
        price_value = 29.00  # Standard impulse-buy digital tier pricing

        # Check if product already exists in Supabase to avoid duplicates
        existing = supabase.table("marketplace_products") \
            .select("id") \
            .eq("title", title) \
            .execute()
        
        if existing.data:
            print(f"Product already exists: {title}")
            continue

        # Insert new product into Supabase with broadcasted = False
        new_product = {
            "title": title,
            "seller_contact": seller_contact,
            "price_value": price_value,
            "broadcasted": False
        }
        
        insert_res = supabase.table("marketplace_products").insert(new_product).execute()
        print(f"Successfully added new product to Supabase: {title}")

if __name__ == "__main__":
    fetch_and_store_trending_software()
