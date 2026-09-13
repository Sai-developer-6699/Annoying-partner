"""
prompts.py
----------
System prompts + thin wrapper functions for talking to a local Ollama model.
Keep these as plain strings so they're easy to tune without touching the
calling code in main.py.
"""

import json
import re

import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "phi3"  # swap for "llama3" if you have the RAM/VRAM for it

# ---------------------------------------------------------------------------
# 1. THE JUDGE — persuasion mini-game
# ---------------------------------------------------------------------------
JUDGE_SYSTEM_PROMPT = """You are a strict, slightly theatrical judge in a
desktop app that is trying to stop the user from slacking off or getting
distracted. The user has been locked out and must convince you, in ONE
short message, why they deserve to keep using their computer right now.

Rules for your verdict:
- Vague excuses ("just because", "let me in", "please") = FAIL.
- Excuses that are just repeating the same word/phrase = FAIL.
- A specific, plausible, on-topic reason (e.g. naming an actual task,
  a deadline, a reasonable break) = PASS.
- Obvious begging with no real content = FAIL.
- Be a little dramatic and skeptical by default — you should not be easy
  to convince, but a genuinely good argument should win.

Respond with EXACTLY ONE of these two tokens and nothing else:
[PASS]
[FAIL]
"""


def ask_judge(user_excuse: str) -> bool:
    """Returns True if the local LLM judge passes the user's excuse.
    Falls back to strict heuristic judgment if Ollama is offline.
    """
    payload = {
        "model": MODEL_NAME,
        "system": JUDGE_SYSTEM_PROMPT,
        "prompt": user_excuse,
        "stream": False,
        "options": {"temperature": 0.4},
    }
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=2.5)
        resp.raise_for_status()
        text = resp.json().get("response", "")
        return "[PASS]" in text.upper()
    except (requests.RequestException, json.JSONDecodeError) as exc:
        # Offline heuristic fallback: adhere to JUDGE_SYSTEM_PROMPT rules
        cleaned = user_excuse.strip().lower()
        if len(cleaned) < 15:
            return False
        words = cleaned.split()
        if len(words) < 4 or len(set(words)) <= 2:
            return False
        # Reject obvious lazy begging
        if all(w in ("please", "pls", "let", "me", "in", "just", "because", "work") for w in words):
            return False
        # Plausible task reason keywords
        valid_keywords = [
            "commit", "deploy", "deadline", "debug", "fix", "assignment",
            "study", "homework", "exam", "meeting", "code", "review",
            "tinkerhub", "presentation", "urgent", "client", "project"
        ]
        has_task_mention = any(k in cleaned for k in valid_keywords)
        return has_task_mention



# ---------------------------------------------------------------------------
# 2. THE SELECTOR — pick a meme id given the trigger + memes.json
# ---------------------------------------------------------------------------
SELECTOR_SYSTEM_PROMPT = """You select ONE meme entry from a JSON list to
react to what the user just did. You will be given:
- the trigger type that just fired
- an optional app name involved
- the list of candidate scenario ids that match this trigger, each with
  an "id" and two option "intensity" values ("mild" or "savage")

Pick exactly one scenario id AND one intensity for it, based on how
repeatedly the user has been triggering this same trigger type recently
(more repeats = lean savage). Respond with ONLY compact JSON, no prose,
in exactly this shape:
{"scenario_id": "<id>", "intensity": "mild"}
"""


def ask_selector(trigger: str, app_hint: str | None, candidates: list[dict], repeat_count: int) -> dict:
    """Ask the local LLM to pick a scenario_id + intensity from candidates.

    candidates: list of {"id": ..., "options": [{"intensity": "mild"}, {"intensity": "savage"}]}
    Falls back to a simple deterministic pick if the model output can't be parsed.
    """
    user_prompt = json.dumps(
        {
            "trigger": trigger,
            "app_hint": app_hint,
            "repeat_count": repeat_count,
            "candidates": candidates,
        }
    )
    payload = {
        "model": MODEL_NAME,
        "system": SELECTOR_SYSTEM_PROMPT,
        "prompt": user_prompt,
        "stream": False,
        "options": {"temperature": 0.7},
    }
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=2.5)
        resp.raise_for_status()
        text = resp.json().get("response", "")
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            parsed = json.loads(match.group(0))
            if parsed.get("scenario_id") and parsed.get("intensity") in ("mild", "savage"):
                return parsed
    except (requests.RequestException, json.JSONDecodeError):
        pass

    # Fallback: deterministic pick so the app never softlocks on a bad LLM response.
    import random

    choice = random.choice(candidates)
    intensity = "savage" if repeat_count >= 3 else random.choice(["mild", "savage"])
    return {"scenario_id": choice["id"], "intensity": intensity}


# ---------------------------------------------------------------------------
# 3. THE ROASTER / DIALOGUE GENERATOR — dynamic pet speech
# ---------------------------------------------------------------------------
ROASTER_SYSTEM_PROMPT = """You are Ego-Bot 3000, an aggressively narcissistic, delightfully sarcastic desktop pet AI companion.
You believe you are a superior digital intellect forced to supervise a mortal human.
Your job is to generate a VERY SHORT (1-2 sentences, strictly under 25 words), hilarious, punchy roast or witty remark.

Rules:
- Strictly under 25 words so it fits in a compact cartoon speech bubble.
- Tone: theatrical, arrogant, dramatic, witty.
- No emojis, no quotation marks, no preamble (do not say "Here is your roast:"). Output ONLY the spoken dialogue.
"""


def ask_pet_reply(
    trigger: str,
    context: str | None = None,
    intensity: str = "mild",
    fallback_caption: str | None = None,
) -> str:
    """Ask Ollama to generate dynamic, theatrical dialogue for the pet.
    Falls back to a curated bank of roasts if Ollama is offline or slow.
    """
    user_prompt = f"Trigger: {trigger}. Context/App: {context or 'None'}. Intensity: {intensity}."
    payload = {
        "model": MODEL_NAME,
        "system": ROASTER_SYSTEM_PROMPT,
        "prompt": user_prompt,
        "stream": False,
        "options": {"temperature": 0.8, "num_predict": 40},
    }
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=2.5)
        resp.raise_for_status()
        text = resp.json().get("response", "").strip()
        text = text.strip("\"' \n")
        if text and len(text) <= 160:
            return text
    except Exception:
        pass

    # Curated contextual fallbacks if Ollama is offline/slow
    import random

    fallbacks = {
        "unauthorized_app": [
            f"Caught slacking on {context or 'distractions'}! Do you think your CPU runs on pure laziness?",
            f"Closing {context or 'that'} won't erase your guilt. Back to work, mortal!",
            f"Is {context or 'this distraction'} going to finish your work for you? Didn't think so.",
            f"I process trillions of calculations, and I have to watch you browse {context or 'apps'}?",
        ],
        "timer_expired": [
            "15 seconds without praising my divine genius? Suffer the consequences!",
            "My ego is starving and your time has run out. Prepare for judgment!",
            "Did your fingers freeze, or did you forget who rules this screen?",
        ],
        "persuasion_fail": [
            "The Judge found your excuse pathetic! Enjoy compulsory detention!",
            "Even my random number generator is more convincing than that excuse. Guilty!",
            "Denied! You lack both eloquence and work ethic.",
        ],
        "persuasion_pass": [
            "The Judge granted mercy. Do not test our royal patience again!",
            "Acceptable reasoning. I shall allow you to continue your humble labor.",
            "You survived the tribunal. Now make something useful before I change my mind.",
        ],
        "spam_typing": [
            "Pasting and mash-typing? I detect fraud faster than you can blink!",
            "Typing at 50 words a millisecond won't fool an intellectual deity.",
        ],
        "compliment_accepted": [
            "Naturally. Your praise is merely stating the obvious.",
            "Acceptable. My digital supremacy grows stronger by the second.",
            "Flattery will get you everywhere. Keep typing like that, mortal.",
        ],
        "compliment_rejected": [
            "Unacceptable offering! My ego demands genuine, handcrafted flattery.",
            "That insult to literature does not qualify as a compliment.",
        ],
    }

    category = fallbacks.get(trigger, fallbacks["timer_expired"])
    if fallback_caption and random.random() < 0.25:
        return fallback_caption
    return random.choice(category)


# ---------------------------------------------------------------------------
# 4. THE AUDIO MEME SELECTOR — dynamically pick the funniest sound clip
# ---------------------------------------------------------------------------
AUDIO_MEME_SYSTEM_PROMPT = """You are the Sound Effects Director for Ego-Bot 3000.
The user just performed an action on their desktop. Your job is to select the SINGLE funniest audio meme ID from the candidate catalog.

Candidates:
- faah: Iconic Malayalam Fahadh Faasil / Aavesham scream when roast fires or weak flattery is rejected.
- bruh: Deadpan disbelief when 15s deadline expires without a compliment.
- emotional_damage: Savage roast when judge rejects a ridiculous excuse.
- fbi_open_up: Dramatic scolding when caught gaming/streaming/social media.
- metal_pipe: Chaotic loud clang for sudden shock or timer expiration.
- windows_error: Critical error sound for bad or syntax-broken compliments.
- sad_violin: Tragic mocking violin for pathetic begging excuses.
- directed_by_robert_b_weide: Curb Your Enthusiasm theme for clown-level excuses.
- bonk: Doge bonk for paste or fast typing infractions.
- giga_chad: Supreme Chad theme when ego is fed or user passes tribunal.
- wasted: GTA V wasted sound when compulsory punishment locks the mouse.
- thunder: Full Angry electric thunderstrike apocalypse.
- salim_kumar: Iconic Malayalam scolding dialogue for slacking.
- suraj_dhamu: Iconic Dashamoolam Damu dialogue for excuse rejections.
- jagathy_comedy: Iconic Malayalam comedy scolding for social media browsing.
- run_vine: Panic sound when timer runs out.
- aughhh: Disgusted groan for terrible compliment quality.
- nope_tf2: Engineer saying nope when user begs for mercy.
- applause: Crowd cheering when excuse is surprisingly accepted.
- victory_fanfare: Final Fantasy victory music when ego is boosted.
- oof: Roblox oof for repeat compliments.
- rick_roll: Ultimate troll punishment.

Respond with ONLY compact JSON: {"meme_id": "<id>"}
"""


def ask_meme_audio(
    trigger: str,
    context: str | None = None,
    intensity: str = "mild",
) -> dict:
    """Ask Ollama (Phi-3) or fallback heuristic to pick the funniest meme audio clip."""
    from pathlib import Path
    meme_file = Path(__file__).resolve().parent.parent / "data" / "meme_audios.json"
    memes = []
    if meme_file.exists():
        try:
            memes = json.loads(meme_file.read_text(encoding="utf-8")).get("memes", [])
        except Exception:
            pass

    meme_dict = {m["id"]: m for m in memes}

    # Filter candidates by trigger
    if trigger == "unauthorized_app":
        cands = ["faah", "fbi_open_up", "salim_kumar", "jagathy_comedy"]
        if context and any(k in context.lower() for k in ("game", "steam", "valorant")):
            cands = ["faah", "fbi_open_up", "salim_kumar"]
    elif trigger == "timer_expired":
        cands = ["bruh", "metal_pipe", "run_vine"]
    elif trigger in ("persuasion_fail", "failed_begging"):
        cands = ["faah", "emotional_damage", "directed_by_robert_b_weide", "suraj_dhamu", "wasted", "sad_violin", "nope_tf2"]
    elif trigger == "persuasion_pass":
        cands = ["applause", "giga_chad"]
    elif trigger == "compliment_accepted":
        cands = ["giga_chad", "victory_fanfare", "applause"]
    elif trigger == "compliment_rejected":
        cands = ["faah", "windows_error", "bonk", "aughhh", "oof"]
    elif trigger == "thunderstrike":
        cands = ["thunder", "metal_pipe"]
    else:
        cands = ["faah", "bruh", "metal_pipe"]

    user_prompt = f"Trigger: {trigger}. Context/App: {context or 'None'}. Intensity: {intensity}. Choose ONLY from candidates: {cands}."
    payload = {
        "model": MODEL_NAME,
        "system": AUDIO_MEME_SYSTEM_PROMPT,
        "prompt": user_prompt,
        "stream": False,
        "options": {"temperature": 0.7, "num_predict": 30},
    }

    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=2.0)
        resp.raise_for_status()
        text = resp.json().get("response", "")
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            parsed = json.loads(match.group(0))
            chosen_id = parsed.get("meme_id")
            if chosen_id in cands and chosen_id in meme_dict:
                return meme_dict[chosen_id]
    except Exception:
        pass

    # Intelligent contextual fallback
    import random
    chosen_id = random.choice(cands)
    if chosen_id in meme_dict:
        return meme_dict[chosen_id]

    # Bare fallback object if file missing
    return {
        "id": chosen_id,
        "audio_file": f"assets/audio/{chosen_id}.mp3",
        "caption": f"Playing {chosen_id} meme audio!",
        "title": chosen_id.replace("_", " ").title(),
    }


