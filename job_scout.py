import os
import re
from itertools import zip_longest
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

FEEDS = [
    ("Remotive", "https://remotive.com/api/remote-jobs?category=software-dev&limit=40"),
    ("RemoteOK", "https://remoteok.com/api"),
    ("Jobicy", "https://jobicy.com/api/v2/remote-jobs?count=40&industry=dev"),
    ("WWR-Programming", "https://weworkremotely.com/categories/remote-programming-jobs.rss"),
    ("WWR-DevOps", "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss"),
]

KEYWORDS = {
    "lead capture": "Lead-Capture & AI Intake",
    "ai intake": "Lead-Capture & AI Intake",
    "intake": "Lead-Capture & AI Intake",
    "chatbot": "Lead-Capture & AI Intake",
    "ai agent": "Lead-Capture & AI Intake",
    "web scraping": "Automated Web Monitor & Scraper",
    "scraping": "Automated Web Monitor & Scraper",
    "scraper": "Automated Web Monitor & Scraper",
    "webhook": "Workflow & API Automation",
    "webhooks": "Workflow & API Automation",
    "workflow automation": "Workflow & API Automation",
    "automation": "Workflow & API Automation",
    "telegram": "Telegram / Operations Bot",
    "discord bot": "Telegram / Operations Bot",
    "bot": "Telegram / Operations Bot",
    "etl": "Automated Data Pipeline",
    "data pipeline": "Automated Data Pipeline",
    "python": "Python Backend / Script",
}

CONTRACT_TERMS = [
    "contract",
    "contractor",
    "freelance",
    "consultant",
    "consulting",
    "part-time",
    "part time",
    "project-based",
    "b2b",
    "independent",
]

NOISE_TERMS = [
    "mechanical",
    "reliability",
    "machinist",
    "hvac",
    "warehouse",
    "truck driver",
    "delivery driver",
    "nurse",
    "dental",
    "recruiter",
    "account executive",
    "inside sales",
    "broker dealer",
]

STRONG_TECH_TERMS = [
    "python",
    "scraper",
    "scraping",
    "webhook",
    "webhooks",
    "automation",
    "chatbot",
    "ai agent",
    "lead capture",
    "etl",
    "data pipeline",
    "telegram",
]

KEYWORD_PATTERNS = {
    kw: re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE)
    for kw in KEYWORDS
}

CONTRACT_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(t) for t in CONTRACT_TERMS) + r")\b",
    re.IGNORECASE,
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, application/xml, text/xml, */*",
}


def clean_html(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text or "")).strip()


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

    if any(re.search(r"\b" + re.escape(term) + r"\b", haystack) for term in NOISE_TERMS):
        if not any(re.search(r"\b" + re.escape(tech) + r"\b", haystack) for tech in STRONG_TECH_TERMS):
            return None

    matched = [kw for kw, pat in KEYWORD_PATTERNS.items() if pat.search(haystack)]
    if not matched:
        return None

    is_contract = bool(CONTRACT_PATTERN.search(haystack))
    primary_category = KEYWORDS[matched[0]]
    return matched, primary_category, is_contract


def parse_rss(source_name: str, feed_url: str) -> list:
    items = []
    r = requests.get(feed_url, headers=HEADERS, timeout=25)
    r.raise_for_status()
    root = ET.fromstring(r.text)
    for item in root.findall(".//item")[:35]:
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
    for entry in data[1:45]:
        title = (entry.get("position") or "").strip()
        company = (entry.get("company") or "").strip()
        link = (entry.get("url") or "").strip()
        tags = " ".join(entry.get("tags") or [])
        desc = clean_html(entry.get("description") or "")
        if title and link:
            full_title = f"{title} — {company}" if company else title
            items.append({"source": source_name, "title": full_title, "url": link, "summary": f"{tags} {desc}"})
    return items


def parse_remotive(source_name: str, feed_url: str) -> list:
    items = []
    r = requests.get(feed_url, headers=HEADERS, timeout=25)
    r.raise_for_status()
    for entry in r.json().get("jobs", [])[:40]:
        title = (entry.get("title") or "").strip()
        company = (entry.get("company_name") or "").strip()
        link = (entry.get("url") or "").strip()
        job_type = (entry.get("job_type") or "").strip()
        desc = clean_html(entry.get("description") or "")
        if title and link:
            full_title = f"{title} — {company}" if company else title
            items.append({"source": source_name, "title": full_title, "url": link, "summary": f"{job_type} {desc}"})
    return items


def parse_jobicy(source_name: str, feed_url: str) -> list:
    items = []
    r = requests.get(feed_url, headers=HEADERS, timeout=25)
    r.raise_for_status()
    for entry in r.json().get("jobs", [])[:40]:
        title = (entry.get("jobTitle") or "").strip()
        company = (entry.get("companyName") or "").strip()
        link = (entry.get("url") or "").strip()
        raw_type = entry.get("jobType") or ""
        job_type = " ".join(raw_type) if isinstance(raw_type, list) else str(raw_type)
        desc = clean_html(entry.get("jobExcerpt") or entry.get("jobDescription") or "")
        if title and link:
            full_title = f"{title} — {company}" if company else title
            items.append({"source": source_name, "title": full_title, "url": link, "summary": f"{job_type} {desc}"})
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
        f"*Type:* {row['budget_hint']}\n"
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
    source_buckets = []

    for source_name, feed_url in FEEDS:
        try:
            if "remoteok.com" in feed_url:
                items = parse_remoteok(source_name, feed_url)
            elif "remotive.com" in feed_url:
                items = parse_remotive(source_name, feed_url)
            elif "jobicy.com" in feed_url:
                items = parse_jobicy(source_name, feed_url)
            else:
                items = parse_rss(source_name, feed_url)
            print(f"[INFO] {source_name}: fetched {len(items)} raw items")
            source_buckets.append(items)
        except Exception as exc:
            print(f"[WARN] Failed {source_name}: {exc}")

    interleaved = [
        item
        for group in zip_longest(*source_buckets)
        for item in group
        if item is not None
    ]

    by_source = {}
    for item in interleaved:
        if item["url"] in existing:
            continue
        scored = score_item(item["title"], item["summary"])
        if not scored:
            continue
        matched, category, is_contract = scored
        by_source.setdefault(item["source"], []).append((is_contract, item, matched, category))

    for src in by_source:
        by_source[src].sort(key=lambda x: x[0], reverse=True)

    diverse_queue = [
        entry
        for group in zip_longest(*by_source.values())
        for entry in group
        if entry is not None
    ]

    per_source_count = {}
    max_per_source = 2
    new_count = 0

    for is_contract, item, matched, category in diverse_queue:
        if item["url"] in existing:
            continue
        src = item["source"]
        if per_source_count.get(src, 0) >= max_per_source:
            continue

        row = {
            "job_url": item["url"],
            "title": item["title"],
            "source": src,
            "category": category,
            "matched_keywords": ", ".join(matched[:5]),
            "budget_hint": "🔥 Contract / Freelance" if is_contract else "Remote Role",
            "proposal_draft": build_proposal(item["title"], category),
            "status": "new",
        }
        saved = save_lead(row)
        if saved:
            existing.add(item["url"])
            per_source_count[src] = per_source_count.get(src, 0) + 1
            notify_telegram(row)
            new_count += 1
            if new_count >= 5:
                break

    print(f"Job Scout completed. New matches sent: {new_count} | By source: {per_source_count}")


if __name__ == "__main__":
    main()
