"""
lottery.py
----------
70/30 Punishment Lottery and scenario matching.
- 70% persuasion duel (fullscreen judge modal)
- 30% compulsory punishment (savage meme + mouse freeze)
"""

import json
import logging
import random
from pathlib import Path
from ai.prompts import ask_selector

logger = logging.getLogger("lottery")

MEMES_JSON = Path(__file__).resolve().parent.parent / "data" / "memes_template.json"


def roll_punishment(trigger: str, app_hint: str | None = None) -> tuple[str, str, str | None]:
    """
    Returns ("persuasion", trigger, app_hint) with 70% probability,
    or ("compulsory", trigger, app_hint) with 30% probability.
    """
    if random.random() < 0.70:
        return ("persuasion", trigger, app_hint)
    return ("compulsory", trigger, app_hint)


def load_memes_data() -> dict:
    if MEMES_JSON.exists():
        try:
            return json.loads(MEMES_JSON.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.error(f"Failed to read memes_template.json: {exc}")
    return {"scenarios": []}


def get_candidate_scenarios(trigger: str, app_hint: str | None, memes_data: dict) -> list[dict]:
    """
    Filter scenarios from memes_template.json matching the trigger and optional app_hint.
    """
    scenarios = memes_data.get("scenarios", [])
    matching_trigger = [s for s in scenarios if s.get("trigger") == trigger]

    if not matching_trigger:
        # Fallback to any scenario
        matching_trigger = scenarios

    if app_hint:
        app_hint_lower = app_hint.lower()
        hint_matches = [
            s for s in matching_trigger
            if s.get("app_hint") and (
                s["app_hint"].lower() in app_hint_lower or app_hint_lower in s["app_hint"].lower()
            )
        ]
        if hint_matches:
            return hint_matches

    return matching_trigger


def select_meme_reaction(
    trigger: str,
    app_hint: str | None,
    repeat_count: int,
    memes_data: dict | None = None,
) -> tuple[dict, dict]:
    """
    Uses ai.prompts.ask_selector to pick a scenario and intensity option.
    Returns (scenario_dict, option_dict).
    """
    if memes_data is None:
        memes_data = load_memes_data()

    candidates = get_candidate_scenarios(trigger, app_hint, memes_data)
    if not candidates:
        default_scenario = {
            "id": "fallback_00",
            "trigger": trigger,
            "options": [
                {"intensity": "mild", "caption": "Back to work!", "avatar_expression": "unimpressed", "audio_file": None},
                {"intensity": "savage", "caption": "Focus or face the consequences!", "avatar_expression": "furious", "audio_file": None},
            ],
        }
        return default_scenario, default_scenario["options"][0]

    # Format candidates for the selector LLM prompt
    selector_candidates = [
        {
            "id": c["id"],
            "options": [{"intensity": opt.get("intensity", "mild")} for opt in c.get("options", [])],
        }
        for c in candidates
    ]

    selected = ask_selector(trigger, app_hint, selector_candidates, repeat_count)
    selected_id = selected.get("scenario_id")
    selected_intensity = selected.get("intensity", "mild")

    target_scenario = next((c for c in candidates if c["id"] == selected_id), candidates[0])
    target_option = next(
        (opt for opt in target_scenario.get("options", []) if opt.get("intensity") == selected_intensity),
        target_scenario.get("options", [{}])[0],
    )

    return target_scenario, target_option
