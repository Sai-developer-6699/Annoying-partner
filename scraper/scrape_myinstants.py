"""
scrape_myinstants.py
---------------------
Personal-use scraper for myinstants.com.

For every scenario/option in data/memes_template.json that still has
audio_file == null, this script:
  1. Searches myinstants.com/en/search/?name=<search_query>
  2. Grabs the first result's mp3 URL + on-page caption/title
  3. Downloads the mp3 into assets/audio/<scenario_id>_<intensity>.mp3
  4. Writes the real filename + caption back into the JSON

IMPORTANT / READ BEFORE RUNNING
--------------------------------
- This is for a personal desktop toy you're building for yourself, not for
  redistributing scraped audio. Don't upload the downloaded clips to a repo
  or ship them inside an installer you distribute publicly — Myinstants'
  clips are uploaded audio of copyrighted movie dialogue/soundtrack, and
  scraping your own local copy for personal use is a very different thing
  from redistributing that copyrighted audio to other people.
- Keep requests slow (SLEEP_SECONDS below) and run this once, not in a loop
  inside the main app. Don't hit the site from inside your Tkinter app at
  runtime — scrape once, offline, then only ever read local files at runtime.
- Myinstants' HTML structure can change. If SELECTORS below stop matching,
  right-click a search results page -> Inspect, and update the regex/CSS
  selectors accordingly. This sandbox has no network path to myinstants.com,
  so this script is written to be correct against the site's known
  structure but hasn't been executed here — run and sanity-check it on your
  own machine first.
- This machine (Claude's tool sandbox) cannot reach myinstants.com, so this
  file could not be test-run here. Run it locally and adjust selectors if
  the site's markup has changed.
"""

import json
import re
import time
import unicodedata
from pathlib import Path
from urllib.parse import quote, urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.myinstants.com"
SEARCH_URL = BASE_URL + "/en/search/?name={query}"
HEADERS = {
    # A normal browser UA is polite and avoids being blocked as a bare script.
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}
SLEEP_SECONDS = 2.0  # be polite; don't hammer the site

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MEMES_JSON = PROJECT_ROOT / "data" / "memes_template.json"
AUDIO_DIR = PROJECT_ROOT / "assets" / "audio"


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "_", text)


def search_first_result(query: str) -> dict | None:
    """Search Myinstants and return {'title': str, 'mp3_url': str} for the
    first hit, or None if nothing was found."""
    url = SEARCH_URL.format(query=quote(query))
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # Each result button looks like:
    # <div class="instant" ...>
    #   <button onclick="play('/media/sounds/xyz.mp3')" ...></button>
    #   <a class="instant-link" href="/en/instant/xyz/">Some Title</a>
    # </div>
    container = soup.find("div", class_="instant") or soup.select_one(".instants-grid .instant")
    if container is None:
        return None

    button = container.find("button", onclick=True)
    link = container.find("a", class_="instant-link") or container.find("a")

    if button is None or link is None:
        return None

    match = re.search(r"play\(['\"]([^'\"]+)['\"]", button["onclick"])
    if not match:
        return None

    mp3_path = match.group(1)
    mp3_url = urljoin(BASE_URL, mp3_path)
    title = link.get_text(strip=True)

    return {"title": title, "mp3_url": mp3_url}


def download_mp3(mp3_url: str, dest_path: Path) -> None:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    resp = requests.get(mp3_url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    dest_path.write_bytes(resp.content)


def main() -> None:
    data = json.loads(MEMES_JSON.read_text(encoding="utf-8"))

    for scenario in data["scenarios"]:
        query = scenario["search_query"]
        for option in scenario["options"]:
            if option.get("audio_file"):
                continue  # already filled in from a previous run

            print(f"[searching] {scenario['id']} / {option['intensity']} -> '{query}'")
            try:
                result = search_first_result(query)
            except requests.RequestException as exc:
                print(f"  ! request failed: {exc}")
                continue

            if result is None:
                print("  ! no result found, leaving as null (edit search_query and retry)")
                continue

            filename = f"{scenario['id']}_{option['intensity']}.mp3"
            dest = AUDIO_DIR / filename
            try:
                download_mp3(result["mp3_url"], dest)
            except requests.RequestException as exc:
                print(f"  ! download failed: {exc}")
                continue

            option["audio_file"] = f"assets/audio/{filename}"
            option["caption"] = result["title"]
            print(f"  -> saved '{result['title']}' as {filename}")

            time.sleep(SLEEP_SECONDS)

    MEMES_JSON.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nUpdated {MEMES_JSON}")


if __name__ == "__main__":
    main()
