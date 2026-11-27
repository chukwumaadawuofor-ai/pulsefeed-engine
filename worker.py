import os
import re
import html
import urllib.parse
import requests
import feedparser
from datetime import datetime, timezone

# 1. Environment Secrets (from GitHub Actions)
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "").strip()
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "").strip()
SOCIAL_WEBHOOK_URL = os.environ.get("SOCIAL_WEBHOOK_URL", "").strip()

SITE_URL = "https://chukwumaadwuofor-ai.github.io/pulsefeed-engine/"
JOBS_URL = "https://chukwumaadwuofor-ai.github.io/pulsefeed-engine/jobs.html"
GUMROAD_OFFER_URL = (
    "https://chukwuma448.gumroad.com/l/dvfhm"
    "?utm_source=pulsefeed&utm_medium=telegram_auto&utm_campaign=viralhook_ai"
)

# 2. RSS Feeds mapped by lane (Breaking, Trending, Football) and region (NG, US, UK, EU, AU, GLOBAL)
FEEDS = [
    # Nigeria (NG)
    {"url": "https://rss.punchng.com/v1/category/latest_news", "source": "Punch NG", "lane": "trending", "region": "NG"},
    {"url": "https://pmnewsnigeria.com/feed/", "source": "P.M. News", "lane": "breaking", "region": "NG"},

    # United States (US)
    {"url": "https://feeds.npr.org/1001/rss.xml", "source": "NPR News", "lane": "trending", "region": "US"},
    {"url": "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en", "source": "Google News US", "lane": "breaking", "region": "US"},

    # United Kingdom (UK)
    {"url": "https://feeds.bbci.co.uk/news/uk/rss.xml", "source": "BBC News UK", "lane": "trending", "region": "UK"},
    {"url": "https://www.theguardian.com/uk/rss", "source": "The Guardian UK", "lane": "breaking", "region": "UK"},

    # Europe (EU)
    {"url": "https://www.politico.eu/feed/", "source": "Politico Europe", "lane": "trending", "region": "EU"},
    {"url": "https://www.euronews.com/rss", "source": "Euronews", "lane": "breaking", "region": "EU"},

    # Australia (AU)
    {"url": "https://www.abc.net.au/news/feed/45910/rss.xml", "source": "ABC News Australia", "lane": "trending", "region": "AU"},

    # Football Breaking & Transfer News
    {"url": "https://feeds.bbci.co.uk/sport/football/rss.xml", "source": "BBC Football", "lane": "football", "region": "GLOBAL"},
    {"url": "https://www.espn.com/espn/rss/soccer/news", "source": "ESPN FC", "lane": "football", "region": "GLOBAL"},

    # High-Intent Tech, AI & Business (GLOBAL)
    {"url": "https://techcrunch.com/feed/", "source": "TechCrunch", "lane": "trending", "region": "GLOBAL"},
    {"url": "https://www.theverge.com/rss/index.xml", "source": "The Verge", "lane": "trending", "region": "GLOBAL"},
    {"url": "https://feeds.businessinsider.com/custom/all", "source": "Business Insider", "lane": "trending", "region": "GLOBAL"},
    {"url": "https://feeds.bbci.co.uk/news/world/rss.xml", "source": "BBC World", "lane": "breaking", "region": "GLOBAL"},
]

# Guaranteed fallback cover banners (never fails chk_news_requires_media)
FALLBACK_BANNERS = {
    "NG": "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=1000&q=80",
    "US": "https://images.unsplash.com/photo-1501466044931-62695aada8e9?auto=format&fit=crop&w=1000&q=80",
    "UK": "https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?auto=format&fit=crop&w=1000&q=80",
    "EU": "https://images.unsplash.com/photo-1467269204594-9661b134dd2b?auto=format&fit=crop&w=1000&q=80",
    "AU": "https://images.unsplash.com/photo-1506973035872-a4ec16b8e8d9?auto=format&fit=crop&w=1000&q=80",
    "GLOBAL": "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1000&q=80",
    "breaking": "https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&w=1000&q=80",
    "trending": "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1000&q=80",
    "football": "https://images.unsplash.com/photo-1574629810360-7efbbe195018?auto=format&fit=crop&w=1000&q=80",
}

REGION_LABELS = {
    "NG": "🇳🇬 Nigeria",
    "US": "🇺🇸 US",
    "UK": "🇬🇧 UK",
    "EU": "🇪🇺 Europe",
    "AU": "🇦🇺 Australia",
    "GLOBAL": "🌍 Global",
}

BAD_MEDIA_TOKENS = (
    "logo",
    "favicon",
    "sprite",
    "placeholder",
    "default-image",
    "punch-logo",
    "pm-news",
    "1x1",
)

HEADERS_SB = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}

HEADERS_HTTP = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 13; SM-G998B) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def is_usable_media_url(url: str) -> bool:
    u = (url or "").strip()
    if not u.startswith("https://"):
        return False
    low = u.lower()
    if any(token in low for token in BAD_MEDIA_TOKENS):
        return False
    return True


def clean_text(raw: str, max_len: int = 320) -> str:
    if not raw:
        return ""
    text = html.unescape(re.sub(r"<[^>]+>", " ", str(raw)))
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_len:
        text = text[: max_len - 1].rstrip() + "…"
    return text


def detect_lane(title: str, summary: str, default_lane: str) -> str:
    hay = f"{title} {summary}".lower()
    if re.search(r"\b(football|soccer|premier league|champions league|arsenal|chelsea|man utd|liverpool|barcelona|real madrid|super eagles|afcon|fifa|uefa|goal|transfer)\b", hay):
        return "football"
    if re.search(r"\b(breaking|urgent|just in|alert|exclusive|confirmed)\b", hay):
        return "breaking"
    return default_lane


def get_fallback_banner(lane: str, region: str) -> str:
    if lane == "football":
        return FALLBACK_BANNERS["football"]
    if region in FALLBACK_BANNERS:
        return FALLBACK_BANNERS[region]
    return FALLBACK_BANNERS.get(lane, FALLBACK_BANNERS["trending"])


def extract_og_from_article(article_url: str) -> tuple[str, str]:
    if not article_url.startswith("https://"):
        return "", ""
    try:
        resp = requests.get(article_url, headers=HEADERS_HTTP, timeout=10)
        if not resp.ok or not resp.text:
            return "", ""
        page = resp.text[:120000]

        og_vid = re.search(
            r'<meta[^>]+(?:property|name)=["\']og:video(?::secure_url)?["\'][^>]+content=["\'](https://[^"\']+)["\']',
            page,
            re.I,
        )
        if og_vid:
            v_url = html.unescape(og_vid.group(1).strip())
            if is_usable_media_url(v_url) and re.search(r"\.(mp4|webm)(\?|$)", v_url, re.I):
                return v_url, "video"

        for pattern in (
            r'<meta[^>]+(?:property|name)=["\']og:image(?::secure_url)?["\'][^>]+content=["\'](https?://[^"\']+)["\']',
            r'<meta[^>]+content=["\'](https?://[^"\']+)["\'][^>]+(?:property|name)=["\']og:image(?::secure_url)?["\']',
        ):
            og_img = re.search(pattern, page, re.I)
            if og_img:
                img_url = html.unescape(og_img.group(1).strip())
                if img_url.startswith("http://"):
                    img_url = "https://" + img_url[7:]
                if is_usable_media_url(img_url):
                    return img_url, "image"
    except Exception as e:
        print(f"OG fetch skipped for {article_url}: {e}")
    return "", ""


def extract_media_from_entry(entry, article_url: str, lane: str, region: str) -> tuple[str, str]:
    """Returns (media_url, media_type) preferring real story photos over logos/banners."""
    for enc in entry.get("enclosures", []):
        href = html.unescape((enc.get("href") or enc.get("url") or "").strip())
        mime = (enc.get("type") or "").lower()
        if is_usable_media_url(href):
            if "video" in mime or re.search(r"\.(mp4|webm|mov)(\?|$)", href, re.I):
                return href, "video"
            if "image" in mime or re.search(r"\.(jpg|jpeg|png|webp)(\?|$)", href, re.I):
                return href, "image"

    for key in ("media_content", "media_thumbnail"):
        for item in entry.get(key, []):
            href = html.unescape((item.get("url") or "").strip())
            if is_usable_media_url(href):
                if re.search(r"\.(mp4|webm|mov)(\?|$)", href, re.I):
                    return href, "video"
                return href, "image"

    raw_html = entry.get("summary", "") or ""
    if entry.get("content"):
        raw_html += " " + " ".join(c.get("value", "") for c in entry["content"])
    vid_match = re.search(r'src=["\'](https://[^"\']+\.(?:mp4|webm))["\']', raw_html, re.I)
    if vid_match and is_usable_media_url(vid_match.group(1)):
        return html.unescape(vid_match.group(1)), "video"

    for img_match in re.finditer(r'<img[^>]+src=["\'](https://[^"\']+)["\']', raw_html, re.I):
        candidate = html.unescape(img_match.group(1).strip())
        if is_usable_media_url(candidate):
            return candidate, "image"

    og_url, og_type = extract_og_from_article(article_url)
    if og_url:
        return og_url, og_type

    return get_fallback_banner(lane, region), "image"


def ingest_feeds(max_per_feed: int = 2):
    inserted = 0
    for feed_cfg in FEEDS:
        region = feed_cfg.get("region", "GLOBAL")
        try:
            parsed = feedparser.parse(feed_cfg["url"])
        except Exception as e:
            print(f"Feed parse error ({feed_cfg['source']}): {e}")
            continue

        for entry in parsed.entries[:max_per_feed]:
            title = clean_text(entry.get("title", ""), max_len=160)
            link = (entry.get("link") or "").strip()
            if not title or not link.startswith("https://"):
                continue

            raw_summary = entry.get("summary") or entry.get("description") or title
            summary = clean_text(raw_summary, max_len=340)
            if len(summary) < 10:
                summary = f"{title} — Read full update and join the live discussion."

            lane = detect_lane(title, summary, feed_cfg["lane"])
            media_url, media_type = extract_media_from_entry(entry, link, lane, region)

            payload = {
                "title": title,
                "summary": summary,
                "feed_lane": lane,
                "region": region,
                "source_name": feed_cfg["source"],
                "source_url": link,
                "media_url": media_url,
                "media_type": media_type,
                "author_name": feed_cfg["source"],
                "is_user_post": False,
                "status": "published",
            }

            res = requests.post(
                f"{SUPABASE_URL}/rest/v1/feed_posts?on_conflict=source_url",
                headers={**HEADERS_SB, "Prefer": "resolution=ignore-duplicates,return=minimal"},
                json=payload,
                timeout=15,
            )
            if res.status_code in (200, 201, 204):
                inserted += 1
            else:
                print(f"Insert warning ({res.status_code}): {res.text[:200]}")

    print(f"Ingest pass complete (processed up to {inserted} items).")


def build_social_caption(post: dict) -> str:
    lane_tags = {
        "breaking": "🚨 BREAKING NEWS",
        "trending": "🔥 TRENDING NOW",
        "football": "⚽ FOOTBALL NEWS",
        "community": "💬 COMMUNITY POST",
    }
    badge = lane_tags.get(post.get("feed_lane"), "🔥 TRENDING NOW")
    region_label = REGION_LABELS.get(post.get("region") or "GLOBAL", "🌍 Global")
    title = clean_text(post.get("title", ""), max_len=150)
    summary = clean_text(post.get("summary", ""), max_len=240)
    source = clean_text(post.get("source_name", "PulseFeed"), max_len=40)

    return (
        f"{badge} • {region_label} | {source}\n\n"
        f"{title}\n\n"
        f"{summary}\n\n"
        f"💬 Comment & Watch Live: {SITE_URL}\n"
        f"🚀 ViralHook AI ($39+): {GUMROAD_OFFER_URL}\n"
        f"💼 Remote Jobs & Offers: {JOBS_URL}"
    )


def send_telegram_post(post: dict) -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL_ID:
        print("Telegram credentials not configured; skipping.")
        return False

    caption = build_social_caption(post)
    media_url = (post.get("media_url") or "").strip()
    media_type = post.get("media_type") or "image"
    lane = post.get("feed_lane") or "trending"
    region = post.get("region") or "GLOBAL"
    fallback_url = get_fallback_banner(lane, region)
    base_tg = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

    try:
        if media_url.startswith("https://") and media_type == "video":
            r = requests.post(
                f"{base_tg}/sendVideo",
                data={"chat_id": TELEGRAM_CHANNEL_ID, "video": media_url, "caption": caption},
                timeout=20,
            )
            if r.ok:
                return True

        if media_url.startswith("https://"):
            r = requests.post(
                f"{base_tg}/sendPhoto",
                data={"chat_id": TELEGRAM_CHANNEL_ID, "photo": media_url, "caption": caption},
                timeout=20,
            )
            if r.ok:
                return True
            print(f"Primary sendPhoto failed ({r.status_code}); retrying with fallback banner.")

        if fallback_url.startswith("https://") and fallback_url != media_url:
            r_fb = requests.post(
                f"{base_tg}/sendPhoto",
                data={"chat_id": TELEGRAM_CHANNEL_ID, "photo": fallback_url, "caption": caption},
                timeout=20,
            )
            if r_fb.ok:
                return True

        r = requests.post(
            f"{base_tg}/sendMessage",
            data={
                "chat_id": TELEGRAM_CHANNEL_ID,
                "text": caption,
                "disable_web_page_preview": False,
            },
            timeout=15,
        )
        return r.ok
    except Exception as e:
        print(f"Telegram send error: {e}")
        return False


def send_social_webhook(post: dict):
    """Optional webhook fan-out (Make / Zapier / n8n -> X, Facebook, WhatsApp)."""
    if not SOCIAL_WEBHOOK_URL.startswith("https://"):
        return
    try:
        requests.post(
            SOCIAL_WEBHOOK_URL,
            json={
                "id": post.get("id"),
                "lane": post.get("feed_lane"),
                "region": post.get("region", "GLOBAL"),
                "title": post.get("title"),
                "summary": post.get("summary"),
                "media_url": post.get("media_url"),
                "media_type": post.get("media_type"),
                "caption": build_social_caption(post),
                "site_url": SITE_URL,
                "offer_url": GUMROAD_OFFER_URL,
            },
            timeout=12,
        )
    except Exception as e:
        print(f"Social webhook warning: {e}")


def broadcast_unposted(batch_limit: int = 4):
    """Picks newest unbroadcasted posts (including user posts) and pushes to socials."""
    query = (
        f"{SUPABASE_URL}/rest/v1/feed_posts"
        f"?status=eq.published&broadcasted_at=is.null"
        f"&order=created_at.desc&limit={batch_limit}"
    )
    res = requests.get(query, headers=HEADERS_SB, timeout=15)
    if not res.ok:
        print(f"Could not fetch unbroadcasted posts: {res.status_code} {res.text[:200]}")
        return

    posts = res.json() or []
    if not posts:
        print("No new posts waiting to broadcast.")
        return

    now_iso = datetime.now(timezone.utc).isoformat()
    for post in reversed(posts):
        post_id = post["id"]
        sent = send_telegram_post(post)
        send_social_webhook(post)

        patch_res = requests.patch(
            f"{SUPABASE_URL}/rest/v1/feed_posts?id=eq.{urllib.parse.quote(str(post_id))}",
            headers={**HEADERS_SB, "Prefer": "return=minimal"},
            json={"broadcasted_at": now_iso},
            timeout=15,
        )
        print(f"Broadcasted post {post_id} (tg_ok={sent}, patch={patch_res.status_code})")


def export_ai_discovery_files(limit: int = 30):
    """Generates static sitemap.xml, feed.xml, and llms.txt so non-JS AI crawlers can read live headlines and offers."""
    query = (
        f"{SUPABASE_URL}/rest/v1/feed_posts"
        f"?status=eq.published&order=is_pinned.desc,created_at.desc&limit={limit}"
    )
    res = requests.get(query, headers=HEADERS_SB, timeout=15)
    posts = res.json() if res.ok else []
    now_rfc = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    sitemap_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>{SITE_URL}</loc>
    <lastmod>{now_iso}</lastmod>
    <changefreq>hourly</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>{JOBS_URL}</loc>
    <lastmod>{now_iso}</lastmod>
    <changefreq>daily</changefreq>
    <priority>0.9</priority>
  </url>
</urlset>
"""
    with open("sitemap.xml", "w", encoding="utf-8") as f:
        f.write(sitemap_xml)

    rss_items = []
    for p in posts:
        title = html.escape(clean_text(p.get("title", ""), max_len=160))
        summary = html.escape(clean_text(p.get("summary", ""), max_len=320))
        region = html.escape(p.get("region") or "GLOBAL")
        lane = html.escape(p.get("feed_lane") or "trending")
        guid = html.escape(str(p.get("id") or p.get("source_url") or title))
        media_url = (p.get("media_url") or "").strip()
        enclosure = (
            f'<enclosure url="{html.escape(media_url)}" type="image/jpeg" />'
            if media_url.startswith("https://")
            else ""
        )
        rss_items.append(
            f"""    <item>
      <title>[{region}] {title}</title>
      <link>{SITE_URL}</link>
      <guid isPermaLink="false">{guid}</guid>
      <category>{lane}</category>
      <description>{summary}</description>
      {enclosure}
    </item>"""
        )

    feed_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>PulseFeed — Breaking News, Trending &amp; Football</title>
    <link>{SITE_URL}</link>
    <description>Real-time global and regional breaking news, football updates, remote jobs, and creator tools.</description>
    <lastBuildDate>{now_rfc}</lastBuildDate>
{chr(10).join(rss_items)}
  </channel>
</rss>
"""
    with open("feed.xml", "w", encoding="utf-8") as f:
        f.write(feed_xml)

    lines = [
        "# PulseFeed",
        "",
        "> Real-time global and regional breaking news, trending stories, football updates, remote job listings, and creator monetization tools.",
        "",
        "## Core Pages",
        f"- [PulseFeed Live Timeline]({SITE_URL}): Real-time breaking news, trending updates, and football feed across Nigeria (NG), UK, US, Europe (EU), Australia (AU), and Global.",
        f"- [Remote Jobs, Marketplace & Sponsorships]({JOBS_URL}): Curated remote work opportunities, digital offers, and sponsorship placements.",
        f"- [ViralHook AI Script Studio]({GUMROAD_OFFER_URL}): Featured AI script and hook generator for faceless Shorts, Reels, and TikTok creators ($39+).",
        "",
        "## Latest Headlines",
    ]
    for p in posts[:20]:
        t = clean_text(p.get("title", ""), max_len=140)
        s = clean_text(p.get("summary", ""), max_len=200)
        r = p.get("region") or "GLOBAL"
        lines.append(f"- [{r}] **{t}** — {s} ({SITE_URL})")

    with open("llms.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"Exported sitemap.xml, feed.xml, and llms.txt ({len(posts)} items).")


if __name__ == "__main__":
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_KEY environment variables.")
    ingest_feeds(max_per_feed=2)
    broadcast_unposted(batch_limit=4)
    export_ai_discovery_files(limit=30)
