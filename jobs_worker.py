import hashlib
import html
import os
import re
import urllib.parse
import xml.etree.ElementTree as ET
import requests

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()

MOJIBAKE_MAP = {
    "â€™": "’",
    "â€˜": "‘",
    "â€œ": "“",
    "â€": "”",
    "â€”": "—",
    "â€“": "–",
    "â€¦": "…",
    "Â": " ",
    "\u00a0": " ",
}


def normalize_str(raw: str) -> str:
    if not raw:
        return ""
    s = str(raw)
    # Unescape HTML entities twice in case feeds double-encode (e.g. &amp;nbsp;)
    s = html.unescape(html.unescape(s))
    for bad, good in MOJIBAKE_MAP.items():
        s = s.replace(bad, good)
    return s


def clean_text(raw: str, limit: int = 240, strip_urls: bool = False) -> str:
    text = normalize_str(raw)
    text = re.sub(r"<[^>]+>", " ", text)
    if strip_urls:
        text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    trimmed = text[:limit]
    if " " in trimmed:
        trimmed = trimmed.rsplit(" ", 1)[0]
    trimmed = trimmed.rstrip(".,;:-—– ")
    return f"{trimmed}…"


def make_dedupe_key(source: str, title: str, url: str) -> str:
    seed = f"{source}|{title}|{url}".lower().strip()
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]


def fetch_remoteok(limit: int = 15) -> list[dict]:
    jobs = []
    try:
        resp = requests.get(
            "https://remoteok.com/api",
            headers={"User-Agent": "PulseFeedJobsBot/1.0"},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        for item in data:
            if not isinstance(item, dict) or not item.get("position"):
                continue
            title = clean_text(item["position"], 140)
            company = clean_text(item.get("company", "RemoteOK"), 80)
            location = clean_text(item.get("location") or "Remote", 80)
            apply_url = normalize_str(item.get("apply_url") or item.get("url") or "").strip()
            if not apply_url:
                continue
            tags = ", ".join(clean_text(t, 40) for t in (item.get("tags") or []) if t)
            raw_desc = item.get("description") or tags or "Remote role"
            summary = clean_text(f"{company} — {raw_desc}", 260, strip_urls=True)
            jobs.append({
                "dedupe_key": make_dedupe_key("RemoteOK", title, apply_url),
                "source_name": "RemoteOK",
                "title": title,
                "location_or_type": location,
                "summary": summary,
                "apply_url": apply_url,
                "status": "published",
            })
            if len(jobs) >= limit:
                break
        print(f"Fetched {len(jobs)} jobs from RemoteOK.")
    except Exception as exc:
        print(f"RemoteOK fetch error: {exc}")
    return jobs


def fetch_weworkremotely(limit: int = 15) -> list[dict]:
    jobs = []
    feeds = [
        "https://weworkremotely.com/categories/remote-programming-jobs.rss",
        "https://weworkremotely.com/categories/remote-customer-support-jobs.rss",
    ]
    for feed_url in feeds:
        try:
            resp = requests.get(
                feed_url,
                headers={"User-Agent": "PulseFeedJobsBot/1.0"},
                timeout=20,
            )
            resp.raise_for_status()
            root = ET.fromstring(resp.text)
            for item in root.findall(".//item"):
                raw_title = item.findtext("title") or ""
                link = normalize_str(item.findtext("link") or "").strip()
                desc = item.findtext("description") or ""
                if not raw_title or not link:
                    continue
                clean_raw_title = clean_text(raw_title, 200)
                if ":" in clean_raw_title:
                    company, role = [p.strip() for p in clean_raw_title.split(":", 1)]
                else:
                    company, role = "WeWorkRemotely", clean_raw_title.strip()
                title = clean_text(role, 140)
                summary = clean_text(
                    f"{company} — {desc or 'Remote opportunity'}",
                    260,
                    strip_urls=True,
                )
                jobs.append({
                    "dedupe_key": make_dedupe_key("WeWorkRemotely", title, link),
                    "source_name": "WeWorkRemotely",
                    "title": title,
                    "location_or_type": "Remote",
                    "summary": summary,
                    "apply_url": link,
                    "status": "published",
                })
                if len(jobs) >= limit:
                    break
        except Exception as exc:
            print(f"WeWorkRemotely fetch error ({feed_url}): {exc}")
    print(f"Fetched {len(jobs)} jobs from WeWorkRemotely.")
    return jobs


def upsert_jobs(jobs: list[dict]) -> None:
    if not jobs:
        print("No jobs to upsert.")
        return
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_KEY environment variable.")

    parsed = urllib.parse.urlparse(SUPABASE_URL)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    endpoint = f"{base_url}/rest/v1/job_drops?on_conflict=dedupe_key"
    print(f"Target Supabase host: {parsed.netloc}")

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    resp = requests.post(endpoint, headers=headers, json=jobs, timeout=20)
    if not resp.ok:
        print(f"Supabase error {resp.status_code}: {resp.text}")
    resp.raise_for_status()
    print(f"Upserted {len(jobs)} jobs into job_drops.")


def main() -> None:
    all_jobs = fetch_remoteok(limit=15) + fetch_weworkremotely(limit=15)
    deduped = {}
    for job in all_jobs:
        deduped[job["dedupe_key"]] = job
    final_jobs = list(deduped.values())
    print(f"Total unique jobs ready to sync: {len(final_jobs)}")
    upsert_jobs(final_jobs)


if __name__ == "__main__":
    main()
