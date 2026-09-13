# The Annoying AI Companion — Full Project Spec

A borderless, always-on-top desktop pet that demands compliments, snoops on
your active window, and punishes slacking off with either a persuasion
duel against a local LLM or a forced meme-and-mouse-freeze timeout.

This doc is written to be dropped straight into an agentic IDE (Google
Antigravity) as project context. See **Section 8** for how to actually run
it there.

---

## 1. Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.11+ | Fast to prototype, good desktop-automation ecosystem |
| UI / Avatar | `Tkinter` (`tkinter.Toplevel`, `overrideredirect(True)`) | No extra install, good enough for a borderless floating widget. Swap for `PyQt6` later if you want smoother animations/shadows |
| Window watching | `pygetwindow` | Cross-platform-ish active window title polling |
| Mouse/keyboard control | `pyautogui` | Move the mouse into a corner and hold it |
| Process info | `psutil` | Identify running processes by name for the "unauthorized app" check |
| Audio | `pygame.mixer` | Non-blocking sound playback, doesn't freeze the Tkinter mainloop |
| Scraping | `requests` + `beautifulsoup4` | One-time offline scrape of Myinstants (see Section 4) |
| AI brain | `Ollama` running `phi3` or `llama3` locally | Free, private, low-latency judge + meme selector |

---

## 2. File Structure

```
annoying-ai-companion/
├── AGENTS.md                     # standing rules for Antigravity agents (Section 8)
├── PROJECT_SPEC.md               # this file
├── main.py                       # entrypoint: boots UI + watcher + scheduler
├── ui/
│   ├── pet_window.py              # borderless always-on-top Toplevel + avatar
│   ├── compliment_bar.py          # the 15s countdown + text entry
│   └── punishment_screen.py       # fullscreen lock UI for the persuasion game
├── system/
│   ├── window_watcher.py          # pygetwindow polling loop
│   ├── mouse_lock.py              # pyautogui corner-freeze
│   ├── compliment_validator.py    # dedupe + spam/paste detection (already written, see below)
│   └── lottery.py                 # 70/30 randomizer + trigger routing
├── ai/
│   └── prompts.py                 # Ollama system prompts (already written, see below)
├── scraper/
│   ├── scrape_myinstants.py       # one-time offline scraper (already written, see below)
│   └── requirements.txt
├── data/
│   ├── memes_template.json        # 25 scenarios × 2 intensity options (already written)
│   └── compliments.json           # rolling history + fallback starters (already written)
└── assets/
    └── audio/                     # scraped .mp3 files land here (gitignored)
```

Files marked "already written" are included alongside this spec — see the
project zip. Everything else is what the agents (or you) still need to build.

---

## 3. Core Features, in Implementation Order

### 3.1 The Unclosable UI
- `tk.Tk()` root stays hidden; spawn a `tk.Toplevel()` for the pet with
  `overrideredirect(True)` (removes borders/close button) and
  `attributes("-topmost", True)`.
- Reassert `-topmost` every couple seconds in a `after()` loop — some window
  managers let other always-on-top windows steal focus otherwise.
- Position it in a screen corner by default; make it draggable via
  `<Button-1>` + `<B1-Motion>` bindings so it's annoying but not literally
  unusable.

### 3.2 The 15-Second Ego Boost
- A `tk.Entry` + countdown label. On each `<KeyRelease>` call
  `ComplimentValidator.on_keystroke`; on `<<Paste>>` call `on_paste_event`.
- On Enter / submit button, call `ComplimentValidator.submit(text)`
  (already implemented in `system/compliment_validator.py`):
  - Rejects empty text, pasted text, "typed suspiciously fast" text
    (see 3.5 below), and near-duplicates of the last 15 compliments
    (fuzzy match via `difflib`, threshold 0.82).
  - On accept: nod animation, reset the 15s timer.
  - On reject: DON'T reset the timer — the clock keeps ticking, so
    spamming garbage doesn't buy time.
- When the timer hits 0 with no accepted compliment → feed `"timer_expired"`
  into the lottery (3.4).

### 3.3 App Snooping
- `system/window_watcher.py`: poll `pygetwindow.getActiveWindowTitle()`
  (or `psutil` process names, which is more reliable for matching an exe
  like `chrome.exe` regardless of the tab title) every 2-3 seconds.
- Keep an `unauthorized_apps` allow/deny list in a small config file so you
  can tune it without touching code (e.g. `chrome`, `steam`, any process
  matching a games folder).
- On a hit → feed `"unauthorized_app"` (with the app name) into the lottery.

### 3.4 The Punishment Lottery
`system/lottery.py` — a single function:

```python
import random

def roll_punishment(trigger: str, app_hint: str | None):
    if random.random() < 0.70:
        return ("persuasion", trigger, app_hint)   # 70%
    return ("compulsory", trigger, app_hint)        # 30%
```

- `"persuasion"` → open the fullscreen lock UI (3.4a).
- `"compulsory"` → play a savage-intensity meme immediately + freeze the
  mouse for 30s (3.4b), no input accepted.

**3.4a Persuasion Game**
- Fullscreen (or large) Toplevel with a text (and optionally voice-to-text)
  input box.
- Send the user's message to `ai.prompts.ask_judge()`.
- `[PASS]` → close the lock screen, resume normal operation.
- `[FAIL]` → feed `"persuasion_fail"` into the meme selector, play the
  roast, and either let them retry once more or drop into 3.4b — your call
  on how mean you want it to be.

**3.4b Compulsory Punishment**
- `system/mouse_lock.py`: use `pyautogui.moveTo()` in a tight loop for 30s,
  targeting a screen corner, ignoring `pyautogui.FAILSAFE` interruptions if
  you want it truly inescapable (careful — this also disables the safety
  corner-abort, so make sure you have another kill switch, see Section 6).
- Simultaneously show a large meme image + play its audio via
  `ai.prompts.ask_selector()` picking a `"savage"` intensity entry.

### 3.5 The "Too Much Typing" Blame Feature
Already implemented in `system/compliment_validator.py`:
- Tracks time between first keystroke and submit; if characters-per-second
  implies faster than `MIN_MS_PER_CHAR` (25ms/char ≈ 40+ chars/sec, well
  past realistic typing), it's flagged as suspicious and rejected with a
  blame line ("Nobody types that fast and means it...").
- A genuine paste (`<<Paste>>` event) is rejected outright regardless of
  speed math.
- Both rejections keep the countdown running (see 3.2) — so spam-typing
  costs the user time instead of buying it.

### 3.6 Malayalam Meme Arsenal
- `data/memes_template.json` already has 25 scenarios × 2 intensity
  options (50 total meme slots) mapped across every trigger type.
- Run `scraper/scrape_myinstants.py` **once, locally** (see Section 4) to
  fill in real `audio_file` + `caption` values by searching Myinstants for
  each `search_query`.
- At runtime, `ai.prompts.ask_selector()` picks one scenario_id + intensity
  given the trigger and how many times it's recently fired; the UI then
  plays `assets/audio/<file>` via `pygame.mixer.Sound(...).play()` and
  updates the avatar's expression + a text bubble with the caption.

---

## 4. Scraper Design (already written: `scraper/scrape_myinstants.py`)

Flow:
1. For every scenario/option in `memes_template.json` with `audio_file: null`,
   hit `myinstants.com/en/search/?name=<search_query>`.
2. Parse the first result's `onclick="play('/media/sounds/xxx.mp3')"` to get
   the real mp3 URL, and its title/caption text.
3. Download the mp3 into `assets/audio/<scenario_id>_<intensity>.mp3`.
4. Write the real filename + caption back into the JSON so the app never
   needs network access at runtime.

**Copyright/ethics note:** these clips are uploaded audio of copyrighted
movie dialogue. Scraping a personal local copy for your own desktop toy is
a very different thing from bundling/redistributing that audio to other
people (e.g. publishing an installer with the mp3s baked in, or committing
them to a public repo). Keep `assets/audio/` out of version control
(add it to `.gitignore`) and treat this as strictly for-your-own-machine use.

Myinstants' HTML can change — if the scraper stops finding results, inspect
a live search page and update the CSS selector / `onclick` regex in
`search_first_result()`.

---

## 5. Ollama Prompts (already written: `ai/prompts.py`)

- **Judge** (`JUDGE_SYSTEM_PROMPT`): strict, skeptical by default, rejects
  vague/repetitive excuses, outputs only `[PASS]` or `[FAIL]`.
- **Selector** (`SELECTOR_SYSTEM_PROMPT`): given the trigger + a filtered
  list of candidate scenarios for that trigger, picks one `scenario_id` +
  `intensity`, leaning "savage" the more times that trigger has repeated
  recently. Has a deterministic fallback if the model output doesn't parse,
  so a bad LLM response never softlocks the app.

Run `ollama pull phi3` once before first launch. `phi3` is small enough to
respond in well under a second on most laptops; swap to `llama3` in
`ai/prompts.py::MODEL_NAME` if you want smarter judging and have the RAM.

---

## 6. Safety / Escape Hatches (build these even though the concept is "inescapable")

You will want at least one of these while developing, or you'll lock
yourself out of your own machine:

- A hidden global hotkey (e.g. `Ctrl+Alt+Shift+Q` via the `keyboard`
  library) that force-kills the app regardless of lock state.
- Don't fully disable `pyautogui.FAILSAFE` until the rest of the app is
  solid — leave the "slam mouse into top-left corner" abort on during
  development.
- A `--debug` launch flag that disables the mouse-freeze and shortens the
  15s timer to 3s, so you're not fighting your own app while building it.

---

## 7. 1-Day Build Order (unchanged from the original plan, cross-referenced)

**Phase 1 (Hrs 1-3) — Core Mechanics**
1. Borderless always-on-top window + static avatar (`ui/pet_window.py`).
2. Window watcher loop printing active window name (`system/window_watcher.py`).
3. Mouse-freeze test function (`system/mouse_lock.py`).
4. Wire in `compliment_validator.py` (already written) to the entry box.

**Phase 2 (Hrs 4-5) — Arsenal & Media**
1. Run `scraper/scrape_myinstants.py` to populate real audio + captions.
2. Sanity-check `data/memes_template.json` after scraping (spot check a
   few entries actually have working file paths).
3. Get `pygame.mixer` playing a clip from a test button.

**Phase 3 (Hrs 6-8) — AI Brain**
1. `ollama pull phi3` and confirm `ollama serve` is running.
2. Wire `ai/prompts.py::ask_judge` to the persuasion lock screen.
3. Wire `ai/prompts.py::ask_selector` to the meme arsenal.

**Phase 4 (Hrs 8-10) — Wire It All Together**
1. `system/lottery.py` connecting triggers → 70/30 split.
2. Persuasion loop: text input → judge → pass/fail → mouse lock on fail.
3. Sync: selector output updates avatar expression + text bubble + audio
   simultaneously (fire all three off the same selector result object).

---

## 8. Building This in Google Antigravity

Antigravity (Google's agentic IDE, VS Code-based) works best when you give
it standing rules + a clear task list up front, then supervise via its
Manager Surface rather than typing everything yourself.

1. **Open this folder as a workspace.** Antigravity reads project-root
   `AGENTS.md` automatically before any agent starts work — that file
   (included alongside this one) already encodes the stack choices, file
   layout, and constraints above so you don't have to repeat them in every
   prompt.
2. **Pick a review mode.** For a project that controls the mouse and locks
   the screen, start in "Review-driven development" (checkpoints before
   risky actions) rather than full autonomous mode — you want to eyeball
   the `pyautogui`/`psutil` code before it runs on your real machine.
3. **Break the work into agent tasks matching Section 7's phases** — spin
   up one agent per phase in the Manager Surface (e.g. "Agent A: Phase 1
   core mechanics", "Agent B: Phase 2 scraper wiring") so they run in
   parallel workspaces instead of one long serial chat.
4. **Give the scraper its own isolated task** and tell the agent explicitly
   that it cannot verify the scraper against the live site (no network
   access in a sandboxed agent run) — have it write the code + a short
   manual test checklist for you to run locally, rather than trying to
   "verify" scraped output itself.
5. **Let the agent use its terminal access** to `pip install -r
   scraper/requirements.txt`, run `pytest` if you add tests, and start
   `ollama serve` — but keep the mouse-freeze and screen-lock code behind a
   manual approval step (most agentic IDEs gate shell/system-control
   actions by default; don't turn that off for this project).
6. **After each phase, ask the agent to run `main.py --debug`** (see
   Section 6) so it can self-verify the UI actually launches without
   locking up your test machine.

---

## 9. Open Design Decisions (yours to make, not the agent's)

- Exact `unauthorized_apps` list — depends on what you actually use.
- Whether "failed begging" is its own text box or just repeated presses of
  a "please" button that gets rate-limited the same way as compliments.
- Whether voice input for the persuasion game is v1 or a stretch goal
  (text-only is much less work and ships the same day).
