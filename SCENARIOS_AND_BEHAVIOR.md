# 🐾 Ego-Bot 3000 — Scenarios & Behavior Reference

A complete reference guide for every state, trigger, condition, and reaction inside Ego-Bot 3000. Use this to understand what the digital pet does, when it does it, and why it does it.

---

## 📊 Master State Machine

```
                        ┌─────────────────┐
                        │   IDLE / BOOT   │
                        │  (Pet appears)  │
                        └────────┬────────┘
                                 │
                    ┌────────────▼────────────┐
                    │     PRAISE LOOP ACTIVE  │ ◄──── (reset on valid compliment)
                    │  ⏱ 15-second countdown  │
                    └─────┬──────────┬────────┘
                          │          │
               Timer = 0  │          │  Slacking Detected
                          │          │  (any time, background)
                          ▼          ▼
                    ┌──────────────────────┐
                    │   PUNISHMENT TRIGGER │
                    │  (lottery.py rolls)  │
                    └──────┬───────┬───────┘
                           │       │
                      70%  │       │  30%
                           ▼       ▼
              ┌──────────────┐  ┌──────────────────┐
              │  PERSUASION  │  │   COMPULSORY     │
              │  TRIBUNAL    │  │   LOCKOUT        │
              │  (AI Judge)  │  │  (Mouse Chaos)   │
              └──────┬───────┘  └──────────────────┘
                     │
             [PASS]  │  [FAIL]
                     │     │
                     ▼     ▼
               Resume   Compulsory
               Normal   Lockout
```

---

## 🏆 Feature 1: The Praise Loop (Always Active)

### What happens
Luna (the pet) demands a fresh, unique, genuine compliment every **15 seconds**. The countdown is always visible with a glowing progress bar.

### Accept Conditions (ALL must be true)
| Condition | Rule | What Happens if Violated |
|---|---|---|
| **Non-empty** | Text field must have ≥ 1 character | Silent reject, timer keeps running |
| **Not pasted** | `<<Paste>>` event detected = auto-reject | "No cheating with Ctrl+V!" — timer keeps running |
| **Typed fast enough** | Must not exceed 40 chars/sec (25ms/char min) | "Nobody types that fast and means it..." — timer keeps running |
| **Not a duplicate** | Fuzzy-match score < 0.82 against last 15 accepted compliments | "You already said something like that!" — timer keeps running |
| **Non-trivial** | Empty or whitespace-only rejected outright | Silent reject |

> ⚠️ **Key design rule:** Failed submissions do NOT reset the timer. Only valid compliments reset it. Spamming random keys wastes your time.

### Troll Autocorrect — Word Replacements
When you type certain "productivity" words, they get silently replaced in the text box:

| You type | Luna replaces with |
|---|---|
| `work` | `nap` |
| `deadline` | `naptime` |
| `meeting` | `snack break` |
| `urgent` | `eventually` |
| `important` | `mildly interesting` |
| `finish` | `think about starting` |
| `submit` | `maybe submit` |
| `task` | `daydream` |
| `project` | `vibe session` |
| `code` | `pretend to code` |
| `focus` | `spiral` |

### Mic Voice Input
- 🎙️ **Mic button** (bottom of pet window) opens voice capture
- Uses `speech_recognition` + `sounddevice` to record 4 seconds of audio
- Transcribed text is pasted into the compliment field
- Same validation rules apply — paste-detection is suppressed for voice input only
- Falls back to showing "Could not hear you, speak up!" if transcription fails

### What Luna Says (Mood States)
| Mood | Trigger | Sample Speech Bubble |
|---|---|---|
| **SMUG** | Default / just received compliment | *"Praise my digital genius, human."* |
| **IMPATIENT** | < 5 seconds left on timer | *"Tick tock. You were saying?"* |
| **FURIOUS** | Timer hits 0 | *"UNACCEPTABLE. Face the consequences."* |
| **SATISFIED** | Valid compliment accepted | *"...I suppose that will do."* |
| **SUSPICIOUS** | Compliment rejected (duplicate/paste) | *"Did you really think I wouldn't notice?"* |

---

## 🕵️ Feature 2: App Snooping (Window Watcher)

### How it works
- `window_watcher.py` polls `pygetwindow.getActiveWindowTitle()` and `psutil` process list every **2–3 seconds**
- Process-name matching (exe level) is used — works even if tab titles change

### Monitored Processes
| Process / App | Category | Why it's unauthorized |
|---|---|---|
| `brave.exe` | Browser | YouTube, Reddit, time-wasting |
| `chrome.exe` | Browser | Same as above |
| `msedge.exe` | Browser | Same as above |
| `firefox.exe` | Browser | Same as above |
| `discord.exe` | Social | Chatting instead of working |
| `steam.exe` | Gaming | Gaming during work hours |
| `epicgameslauncher.exe` | Gaming | Fortnite is not productive |
| `spotify.exe` | Music | Debatable, but Luna decides |
| `vlc.exe` | Video | Movie time = crime |
| `netflix.exe` | Streaming | Absolutely not |
| Any window title containing: `YouTube`, `Reddit`, `Twitter/X`, `Instagram`, `TikTok` | Social Media | Self-explanatory |

### Thunderstrike Animation (Slacking Detected)
When an unauthorized app is detected:
1. 🌩️ **Thunderstrike flash** — red lightning overlay blinks on the pet window
2. Pet window **shakes and minimizes** any fullscreen windows
3. **2.5 second scolding prelude** — speech bubble shows scolding message
4. Feeds `"unauthorized_app"` + app name into the **Punishment Lottery**

### Sample Scolding Messages
- *"Oh? Brave? In THIS economy?"*
- *"Steam detected. Case closed. You're guilty."*
- *"Discord at work? You absolute menace."*
- *"Put the YouTube down and back away slowly."*

---

## 🎲 Feature 3: The 70/30 Punishment Lottery

### Trigger conditions
- Timer reaches 0 with no valid compliment
- Unauthorized app detected
- Repeated compliment spam (>3 rejected in a row)

### The Roll
```python
if random.random() < 0.70:
    → PERSUASION TRIBUNAL (70%)
else:
    → COMPULSORY LOCKOUT  (30%)
```

---

## ⚖️ Feature 4: Persuasion Tribunal (70% outcome)

### Scenario: You got caught slacking or ran out of time

**What appears:** A fullscreen dark courtroom UI with:
- Title: *"PERSUASION TRIBUNAL — State Your Case"*
- Text box (and mic button) to type/speak your excuse
- A countdown timer (you have limited time to respond)
- Luna in judge mode with arms crossed

### How the AI Judge works
- Your excuse is sent to **local Ollama** running **Phi-3** (or llama3)
- The Judge uses a strict system prompt (`ai/prompts.py::JUDGE_SYSTEM_PROMPT`)
- Response is exactly one of: `[PASS]` or `[FAIL]`

### Judge Verdicts

| Your Excuse | Likely Verdict | Why |
|---|---|---|
| *"I was researching for my project"* | `[PASS]` ✅ | Plausible, specific |
| *"I needed a quick break"* | `[FAIL]` ❌ | Vague, no justification |
| *"I was checking Discord for work messages"* | `[PASS]` ✅ | Defensible context |
| *"I like YouTube"* | `[FAIL]` ❌ | Not an excuse |
| *"My cat walked on my keyboard"* | `[FAIL]` ❌ | Implausible |
| *"I was looking up documentation"* | `[PASS]` ✅ | Developer-credible |
| *"I just wanted to"* | `[FAIL]` ❌ | Lazy, no effort |
| *"Please"* (alone) | `[FAIL]` ❌ | Absolutely not |

### PASS outcome
- Lock screen dismisses
- Pet resumes normal praise loop with a smug comment: *"Lucky. Don't make it a habit."*
- Timer resets to 15s

### FAIL outcome
- **Emotional Damage card** pops up with a savage roast from the meme arsenal
- Drops into **Compulsory Lockout** (see below)
- Roast audio plays (Malayalam comedy clip or scraped sound)

---

## 🔒 Feature 5: Compulsory Lockout (30% outcome, or after Tribunal FAIL)

### What happens
Fullscreen black overlay appears. One of three mouse punishment modes is randomly selected:

### Punishment Modes
| Mode | What it does | Duration |
|---|---|---|
| **Corner Freeze** | Cursor is forcibly dragged to bottom-right corner every 50ms; you cannot move it | **15 seconds** |
| **Inverted Mouse** | Mouse movement is mirrored: moving right moves left, up moves down | **15 seconds** |
| **Cursor Gravity** | Mouse is constantly pulled downward by 8–15 pixels per tick | **15 seconds** |

The active mode is displayed on screen: *"CURSOR GRAVITY ENGAGED (Mouse Dragged Down)"*

### Sub-text shown during lockout
- *"Contemplate your work habits while the cursor is incapacitated."*
- *"This is what you chose."*
- *"Luna is disappointed. And a little smug."*

### After lockout ends
- Screen fades back to normal
- Pet window reappears
- Praise loop resets with a fresh 15-second timer
- Luna says: *"I hope you've learned something. (I know you haven't.)"*

---

## 🎭 Feature 6: Meme Arsenal (Scraped + AI-Selected)

### How it works
- `data/memes_template.json` contains **25 scenarios × 2 intensity levels = 50 meme slots**
- Each slot has a `search_query` for Myinstants, a `caption`, and an `audio_file` path
- `ai/prompts.py::ask_selector()` asks Ollama to pick the best scenario + intensity based on:
  - The trigger type (`timer_expired`, `unauthorized_app`, `persuasion_fail`, etc.)
  - How many times that trigger has fired recently (escalates to "savage" on repeats)

### Intensity Levels
| Intensity | When used | Tone |
|---|---|---|
| `mild` | First offense, first time that trigger fires | Light teasing |
| `savage` | Repeated offenses, escalation, FAIL after Tribunal | Full roast mode |

### Sample Scenario Triggers & Reactions

| Trigger | Mild Reaction | Savage Reaction |
|---|---|---|
| `timer_expired` | *"Oh look who forgot to compliment me."* | *"TIMER REPEAT 08 — Clock nadakkunnundu, ninak parayan onnumilla?"* |
| `unauthorized_app::brave` | *"Brave detected. Interesting choice."* | *"Ithu evideyanu ninnal? YouTube-il? Athu paavam."* |
| `persuasion_fail` | *"Oh, mortals always fall short."* | *"EMOTIONAL DAMAGE! That excuse was physically painful."* |
| `spam_compliment` | *"Try harder. Much harder."* | *"Copy-paste detected. I'm offended on a cellular level."* |
| `voice_fail` | *"Did you mumble that?"* | *"Speak up! Or are you afraid of what I'll say?"* |

### Audio System
- **Playback:** `pygame.mixer.Sound().play()` — non-blocking, doesn't freeze the UI
- **Clip source:** Locally downloaded `.mp3` files from Myinstants (via one-time scraper)
- **Fallback:** System beep / tone if audio file is missing
- **Malayalam comedy clips:** Curated regional humor clips mapped to specific triggers

---

## 🎨 Feature 7: Luna — The Avatar

### Sprite System
- Animated anime-style sprite loaded via `PIL.ImageTk`
- Spritesheet with multiple expression frames:

| Expression | When shown |
|---|---|
| Neutral / Smug | Default idle state |
| Arms crossed (Tsundere Proud) | After valid compliment |
| Angry (Furious) | Timer expired |
| Judging (Eyebrow raised) | Tribunal mode |
| Celebration (Sparkles) | After PASS verdict |
| Sad (Disappointed) | Compulsory lockout initiated |

### Speech Bubbles
- Comic-style white bubble with black border
- Text dynamically set based on state
- Fades in with a 150ms animation on state change

### Status Bar (always visible at top)
```
👑 EGO: 85% • 😤 MOOD: SMUG          🤖 PHI-3 ACTIVE
▶ Current Action: Expectant Smirk (Waiting for flattery)
```

- **EGO %** increases when compliments are accepted, decreases over time
- **MOOD** reflects current emotional state
- **PHI-3 ACTIVE** / **OFFLINE MODE** shows Ollama connection status

---

## 🚨 Feature 8: Emergency Kill Switches

Luna is annoying, but not sadistic. Multiple escape routes exist:

| Method | How | When available |
|---|---|---|
| **F12** | Press F12 key | Always, including during lockout |
| **Ctrl+Q** | Keyboard shortcut | Always |
| **Kill button** | Bottom-right "💀 Kill (F12)" button in pet window | When pet is visible |
| **`stop.py`** | Run `python stop.py` in terminal | When app is running |
| **`--debug` flag** | `python main.py --debug` — 3s timers, no real mouse lock | Development only |

---

## 🔧 Feature 9: Ollama Integration (Required for Full Features)

### Why Ollama is needed
| Feature | Without Ollama | With Ollama |
|---|---|---|
| Persuasion Tribunal verdict | Heuristic fallback (keyword matching) | Real Phi-3 reasoning |
| Meme selection | Random pick from template | Context-aware scenario selection |
| Excuse evaluation | Simple keyword check | Nuanced argument analysis |

### Setup
```bash
# 1. Install Ollama (one-time)
# Download from https://ollama.com

# 2. Pull the model
ollama pull phi3

# 3. Start the Ollama server (in background)
ollama serve

# 4. Run the app (Ollama auto-detected)
python main.py
```

### Offline Fallback
If Ollama is not running, the app:
- Uses keyword-based heuristic verdict for Tribunal (`"work"`, `"research"`, `"document"` → PASS, everything else → FAIL)
- Randomly picks a meme scenario instead of AI-selecting
- Shows `OFFLINE MODE` in the status bar

---

## 📋 Full Scenario Showcase Guide

To demonstrate all features in a live demo, follow this sequence:

### Scenario 1: Normal Praise Loop
1. Launch `python main.py`
2. Watch the 15s countdown in the pet window
3. Type a compliment and submit — watch Luna react with satisfaction
4. Submit the same compliment again — see duplicate detection reject it

### Scenario 2: Troll Autocorrect
1. In the praise box, type *"I need to finish this work task"*
2. Watch the words transform as you type

### Scenario 3: Paste Detection
1. Copy any text to clipboard
2. Paste into the praise box with Ctrl+V
3. See the immediate rejection with "No cheating!" message

### Scenario 4: Timer Expiry → Tribunal
1. Let the 15s timer run out without submitting
2. Tribunal fullscreen appears
3. Type a good excuse → see `[PASS]` verdict → pet resumes
4. Type a bad excuse → see `[FAIL]` → Emotional Damage card → lockout

### Scenario 5: Slacking Detection → Compulsory Lockout
1. While app is running, open Brave/Chrome browser
2. Watch the Thunderstrike animation
3. See the 2.5s scolding, then lottery rolls Compulsory Lockout
4. Experience 15s of cursor gravity — try to move your mouse!

### Scenario 6: Voice Input
1. Click the 🎙️ mic button
2. Speak a compliment into your microphone
3. See it transcribed and auto-filled into the praise box

### Scenario 7: Meme Arsenal
1. Trigger a punishment multiple times
2. Watch intensity escalate from mild to savage
3. Hear the Malayalam comedy audio clip play alongside the meme card

---

*Built with 🎭 chaos and ❤️ at TinkerHub Useless Projects 3.0*
