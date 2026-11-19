import os
import re
import time
from urllib.parse import urlparse, parse_qs, unquote
import requests
from bs4 import BeautifulSoup
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHANNEL_ID")

# Configure target region ("US", "UK", "EUROPE", or "AUSTRALIA") and niche
TARGET_REGION = os.environ.get("TARGET_REGION", "US").upper()
TARGET_NICHE = os.environ.get("TARGET_NICHE", "digital marketing agency")

REGION_CONFIG = {
    "US": {"kl": "us-en", "query_suffix": "United States"},
    "UK": {"kl": "uk-en", "query_suffix": "United Kingdom OR London"},
    "EUROPE": {"kl": "ie-en", "query_suffix": "Europe OR Germany OR Netherlands OR Ireland"},
    "AUSTRALIA": {"kl": "au-en", "query_suffix": "Australia"}
}

SKIP_DOMAINS = (
    "linkedin.com", "facebook.com", "instagram.com", "x.com", "twitter.com",
    "youtube.com", "tiktok.com", "wikipedia.org", "yelp.com", "clutch.co",
    "upcity.com", "goodfirms.co", "trustpilot.com", "reddit.com", "medium.com"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
}

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def search_duckduckgo_html(query: str, kl_code: str, max_results: int = 12):
    url = "https://html.duckduckgo.com/html/"
    resp = requests.post(url, data={"q": query, "kl": kl_code}, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    results = []

    for a in soup.select("a.result__a"):
        href = a.get("href", "")
        if "uddg=" in href:
            parsed = parse_qs(urlparse(href).query)
            real_url = unquote(parsed.get("uddg", [""])[0])
        else:
            real_url = href

        if not real_url.startswith("http"):
            continue

        domain = urlparse(real_url).netloc.lower()
        if any(skip in domain for skip in SKIP_DOMAINS):
            continue

        base_url = f"{urlparse(real_url).scheme}://{domain}"
        title = a.get_text(strip=True)
        if base_url not in [r["url"] for r in results]:
            results.append({"title": title, "url": base_url})

        if len(results) >= max_results:
            break

    return results


def audit_public_site(url: str):
    start = time.time()
    resp = requests.get(url, headers=HEADERS, timeout=12)
    load_time = round(time.time() - start, 2)
    html = resp.text
    lower_html = html.lower()
    soup = BeautifulSoup(html, "html.parser")

    # Extract public email if visible on homepage
    emails = set(re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", html))
    clean_emails = [
        e for e in emails
        if not e.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".css", ".js"))
        and "example.com" not in e.lower()
        and "sentry" not in e.lower()
    ]
    contact_email = clean_emails[0] if clean_emails else ""

    # Detect clear public conversion / automation gaps
    gaps = []
    if not soup.find("meta", attrs={"name": "viewport"}):
        gaps.append("Missing mobile viewport optimization")
    if load_time > 3.0:
        gaps.append(f"Slow homepage response ({load_time}s)")
    if not any(k in lower_html for k in ["calendly", "book a call", "schedule a", "instant quote", "calculator"]):
        gaps.append("No instant self-serve quote/booking automation detected")
    if not any(k in lower_html for k in ["intercom", "tidio", "drift", "crisp", "live chat", "ai assistant"]):
        gaps.append("No automated 24/7 lead-capture assistant on homepage")

    if not gaps:
        gaps.append("Opportunity to add a custom AI client-intake or instant ROI tool")

    page_title = soup.title.string.strip() if soup.title and soup.title.string else url
    return {
        "page_title": page_title[:120],
        "contact_email": contact_email,
        "spotted_gap": " | ".join(gaps[:2])
    }


def build_outreach_draft(region: str, site_url: str, gap: str):
    return (
        f"Subject: Quick idea for {urlparse(site_url).netloc}\n\n"
        f"Hi there,\n\n"
        f"I was reviewing your website ({site_url}) and noticed a quick conversion opportunity: {gap}.\n\n"
        f"At Curated AI & SaaS Software Deals, we build lightweight custom AI web tools and automated lead-capture workflows "
        f"that solve this in days—with zero recurring monthly server fees.\n\n"
        f"You can view our live software showcase here: https://chukwumaadawuofor-ai.github.io/pulsefeed-engine/\n\n"
        f"Would you be open to me sending over a quick 1-page mockup tailored to your site?\n\n"
        f"Best regards,\n"
        f"Damian Adawuofor\n"
        f"Founder, Curated AI & SaaS Software Deals\n"
        f"Reply 'no thanks' anytime if this isn't a fit."
    )


def send_telegram_report(text: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram credentials missing; skipping notification.")
        return
    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(
        api_url,
        json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "disable_web_page_preview": True},
        timeout=15
    )


def run_scout():
    cfg = REGION_CONFIG.get(TARGET_REGION, REGION_CONFIG["US"])
    search_query = f'"{TARGET_NICHE}" "contact" {cfg["query_suffix"]}'
    print(f"Running Phase 1 Lead Scout | Region: {TARGET_REGION} | Niche: {TARGET_NICHE}")

    candidates = search_duckduckgo_html(search_query, cfg["kl"], max_results=10)
    new_leads_found = 0

    for item in candidates:
        url = item["url"]
        existing = supabase.table("prospect_leads").select("id").eq("business_url", url).execute()
        if existing.data:
            print(f"Skipping already recorded lead: {url}")
            continue

        try:
            audit = audit_public_site(url)
            draft = build_outreach_draft(TARGET_REGION, url, audit["spotted_gap"])

            supabase.table("prospect_leads").insert({
                "region": TARGET_REGION,
                "niche": TARGET_NICHE,
                "business_url": url,
                "business_title": audit["page_title"],
                "contact_email": audit["contact_email"],
                "spotted_gap": audit["spotted_gap"],
                "outreach_draft": draft,
                "status": "new"
            }).execute()

            email_line = audit["contact_email"] if audit["contact_email"] else "Not on homepage (check /contact)"
            report_msg = (
                f"🎯 NEW {TARGET_REGION} LEAD REPORT\n\n"
                f"🏢 Site: {url}\n"
                f"📧 Email: {email_line}\n"
                f"🔍 Gap Spotted: {audit['spotted_gap']}\n\n"
                f"--- READY-TO-SEND EMAIL (damiancuratedaideals@gmail.com) ---\n\n"
                f"{draft}"
            )
            send_telegram_report(report_msg)
            new_leads_found += 1
            print(f"Saved & reported new lead: {url}")
            time.sleep(2)
        except Exception as exc:
            print(f"Skipped {url} due to error: {exc}")

    print(f"Completed scan. New leads reported: {new_leads_found}")


if __name__ == "__main__":
    run_scout()
