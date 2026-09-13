import sys
import os
from pathlib import Path

print("=" * 50)
print("RUNNING ANNOYING AI COMPANION VERIFICATION SUITE")
print("=" * 50)

# 1. Imports check
print("\n[1/6] Testing Module Imports...")
try:
    import system.compliment_validator as cv
    import system.mouse_lock as ml
    import system.window_watcher as ww
    import system.lottery as lot
    import ai.prompts as pr
    import ui.compliment_bar as cb
    import ui.pet_window as pw
    import ui.punishment_screen as ps
    import ui.thunderstrike as ts
    import ui.alphabetical_keyboard as ak
    import main
    print("  -> All 11 modules imported successfully!")
except Exception as e:
    print(f"  ! Import failed: {e}")
    sys.exit(1)

# 2. Compliment validator tests
print("\n[2/6] Testing ComplimentValidator (with Wall-of-Text & Spam Checks)...")
validator = cv.ComplimentValidator()
r1 = validator.submit("Your code is remarkably clean and brilliant!")
assert r1["accepted"] is True, f"First compliment should pass: {r1}"
print("  -> Valid compliment accepted: OK")

r_dup = validator.submit("Your code is remarkably clean and brilliant!")
assert r_dup["accepted"] is False and r_dup["reason"] == "repeat", f"Duplicate should fail: {r_dup}"
print("  -> Duplicate compliment rejected: OK")

r_empty = validator.submit("   ")
assert r_empty["accepted"] is False and r_empty["reason"] == "empty", f"Empty should fail: {r_empty}"
print("  -> Empty compliment rejected: OK")

validator.on_paste_event()
r_paste = validator.submit("Pasted text compliment!")
assert r_paste["accepted"] is False and r_paste["reason"] == "pasted", f"Pasted should fail: {r_paste}"
print("  -> Pasted compliment rejected: OK")

r_wall = validator.submit("A" * 250)
assert r_wall["accepted"] is False and r_wall["reason"] == "wall_of_text", f"Wall of text should fail: {r_wall}"
print("  -> Wall-of-text (>220 chars) rejected: OK")

r_punct = validator.submit("You are so great!!! What a genius???")
assert r_punct["accepted"] is False and r_punct["reason"] == "punctuation_spam", f"Punctuation spam should fail: {r_punct}"
print("  -> Punctuation spam (!!! / ???) rejected: OK")

# 3. Lottery distribution and Malayalam meme matching
print("\n[3/6] Testing Lottery & Merged Malayalam Meme Arsenal...")
results = [lot.roll_punishment("timer_expired", None)[0] for _ in range(200)]
persuasion_count = results.count("persuasion")
compulsory_count = results.count("compulsory")
print(f"  -> 200 rolls: persuasion={persuasion_count} (~70%), compulsory={compulsory_count} (~30%)")
assert 100 <= persuasion_count <= 180, "Lottery distribution out of expected 70% range"

memes_data = lot.load_memes_data()
candidates = lot.get_candidate_scenarios("unauthorized_app", "chrome", memes_data)
assert len(candidates) > 0, "Should find candidate scenarios for chrome"
print(f"  -> Found {len(candidates)} candidate scenarios for 'unauthorized_app' / 'chrome': OK")

scen, opt = lot.select_meme_reaction("unauthorized_app", "chrome", 1, memes_data)
assert "id" in scen and "intensity" in opt, "Reaction selection output malformed"
print(f"  -> Selected Malayalam reaction: '{scen['id']}' [{opt['intensity']}]: '{opt.get('caption')}' OK")

# 4. Mouse lock & cursor physics modes
print("\n[4/6] Testing Cursor Chaos Physics (Gravity & Inverted Mouse)...")
import threading

for mode in ("corner_freeze", "cursor_gravity", "inverted_mouse"):
    abort_ev = threading.Event()
    thread, abort_ev = ml.start_mouse_freeze_thread(duration=0.2, debug=True, abort_event=abort_ev, mode=mode)
    thread.join(timeout=2.0)
    assert not thread.is_alive(), f"Thread for mode '{mode}' should complete"
    print(f"  -> Mode '{mode}' simulated cleanly: OK")

# 5. Prompts & Roaster test
print("\n[5/6] Testing AI Prompts, Judge & Dialogue Generator...")
excuse_pass = pr.ask_judge("I have an urgent deployment deadline for the tinkerhub project review.")
print(f"  -> Plausible excuse verdict: {excuse_pass} (Expected True if offline heuristic)")
excuse_fail = pr.ask_judge("please please let me in")
print(f"  -> Lazy excuse verdict: {excuse_fail} (Expected False)")
assert excuse_fail is False, "Lazy excuse must fail"

pet_reply = pr.ask_pet_reply("unauthorized_app", context="steam.exe", intensity="savage")
assert isinstance(pet_reply, str) and len(pet_reply) > 5
print(f"  -> Generated Pet Reply: '{pet_reply}' OK")

# 6. Keyboard & Thunderstrike component test
print("\n[6/7] Testing Thunderstrike & Alphabetical Keyboard Components...")
assert callable(ts.minimize_all_windows)
assert hasattr(ak, "AlphabeticalKeyboard")
print("  -> Thunderstrike and Alphabetical Keyboard verified: OK")

# 7. Scraped Meme Audio Arsenal & Playback test
print("\n[7/7] Testing Scraped Meme Arsenal (21 Audio Clips & Phi-3 Selector)...")
import json
import pygame
if not pygame.mixer.get_init():
    pygame.mixer.init()

meme_json_path = Path("data/meme_audios.json")
assert meme_json_path.exists(), "data/meme_audios.json missing"
memes_catalog = json.loads(meme_json_path.read_text(encoding="utf-8"))["memes"]
assert len(memes_catalog) >= 20, f"Expected at least 20 memes, found {len(memes_catalog)}"

verified_files = 0
for m in memes_catalog:
    p = Path(m["audio_file"])
    assert p.exists() and p.stat().st_size > 1000, f"Audio file missing or corrupted: {p}"
    # Verify pygame can load it as a sound object
    sound = pygame.mixer.Sound(str(p))
    assert sound.get_length() > 0.1, f"Sound length invalid for {p}"
    verified_files += 1

print(f"  -> Verified {verified_files} audio files on disk and loaded in pygame.mixer: OK")

# Test Phi-3 meme audio selector function
m_slacking = pr.ask_meme_audio("unauthorized_app", context="valorant.exe")
assert m_slacking["id"] in ("faah", "fbi_open_up", "salim_kumar", "jagathy_comedy")
print(f"  -> Selector for slacking (valorant.exe): '{m_slacking['id']}' ({m_slacking['audio_file']}) OK")

m_timer = pr.ask_meme_audio("timer_expired")
assert m_timer["id"] in ("bruh", "metal_pipe", "run_vine")
print(f"  -> Selector for timer expired: '{m_timer['id']}' ({m_timer['audio_file']}) OK")

m_court = pr.ask_meme_audio("persuasion_fail")
assert m_court["id"] in ("faah", "emotional_damage", "directed_by_robert_b_weide", "suraj_dhamu", "wasted", "sad_violin", "nope_tf2")
print(f"  -> Selector for court rejection: '{m_court['id']}' ({m_court['audio_file']}) OK")

# 8. Troll Autocorrect & Voice Synthesis & Faaah Meme
print("\n[8/8] Testing Troll Autocorrect, Voice Synthesizer & Faaah Meme...")
from ui.compliment_bar import mutate_text_chaotically
mutated, changed = mutate_text_chaotically("You are a genius master coder with clean code", mutation_chance=1.0)
assert changed, "Mutation engine should mutate words"
assert any(w in mutated for w in ("potato", "rookie", "spaghetti", "syntax error")), f"Expected troll word in: {mutated}"
print(f"  -> Troll Autocorrect: 'genius master' mutated to '{mutated}': OK")

from system.voice import VoiceSynthesizer
voice = VoiceSynthesizer(enabled=True)
voice.speak_async("Ego-Bot voice test")
voice.stop()
print("  -> VoiceSynthesizer initialized and queued speech cleanly: OK")

faah_p = Path("assets/audio/faah.mp3")
assert faah_p.exists() and faah_p.stat().st_size > 1000, "faah.mp3 missing"
faah_sound = pygame.mixer.Sound(str(faah_p))
assert faah_sound.get_length() > 0.1, "faah.mp3 audio corrupted"
print("  -> Faaah meme sound (assets/audio/faah.mp3) verified in pygame.mixer: OK")

import ui.meme_popup as mp
assert hasattr(mp, "show_meme_card")
print("  -> MemeCardPopup verified: OK")

print("\n" + "=" * 50)
print("ALL 8 VERIFICATION CHECKS PASSED SUCCESSFULLY!")
print("=" * 50)
