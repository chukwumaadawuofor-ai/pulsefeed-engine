import os
import re
import xml.etree.ElementTree as ET
import requests


def _clean_url(raw: str) -> str:
    val = (raw or "").strip().strip('"').strip("'").rstrip("/")
    if "/rest/v1" in val:
        val = val.split("/rest/v1", 1)[0].rstrip("/")
    if val and not val.startswith("http"):
        val = f"https://{val}"
    return val


SUPABASE_URL = _clean_url(os.environ["SUPABASE_URL"])
SUPABASE_KEY = os.environ["SUPABASE_KEY"].strip()
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"].strip()
CHAT_ID = os.environ["TELEGRAM_ADMIN_CHAT_ID"].strip()
STOREFRONT_URL = "https://chukwumaadawuofor-ai.github.io/pulsefeed-engine/"

# Public remote job feeds (no API keys required)
FEEDS = [
    ("WeWorkRemotely-Programming", "https://weworkremotely.com/categories/remote-programming-jobs.rss"),
    ("WeWorkRemotely-DevOpsSysAdmin", "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss"),
    ("RemoteOK-API", "https://remoteok.com/api"),
]

# High-fit keywords mapped to your fast-execution templates
KEYWORDS = {
    "lead capture": "Lead-Capture & AI Intake",
    "intake": "Lead-Capture & AI Intake",
    "chatbot": "Lead-Capture & AI Intake",
    "ai agent": "Lead-Capture & AI Intake",
    "scraper": "Automated Web Monitor & Scraper",
    "scraping": "Automated Web Monitor & Scraper",
    "web scraping": "Automated Web Monitor & Scraper",
    "automation": "Workflow & API Automation",
    "webhook": "Workflow & API Automation",
    "telegram": "Telegram / Operations Bot",
    "bot": "Telegram / Operations Bot",
    "python": "Python Backend / Script",
    "etl": "Automated Data Pipeline",
}

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PulseFeedJobScout/1.0)"}


def clean_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text or "").strip()


def fetch_existing_urls() -> set:
    url = f"{SUPABASE_URL}/rest/v1/job_leads?select=job_url&limit=1000"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    r = requests.get(url, headers=headers, timeout=20)
    if not r.ok:
        print("Supabase GET error:", r.status_code, r.text)
    r.raise_for_status()
    return {row["job_url"] for row in r.json()}


def build_proposal(title: str, category: str) -> str:
    if "Scraper" in category or "Pipeline" in category:
        return (
            f"Hi — I can build a clean, automated Python monitoring/extraction pipeline for '{title}' "
            f"with scheduled runs, deduplicated database storage, and instant Telegram/email alerts—"
            f"designed with zero recurring monthly server bloat.\n\n"
            f"Live examples & flat-rate packages ($450 / $950 / $1,850+): {STOREFRONT_URL}"
        )
    return (
        f"Hi — I build fast, lightweight AI intake, lead-routing, and workflow automation systems "
        f"that capture inquiries, qualify intent, and trigger instant alerts without bloated monthly software fees.\n\n"
        f"Live interactive preview & flat-rate packages ($450 / $950 / $1,850+): {STOREFRONT_URL}"
    )


def score_item(title: str, summary: str):
    haystack = f"{title} {summary}".lower()
    matched = [kw for kw in KEYWORDS if kw in haystack]
    if not matched:
        return None
    primary_category = KEYWORDS[matched[0]]
    return matched, primary_category


def parse_rss(source_name: str, feed_url: str) -> list:
    items = []
    r = requests.get(feed_url, headers=HEADERS, timeout=25)
    r.raise_for_status()
    root = ET.fromstring(r.text)
    for item in root.findall(".//item")[:40]:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        desc = clean_html(item.findtext("description") or "")
        if title and link:
            items.append({"source": source_name, "title": title, "url": link, "summary": desc})
    return items


def parse_remoteok(source_name: str, feed_url: str) -> list:
    items = []
    r = requests.get(feed_url, headers=HEADERS, timeout=25)
    r.raise_for_status()
    data = r.json()
    for entry in data[1:50]:
        title = (entry.get("position") or "").strip()
        company = (entry.get("company") or "").strip()
        link = (entry.get("url") or "").strip()
        tags = " ".join(entry.get("tags") or [])
        desc = clean_html(entry.get("description") or "")
        if title and link:
            full_title = f"{title} — {company}" if company else title
            items.append({"source": source_name, "title": full_title, "url": link, "summary": f"{tags} {desc}"})
    return items


def save_lead(row: dict):
    url = f"{SUPABASE_URL}/rest/v1/job_leads?on_conflict=job_url"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=ignore-duplicates,return=representation",
    }
    r = requests.post(url, headers=headers, json=[row], timeout=20)
    r.raise_for_status()
    return r.json()


def notify_telegram(row: dict):
    msg = (
        f"💼 *New High-Fit Remote Gig*\n"
        f"*Role:* {row['title']}\n"
        f"*Track:* {row['category']}\n"
        f"*Source:* {row['source']}\n"
        f"*Keywords:* `{row['matched_keywords']}`\n"
        f"*Apply:* {row['job_url']}\n\n"
        f"📋 *Ready-to-Send Pitch:*\n`{row['proposal_draft']}`"
    )
    tg_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(
        tg_url,
        json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown", "disable_web_page_preview": True},
        timeout=20,
    ).raise_for_status()


def main():
    existing = fetch_existing_urls()
    candidates = []
    for source_name, feed_url in FEEDS:
        try:
            if "remoteok.com" in feed_url:
                candidates.extend(parse_remoteok(source_name, feed_url))
            else:
                candidates.extend(parse_rss(source_name, feed_url))
        except Exception as exc:
            print(f"[WARN] Failed {source_name}: {exc}")

    new_count = 0
    for item in candidates:
        if item["url"] in existing:
            continue
        scored = score_item(item["title"], item["summary"])
        if not scored:
            continue
        matched, category = scored
        row = {
            "job_url": item["url"],
            "title": item["title"],
            "source": item["source"],
            "category": category,
            "matched_keywords": ", ".join(matched[:5]),
            "budget_hint": "Remote / Contract",
            "proposal_draft": build_proposal(item["title"], category),
            "status": "new",
        }
        saved = save_lead(row)
        if saved:
            existing.add(item["url"])
            notify_telegram(row)
            new_count += 1
            if new_count >= 5:
                break

    print(f"Job Scout completed. New matches sent: {new_count}")


if __name__ == "__main__":
    main()
