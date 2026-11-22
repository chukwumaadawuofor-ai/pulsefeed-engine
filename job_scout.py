import hashlib
import html
import json
import os
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any

# ==============================================================================
# CONFIGURATION & ENVIRONMENT VARIABLES
# ==============================================================================
SUPABASE_URL = (os.getenv("SUPABASE_URL") or "").strip().rstrip("/")
SUPABASE_KEY = (os.getenv("SUPABASE_KEY") or "").strip()
TELEGRAM_BOT_TOKEN = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
TELEGRAM_CHAT_ID = (
    os.getenv("TELEGRAM_CHAT_ID") or os.getenv("TELEGRAM_ADMIN_CHAT_ID") or ""
).strip()

print(
    "[DEBUG ENV]",
    "has_sb_url=", bool(SUPABASE_URL),
    "sb_url_starts_https=", SUPABASE_URL.startswith("https://"),
    "has_sb_key=", bool(SUPABASE_KEY),
    "has_tg_token=", bool(TELEGRAM_BOT_TOKEN),
    "has_tg_chat=", bool(TELEGRAM_CHAT_ID),
)

MAX_ALERTS_PER_RUN = int(os.getenv("MAX_ALERTS_PER_RUN", "12"))
MAX_ALERTS_PER_SOURCE = int(os.getenv("MAX_ALERTS_PER_SOURCE", "4"))
MIN_JOB_SCORE = int(os.getenv("MIN_JOB_SCORE", "15"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "20"))

FEED_SOURCES = [
    {
        "name": "remotive",
        "url": "https://remotive.com/api/remote-jobs",
        "type": "remotive_json",
    },
    {
        "name": "remoteok",
        "url": "https://remoteok.com/api",
        "type": "remoteok_json",
    },
    {
        "name": "jobicy",
        "url": "https://jobicy.com/api/v2/remote-jobs?count=50",
        "type": "jobicy_json",
    },
    {
        "name": "weworkremotely",
        "url": "https://weworkremotely.com/categories/remote-programming-jobs.rss",
        "type": "rss_xml",
    },
]

# ==============================================================================
# TARGETING, EXCLUSIONS & SCORING RULES
# ==============================================================================
TARGET_KEYWORDS = [
    "full-stack",
    "full stack",
    "fullstack",
    "next.js",
    "nextjs",
    "typescript",
    "javascript",
    "react",
    "webhook",
    "webhooks",
    "n8n",
    "automation",
    "workflow",
    "api",
    "convex",
    "supabase",
    "postgres",
    "postgresql",
    "bot",
    "scraper",
]

PREFERRED_LOCATION_TERMS = [
    "worldwide",
    "anywhere",
    "global",
    "remote - worldwide",
]

RESTRICTED_LOCATION_TERMS = [
    "usa only",
    "us only",
    "united states only",
    "eu only",
    "europe only",
    "uk only",
    "latam",
    "apac",
]

CONTRACT_RATE_TERMS = [
    "contract",
    "contractor",
    "freelance",
    "/month",
    "per month",
    "monthly",
    "$3k",
    "$4k",
    "$5k",
    "take-home",
]

EXCLUDED_TITLE_TERMS = [
    "director",
    "vp",
    "chief",
    "professor",
    "phd",
    "principal",
    "staff",
    "sap",
    "salesforce",
    "mainframe",
]


# ==============================================================================
# TEXT & NETWORK HELPERS
# ==============================================================================
def _clean_text(value: Any) -> str:
    if not value:
        return ""
    text = re.sub(r"<[^>]+>", " ", str(value))
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _norm(value: Any) -> str:
    return _clean_text(value).lower()


def _http_get_text(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; PulseFeedJobScout/1.0; +https://github.com/chukwumaadawuofor-ai)",
            "Accept": "application/json, application/xml, text/xml, */*",
        },
    )
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        raw = resp.read()
        return raw.decode("utf-8", errors="replace")


def compute_job_fingerprint(job: dict[str, Any]) -> str:
    seed = f"{_norm(job.get('title'))}|{_norm(job.get('company'))}|{_norm(job.get('url'))}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]


# ==============================================================================
# FEED PARSERS
# ==============================================================================
def _parse_remotive(payload_text: str) -> list[dict[str, Any]]:
    data = json.loads(payload_text)
    jobs = []
    for item in data.get("jobs", []):
        jobs.append(
            {
                "source": "remotive",
                "title": _clean_text(item.get("title")),
                "company": _clean_text(item.get("company_name")),
                "location": _clean_text(item.get("candidate_required_location") or "Remote"),
                "url": _clean_text(item.get("url")),
                "salary": _clean_text(item.get("salary")),
                "description": _clean_text(item.get("description")),
            }
        )
    return jobs


def _parse_remoteok(payload_text: str) -> list[dict[str, Any]]:
    data = json.loads(payload_text)
    if not isinstance(data, list):
        return []
    jobs = []
    for item in data:
        if not isinstance(item, dict) or not item.get("position"):
            continue
        tags = item.get("tags") or []
        tag_str = ", ".join(str(t) for t in tags if t)
        jobs.append(
            {
                "source": "remoteok",
                "title": _clean_text(item.get("position")),
                "company": _clean_text(item.get("company")),
                "location": _clean_text(item.get("location") or "Remote"),
                "url": _clean_text(item.get("url") or item.get("apply_url")),
                "salary": _clean_text(item.get("salary")),
                "description": _clean_text(f"{tag_str} {item.get('description') or ''}"),
            }
        )
    return jobs


def _parse_jobicy(payload_text: str) -> list[dict[str, Any]]:
    data = json.loads(payload_text)
    jobs = []
    for item in data.get("jobs", []):
        geo = item.get("jobGeo") or "Remote"
        if isinstance(geo, list):
            geo = ", ".join(str(g) for g in geo)
        jobs.append(
            {
                "source": "jobicy",
                "title": _clean_text(item.get("jobTitle")),
                "company": _clean_text(item.get("companyName")),
                "location": _clean_text(geo),
                "url": _clean_text(item.get("url")),
                "salary": _clean_text(item.get("annualSalaryMin") or item.get("salaryCurrency") or ""),
                "description": _clean_text(
                    f"{item.get('jobExcerpt') or ''} {item.get('jobDescription') or ''}"
                ),
            }
        )
    return jobs


def _parse_rss(source_name: str, xml_text: str) -> list[dict[str, Any]]:
    root = ET.fromstring(xml_text)
    jobs = []
    for item in root.findall(".//item"):
        raw_title = _clean_text(item.findtext("title"))
        link = _clean_text(item.findtext("link"))
        desc = _clean_text(item.findtext("description"))

        company = ""
        title = raw_title
        if ":" in raw_title:
            maybe_company, rest = raw_title.split(":", 1)
            if len(maybe_company) <= 60:
                company = maybe_company.strip()
                title = rest.strip()

        region_match = re.search(
            r"(worldwide|anywhere|usa only|us only|eu only|europe only|uk only|latam|apac)",
            f"{title} {desc}".lower(),
        )
        location = region_match.group(1) if region_match else "Remote"

        jobs.append(
            {
                "source": source_name,
                "title": title,
                "company": company,
                "location": location,
                "url": link,
                "salary": "",
                "description": desc,
            }
        )
    return jobs


def fetch_source_jobs(source: dict[str, str]) -> list[dict[str, Any]]:
    try:
        raw_text = _http_get_text(source["url"])
        kind = source["type"]
        if kind == "remotive_json":
            return _parse_remotive(raw_text)
        if kind == "remoteok_json":
            return _parse_remoteok(raw_text)
        if kind == "jobicy_json":
            return _parse_jobicy(raw_text)
        if kind == "rss_xml":
            return _parse_rss(source["name"], raw_text)
        return []
    except Exception as exc:
        print(f"[WARN] Failed fetching {source['name']}: {exc}")
        return []


# ==============================================================================
# FILTERING, SCORING & ROUND-ROBIN QUEUEING
# ==============================================================================
def is_excluded_title(title: str) -> bool:
    norm_title = _norm(title)
    return any(term in norm_title for term in EXCLUDED_TITLE_TERMS)


def evaluate_job_fit(job: dict[str, Any], min_score: int = MIN_JOB_SCORE) -> dict[str, Any]:
    title_raw = _norm(job.get("title"))
    location_raw = _norm(job.get("location"))
    salary_raw = _norm(job.get("salary"))
    desc_raw = _norm(job.get("description"))
    combined = f"{title_raw} {location_raw} {salary_raw} {desc_raw}"

    if not title_raw or not job.get("url"):
        return {
            "qualified": False,
            "score": -100,
            "reasons": ["missing_title_or_url"],
            "region_flag": "invalid",
        }

    if is_excluded_title(title_raw):
        return {
            "qualified": False,
            "score": -100,
            "reasons": ["excluded_title"],
            "region_flag": "excluded",
        }

    score = 0
    reasons: list[str] = []

    matched_keywords = [kw for kw in TARGET_KEYWORDS if kw in combined]
    if matched_keywords:
        score += min(len(matched_keywords) * 10, 50)
        reasons.append(f"stack/role ({', '.join(matched_keywords[:5])})")

    has_worldwide = any(loc in location_raw or loc in combined for loc in PREFERRED_LOCATION_TERMS)
    has_restricted = any(loc in location_raw for loc in RESTRICTED_LOCATION_TERMS)

    if has_worldwide and not has_restricted:
        score += 25
        reasons.append("worldwide/global")
        region_flag = "worldwide"
    elif has_restricted and not has_worldwide:
        score -= 25
        reasons.append("region_restricted")
        region_flag = "restricted"
    else:
        region_flag = "unspecified"

    if any(term in combined for term in CONTRACT_RATE_TERMS):
        score += 15
        reasons.append("contract/rate signal")

    return {
        "qualified": score >= min_score,
        "score": score,
        "reasons": reasons,
        "region_flag": region_flag,
    }


def interleave_by_source(scored_jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = {}
    for item in scored_jobs:
        src = item["job"].get("source", "unknown")
        buckets.setdefault(src, []).append(item)

    for src in buckets:
        buckets[src].sort(key=lambda x: x["evaluation"]["score"], reverse=True)

    ordered: list[dict[str, Any]] = []
    source_names = list(buckets.keys())
    idx = 0
    while True:
        added_in_round = False
        for src in source_names:
            if idx < len(buckets[src]):
                ordered.append(buckets[src][idx])
                added_in_round = True
        if not added_in_round:
            break
        idx += 1
    return ordered


# ==============================================================================
# SUPABASE DEDUPLICATION & TELEGRAM ALERTS
# ==============================================================================
def supabase_is_seen(fingerprint: str) -> bool:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return False
    encoded_fp = urllib.parse.quote(fingerprint)
    url = f"{SUPABASE_URL}/rest/v1/job_leads?fingerprint=eq.{encoded_fp}&select=id&limit=1"
    req = urllib.request.Request(
        url,
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            rows = json.loads(resp.read().decode("utf-8", errors="replace"))
            return bool(rows)
    except Exception as exc:
        print(f"[WARN] Supabase lookup failed: {exc}")
        return False


def supabase_record_lead(job: dict[str, Any], evaluation: dict[str, Any], fingerprint: str) -> None:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return
    url = f"{SUPABASE_URL}/rest/v1/job_leads"
    payload = {
        "fingerprint": fingerprint,
        "source": job.get("source"),
        "title": job.get("title"),
        "company": job.get("company"),
        "location": job.get("location"),
        "url": job.get("url"),
        "score": evaluation.get("score"),
        "region_flag": evaluation.get("region_flag"),
        "reasons": ", ".join(evaluation.get("reasons") or []),
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "resolution=ignore-duplicates,return=minimal",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT):
            pass
    except Exception as exc:
        print(f"[WARN] Supabase insert failed: {exc}")


def format_job_alert(job: dict[str, Any], evaluation: dict[str, Any]) -> str:
    score = evaluation.get("score", 0)
    badge = "🔥 High-Fit Lead" if score >= 50 else "⚡ Contract/Stack Match"
    title = (job.get("title") or "Untitled Role").strip()
    company = (job.get("company") or "Unknown Company").strip()
    location = (job.get("location") or "Remote / Unspecified").strip()
    source = (job.get("source") or "feed").strip()
    url = (job.get("url") or "").strip()
    reasons = " | ".join(evaluation.get("reasons") or []) or "general match"

    lines = [
        f"{badge} (Score: {score}) [{source}]",
        f"*{title}* @ *{company}*",
        f"📍 {location} ({evaluation.get('region_flag', 'unspecified')})",
        f"🧩 {reasons}",
    ]
    if job.get("salary"):
        lines.append(f"💸 {job['salary']}")
    if url:
        lines.append(f"🔗 {url}")
    return "\n".join(lines)


def send_telegram_message(text: str) -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[INFO] Telegram env vars not set; printing alert locally:\n" + text + "\n")
        return True
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            return resp.status == 200
    except Exception as exc:
        print(f"[WARN] Telegram send failed: {exc}")
        return False


# ==============================================================================
# MAIN RUNNER
# ==============================================================================
def run_job_scout() -> None:
    all_raw_jobs: list[dict[str, Any]] = []
    for src in FEED_SOURCES:
        fetched = fetch_source_jobs(src)
        print(f"[INFO] {src['name']}: fetched {len(fetched)} raw listings")
        all_raw_jobs.extend(fetched)

    qualified_items: list[dict[str, Any]] = []
    for job in all_raw_jobs:
        evaluation = evaluate_job_fit(job, min_score=MIN_JOB_SCORE)
        if evaluation["qualified"]:
            qualified_items.append({"job": job, "evaluation": evaluation})

    queued_items = interleave_by_source(qualified_items)
    per_source_sent: dict[str, int] = {}
    total_sent = 0

    for item in queued_items:
        if total_sent >= MAX_ALERTS_PER_RUN:
            break

        job = item["job"]
        evaluation = item["evaluation"]
        source_name = job.get("source", "unknown")

        if per_source_sent.get(source_name, 0) >= MAX_ALERTS_PER_SOURCE:
            continue

        fp = compute_job_fingerprint(job)
        if supabase_is_seen(fp):
            continue

        msg = format_job_alert(job, evaluation)
        if send_telegram_message(msg):
            supabase_record_lead(job, evaluation, fp)
            per_source_sent[source_name] = per_source_sent.get(source_name, 0) + 1
            total_sent += 1

    print(f"[DONE] Sent {total_sent} new job alerts across {len(per_source_sent)} sources.")


if __name__ == "__main__":
    run_job_scout()
