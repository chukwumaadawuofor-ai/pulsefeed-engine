import os
import re
import html
import urllib.parse
import requests
import feedparser
from datetime import datetime, timezone, timedelta

# 1. Environment Secrets (from GitHub Actions)
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "").strip()
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "").strip()
FB_PAGE_ID = os.environ.get("FB_PAGE_ID", "").strip()
FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN", "").strip()
SOCIAL_WEBHOOK_URL = os.environ.get("SOCIAL_WEBHOOK_URL", "").strip()
DAILY_BOOKING_CODE = os.environ.get("DAILY_BOOKING_CODE", "").strip()
FORCE_PROMO_BANNER = os.environ.get("FORCE_PROMO_BANNER", "").strip().lower() in ("1", "true", "yes")

WAT_TZ = timezone(timedelta(hours=1))

SITE_URL = "https://chukwumaadawuofor-ai.github.io/pulsefeed-engine/"
JOBS_URL = "https://chukwumaadawuofor-ai.github.io/pulsefeed-engine/jobs.html"
GUMROAD_OFFER_URL = (
    "https://chukwuma448.gumroad.com/l/dvfhm"
    "?utm_source=pulsefeed&utm_medium=social_auto&utm_campaign=viralhook_ai"
)
PROMO_BANNER_URL = (
    "https://images.unsplash.com/photo-1551288049-bebda4e38f71"
    "?auto=format&fit=crop&w=1200&h=630&q=85"
)

# 2. RSS Feeds mapped by lane (Breaking, Trending, Football) and region
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

# Leagues tracked for daily football betting slips & EOD score verification
SOCCER_LEAGUES = [
    ("eng.1", "Premier League"),
    ("esp.1", "La Liga"),
    ("ita.1", "Serie A"),
    ("ger.1", "Bundesliga"),
    ("fra.1", "Ligue 1"),
    ("uefa.champions", "Champions League"),
    ("uefa.europa", "Europa League"),
    ("eng.2", "Championship"),
    ("ned.1", "Eredivisie"),
    ("por.1", "Primeira Liga"),
]

FALLBACK_BANNERS = {
    "NG": "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=1200&h=630&q=85",
    "US": "https://images.unsplash.com/photo-1501466044931-62695aada8e9?auto=format&fit=crop&w=1200&h=630&q=85",
    "UK": "https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?auto=format&fit=crop&w=1200&h=630&q=85",
    "EU": "https://images.unsplash.com/photo-1467269204594-9661b134dd2b?auto=format&fit=crop&w=1200&h=630&q=85",
    "AU": "https://images.unsplash.com/photo-1506973035872-a4ec16b8e8d9?auto=format&fit=crop&w=1200&h=630&q=85",
    "GLOBAL": "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1200&h=630&q=85",
    "breaking": "https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&w=1200&h=630&q=85",
    "trending": "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1200&h=630&q=85",
    "football": "https://images.unsplash.com/photo-1574629810360-7efbbe195018?auto=format&fit=crop&w=1200&h=630&q=85",
    "betting": "https://images.unsplash.com/photo-1508098682722-e99c43a406b2?auto=format&fit=crop&w=1200&h=630&q=85",
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
    "Accept": "application/json,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

MEDIA_FETCH_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
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
    if lane in ("football", "betting"):
        return FALLBACK_BANNERS[lane]
    if region in FALLBACK_BANNERS:
        return FALLBACK_BANNERS[region]
    return FALLBACK_BANNERS.get(lane, FALLBACK_BANNERS["trending"])


def pick_best_image_url(media_url: str, media_type: str, lane: str, region: str) -> str:
    fallback_url = get_fallback_banner(lane, region)
    u = (media_url or "").strip()
    if is_usable_media_url(u) and media_type != "video":
        return u
    return fallback_url


def _download_photo_bytes(url: str) -> tuple[bytes | None, str, str]:
    """Downloads image bytes from an HTTPS URL; returns (bytes, filename, mime_type)."""
    u = (url or "").strip()
    if not u.startswith("https://"):
        return None, "photo.jpg", "image/jpeg"
    try:
        resp = requests.get(u, headers=MEDIA_FETCH_HEADERS, timeout=15, allow_redirects=True)
        if not resp.ok or not resp.content:
            return None, "photo.jpg", "image/jpeg"
        if len(resp.content) > 9_500_000:
            return None, "photo.jpg", "image/jpeg"

        ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if "png" in ctype or u.lower().endswith(".png"):
            return resp.content, "photo.png", "image/png"
        if "webp" in ctype or u.lower().endswith(".webp"):
            return resp.content, "photo.webp", "image/webp"
        if ctype.startswith("image/") or resp.content[:2] == b"\xff\xd8" or resp.content[:8] == b"\x89PNG\r\n\x1a\n":
            return resp.content, "photo.jpg", "image/jpeg"
    except Exception as e:
        print(f"[TG] Photo download error ({u[:80]}): {e}")
    return None, "photo.jpg", "image/jpeg"


def _send_tg_photo_with_upload(base_tg: str, caption: str, photo_url: str) -> bool:
    """Uploads downloaded image bytes via multipart/form-data, with URL fallback if needed."""
    img_bytes, filename, mime_type = _download_photo_bytes(photo_url)
    if img_bytes:
        r = requests.post(
            f"{base_tg}/sendPhoto",
            data={"chat_id": TELEGRAM_CHANNEL_ID, "caption": caption[:1020]},
            files={"photo": (filename, img_bytes, mime_type)},
            timeout=25,
        )
        if r.ok:
            return True
        print(f"[TG] multipart sendPhoto failed ({r.status_code}): {r.text[:220]}")

    r_url = requests.post(
        f"{base_tg}/sendPhoto",
        data={"chat_id": TELEGRAM_CHANNEL_ID, "photo": photo_url, "caption": caption[:1020]},
        timeout=20,
    )
    if r_url.ok:
        return True
    print(f"[TG] url sendPhoto failed ({r_url.status_code}): {r_url.text[:220]}")
    return False


def send_telegram_raw(caption: str, photo_url: str = "") -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL_ID:
        print("[TG] Credentials not configured; skipping.")
        return False

    base_tg = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
    try:
        if photo_url.startswith("https://") and len(caption) <= 1020:
            if _send_tg_photo_with_upload(base_tg, caption, photo_url):
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
        if r.ok:
            return True
        print(f"[TG] sendMessage failed ({r.status_code}): {r.text[:220]}")
        return False
    except Exception as e:
        print(f"[TG] Raw send error: {e}")
        return False


def post_to_facebook(caption: str, image_url: str = "", link_url: str = SITE_URL) -> bool:
    """Publishes an HD photo post to the connected Facebook Page and drops the portal link in a comment."""
    if not FB_PAGE_ID or not FB_PAGE_ACCESS_TOKEN:
        return False

    photo_target = image_url.strip() if is_usable_media_url(image_url) else FALLBACK_BANNERS["trending"]
    try:
        photo_resp = requests.post(
            f"https://graph.facebook.com/v21.0/{FB_PAGE_ID}/photos",
            data={
                "url": photo_target,
                "caption": caption[:2000],
                "access_token": FB_PAGE_ACCESS_TOKEN,
            },
            timeout=25,
        )
        data = photo_resp.json() if photo_resp.text else {}
        post_id = data.get("post_id") or data.get("id")
        if not photo_resp.ok or not post_id:
            print(f"[FB] Publish failed ({photo_resp.status_code}): {str(data)[:240]}")
            return False

        comment_resp = requests.post(
            f"https://graph.facebook.com/v21.0/{post_id}/comments",
            data={
                "message": f"Read full story & live feed: {link_url}",
                "access_token": FB_PAGE_ACCESS_TOKEN,
            },
            timeout=15,
        )
        if not comment_resp.ok:
            print(f"[FB] Link comment warning ({comment_resp.status_code}): {comment_resp.text[:180]}")

        print(f"[FB] Published post {post_id}")
        return True
    except Exception as e:
        print(f"[FB] Publish error: {e}")
        return False


# ==============================================================================
# 3. SMART COMBO FOOTBALL SLIP GENERATOR (SMALL + BIG ODDS) & EOD VERIFIER
# ==============================================================================
def american_to_decimal(ml) -> float:
    try:
        val = float(str(ml).replace("+", "").strip())
        if val > 0:
            return round(1.0 + (val / 100.0), 2)
        if val < 0:
            return round(1.0 + (100.0 / abs(val)), 2)
    except Exception:
        pass
    return 0.0


def fetch_espn_events_for_date(date_yyyymmdd: str) -> list[dict]:
    """Pulls fixtures, odds, and live/final scores across top soccer leagues."""
    events_out = []
    for league_code, league_name in SOCCER_LEAGUES:
        url = (
            f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_code}/scoreboard"
            f"?dates={date_yyyymmdd}"
        )
        try:
            resp = requests.get(url, headers=HEADERS_HTTP, timeout=10)
            if not resp.ok:
                continue
            data = resp.json()
            for ev in data.get("events", []):
                comp = (ev.get("competitions") or [{}])[0]
                competitors = comp.get("competitors") or []
                if len(competitors) < 2:
                    continue

                home = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
                away = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])

                home_name = home.get("team", {}).get("shortDisplayName") or home.get("team", {}).get("displayName", "Home")
                away_name = away.get("team", {}).get("shortDisplayName") or away.get("team", {}).get("displayName", "Away")

                status_obj = comp.get("status", {}).get("type", {})
                state = status_obj.get("state", "pre")
                completed = bool(status_obj.get("completed", False))

                try:
                    home_score = int(home.get("score", 0))
                    away_score = int(away.get("score", 0))
                except Exception:
                    home_score, away_score = 0, 0

                home_dec, away_dec, draw_dec = 0.0, 0.0, 0.0
                odds_list = comp.get("odds") or []
                if odds_list:
                    o0 = odds_list[0]
                    ml_home = (o0.get("homeTeamOdds") or {}).get("moneyLine")
                    ml_away = (o0.get("awayTeamOdds") or {}).get("moneyLine")
                    ml_draw = (o0.get("drawOdds") or {}).get("moneyLine")
                    home_dec = american_to_decimal(ml_home)
                    away_dec = american_to_decimal(ml_away)
                    draw_dec = american_to_decimal(ml_draw)

                kickoff_iso = ev.get("date", "")
                kickoff_wat = "Today"
                try:
                    dt_utc = datetime.fromisoformat(kickoff_iso.replace("Z", "+00:00"))
                    kickoff_wat = dt_utc.astimezone(WAT_TZ).strftime("%H:%M WAT")
                except Exception:
                    pass

                events_out.append({
                    "event_id": str(ev.get("id")),
                    "league_code": league_code,
                    "league": league_name,
                    "home": home_name,
                    "away": away_name,
                    "kickoff_wat": kickoff_wat,
                    "state": state,
                    "completed": completed,
                    "home_score": home_score,
                    "away_score": away_score,
                    "home_dec": home_dec,
                    "away_dec": away_dec,
                    "draw_dec": draw_dec,
                })
        except Exception as e:
            print(f"ESPN scoreboard skip ({league_code}): {e}")
    return events_out


def build_daily_slip_legs(events: list[dict], max_legs: int = 4) -> list[dict]:
    """Builds a balanced slip combining 2 Safe Banker small odds + 2 Big Value odds."""
    upcoming = [e for e in events if e["state"] == "pre"]
    if not upcoming:
        return []

    small_bankers = []
    big_boosters = []

    for ev in upcoming:
        h_odds = ev["home_dec"]
        a_odds = ev["away_dec"]

        if 1.25 <= h_odds <= 1.68:
            small_bankers.append((h_odds, {
                "event_id": ev["event_id"],
                "league_code": ev["league_code"],
                "league": ev["league"],
                "match": f"{ev['home']} vs {ev['away']}",
                "home": ev["home"],
                "away": ev["away"],
                "kickoff_wat": ev["kickoff_wat"],
                "tier": "SAFE BANKER",
                "pick_code": "HOME_WIN",
                "pick_label": f"{ev['home']} Win (1)",
                "odds": h_odds,
                "result": "pending",
                "final_score": "",
            }))
        elif 1.25 <= a_odds <= 1.68:
            small_bankers.append((a_odds, {
                "event_id": ev["event_id"],
                "league_code": ev["league_code"],
                "league": ev["league"],
                "match": f"{ev['home']} vs {ev['away']}",
                "home": ev["home"],
                "away": ev["away"],
                "kickoff_wat": ev["kickoff_wat"],
                "tier": "SAFE BANKER",
                "pick_code": "AWAY_WIN",
                "pick_label": f"{ev['away']} Win (2)",
                "odds": a_odds,
                "result": "pending",
                "final_score": "",
            }))
        elif 1.70 <= h_odds <= 2.15:
            dc_odd = round(max(1.24, h_odds * 0.68), 2)
            small_bankers.append((dc_odd, {
                "event_id": ev["event_id"],
                "league_code": ev["league_code"],
                "league": ev["league"],
                "match": f"{ev['home']} vs {ev['away']}",
                "home": ev["home"],
                "away": ev["away"],
                "kickoff_wat": ev["kickoff_wat"],
                "tier": "SAFE BANKER",
                "pick_code": "HOME_OR_DRAW",
                "pick_label": f"{ev['home']} Win or Draw (1X)",
                "odds": dc_odd,
                "result": "pending",
                "final_score": "",
            }))

        if 1.85 <= h_odds <= 3.10:
            big_boosters.append((h_odds, {
                "event_id": ev["event_id"],
                "league_code": ev["league_code"],
                "league": ev["league"],
                "match": f"{ev['home']} vs {ev['away']}",
                "home": ev["home"],
                "away": ev["away"],
                "kickoff_wat": ev["kickoff_wat"],
                "tier": "BIG VALUE",
                "pick_code": "HOME_WIN",
                "pick_label": f"{ev['home']} Straight Win (1)",
                "odds": h_odds,
                "result": "pending",
                "final_score": "",
            }))
        elif 1.95 <= a_odds <= 3.10:
            big_boosters.append((a_odds, {
                "event_id": ev["event_id"],
                "league_code": ev["league_code"],
                "league": ev["league"],
                "match": f"{ev['home']} vs {ev['away']}",
                "home": ev["home"],
                "away": ev["away"],
                "kickoff_wat": ev["kickoff_wat"],
                "tier": "BIG VALUE",
                "pick_code": "AWAY_WIN",
                "pick_label": f"{ev['away']} Straight Win (2)",
                "odds": a_odds,
                "result": "pending",
                "final_score": "",
            }))
        elif h_odds == 0.0 and a_odds == 0.0:
            small_bankers.append((1.30, {
                "event_id": ev["event_id"],
                "league_code": ev["league_code"],
                "league": ev["league"],
                "match": f"{ev['home']} vs {ev['away']}",
                "home": ev["home"],
                "away": ev["away"],
                "kickoff_wat": ev["kickoff_wat"],
                "tier": "SAFE BANKER",
                "pick_code": "OVER_1_5",
                "pick_label": "Over 1.5 Goals",
                "odds": 1.30,
                "result": "pending",
                "final_score": "",
            }))
            big_boosters.append((1.95, {
                "event_id": ev["event_id"],
                "league_code": ev["league_code"],
                "league": ev["league"],
                "match": f"{ev['home']} vs {ev['away']}",
                "home": ev["home"],
                "away": ev["away"],
                "kickoff_wat": ev["kickoff_wat"],
                "tier": "BIG VALUE",
                "pick_code": "OVER_2_5",
                "pick_label": "Over 2.5 Goals",
                "odds": 1.95,
                "result": "pending",
                "final_score": "",
            }))

    small_bankers.sort(key=lambda x: x[0])
    big_boosters.sort(key=lambda x: x[0], reverse=True)

    selected = []
    used_ids = set()

    for _, leg in small_bankers:
        if leg["event_id"] not in used_ids and len(selected) < 2:
            selected.append(leg)
            used_ids.add(leg["event_id"])

    for _, leg in big_boosters:
        if leg["event_id"] not in used_ids and len(selected) < max_legs:
            selected.append(leg)
            used_ids.add(leg["event_id"])

    for _, leg in small_bankers:
        if leg["event_id"] not in used_ids and len(selected) < max_legs:
            selected.append(leg)
            used_ids.add(leg["event_id"])

    return selected


def evaluate_leg_result(leg: dict, ev: dict) -> str:
    hs = ev["home_score"]
    as_ = ev["away_score"]
    total_goals = hs + as_
    code = leg.get("pick_code")

    if code == "HOME_WIN":
        return "won" if hs > as_ else "lost"
    if code == "AWAY_WIN":
        return "won" if as_ > hs else "lost"
    if code == "HOME_OR_DRAW":
        return "won" if hs >= as_ else "lost"
    if code == "AWAY_OR_DRAW":
        return "won" if as_ >= hs else "lost"
    if code == "OVER_1_5":
        return "won" if total_goals >= 2 else "lost"
    if code == "OVER_2_5":
        return "won" if total_goals >= 3 else "lost"
    if code == "GG":
        return "won" if (hs >= 1 and as_ >= 1) else "lost"
    return "lost"


def format_daily_slip_post(slip_date_str: str, legs: list[dict], total_odds: float, booking_code: str) -> str:
    lines = [
        f"⚽🔥 PULSEFEED SMART COMBO SLIP ({slip_date_str})",
        f"📊 Combined Odds: {total_odds:.2f}x (Safe Bankers + Big Value)",
    ]
    if booking_code:
        lines.append(f"🎟️ Booking Code: {booking_code}")
    lines.append("")

    for idx, leg in enumerate(legs, 1):
        tier_tag = "🛡️" if leg.get("tier") == "SAFE BANKER" else "🚀"
        lines.append(
            f"{idx}. {leg['match']} ({leg['league']})\n"
            f"   ⏰ {leg['kickoff_wat']} | {tier_tag} {leg['pick_label']} @ {leg['odds']:.2f}"
        )

    lines.extend([
        "",
        "🔁 End-of-day verified results drop tonight after full-time!",
        f"🌐 Live Scores & News: {SITE_URL}",
        f"💼 Remote Jobs & AI Tools: {JOBS_URL}",
        "⚠️ 18+ Only • Stake responsibly.",
    ])
    return "\n".join(lines)


def format_verified_slip_post(slip_date_str: str, legs: list[dict], total_odds: float, booking_code: str, won_count: int) -> str:
    all_won = won_count == len(legs)
    header = (
        f"🏆✅ BOOM! VERIFIED WINNING SLIP ({slip_date_str})"
        if all_won
        else f"📋✅ END-OF-DAY VERIFIED SLIP RECAP ({slip_date_str})"
    )
    lines = [
        header,
        f"📈 Slip Result: {won_count}/{len(legs)} Legs Won | Total Odds: {total_odds:.2f}x",
    ]
    if booking_code:
        lines.append(f"🎟️ Booking Code: {booking_code}")
    lines.append("")

    for idx, leg in enumerate(legs, 1):
        icon = "✅ WON" if leg.get("result") == "won" else "❌ LOST"
        score_txt = f" [{leg['final_score']}]" if leg.get("final_score") else ""
        lines.append(
            f"{idx}. {leg['match']}{score_txt}\n"
            f"   🎯 {leg['pick_label']} ({leg['odds']:.2f}) — {icon}"
        )

    lines.extend([
        "",
        "🔔 Turn on channel notifications so you don't miss tomorrow's slip!",
        f"🌐 Live Football & Breaking News: {SITE_URL}",
        f"🚀 ViralHook AI ($39+): {GUMROAD_OFFER_URL}",
    ])
    return "\n".join(lines)


def process_daily_betting_slips():
    """Publishes today's Smart Combo Slip once per day and verifies final scores at end of day (WAT)."""
    now_wat = datetime.now(WAT_TZ)
    today_iso = now_wat.strftime("%Y-%m-%d")
    today_compact = now_wat.strftime("%Y%m%d")

    existing_slip = None
    try:
        q = f"{SUPABASE_URL}/rest/v1/betting_slips?slip_date=eq.{today_iso}&limit=1"
        r = requests.get(q, headers=HEADERS_SB, timeout=12)
        if r.ok and r.json():
            existing_slip = r.json()[0]
    except Exception as e:
        print(f"betting_slips lookup skipped: {e}")

    if not existing_slip and now_wat.hour < 21:
        events = fetch_espn_events_for_date(today_compact)
        legs = build_daily_slip_legs(events, max_legs=4)
        if not legs:
            print("No upcoming soccer fixtures available for today's slip yet.")
            return

        total_odds = 1.0
        for leg in legs:
            total_odds *= float(leg["odds"])
        total_odds = round(total_odds, 2)

        caption = format_daily_slip_post(today_iso, legs, total_odds, DAILY_BOOKING_CODE)
        banner = FALLBACK_BANNERS["betting"]
        tg_ok = send_telegram_raw(caption, banner)
        fb_ok = post_to_facebook(caption, banner, SITE_URL)

        if tg_ok or fb_ok:
            try:
                requests.post(
                    f"{SUPABASE_URL}/rest/v1/betting_slips?on_conflict=slip_date",
                    headers={**HEADERS_SB, "Prefer": "resolution=merge-duplicates,return=minimal"},
                    json={
                        "slip_date": today_iso,
                        "title": f"PulseFeed Smart Combo Slip {today_iso}",
                        "booking_code": DAILY_BOOKING_CODE,
                        "total_odds": total_odds,
                        "legs": legs,
                        "status": "pending",
                    },
                    timeout=12,
                )
            except Exception as e:
                print(f"betting_slips save warning: {e}")
            print(f"Posted daily Smart Combo slip for {today_iso} (tg={tg_ok}, fb={fb_ok}).")
        return

    if existing_slip and existing_slip.get("status") == "pending" and now_wat.hour >= 21:
        legs = existing_slip.get("legs") or []
        if not legs:
            return

        events = fetch_espn_events_for_date(today_compact)
        ev_map = {e["event_id"]: e for e in events}

        completed_count = 0
        won_count = 0
        for leg in legs:
            ev = ev_map.get(str(leg.get("event_id")))
            if ev and ev.get("completed"):
                completed_count += 1
                leg["final_score"] = f"{ev['home_score']}-{ev['away_score']}"
                leg["result"] = evaluate_leg_result(leg, ev)
                if leg["result"] == "won":
                    won_count += 1

        if completed_count < len(legs) and now_wat.hour < 23:
            print(f"EOD verification waiting: {completed_count}/{len(legs)} matches finished.")
            return

        final_status = "won" if won_count == len(legs) else "settled"
        total_odds = float(existing_slip.get("total_odds") or 1.0)
        b_code = existing_slip.get("booking_code") or ""

        recap_caption = format_verified_slip_post(today_iso, legs, total_odds, b_code, won_count)
        banner = FALLBACK_BANNERS["betting"]
        tg_ok = send_telegram_raw(recap_caption, banner)
        fb_ok = post_to_facebook(recap_caption, banner, SITE_URL)

        if tg_ok or fb_ok:
            try:
                requests.patch(
                    f"{SUPABASE_URL}/rest/v1/betting_slips?slip_date=eq.{today_iso}",
                    headers={**HEADERS_SB, "Prefer": "return=minimal"},
                    json={
                        "legs": legs,
                        "status": final_status,
                        "verified_at": datetime.now(timezone.utc).isoformat(),
                    },
                    timeout=12,
                )
            except Exception as e:
                print(f"betting_slips EOD patch warning: {e}")
            print(f"Posted EOD verified slip recap ({won_count}/{len(legs)} won, tg={tg_ok}, fb={fb_ok}).")


# ==============================================================================
# 4. EXISTING NEWS & FOOTBALL RSS PIPELINE
# ==============================================================================
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
                if re.search(r"\.(mp4|webm)(\?|$)", href, re.I):
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
        print("[TG] Credentials not configured; skipping.")
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
                data={"chat_id": TELEGRAM_CHANNEL_ID, "video": media_url, "caption": caption[:1020]},
                timeout=20,
            )
            if r.ok:
                return True
            print(f"[TG] sendVideo failed ({r.status_code}): {r.text[:220]}")

        for candidate_url in (media_url, fallback_url):
            if candidate_url.startswith("https://") and len(caption) <= 1020:
                if _send_tg_photo_with_upload(base_tg, caption, candidate_url):
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
        if r.ok:
            return True
        print(f"[TG] sendMessage failed ({r.status_code}): {r.text[:200]}")
        return False
    except Exception as e:
        print(f"[TG] Send error: {e}")
        return False


def send_social_webhook(post: dict):
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
        caption = build_social_caption(post)
        best_img = pick_best_image_url(
            post.get("media_url") or "",
            post.get("media_type") or "image",
            post.get("feed_lane") or "trending",
            post.get("region") or "GLOBAL",
        )

        tg_ok = send_telegram_post(post)
        fb_ok = post_to_facebook(caption, best_img, SITE_URL)
        send_social_webhook(post)

        if tg_ok or fb_ok:
            patch_res = requests.patch(
                f"{SUPABASE_URL}/rest/v1/feed_posts?id=eq.{urllib.parse.quote(str(post_id))}",
                headers={**HEADERS_SB, "Prefer": "return=minimal"},
                json={"broadcasted_at": now_iso},
                timeout=15,
            )
            print(f"Broadcasted post {post_id} (tg={tg_ok}, fb={fb_ok}, patch={patch_res.status_code})")
        else:
            print(f"Skipped marking post {post_id} as broadcasted because no social destination succeeded.")


def maybe_post_promo_banner():
    """Publishes a dedicated visual promo card to Telegram & Facebook every 4 hours (WAT) or when forced."""
    now_wat = datetime.now(WAT_TZ)
    if not FORCE_PROMO_BANNER and (now_wat.hour % 4 != 0 or now_wat.minute >= 30):
        return

    promo_caption = (
        "🚀🔥 VIRALHOOK AI SCRIPT STUDIO — TURN IDEAS INTO VIRAL VIDEOS!\n\n"
        "Stop staring at a blank screen. Generate scroll-stopping hooks, Shorts/Reels scripts, "
        "and high-retention angles in seconds.\n\n"
        "✅ Instant AI Hooks & Viral Angles\n"
        "✅ Built for Faceless Creators, TikTok & YouTube Shorts\n"
        "✅ One-Time Access ($39+)\n\n"
        f"👉 Get Instant Access: {GUMROAD_OFFER_URL}\n"
        f"🌐 Live News & Scores: {SITE_URL}\n"
        f"💼 Remote Jobs & Offers: {JOBS_URL}"
    )

    tg_ok = send_telegram_raw(promo_caption, PROMO_BANNER_URL)
    fb_ok = post_to_facebook(promo_caption, PROMO_BANNER_URL, GUMROAD_OFFER_URL)
    print(f"[PROMO] Broadcasted visual promo banner (tg={tg_ok}, fb={fb_ok})")


def export_ai_discovery_files(limit: int = 30):
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

    feed_xml = f"""<?xml version="1.0" encoding="utf-8"?>
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
    process_daily_betting_slips()
    maybe_post_promo_banner()
    ingest_feeds(max_per_feed=2)
    broadcast_unposted(batch_limit=4)
    export_ai_discovery_files(limit=30)
