import json
import re
from datetime import datetime, timezone

from playwright.sync_api import sync_playwright

URL = "https://luna.amazon.com/claims/home"

KNOWN_TITLES = [
    "Between Time: Escape Room",
    "Sugardew Island",
    "Space Grunts 2",
    "Wargame Construction Set III: Age of Rifles 1846-1905",
    "G.I. JOE: Wrath of Cobra",
    "Tested on Humans: Escape Room",
    "Sin Slayers: Reign of The 8th",
    "Paradise Killer",
    "XCOM: Chimera Squad",
]

def clean(text):
    return re.sub(r"\s+", " ", text or "").strip()

items = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 1800})

    page.goto(URL, wait_until="networkidle", timeout=90000)
    page.wait_for_timeout(5000)

    images = page.evaluate("""
    () => [...document.images].map(img => ({
      src: img.src,
      alt: img.alt || "",
      text: img.closest("div")?.innerText || ""
    }))
    """)

    text = page.inner_text("body")

    for title in KNOWN_TITLES:
        if title not in text:
            continue

        image = ""
        for img in images:
            combined = (img.get("alt", "") + " " + img.get("text", "")).lower()
            if title.lower().split(":")[0] in combined:
                image = img.get("src", "")
                break

        items.append({
            "title": title,
            "platform": "Luna / Prime Gaming",
            "status": "claimable",
            "url": URL,
            "image": image,
            "source": "Amazon Luna"
        })

    browser.close()

output = {
    "updatedAt": datetime.now(timezone.utc).isoformat(),
    "count": len(items),
    "items": items,
}

with open("data/luna-games.json", "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"Saved {len(items)} Luna games")
