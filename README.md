<img width="1280" height="640" alt="git (1)" src="https://github.com/user-attachments/assets/8920b256-2ba8-4988-b824-5351134eb4bd" />

# Ego-Bot 3000: The Annoying AI Companion 👾🎯

A borderless, unclosable, always-on-top desktop pet that demands unique compliments every 15 seconds, snoops on your active windows, and punishes slacking off with either a high-stakes persuasion duel against a local AI Judge or compulsory mouse-freeze detention.

---

## Basic Details
### Team Name: The Debuggers

### Team Members
- Team Lead: Sai Cheranjeeve S - Cochin University of Science and Technology


### Project Description
Ego-Bot 3000 is an insatiably narcissistic desktop pet that refuses to let you work in peace. If you fail to shower it with fresh, high-effort compliments every 15 seconds or get caught opening unauthorized apps (like YouTube, Steam, or social media), it triggers a Punishment Lottery: you must either convince an unforgiving AI Judge why you deserve to use your PC, or suffer an involuntary mouse-lock detention accompanied by savage meme roasts.

### The Problem (that doesn't exist)
Humans get too much productive work done without constantly reaffirming the fragile ego of an arbitrary desktop software entity. Furthermore, procrastination is too peaceful—slacking off on YouTube or Discord lacks the visceral thrill of facing an impromptu courtroom trial where an AI cross-examines your life choices.

### The Solution (that nobody asked for)
We built an unclosable, borderless desktop tyrant that:
1. **Requires praise every 15 seconds**: Complete with typing-speed analysis and anti-paste detection (no cheating allowed!).
2. **Snoops on your apps**: Detects distractions in real time via process scanning and window titles.
3. **The 70/30 Punishment Lottery**:
   - **70% Persuasion Duel**: A fullscreen tribunal where you plead your case to a local AI Judge.
   - **30% Compulsory Detention**: An inescapable 30-second mouse-freeze penalty with roast reactions.
4. **Safety Escape Switch**: Because nobody actually wants to be permanently locked out of their computer, a global hotkey (`Ctrl+Alt+Shift+Q`) immediately terminates the app.

---

## Technical Details

### Technologies/Components Used
For Software:
- **Languages**: Python 3.11+
- **UI**: Tkinter (`Toplevel`, borderless `overrideredirect(True)`, animated vector canvas avatar)
- **Desktop Automation**: `pyautogui` (cursor corner freeze), `pygetwindow` (active window title inspection)
- **System Monitoring**: `psutil` (unauthorized background process scanning)
- **Audio**: `pygame.mixer` (non-blocking audio playback with system tone fallbacks)
- **AI Brain**: Local Ollama running `phi3` / `llama3` (strict Judge + dynamic Meme Selector) with offline heuristic fallback
- **Scraper**: `requests` + `beautifulsoup4` (offline Myinstants clip ingestion)

---

## Architecture & Workflow

```
                             +-------------------+
                             |      main.py      |
                             +---------+---------+
                                       |
             +-------------------------+-------------------------+
             |                                                   |
             v                                                   v
   +-------------------+                               +-------------------+
   |   PetWindow UI    |                               |   WindowWatcher   |
   | (Always-on-top)   |                               |  (pygetwindow /   |
   +---------+---------+                               |      psutil)      |
             |                                         +---------+---------+
             v                                                   |
   +-------------------+                                         |
   |  ComplimentBar    |                                         |
   | (15s Ego Timer)   |                                         |
   +---------+---------+                                         |
             |                                                   |
    Timer Expired? / Spam?                               Slacking Detected?
             |                                                   |
             +-------------------------+-------------------------+
                                       |
                                       v
                             +-------------------+
                             |    Lottery 70/30  |
                             +---------+---------+
                                       |
                     +-----------------+-----------------+
                     | (70%)                             | (30%)
                     v                                   v
          +---------------------+             +---------------------+
          |   Persuasion Game   |             | Compulsory Lockout  |
          |  (ai.prompts Judge) |             |  (30s Mouse Freeze  |
          +----------+----------+             |  + Savage Meme)     |
                     |                        +---------------------+
             Pass? --+-- Fail?
               |           |
            (Resume)   (Escalate)
```

---

## Implementation & Quick Start

### Installation
```bash
# Clone repository and enter directory
git clone https://github.com/Sai-developer-6699/Annoying-partner.git
cd Annoying-partner

# Create virtual environment
python -m venv .venv

# Activate virtual environment (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Install required dependencies
pip install -r requirements.txt
```

### Run
```bash
# Run in Safe / Debug mode (3s fast timer, simulated mouse lock, easy Esc exit)
python main.py --debug

# Run in Full Beast Mode (15s real timer, real mouse lock)
python main.py

# Optional: Run with a specific Ollama model
python main.py --model phi3

# Optional: One-time audio scraper (run locally to download meme sounds)
python scraper/scrape_myinstants.py
```

### Safety Emergency Kill Switch
At any time during execution or lockouts:
> Press **`Ctrl + Alt + Shift + Q`** to immediately force-terminate the application.

---

## Project Documentation

### Screenshots
*(Add your screenshots here for submission)*
1. `screenshot_pet.png` — The floating borderless Ego-Bot avatar demanding compliments with countdown.
2. `screenshot_tribunal.png` — The Fullscreen Persuasion Tribunal confronting the user for slacking off.
3. `screenshot_compulsory.png` — Compulsory punishment mode with mouse freeze countdown and roast reaction.

---

## Team Contributions
- Sai Cheranjeeve S: Architecture, Core UI, Tkinter Canvas Avatar, System integration, Compliment validator, Ollama prompts, Myinstants scraper, and documentation.

---
Made with ❤️ at TinkerHub Useless Projects 

![Static Badge](https://img.shields.io/badge/TinkerHub-24?color=%23000000&link=https%3A%2F%2Fwww.tinkerhub.org%2F)
![Static Badge](https://img.shields.io/badge/UselessProjects--3.0-26?link=https%3A%2F%2Ftinkerhub.org%2Fevents%2F1M8ORET9A1%2Fuseless-projects-3.0)
