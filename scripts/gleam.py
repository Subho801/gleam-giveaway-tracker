import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html import unescape

import requests

URL = "https://www.reddit.com/r/FreeGameFindings/new/.rss?limit=50"

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


def is_game_key(title: str) -> bool:
    t = title.lower()
    return any(w in t for w in KEEP_WORDS) and not any(w in t for w in BLOCK_WORDS)


def clean_text(text: str) -> str:
    return unescape(re.sub(r"\s+", " ", text or "")).strip()


res = requests.get(URL, headers=HEADERS, timeout=30)
res.raise_for_status()

root = ET.fromstring(res.text)
ns = {"atom": "http://www.w3.org/2005/Atom"}

items = []

for entry in root.findall("atom:entry", ns):
    title = clean_text(entry.findtext("atom:title", default="", namespaces=ns))
    link_el = entry.find("atom:link", ns)
    url = link_el.attrib.get("href", "") if link_el is not None else ""

    if not is_game_key(title):
        continue

    items.append(
        {
            "title": title,
            "url": url,
            "platform": "Steam" if "steam" in title.lower() else "Game Key",
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

print(f"Saved {len(items)} giveaways")
