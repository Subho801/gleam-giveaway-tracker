import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html import unescape
from urllib.parse import quote

import requests

URL = "https://www.reddit.com/r/FreeGameFindings/new/.rss?limit=100"

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


def extract_gleam_link(text: str) -> str:
    match = re.search(r"https?://(?:www\.)?gleam\.io/[^\s\"'<)]+", text)
    return match.group(0) if match else ""


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


def get_steam_app(game_title: str):
    try:
        q = quote(game_title)
        url = f"https://store.steampowered.com/api/storesearch/?term={q}&l=english&cc=us"
        r = requests.get(url, headers=HEADERS, timeout=20)

        if r.status_code != 200:
            return None

        data = r.json()
        items = data.get("items", [])

        if not items:
            return None

        first = items[0]
        appid = first.get("id")

        if not appid:
            return None

        return {
            "appid": appid,
            "steamName": first.get("name", game_title),
            "steamUrl": f"https://store.steampowered.com/app/{appid}",
            "image": f"https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/{appid}/header.jpg",
        }

    except Exception:
        return None


res = requests.get(URL, headers=HEADERS, timeout=30)
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

    steam = get_steam_app(game_title)

    items.append(
        {
            "title": title,
            "gameTitle": game_title,
            "url": gleam_url,
            "redditUrl": reddit_url,
            "platform": "Steam" if "steam" in combined else "Game Key",
            "appid": steam.get("appid") if steam else None,
            "steamName": steam.get("steamName") if steam else "",
            "steamUrl": steam.get("steamUrl") if steam else "",
            "image": steam.get("image") if steam else "",
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
