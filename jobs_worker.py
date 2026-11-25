import hashlib
import html
import os
import re
import urllib.parse
import xml.etree.ElementTree as ET
import requests

SUPABASE_URL = os.environ["SUPABASE_URL"].strip().rstrip("/")
SUPABASE_KEY = os.environ["SUPABASE_KEY"].strip()

FEED_URLS = [
    ("RemoteOK", "https://remoteok.com/remote-jobs.rss"),
    ("WeWorkRemotely", "https://weworkremotely.com/remote-jobs.rss"),
]


def make_dedupe_key(source_name: str, url: str) -> str:
    parsed = urllib.parse.urlparse(url.strip())
    clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".lower()
    raw = f"{source_name.lower()}|{clean_url}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def clean_text(raw_html: str, limit: int = 240) -> str:
    unescaped = html.unescape(raw_html or "")
    no_tags = re.sub(r"<[^>]+>", " ", unescaped)
    return " ".join(no_tags.split())[:limit]


def fetch_rss_jobs(source_name: str, feed_url: str) -> list[dict]:
    resp = requests.get(
        feed_url,
        timeout=20,
        headers={"User-Agent": "Mozilla/5.0 (PulseFeedJobsBot/1.0)"},
    )
    resp.raise_for_status()
    root = ET.fromstring(resp.content)

    jobs = []
    for item in root.findall(".//item"):
        title = clean_text(item.findtext("title") or "", limit=180)
        link = (item.findtext("link") or "").strip()
        desc = item.findtext("description") or ""
        pub_date = (item.findtext("pubDate") or "").strip()

        if not title or not link:
            continue

        jobs.append({
            "dedupe_key": make_dedupe_key(source_name, link),
            "title": title,
            "company": source_name,
            "location_or_type": "Remote",
            "category": "jobs",
            "source_name": source_name,
            "apply_url": link,
            "summary": clean_text(desc, limit=240),
            "status": "published",
            "published_at": pub_date or None,
        })
    return jobs


def upsert_jobs(jobs: list[dict]) -> None:
    if not jobs:
        return
    endpoint = f"{SUPABASE_URL}/rest/v1/job_drops?on_conflict=dedupe_key"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    resp = requests.post(endpoint, headers=headers, json=jobs, timeout=20)
    resp.raise_for_status()


def run() -> None:
    all_jobs = []
    for source_name, url in FEED_URLS:
        try:
            fetched = fetch_rss_jobs(source_name, url)
            print(f"Fetched {len(fetched)} items from {source_name}")
            all_jobs.extend(fetched)
        except Exception as exc:
            print(f"Feed error ({source_name}): {exc}")

    unique_by_key = {job["dedupe_key"]: job for job in all_jobs}
    upsert_jobs(list(unique_by_key.values()))
    print(f"Upserted {len(unique_by_key)} unique jobs into Supabase.")


if __name__ == "__main__":
    run()
