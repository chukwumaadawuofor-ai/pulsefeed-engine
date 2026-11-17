import os
import requests
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Catalog of 15 Top-Selling JVZoo Software Products across multiple profitable categories
CURATED_SAAS_OFFERS = [
    {
        "title": "EverPitch Bundle - AI Presentation & Pitch Software",
        "seller_contact": "https://www.jvzoo.com/c/3659489/459729",
        "price_value": 197.46,
        "image_url": "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=800",
        "category": "AI Software"
    },
    {
        "title": "Cinematic AI Video Studio Pro",
        "seller_contact": "https://www.jvzoo.com/c/3659489/459730",
        "price_value": 67.00,
        "image_url": "https://images.unsplash.com/photo-1574717024653-61fd2cf4d44d?w=800",
        "category": "Video Generation"
    },
    {
        "title": "Automated Social Media Video & Reel Generator",
        "seller_contact": "https://www.jvzoo.com/c/3659489/459731",
        "price_value": 47.00,
        "image_url": "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=800",
        "category": "Social Media"
    },
    {
        "title": "AI Marketing Funnel & Landing Page Builder",
        "seller_contact": "https://www.jvzoo.com/c/3659489/459732",
        "price_value": 97.00,
        "image_url": "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=800",
        "category": "Marketing SaaS"
    },
    {
        "title": "Advanced AI Copywriting & SEO Ranker Suite",
        "seller_contact": "https://www.jvzoo.com/c/3659489/459733",
        "price_value": 39.00,
        "image_url": "https://images.unsplash.com/photo-1542744094-24638eff58bb?w=800",
        "category": "Content & SEO"
    },
    {
        "title": "Cloud Webinar & Automated Sales Platform",
        "seller_contact": "https://www.jvzoo.com/c/3659489/459734",
        "price_value": 147.00,
        "image_url": "https://images.unsplash.com/photo-1531403009284-440f080d1e12?w=800",
        "category": "Webinars"
    },
    {
        "title": "AI Graphic Design & Brand Asset Studio",
        "seller_contact": "https://www.jvzoo.com/c/3659489/459735",
        "price_value": 57.00,
        "image_url": "https://images.unsplash.com/photo-1626544827763-d516dce335e2?w=800",
        "category": "Design Tools"
    },
    {
        "title": "Automated Email CRM & Autoresponder Suite",
        "seller_contact": "https://www.jvzoo.com/c/3659489/459736",
        "price_value": 79.00,
        "image_url": "https://images.unsplash.com/photo-1563986768609-322da13575f3?w=800",
        "category": "Email Marketing"
    },
    {
        "title": "AI Voiceover & Text-to-Speech Studio Pro",
        "seller_contact": "https://www.jvzoo.com/c/3659489/459737",
        "price_value": 49.00,
        "image_url": "https://images.unsplash.com/photo-1590602847861-f357a9332bbc?w=800",
        "category": "Audio & Voice"
    },
    {
        "title": "E-Commerce Store Builder & Dropship Automation",
        "seller_contact": "https://www.jvzoo.com/c/3659489/459738",
        "price_value": 99.00,
        "image_url": "https://images.unsplash.com/photo-1556742049-0a67d553c2a5?w=800",
        "category": "E-Commerce"
    },
    {
        "title": "Crypto & Forex Chart Analysis AI Bot",
        "seller_contact": "https://www.jvzoo.com/c/3659489/459739",
        "price_value": 199.00,
        "image_url": "https://images.unsplash.com/photo-1642543492481-44e81e3914a7?w=800",
        "category": "Trading Tools"
    },
    {
        "title": "AI Chatbot & Customer Support Suite",
        "seller_contact": "https://www.jvzoo.com/c/3659489/459740",
        "price_value": 89.00,
        "image_url": "https://images.unsplash.com/photo-1531746790731-6c087fecd65a?w=800",
        "category": "Customer Support"
    },
    {
        "title": "Agency Client Finder & Lead Generation SaaS",
        "seller_contact": "https://www.jvzoo.com/c/3659489/459741",
        "price_value": 127.00,
        "image_url": "https://images.unsplash.com/photo-1557804506-669a67965ba0?w=800",
        "category": "Agency Tools"
    },
    {
        "title": "High-Speed Website Hosting & CDN Accelerator",
        "seller_contact": "https://www.jvzoo.com/c/3659489/459742",
        "price_value": 69.00,
        "image_url": "https://images.unsplash.com/photo-1544197150-b99a580bb7a8?w=800",
        "category": "Hosting & Infra"
    },
    {
        "title": "Social Media Traffic Bot & Scheduler Pro",
        "seller_contact": "https://www.jvzoo.com/c/3659489/459743",
        "price_value": 59.00,
        "image_url": "https://images.unsplash.com/photo-1611162617474-5b21e879e113?w=800",
        "category": "Social Media"
    }
]

def fetch_and_store_recurring_saas():
    print("Populating 15-product multi-category catalog into Supabase...")
    
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
