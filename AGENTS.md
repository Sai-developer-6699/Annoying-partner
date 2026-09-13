# AGENTS.md — Standing Rules for This Workspace

Read `PROJECT_SPEC.md` in full before starting any task. It is the source
of truth for architecture, file layout, and the build order.

## Stack (do not substitute without asking)
- Python 3.11+, Tkinter for UI, `pygetwindow` for window watching,
  `pyautogui` for mouse control, `psutil` for process checks,
  `pygame.mixer` for audio, `requests` + `beautifulsoup4` for the one-time
  scraper, local Ollama (`phi3` default model) for the judge/selector.

## File layout
Follow the tree in `PROJECT_SPEC.md` Section 2 exactly. New modules go in
the matching folder (`ui/`, `system/`, `ai/`, `scraper/`, `data/`) — don't
invent a new top-level folder without checking with the human first.

## Already implemented — read, don't rewrite
- `system/compliment_validator.py`
- `ai/prompts.py`
- `scraper/scrape_myinstants.py`
- `data/memes_template.json`
- `data/compliments.json`

Extend these files' public functions/classes if you need new behavior;
don't duplicate their logic elsewhere.

## Hard constraints
1. **No live network calls to myinstants.com from the running app** —
   scraping happens once, offline, via `scraper/scrape_myinstants.py`.
   The main app only ever reads local files under `assets/audio/`.
2. **Never disable the `pyautogui` failsafe** during development. Keep a
   working `--debug` flag (short timers, no mouse-freeze) at all times.
3. **Gate any mouse-freeze / screen-lock code behind manual approval** —
   don't auto-run code that takes control of the mouse without the human
   confirming it first, even in autonomous mode.
4. **Don't commit `assets/audio/`** — add it to `.gitignore`. Those are
   scraped copyrighted clips for personal local use only, not for
   distribution.
5. Keep the Judge/Selector prompts in `ai/prompts.py` as the single source
   of truth — if a task needs different LLM behavior, edit the prompt
   there rather than adding ad-hoc prompt strings in other files.

## Verification expectations
- After any change to `ui/` or `main.py`, launch with
  `python main.py --debug` and confirm the window opens without crashing
  before marking the task done.
- After any change to `scraper/`, don't attempt to run it against the live
  site if you don't have network access — write/update the code and hand
  it back with a short manual test checklist instead of claiming it's verified.
