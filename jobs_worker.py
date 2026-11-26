import hashlib
import html
import json
import os
import re
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
import requests

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "@PulseFeedNG").strip()

SITE_BASE_URL = "https://chukwumaadwuofor-ai.github.io/pulsefeed-engine"
GUMROAD_URL = "https://chukwuma448.gumroad.com/"

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

CATEGORY_IMAGES = {
    "tech": "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=900&q=75",
    "support": "https://images.unsplash.com/photo-1553877522-43269d4ea984?auto=format&fit=crop&w=900&q=75",
    "writing": "https://images.unsplash.com/photo-1455390582262-044cdead277a?auto=format&fit=crop&w=900&q=75",
    "remote": "https://images.unsplash.com/photo-1522202176988-66273c2fd55f?auto=format&fit=crop&w=900&q=75",
}


def get_supabase_base_url() -> str:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_KEY environment variable.")
    raw_url = SUPABASE_URL if "://" in SUPABASE_URL else f"https://{SUPABASE_URL}"
    parsed = urllib.parse.urlparse(raw_url)
    host = parsed.netloc or parsed.path.split("/")[0]
    if not host:
        raise RuntimeError(f"Invalid SUPABASE_URL: {SUPABASE_URL}")
    return f"https://{host}"


def normalize_str(raw: str) -> str:
    if not raw:
        return ""
    s = str(raw)
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


def slugify(text: str, key: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", normalize_str(text).lower()).strip("-")
    base = base[:65].strip("-") or "remote-job"
    short_key = re.sub(r"[^a-z0-9]", "", str(key).lower())[:8]
    return f"{base}-{short_key}" if short_key else base


def make_dedupe_key(source: str, title: str, url: str) -> str:
    seed = f"{source}|{title}|{url}".lower().strip()
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]


def pick_job_image(title: str, summary: str, location: str = "", explicit_url: str = "") -> str:
    candidate = normalize_str(explicit_url).strip()
    if candidate.startswith("https://") or candidate.startswith("http://"):
        return candidate

    hay = f"{title} {summary} {location}".lower()
    if re.search(r"\b(engineer|developer|software|python|react|devops|cloud|data|qa|full[- ]?stack|backend|frontend|ai|ml|security)\b", hay):
        return CATEGORY_IMAGES["tech"]
    if re.search(r"\b(support|customer|assistant|operations|ops|accountant|tax|coordinator|administrator|sales|success)\b", hay):
        return CATEGORY_IMAGES["support"]
    if re.search(r"\b(writer|writing|content|copywriter|editor|design|designer|ui|ux|marketing|social media)\b", hay):
        return CATEGORY_IMAGES["writing"]
    return CATEGORY_IMAGES["remote"]


def extract_rss_image(item: ET.Element) -> str:
    enclosure = item.find("enclosure")
    if enclosure is not None:
        enc_url = (enclosure.attrib.get("url") or "").strip()
        enc_type = (enclosure.attrib.get("type") or "").lower()
        if enc_url.startswith("http") and (not enc_type or enc_type.startswith("image/")):
            return enc_url

    for elem in item.iter():
        if elem.tag.endswith("content") or elem.tag.endswith("thumbnail"):
            media_url = (elem.attrib.get("url") or "").strip()
            if media_url.startswith("http"):
                return media_url
    return ""


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
            logo_url = item.get("company_logo") or item.get("logo") or ""
            jobs.append({
                "dedupe_key": make_dedupe_key("RemoteOK", title, apply_url),
                "source_name": "RemoteOK",
                "title": title,
                "location_or_type": location,
                "summary": summary,
                "apply_url": apply_url,
                "image_url": pick_job_image(title, summary, location, logo_url),
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
                rss_img = extract_rss_image(item)
                jobs.append({
                    "dedupe_key": make_dedupe_key("WeWorkRemotely", title, link),
                    "source_name": "WeWorkRemotely",
                    "title": title,
                    "location_or_type": "Remote",
                    "summary": summary,
                    "apply_url": link,
                    "image_url": pick_job_image(title, summary, "Remote", rss_img),
                    "status": "published",
                })
                if len(jobs) >= limit:
                    break
        except Exception as exc:
            print(f"WeWorkRemotely fetch error ({feed_url}): {exc}")
    print(f"Fetched {len(jobs)} jobs from WeWorkRemotely.")
    return jobs


def fetch_existing_dedupe_keys(base_url: str) -> set[str]:
    try:
        resp = requests.get(
            f"{base_url}/rest/v1/job_drops?select=dedupe_key&limit=500",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
            },
            timeout=20,
        )
        if resp.ok:
            return {
                str(row.get("dedupe_key", "")).strip()
                for row in (resp.json() or [])
                if row.get("dedupe_key")
            }
    except Exception as exc:
        print(f"Warning checking existing keys: {exc}")
    return set()


def send_telegram_alert(job: dict) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL_ID:
        return
    title = clean_text(job.get("title", "New Remote Job"), 140)
    source = clean_text(job.get("source_name", "PulseFeed"), 60)
    loc = clean_text(job.get("location_or_type", "Remote"), 60)
    summary = clean_text(job.get("summary", ""), 200)
    slug = slugify(title, job.get("dedupe_key") or title)
    page_url = f"{SITE_BASE_URL}/jobs/{slug}.html"

    text = (
        f"🚀 <b>NEW REMOTE JOB</b>\n\n"
        f"💼 <b>{html.escape(title)}</b>\n"
        f"🌍 {html.escape(loc)} • via {html.escape(source)}\n\n"
        f"{html.escape(summary)}\n\n"
        f"👉 <b>View &amp; Apply:</b> {page_url}\n"
        f"🛒 <b>Jobs &amp; Market Hub:</b> {SITE_BASE_URL}/jobs.html"
    )
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            data={
                "chat_id": TELEGRAM_CHANNEL_ID,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": "false",
            },
            timeout=15,
        )
    except Exception as exc:
        print(f"Telegram alert skipped: {exc}")


def upsert_jobs(jobs: list[dict]) -> list[dict]:
    if not jobs:
        print("No jobs to upsert.")
        return []

    base_url = get_supabase_base_url()
    existing_keys = fetch_existing_dedupe_keys(base_url)
    new_jobs = [j for j in jobs if j["dedupe_key"] not in existing_keys]

    endpoint = f"{base_url}/rest/v1/job_drops?on_conflict=dedupe_key"
    print(f"Target Supabase host: {urllib.parse.urlparse(base_url).netloc}")

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
    print(f"Upserted {len(jobs)} jobs into job_drops ({len(new_jobs)} new).")

    for job in new_jobs[:5]:
        send_telegram_alert(job)

    return new_jobs


def fetch_published_jobs(limit: int = 60) -> list[dict]:
    base_url = get_supabase_base_url()
    resp = requests.get(
        f"{base_url}/rest/v1/job_drops?status=eq.published&order=created_at.desc&limit={limit}",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        },
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json() or []


def build_static_files(jobs: list[dict]) -> None:
    os.makedirs("jobs", exist_ok=True)
    now_dt = datetime.now(timezone.utc)
    now_iso = now_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    active_filenames = set()
    feed_items = []
    sitemap_urls = [
        (f"{SITE_BASE_URL}/jobs.html", now_iso, "hourly", "1.0"),
        (f"{SITE_BASE_URL}/index.html", now_iso, "hourly", "0.8"),
    ]

    for job in jobs[:60]:
        jid = str(job.get("id") or "")
        dkey = str(job.get("dedupe_key") or jid)
        title = clean_text(job.get("title", "Remote Opportunity"), 140)
        summary = clean_text(job.get("summary", ""), 420)
        source = clean_text(job.get("source_name", "PulseFeed"), 60)
        loc = clean_text(job.get("location_or_type", "Remote"), 80)
        apply_url = normalize_str(job.get("apply_url") or f"{SITE_BASE_URL}/jobs.html").strip()
        img_url = pick_job_image(title, summary, loc, job.get("image_url") or "")
        created_raw = str(job.get("created_at") or now_iso)
        date_posted = created_raw[:10] if len(created_raw) >= 10 else now_dt.strftime("%Y-%m-%d")
        valid_through = (now_dt + timedelta(days=30)).strftime("%Y-%m-%dT23:59:59Z")

        slug = slugify(title, dkey)
        filename = f"{slug}.html"
        active_filenames.add(filename)
        canonical_url = f"{SITE_BASE_URL}/jobs/{filename}"
        hub_anchor = f"{SITE_BASE_URL}/jobs.html#job-{jid}" if jid else f"{SITE_BASE_URL}/jobs.html"

        schema_obj = {
            "@context": "https://schema.org/",
            "@type": "JobPosting",
            "title": title,
            "description": f"<p>{html.escape(summary)}</p><p>Location: {html.escape(loc)}. Source: {html.escape(source)}.</p>",
            "identifier": {
                "@type": "PropertyValue",
                "name": "PulseFeed Jobs",
                "value": dkey,
            },
            "datePosted": date_posted,
            "validThrough": valid_through,
            "employmentType": "FULL_TIME",
            "hiringOrganization": {
                "@type": "Organization",
                "name": source,
                "sameAs": f"{SITE_BASE_URL}/jobs.html",
            },
            "jobLocationType": "TELECOMMUTE",
            "applicantLocationRequirements": {
                "@type": "Country",
                "name": "Worldwide",
            },
            "directApply": True,
        }

        page_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{html.escape(title)} — Remote Job | PulseFeed</title>
  <meta name="description" content="{html.escape(summary[:155])}" />
  <link rel="canonical" href="{canonical_url}" />
  <script type="application/ld+json">{json.dumps(schema_obj, ensure_ascii=False)}</script>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0d1117; color: #f0f6fc; margin: 0; padding: 18px; line-height: 1.6; }}
    .wrap {{ max-width: 680px; margin: 0 auto; }}
    .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 14px; padding: 22px; margin-top: 16px; }}
    .thumb {{ width: 100%; height: 170px; object-fit: cover; border-radius: 10px; margin-bottom: 14px; border: 1px solid #30363d; }}
    .meta {{ color: #8b949e; font-size: 0.85rem; margin-bottom: 8px; }}
    h1 {{ font-size: 1.38rem; margin: 0 0 12px; color: #ffffff; }}
    p {{ color: #c9d1d9; font-size: 0.96rem; }}
    .actions {{ display: flex; gap: 10px; flex-wrap: wrap; margin-top: 18px; }}
    .btn {{ display: inline-block; padding: 11px 16px; border-radius: 8px; font-weight: 700; text-decoration: none; font-size: 0.9rem; }}
    .btn-green {{ background: #238636; color: #ffffff; }}
    .btn-pink {{ background: #ff90e8; color: #111111; }}
    .btn-outline {{ border: 1px solid #30363d; color: #f0f6fc; background: #0d1117; }}
    .promo {{ margin-top: 18px; padding: 16px; border-radius: 12px; border: 1px solid #ff90e8; background: #1b1629; }}
  </style>
</head>
<body>
  <div class="wrap">
    <a class="btn btn-outline" href="../jobs.html">← All Live Remote Jobs &amp; Market</a>
    <article class="card">
      <img class="thumb" src="{html.escape(img_url)}" alt="{html.escape(title)}" loading="lazy" />
      <div class="meta">{html.escape(source)} • {html.escape(loc)} • Posted {html.escape(date_posted)}</div>
      <h1>{html.escape(title)}</h1>
      <p>{html.escape(summary)}</p>
      <div class="actions">
        <a class="btn btn-green" href="{html.escape(apply_url)}" target="_blank" rel="noopener noreferrer">Apply Directly ↗</a>
        <a class="btn btn-outline" href="{html.escape(hub_anchor)}">Discuss / Comment on Hub</a>
      </div>
    </article>
    <aside class="promo">
      <strong style="color:#ff90e8;font-size:0.82rem;text-transform:uppercase;">Creator Toolkit &amp; Remote Guides</strong>
      <h2 style="font-size:1.05rem;margin:6px 0;">Boost Your Remote Income with Automation &amp; Digital Kits</h2>
      <p style="font-size:0.88rem;color:#8b949e;margin:0 0 12px;">Explore e-books, templates, and community offers on PulseFeed.</p>
      <a class="btn btn-pink" href="{GUMROAD_URL}" target="_blank" rel="noopener noreferrer">Visit Gumroad Store →</a>
    </aside>
  </div>
</body>
</html>"""

        with open(os.path.join("jobs", filename), "w", encoding="utf-8") as f:
            f.write(page_html)

        sitemap_urls.append((canonical_url, now_iso, "daily", "0.8"))
        feed_items.append({
            "id": jid,
            "dedupe_key": dkey,
            "title": title,
            "summary": clean_text(summary, 220),
            "source_name": source,
            "location_or_type": loc,
            "hub_url": canonical_url,
            "apply_url": apply_url,
            "date_posted": date_posted,
        })

    for existing_file in os.listdir("jobs"):
        if existing_file.endswith(".html") and existing_file not in active_filenames:
            try:
                os.remove(os.path.join("jobs", existing_file))
            except OSError:
                pass

    with open("jobs.json", "w", encoding="utf-8") as f:
        json.dump({
            "updated_at": now_iso,
            "hub_url": f"{SITE_BASE_URL}/jobs.html",
            "jobs": feed_items[:30],
        }, f, ensure_ascii=False, indent=2)

    rss_items_xml = []
    for item in feed_items[:30]:
        rss_items_xml.append(f"""    <item>
      <title>{html.escape(item['title'])}</title>
      <link>{html.escape(item['hub_url'])}</link>
      <guid isPermaLink="true">{html.escape(item['hub_url'])}</guid>
      <pubDate>{format_datetime(now_dt)}</pubDate>
      <description>{html.escape(item['summary'])} ({html.escape(item['location_or_type'])})</description>
    </item>""")

    rss_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>PulseFeed Remote Jobs &amp; Digital Offers</title>
    <link>{SITE_BASE_URL}/jobs.html</link>
    <description>Live worldwide remote jobs, tech roles, and creator marketplace drops updated automatically.</description>
    <language>en-us</language>
    <lastBuildDate>{format_datetime(now_dt)}</lastBuildDate>
    <atom:link href="{SITE_BASE_URL}/jobs.xml" rel="self" type="application/rss+xml" />
{chr(10).join(rss_items_xml)}
  </channel>
</rss>"""

    with open("jobs.xml", "w", encoding="utf-8") as f:
        f.write(rss_xml)

    url_nodes = []
    for loc_url, lastmod, changefreq, priority in sitemap_urls:
        url_nodes.append(f"""  <url>
    <loc>{html.escape(loc_url)}</loc>
    <lastmod>{lastmod}</lastmod>
    <changefreq>{changefreq}</changefreq>
    <priority>{priority}</priority>
  </url>""")

    sitemap_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(url_nodes)}
</urlset>"""

    with open("sitemap.xml", "w", encoding="utf-8") as f:
        f.write(sitemap_xml)

    robots_txt = f"User-agent: *\nAllow: /\nSitemap: {SITE_BASE_URL}/sitemap.xml\n"
    with open("robots.txt", "w", encoding="utf-8") as f:
        f.write(robots_txt)

    print(f"Built {len(active_filenames)} static SEO pages, jobs.json, jobs.xml, and sitemap.xml.")


def main() -> None:
    all_jobs = fetch_remoteok(limit=15) + fetch_weworkremotely(limit=15)
    deduped = {}
    for job in all_jobs:
        deduped[job["dedupe_key"]] = job
    final_jobs = list(deduped.values())
    print(f"Total unique jobs ready to sync: {len(final_jobs)}")
    upsert_jobs(final_jobs)
    published_jobs = fetch_published_jobs(limit=60)
    build_static_files(published_jobs)


if __name__ == "__main__":
    main()
