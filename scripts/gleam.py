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
    return any(w in t for w in KEEP_WORDS) and not any(
        w in t for w in BLOCK_WORDS
    )


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


def get_steamgriddb_banner(game_title: str) -> str:
    if not STEAMGRIDDB_API_KEY:
        return ""

    try:
        search_url = (
            "https://www.steamgriddb.com/api/v2/search/autocomplete/"
            + quote(game_title)
        )

        headers = {
            "Authorization": f"Bearer {STEAMGRIDDB_API_KEY}",
            "User-Agent": "SubhoGleamTracker/1.0",
        }

        search_res = requests.get(search_url, headers=headers, timeout=20)
        if search_res.status_code != 200:
            return ""

        search_data = search_res.json()
        games = search_data.get("data", [])

        if not games:
            return ""

        game_id = games[0].get("id")
        if not game_id:
            return ""

        heroes_url = f"https://www.steamgriddb.com/api/v2/heroes/game/{game_id}"
        heroes_res = requests.get(heroes_url, headers=headers, timeout=20)

        if heroes_res.status_code == 200:
            heroes_data = heroes_res.json()
            heroes = heroes_data.get("data", [])

            if heroes:
                return heroes[0].get("url", "")

        grids_url = f"https://www.steamgriddb.com/api/v2/grids/game/{game_id}?dimensions=920x430"
        grids_res = requests.get(grids_url, headers=headers, timeout=20)

        if grids_res.status_code == 200:
            grids_data = grids_res.json()
            grids = grids_data.get("data", [])

            if grids:
                return grids[0].get("url", "")

        return ""

    except Exception:
        return ""


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
    image = get_steamgriddb_banner(game_title)

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
