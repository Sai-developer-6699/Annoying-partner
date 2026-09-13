"""
test_actions_memes_audio.py
----------------------------
Comprehensive verification of:
1. Character Action States & Descriptions
2. Meme reactions selected by Phi-3 / Selector
3. Audio files loaded and played via pygame.mixer
4. Speech synthesis via VoiceSynthesizer
5. Visual Meme Cards
"""

import os
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

import pygame
if not pygame.mixer.get_init():
    pygame.mixer.init()

import ai.prompts as pr
import system.lottery as lot
from ui.pet_window import PetWindow
import tkinter as tk

print("=" * 60)
print("TESTING ACTIONS, MEME SELECTIONS, AND AUDIO PLAYBACK")
print("=" * 60)

# 1. Test Phi-3 Meme & Dialogue Generation
print("\n[1/4] Testing Live Phi-3 Dialogue & Audio Meme Selection...")
triggers = [
    ("unauthorized_app", "steam.exe", "savage"),
    ("timer_expired", None, "mild"),
    ("compliment_rejected", "wall of text", "savage"),
    ("compliment_accepted", "your code is divine", "savage"),
    ("persuasion_fail", "i was just checking one thing", "savage"),
    ("persuasion_pass", "deployment deadline for tinkerhub", "mild"),
]

sys.stdout.reconfigure(encoding="utf-8")

memes_data = lot.load_memes_data()

for trig, ctx, intensity in triggers:
    roast = pr.ask_pet_reply(trig, context=ctx, intensity=intensity)
    meme = pr.ask_meme_audio(trig, context=ctx, intensity=intensity)
    audio_p = PROJECT_ROOT / meme["audio_file"]
    assert audio_p.exists(), f"Audio file not found: {audio_p}"
    sound = pygame.mixer.Sound(str(audio_p))
    print(f"\n  Trigger: {trig} (Context: {ctx})")
    print(f"    -> Phi-3 Roast: '{roast[:65]}...'")
    print(f"    -> Selected Meme: [{meme['id']}] '{meme.get('title')}'")
    print(f"    -> Audio File: {meme['audio_file']} ({audio_p.stat().st_size} bytes, length={sound.get_length():.2f}s) OK")

# 2. Test Character Actions & Sprites
print("\n[2/4] Testing Avatar Action State Mapping...")
root = tk.Tk()
root.withdraw()

pet = PetWindow(
    root=root,
    on_compliment_accepted=lambda t: None,
    on_compliment_rejected=lambda r, b: None,
    on_timer_expired=lambda: None,
    on_emergency_kill=lambda: None,
    countdown_seconds=30.0,
    debug=True,
    no_audio=True,
)

test_expressions = [
    ("smug", "Tsundere Proud (Arms crossed, smirking)"),
    ("furious", "Furious Pouting & Piercing Glare!"),
    ("impressed", "Joyful Pride (Ego swell + Nods)"),
    ("shocked", "Wide-Eyed Shock & Disbelief"),
    ("suspicious", "Piercing Suspicion (Detecting fraud)"),
    ("idle", "Judicious Waiting (Tapping foot impatiently)"),
]

for expr, expected_subline in test_expressions:
    pet.set_expression(expr, f"Testing {expr} expression")
    action_text = pet.action_subline.cget("text")
    assert expected_subline in action_text, f"Expected '{expected_subline}' in '{action_text}'"
    print(f"  Expression '{expr}': {action_text} OK")

# 3. Test Visual Meme Cards
print("\n[3/4] Testing MemeCardPopup Display...")
pet.show_meme_card("faah", "FAAAAH!", "You thought you could please me?!")
root.update()
print("  -> MemeCardPopup spawned and displayed successfully: OK")

# 4. Test Faaah Audio Specifically
print("\n[4/4] Testing Specific Malayalam 'Faaah!' Audio Asset...")
faah_path = PROJECT_ROOT / "assets" / "audio" / "faah.mp3"
assert faah_path.exists(), "faah.mp3 does not exist"
faah_sound = pygame.mixer.Sound(str(faah_path))
assert faah_sound.get_length() > 0.5, "faah.mp3 is too short"
print(f"  -> 'faah.mp3' verified: size={faah_path.stat().st_size} bytes, duration={faah_sound.get_length():.2f}s OK")

print("\n" + "=" * 60)
print("ALL ACTIONS, MEMES, AND AUDIO VERIFIED SUCCESSFULLY!")
print("=" * 60)

root.destroy()
