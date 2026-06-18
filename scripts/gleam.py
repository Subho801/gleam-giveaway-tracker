import json
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html import unescape
from urllib.parse import quote

import requests

REDDIT_RSS_URL = "https://www.reddit.com/r/FreeGameFindings/new/.rss?limit=100"

STEAMGRIDDB_API_KEY = os.getenv("STEAMGRIDDB_API_KEY", "")
IGDB_CLIENT_ID = os.getenv("IGDB_CLIENT_ID", "")
IGDB_CLIENT_SECRET = os.getenv("IGDB_CLIENT_SECRET", "")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; SubhoGleamTracker/1.0)"
}

KEEP_WORDS = [
    "steam",
    "steam key",
    "steam keys",
    "game key",
    "game keys",
    "dlc",
    "(game)",
    "[steam]",
]

BLOCK_WORDS = [
    "gift card",
    "paypal",
    "amazon",
    "keyboard",
    "mouse",
    "headset",
    "monitor",
    "hardware",
    "robux",
    "v-bucks",
    "nitro",
    "uc gift",
    "pubg mobile",
]


def clean_text(text: str) -> str:
    return unescape(re.sub(r"\s+", " ", text or "")).strip()


def is_game_key(text: str) -> bool:
    t = text.lower()
    return any(w in t for w in KEEP_WORDS) and not any(w in t for w in BLOCK_WORDS)


def clean_game_title(title: str) -> str:
    title = re.sub(r"\[steam\]", "", title, flags=re.I)
    title = re.sub(r"\(game\)", "", title, flags=re.I)
    title = re.sub(r"\(steam\)", "", title, flags=re.I)
    title = re.sub(r"free\s*x?\d*\s*", "", title, flags=re.I)
    title = re.sub(r"steam\s*keys?", "", title, flags=re.I)
    title = re.sub(r"game\s*keys?", "", title, flags=re.I)
    title = re.sub(r"giveaway", "", title, flags=re.I)
    title = re.sub(r"[-–—|]+", " ", title)
    return clean_text(title)


def extract_gleam_link(text: str) -> str:
    match = re.search(r"https?://(?:www\.)?gleam\.io/[^\s\"'<)]+", text)
    return match.group(0) if match else ""


def get_steamgriddb_image(game_title: str) -> str:
    if not STEAMGRIDDB_API_KEY:
        return ""

    try:
        headers = {
            "Authorization": f"Bearer {STEAMGRIDDB_API_KEY}",
            "User-Agent": "SubhoGleamTracker/1.0",
        }

        search_url = (
            "https://www.steamgriddb.com/api/v2/search/autocomplete/"
            + quote(game_title)
        )

        search_res = requests.get(search_url, headers=headers, timeout=20)
        if search_res.status_code != 200:
            return ""

        games = search_res.json().get("data", [])
        if not games:
            return ""

        best = games[0]

        for game in games:
            name = game.get("name", "").lower()
            if game_title.lower() in name or name in game_title.lower():
                best = game
                break

        game_id = best.get("id")
        if not game_id:
            return ""

        endpoints = [
            f"https://www.steamgriddb.com/api/v2/heroes/game/{game_id}",
            f"https://www.steamgriddb.com/api/v2/grids/game/{game_id}?dimensions=920x430",
            f"https://www.steamgriddb.com/api/v2/grids/game/{game_id}",
        ]

        for endpoint in endpoints:
            r = requests.get(endpoint, headers=headers, timeout=20)
            if r.status_code != 200:
                continue

            results = r.json().get("data", [])
            if results:
                return results[0].get("url", "")

        return ""

    except Exception:
        return ""


def get_igdb_token() -> str:
    if not IGDB_CLIENT_ID or not IGDB_CLIENT_SECRET:
        return ""

    try:
        url = "https://id.twitch.tv/oauth2/token"
        params = {
            "client_id": IGDB_CLIENT_ID,
            "client_secret": IGDB_CLIENT_SECRET,
            "grant_type": "client_credentials",
        }

        res = requests.post(url, params=params, timeout=20)
        if res.status_code != 200:
            return ""

        return res.json().get("access_token", "")

    except Exception:
        return ""


def get_igdb_image(game_title: str, token: str) -> str:
    if not token:
        return ""

    try:
        headers = {
            "Client-ID": IGDB_CLIENT_ID,
            "Authorization": f"Bearer {token}",
        }

        query = f'''
            search "{game_title}";
            fields name,cover.image_id,screenshots.image_id,artworks.image_id;
            limit 5;
        '''

        res = requests.post(
            "https://api.igdb.com/v4/games",
            headers=headers,
            data=query,
            timeout=20,
        )

        if res.status_code != 200:
            return ""

        games = res.json()
        if not games:
            return ""

        best = games[0]

        image_id = ""

        if best.get("artworks"):
            image_id = best["artworks"][0].get("image_id", "")
            if image_id:
                return f"https://images.igdb.com/igdb/image/upload/t_screenshot_big/{image_id}.jpg"

        if best.get("screenshots"):
            image_id = best["screenshots"][0].get("image_id", "")
            if image_id:
                return f"https://images.igdb.com/igdb/image/upload/t_screenshot_big/{image_id}.jpg"

        if best.get("cover"):
            image_id = best["cover"].get("image_id", "")
            if image_id:
                return f"https://images.igdb.com/igdb/image/upload/t_cover_big/{image_id}.jpg"

        return ""

    except Exception:
        return ""


igdb_token = get_igdb_token()

res = requests.get(REDDIT_RSS_URL, headers=HEADERS, timeout=30)
res.raise_for_status()

root = ET.fromstring(res.text)
ns = {"atom": "http://www.w3.org/2005/Atom"}

items = []

for entry in root.findall("atom:entry", ns):
    title = clean_text(entry.findtext("atom:title", default="", namespaces=ns))
    content = entry.findtext("atom:content", default="", namespaces=ns)

    link_el = entry.find("atom:link", ns)
    reddit_url = link_el.attrib.get("href", "") if link_el is not None else ""

    clean_content = clean_text(content)
    combined = f"{title} {clean_content}".lower()

    if "gleam.io" not in combined:
        continue

    if not is_game_key(combined):
        continue

    gleam_url = extract_gleam_link(content) or reddit_url
    game_title = clean_game_title(title)

    image = get_steamgriddb_image(game_title) or get_igdb_image(game_title, igdb_token)

    items.append(
        {
            "title": title,
            "gameTitle": game_title,
            "url": gleam_url,
            "redditUrl": reddit_url,
            "platform": "Steam" if "steam" in combined else "Game Key",
            "image": image,
            "source": "r/FreeGameFindings",
        }
    )

output = {
    "updatedAt": datetime.now(timezone.utc).isoformat(),
    "count": len(items),
    "items": items,
}

with open("data/gleam-giveaways.json", "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"Saved {len(items)} Gleam game key giveaways")
