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

# 2. RSS Feeds mapped by lane (Breaking, Trending, Football)
FEEDS = [
    # Football Breaking & Transfer News
    {"url": "https://feeds.bbci.co.uk/sport/football/rss.xml", "source": "BBC Football", "lane": "football"},
    {"url": "https://www.espn.com/espn/rss/soccer/news", "source": "ESPN FC", "lane": "football"},
    # Breaking World & Tech News
    {"url": "https://feeds.bbci.co.uk/news/world/rss.xml", "source": "BBC World", "lane": "breaking"},
    {"url": "https://www.aljazeera.com/xml/rss/all.xml", "source": "Al Jazeera", "lane": "breaking"},
    # Trending Tech, AI & Business
    {"url": "https://techcrunch.com/feed/", "source": "TechCrunch", "lane": "trending"},
    {"url": "https://www.theverge.com/rss/index.xml", "source": "The Verge", "lane": "trending"},
]

# Guaranteed fallback cover banners (never fails chk_news_requires_media)
FALLBACK_BANNERS = {
    "breaking": "https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&w=1000&q=80",
    "trending": "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1000&q=80",
    "football": "https://images.unsplash.com/photo-1574629810360-7efbbe195018?auto=format&fit=crop&w=1000&q=80",
}

HEADERS_SB = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}

HEADERS_HTTP = {
    "User-Agent": "Mozilla/5.0 (compatible; PulseFeedBot/2.0; +https://chukwumaadwuofor-ai.github.io/pulsefeed-engine/)"
}


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


def extract_media_from_entry(entry, article_url: str, lane: str) -> tuple[str, str]:
    """Returns (media_url, media_type) guaranteed non-empty for news lanes."""
    # 1. Check RSS enclosures
    for enc in entry.get("enclosures", []):
        href = (enc.get("href") or enc.get("url") or "").strip()
        mime = (enc.get("type") or "").lower()
        if href.startswith("https://"):
            if "video" in mime or re.search(r"\.(mp4|webm|mov)(\?|$)", href, re.I):
                return href, "video"
            if "image" in mime or re.search(r"\.(jpg|jpeg|png|webp)(\?|$)", href, re.I):
                return href, "image"

    # 2. Check media:content and media:thumbnail
    for key in ("media_content", "media_thumbnail"):
        for item in entry.get(key, []):
            href = (item.get("url") or "").strip()
            if href.startswith("https://"):
                if re.search(r"\.(mp4|webm|mov)(\?|$)", href, re.I):
                    return href, "video"
                return href, "image"

    # 3. Check inline <img> or <video> in summary/content HTML
    raw_html = entry.get("summary", "") or ""
    if entry.get("content"):
        raw_html += " " + " ".join(c.get("value", "") for c in entry["content"])
    vid_match = re.search(r'src=["\'](https://[^"\']+\.(?:mp4|webm))["\']', raw_html, re.I)
    if vid_match:
        return vid_match.group(1), "video"
    img_match = re.search(r'<img[^>]+src=["\'](https://[^"\']+)["\']', raw_html, re.I)
    if img_match:
        return img_match.group(1), "image"

    # 4. Fetch OpenGraph og:video / og:image from the article page
    if article_url.startswith("https://"):
        try:
            resp = requests.get(article_url, headers=HEADERS_HTTP, timeout=8)
            if resp.ok:
                page = resp.text[:40000]
                og_vid = re.search(
                    r'<meta[^>]+property=["\']og:video(?::secure_url)?["\'][^>]+content=["\'](https://[^"\']+)["\']',
                    page,
                    re.I,
                )
                if og_vid and re.search(r"\.(mp4|webm)(\?|$)", og_vid.group(1), re.I):
                    return og_vid.group(1), "video"

                og_img = re.search(
                    r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\'](https://[^"\']+)["\']',
                    page,
                    re.I,
                )
                if og_img:
                    return html.unescape(og_img.group(1)), "image"
        except Exception as e:
            print(f"OG fetch skipped for {article_url}: {e}")

    # 5. Guaranteed fallback image
    return FALLBACK_BANNERS.get(lane, FALLBACK_BANNERS["trending"]), "image"


def ingest_feeds(max_per_feed: int = 3):
    inserted = 0
    for feed_cfg in FEEDS:
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
            media_url, media_type = extract_media_from_entry(entry, link, lane)

            payload = {
                "title": title,
                "summary": summary,
                "feed_lane": lane,
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
    title = clean_text(post.get("title", ""), max_len=150)
    summary = clean_text(post.get("summary", ""), max_len=240)
    source = clean_text(post.get("source_name", "PulseFeed"), max_len=40)

    return (
        f"{badge} | {source}\n\n"
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

        # Fallback to text message if external media host blocks Telegram fetch
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

        # Mark broadcasted_at so it is never duplicated
        patch_res = requests.patch(
            f"{SUPABASE_URL}/rest/v1/feed_posts?id=eq.{urllib.parse.quote(str(post_id))}",
            headers={**HEADERS_SB, "Prefer": "return=minimal"},
            json={"broadcasted_at": now_iso},
            timeout=15,
        )
        print(f"Broadcasted post {post_id} (tg_ok={sent}, patch={patch_res.status_code})")


if __name__ == "__main__":
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_KEY environment variables.")
    ingest_feeds(max_per_feed=2)
    broadcast_unposted(batch_limit=4)
