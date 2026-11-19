import os
import re
import time
from urllib.parse import urlparse, parse_qs, unquote, quote_plus
import requests
from bs4 import BeautifulSoup
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = (
    os.environ.get("TELEGRAM_ADMIN_CHAT_ID")
    or os.environ.get("TELEGRAM_CHAT_ID")
    or os.environ.get("TELEGRAM_CHANNEL_ID")
    or "6540485008"
)

# Configure target region ("US", "UK", "EUROPE", or "AUSTRALIA") and niche
TARGET_REGION = os.environ.get("TARGET_REGION", "US").upper().strip()
TARGET_NICHE = os.environ.get("TARGET_NICHE", "digital marketing agency").strip()

REGION_CONFIG = {
    "US": {"kl": "us-en", "query_suffix": "United States"},
    "UK": {"kl": "uk-en", "query_suffix": "United Kingdom London"},
    "EUROPE": {"kl": "ie-en", "query_suffix": "Europe Germany Netherlands Ireland"},
    "AUSTRALIA": {"kl": "au-en", "query_suffix": "Australia"},
}

FALLBACK_SEEDS = {
    "UK": [
        {"title": "Impression Digital", "url": "https://www.impression.co.uk"},
        {"title": "Fugu Digital", "url": "https://fugudigital.co.uk"},
        {"title": "Found", "url": "https://www.found.co.uk"},
    ],
    "US": [
        {"title": "Single Grain", "url": "https://www.singlegrain.com"},
        {"title": "KlientBoost", "url": "https://www.klientboost.com"},
        {"title": "Directive Consulting", "url": "https://directiveconsulting.com"},
    ],
    "EUROPE": [
        {"title": "Dept Agency", "url": "https://www.deptagency.com"},
        {"title": "Valtech", "url": "https://www.valtech.com"},
    ],
    "AUSTRALIA": [
        {"title": "Reload Media", "url": "https://www.reloadmedia.com.au"},
        {"title": "Sparro", "url": "https://www.sparro.com.au"},
    ],
}

SKIP_DOMAINS = (
    "linkedin.com", "facebook.com", "instagram.com", "x.com", "twitter.com",
    "youtube.com", "tiktok.com", "wikipedia.org", "yelp.com", "clutch.co",
    "upcity.com", "goodfirms.co", "trustpilot.com", "reddit.com", "medium.com",
    "duckduckgo.com", "bing.com", "microsoft.com", "msn.com", "google.com"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
}

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def _extract_real_url(href: str) -> str:
    if not href:
        return ""
    if "uddg=" in href:
        parsed = parse_qs(urlparse(href).query)
        real_url = unquote(parsed.get("uddg", [""])[0])
    else:
        real_url = href
    if real_url.startswith("//"):
        real_url = "https:" + real_url
    return real_url


def _add_candidate(results: list, title: str, raw_url: str, max_results: int) -> bool:
    real_url = _extract_real_url(raw_url)
    if not real_url.startswith(("http://", "https://")):
        return False

    parsed = urlparse(real_url)
    domain = parsed.netloc.lower()
    clean_domain = domain[4:] if domain.startswith("www.") else domain
    if not clean_domain or any(skip in clean_domain for skip in SKIP_DOMAINS):
        return False

    base_url = f"{parsed.scheme}://{domain}"
    if any(r["url"] == base_url for r in results):
        return False

    results.append({"title": title or clean_domain, "url": base_url})
    return len(results) >= max_results


def discover_websites(query: str, region: str, kl_code: str, max_results: int = 12):
    results = []

    # 1. Bing search
    try:
        bing_url = f"https://www.bing.com/search?q={quote_plus(query)}"
        resp = requests.get(bing_url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for li in soup.select("li.b_algo"):
            a = li.select_one("h2 a")
            if a and _add_candidate(results, a.get_text(strip=True), a.get("href", ""), max_results):
                return results
    except Exception as exc:
        print(f"Bing search note: {exc}")

    # 2. DuckDuckGo HTML
    if len(results) < max_results:
        try:
            ddg_url = "https://html.duckduckgo.com/html/"
            resp = requests.post(
                ddg_url,
                data={"q": query, "kl": kl_code},
                headers=HEADERS,
                timeout=15,
            )
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.select("a.result__a"):
                if _add_candidate(results, a.get_text(strip=True), a.get("href", ""), max_results):
                    return results
        except Exception as exc:
            print(f"DDG HTML note: {exc}")

    # 3. DuckDuckGo Lite
    if len(results) < max_results:
        try:
            lite_url = "https://lite.duckduckgo.com/lite/"
            resp = requests.post(
                lite_url,
                data={"q": query, "kl": kl_code},
                headers=HEADERS,
                timeout=15,
            )
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.select("a.result-link"):
                if _add_candidate(results, a.get_text(strip=True), a.get("href", ""), max_results):
                    return results
        except Exception as exc:
            print(f"DDG Lite note: {exc}")

    # 4. Region seed fallback when live search returns 0 candidates
    if not results:
        for seed in FALLBACK_SEEDS.get(region, FALLBACK_SEEDS["US"]):
            if _add_candidate(results, seed["title"], seed["url"], max_results):
                break

    return results


def _find_emails_in_html(html: str) -> list:
    emails = set(re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", html))
    clean = []
    for e in emails:
        low = e.lower()
        if low.endswith((".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".css", ".js")):
            continue
        if any(bad in low for bad in ("example.com", "sentry", "wixpress.com", "domain.com")):
            continue
        clean.append(e)
    return clean


def audit_public_site(url: str):
    start = time.time()
    resp = requests.get(url, headers=HEADERS, timeout=12, allow_redirects=True)
    resp.raise_for_status()
    load_time = round(time.time() - start, 2)
    html = resp.text
    lower_html = html.lower()
    soup = BeautifulSoup(html, "html.parser")

    clean_emails = _find_emails_in_html(html)

    if not clean_emails:
        for path in ("/contact", "/contact-us"):
            try:
                c_resp = requests.get(f"{url.rstrip('/')}{path}", headers=HEADERS, timeout=8, allow_redirects=True)
                if c_resp.status_code == 200:
                    found = _find_emails_in_html(c_resp.text)
                    if found:
                        clean_emails = found
                        break
            except Exception:
                pass

    contact_email = clean_emails[0] if clean_emails else ""

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
        "spotted_gap": " | ".join(gaps[:2]),
    }


def build_outreach_draft(region: str, site_url: str, gap: str):
    domain = urlparse(site_url).netloc
    return (
        f"Subject: Quick idea for {domain}\n\n"
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
        return False
    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(
            api_url,
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": text,
                "disable_web_page_preview": True,
            },
            timeout=15,
        )
        if not r.ok:
            print(f"Telegram API error ({r.status_code}): {r.text}")
            return False
        return True
    except Exception as exc:
        print(f"Telegram request failed: {exc}")
        return False


def run_scout():
    region = os.environ.get("TARGET_REGION") or TARGET_REGION
    region = region.upper().strip()
    niche = (os.environ.get("TARGET_NICHE") or TARGET_NICHE).strip()

    cfg = REGION_CONFIG.get(region, REGION_CONFIG["US"])
    search_query = f"{niche} {cfg['query_suffix']} contact email"
    print(f"Running Phase 1 Lead Scout | Region: {region} | Niche: {niche} | Chat: {TELEGRAM_CHAT_ID}")

    candidates = discover_websites(search_query, region, cfg["kl"], max_results=12)
    print(f"Candidate websites found: {len(candidates)}")
    new_leads_found = 0

    for item in candidates:
        url = item["url"]
        existing = supabase.table("prospect_leads").select("id").eq("business_url", url).execute()
        if existing.data:
            print(f"Skipping already recorded lead: {url}")
            continue

        try:
            audit = audit_public_site(url)
            draft = build_outreach_draft(region, url, audit["spotted_gap"])

            supabase.table("prospect_leads").insert({
                "region": region,
                "niche": niche,
                "business_url": url,
                "business_title": audit["page_title"],
                "contact_email": audit["contact_email"],
                "spotted_gap": audit["spotted_gap"],
                "outreach_draft": draft,
                "status": "new",
            }).execute()

            email_line = audit["contact_email"] if audit["contact_email"] else "Not found on site (check manually)"
            report_msg = (
                f"🎯 NEW {region} LEAD REPORT\n\n"
                f"🏢 Site: {url}\n"
                f"📧 Email: {email_line}\n"
                f"🔍 Gap Spotted: {audit['spotted_gap']}\n\n"
                f"--- READY-TO-SEND EMAIL (damiancuratedaideals@gmail.com) ---\n\n"
                f"{draft}"
            )
            sent = send_telegram_report(report_msg)
            new_leads_found += 1
            print(f"Saved new lead: {url} | Telegram sent: {sent}")
            time.sleep(2)
        except Exception as exc:
            print(f"Skipped {url} due to error: {exc}")

    print(f"Completed scan. New leads reported: {new_leads_found}")


if __name__ == "__main__":
    run_scout()
