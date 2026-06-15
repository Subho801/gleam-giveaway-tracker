import json
import requests
from datetime import datetime, timezone

URL = "https://www.reddit.com/r/FreeGameFindings/new.json?limit=50"

HEADERS = {
    "User-Agent": "Subho-GleamTracker/1.0"
}

KEYWORDS = [
    "steam key",
    "steam keys",
    "gleam.io",
    "gleam",
    "free steam keys",
    "steam giveaway",
]

response = requests.get(URL, headers=HEADERS, timeout=30)
response.raise_for_status()

posts = response.json()["data"]["children"]

items = []

for post in posts:
    data = post["data"]

    title = data.get("title", "")
    url = data.get("url", "")

    combined = f"{title} {url}".lower()

    if not any(keyword in combined for keyword in KEYWORDS):
        continue

    items.append(
        {
            "title": title,
            "url": url,
            "created": data.get("created_utc"),
            "thumbnail": data.get("thumbnail"),
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
