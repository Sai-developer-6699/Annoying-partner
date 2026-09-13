"""
download_meme_arsenal.py
-------------------------
Downloads curated hilarious meme audio clips from Myinstants into assets/audio/,
categorizes them into semantic buckets, and generates data/meme_audios.json
so Phi-3 / AI prompts and the desktop companion can trigger the exact right meme.
"""

import json
import os
import re
import time
from pathlib import Path
from urllib.parse import quote, urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.myinstants.com"
SEARCH_URL = BASE_URL + "/en/search/?name={query}"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

PROJECT_ROOT = Path(__file__).resolve().parent.parent
AUDIO_DIR = PROJECT_ROOT / "assets" / "audio"
MEME_AUDIOS_JSON = PROJECT_ROOT / "data" / "meme_audios.json"
MEMES_TEMPLATE_JSON = PROJECT_ROOT / "data" / "memes_template.json"

# Curated catalog mapping: ID -> Search Query, Category, Trigger, Tags, Default Caption
CATALOG = [
    {
        "id": "bruh",
        "search_query": "bruh",
        "category": "timer_expired",
        "trigger": "timer_expired",
        "intensity": "mild",
        "tags": ["disbelief", "slacking", "tired", "deadline"],
        "caption": "Bruh... 15 seconds and not a single compliment?",
    },
    {
        "id": "emotional_damage",
        "search_query": "emotional damage",
        "category": "persuasion_fail",
        "trigger": "persuasion_fail",
        "intensity": "savage",
        "tags": ["burn", "rejection", "roast", "tribunal"],
        "caption": "Emotional Damage! That excuse was atrocious.",
    },
    {
        "id": "fbi_open_up",
        "search_query": "fbi open up",
        "category": "unauthorized_app",
        "trigger": "unauthorized_app",
        "intensity": "savage",
        "tags": ["caught", "gaming", "youtube", "distraction"],
        "caption": "FBI OPEN UP! Caught slacking on unauthorized apps!",
    },
    {
        "id": "metal_pipe",
        "search_query": "metal pipe",
        "category": "timer_expired",
        "trigger": "timer_expired",
        "intensity": "savage",
        "tags": ["loud", "shock", "deadline", "crash"],
        "caption": "CLANG! Your time has completely run out!",
    },
    {
        "id": "windows_error",
        "search_query": "windows error",
        "category": "compliment_rejected",
        "trigger": "compliment_rejected",
        "intensity": "mild",
        "tags": ["error", "spam", "syntax", "fail"],
        "caption": "Fatal Error 404: Quality compliment not found.",
    },
    {
        "id": "sad_violin",
        "search_query": "sad violin",
        "category": "persuasion_fail",
        "trigger": "persuasion_fail",
        "intensity": "mild",
        "tags": ["sad", "crying", "begging", "excuse"],
        "caption": "Playing the world's smallest violin for your excuse.",
    },
    {
        "id": "directed_by_robert_b_weide",
        "search_query": "directed by robert b weide",
        "category": "persuasion_fail",
        "trigger": "persuasion_fail",
        "intensity": "savage",
        "tags": ["curb", "clown", "fail", "joke"],
        "caption": "Directed by Robert B. Weide. Nice try though.",
    },
    {
        "id": "bonk",
        "search_query": "bonk",
        "category": "compliment_rejected",
        "trigger": "compliment_rejected",
        "intensity": "mild",
        "tags": ["bonk", "doge", "paste", "spam"],
        "caption": "BONK! Go to slacker detention!",
    },
    {
        "id": "giga_chad",
        "search_query": "giga chad",
        "category": "compliment_accepted",
        "trigger": "compliment_accepted",
        "intensity": "savage",
        "tags": ["chad", "victory", "supremacy", "ego"],
        "caption": "Indeed. My digital intellect is supreme.",
    },
    {
        "id": "wasted",
        "search_query": "wasted",
        "category": "persuasion_fail",
        "trigger": "persuasion_fail",
        "intensity": "savage",
        "tags": ["gta", "death", "gameover", "detention"],
        "caption": "WASTED. Compulsory mouse lockdown initiated.",
    },
    {
        "id": "thunder",
        "search_query": "thunder",
        "category": "thunderstrike",
        "trigger": "thunderstrike",
        "intensity": "savage",
        "tags": ["lightning", "furious", "apocalypse", "minimize"],
        "caption": "FEEL THE WRATH OF EGO-BOT 3000!",
    },
    {
        "id": "salim_kumar",
        "search_query": "salim kumar",
        "category": "unauthorized_app",
        "trigger": "unauthorized_app",
        "intensity": "mild",
        "tags": ["malayalam", "comedy", "caught", "roast"],
        "caption": "Enthokke aayirunnu? Velicham kanda thudangiyathano?",
    },
    {
        "id": "suraj_dhamu",
        "search_query": "suraj",
        "category": "persuasion_fail",
        "trigger": "persuasion_fail",
        "intensity": "savage",
        "tags": ["malayalam", "suraj", "damu", "excuse"],
        "caption": "Dhamu angane paranjooda! Excuse reject cheythu!",
    },
    {
        "id": "jagathy_comedy",
        "search_query": "jagathy comedy",
        "category": "unauthorized_app",
        "trigger": "unauthorized_app",
        "intensity": "mild",
        "tags": ["malayalam", "jagathy", "scolding", "laugh"],
        "caption": "Yashodaa! Ivaan ithu vare work thudangiyille?",
    },
    {
        "id": "run_vine",
        "search_query": "run meme",
        "category": "timer_expired",
        "trigger": "timer_expired",
        "intensity": "savage",
        "tags": ["run", "panic", "escape", "timer"],
        "caption": "RUN! You failed to submit a compliment in time!",
    },
    {
        "id": "aughhh",
        "search_query": "aughhh",
        "category": "compliment_rejected",
        "trigger": "compliment_rejected",
        "intensity": "savage",
        "tags": ["disgust", "pain", "terrible", "grammar"],
        "caption": "AUGHHHHH! That compliment caused me physical pain.",
    },
    {
        "id": "nope_tf2",
        "search_query": "nope tf2",
        "category": "persuasion_fail",
        "trigger": "persuasion_fail",
        "intensity": "mild",
        "tags": ["nope", "deny", "engineer", "rejection"],
        "caption": "NOPE. Request to resume computer use denied.",
    },
    {
        "id": "applause",
        "search_query": "applause",
        "category": "persuasion_pass",
        "trigger": "persuasion_pass",
        "intensity": "mild",
        "tags": ["applause", "cheering", "mercy", "approved"],
        "caption": "The tribunal applauds your honesty. You may pass.",
    },
    {
        "id": "victory_fanfare",
        "search_query": "victory fanfare",
        "category": "compliment_accepted",
        "trigger": "compliment_accepted",
        "intensity": "savage",
        "tags": ["victory", "final_fantasy", "level_up", "praise"],
        "caption": "Victory! Ego boosted by 10,000 points.",
    },
    {
        "id": "oof",
        "search_query": "oof sound",
        "category": "compliment_rejected",
        "trigger": "compliment_rejected",
        "intensity": "mild",
        "tags": ["roblox", "oof", "repeat", "failed"],
        "caption": "OOF! Duplicate compliment detected.",
    },
    {
        "id": "rick_roll",
        "search_query": "rick roll",
        "category": "persuasion_fail",
        "trigger": "persuasion_fail",
        "intensity": "savage",
        "tags": ["rickroll", "troll", "music", "punishment"],
        "caption": "Never gonna give you computer access back!",
    }
]


def search_and_download_item(item: dict) -> dict | None:
    query = item["search_query"]
    url = SEARCH_URL.format(query=quote(query))
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        first = soup.select_one(".instant")
        if not first:
            return None

        button = first.find("button")
        link = first.find("a", class_="instant-link")
        if not button:
            return None

        match = re.search(r"play\('([^']+)'", button.get("onclick", ""))
        if not match:
            return None

        mp3_path = match.group(1)
        mp3_url = urljoin(BASE_URL, mp3_path)
        title = link.get_text(strip=True) if link else item["id"]

        filename = f"{item['id']}.mp3"
        dest_path = AUDIO_DIR / filename
        AUDIO_DIR.mkdir(parents=True, exist_ok=True)

        # Download mp3
        dl_resp = requests.get(mp3_url, headers=HEADERS, timeout=20)
        dl_resp.raise_for_status()
        dest_path.write_bytes(dl_resp.content)

        return {
            "id": item["id"],
            "title": title,
            "category": item["category"],
            "trigger": item["trigger"],
            "intensity": item["intensity"],
            "tags": item["tags"],
            "caption": item["caption"],
            "audio_file": f"assets/audio/{filename}",
            "file_size": len(dl_resp.content)
        }
    except Exception as exc:
        print(f"  ! Error downloading {item['id']} ({query}): {exc}")
        return None


def main():
    print(f"=== DOWNLOADING MEME ARSENAL INTO {AUDIO_DIR} ===")
    results = []

    for item in CATALOG:
        dest = AUDIO_DIR / f"{item['id']}.mp3"
        if dest.exists() and dest.stat().st_size > 1000:
            print(f"[EXISTS] {item['id']} ({dest.stat().st_size} bytes)")
            results.append({
                "id": item["id"],
                "title": item["id"].replace("_", " ").title(),
                "category": item["category"],
                "trigger": item["trigger"],
                "intensity": item["intensity"],
                "tags": item["tags"],
                "caption": item["caption"],
                "audio_file": f"assets/audio/{item['id']}.mp3",
                "file_size": dest.stat().st_size
            })
            continue

        print(f"[DOWNLOADING] {item['id']} (query: '{item['search_query']}')...")
        res = search_and_download_item(item)
        if res:
            print(f"  -> Saved {res['title']} ({res['file_size']} bytes) as {res['audio_file']}")
            results.append(res)
        else:
            print(f"  -> Failed to scrape {item['id']}")
        time.sleep(1.2)

    # Save to data/meme_audios.json
    MEME_AUDIOS_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(MEME_AUDIOS_JSON, "w", encoding="utf-8") as f:
        json.dump({"memes": results}, f, indent=2, ensure_ascii=False)
    print(f"\n[DONE] Saved {len(results)} categorized meme audios to {MEME_AUDIOS_JSON}")


if __name__ == "__main__":
    main()
