"""Settings persistence for FastSkills TUI (~/.fastskills/settings.yaml)."""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

import yaml

SETTINGS_DIR = Path.home() / ".fastskills"
SETTINGS_PATH = SETTINGS_DIR / "settings.yaml"


def fetch_openrouter_models() -> list[dict]:
    """Fetch models from OpenRouter. Returns list of {id, name, display}."""
    try:
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/models",
            headers={"User-Agent": "FastSkills-CLI/1.0"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception:
        return []

    models = []
    for m in data.get("data", []):
        mid = m.get("id", "")
        name = m.get("name", mid)
        pricing = m.get("pricing", {})
        prompt_price = float(pricing.get("prompt", 0)) * 1_000_000
        completion_price = float(pricing.get("completion", 0)) * 1_000_000
        ctx = m.get("context_length", 0)
        ctx_str = f"{ctx // 1_000_000}M" if ctx >= 1_000_000 else f"{ctx // 1000}K"
        if prompt_price == 0 and completion_price == 0:
            price_str = "free"
        else:
            price_str = f"${prompt_price:.2f}/M in · ${completion_price:.2f}/M out"
        display = f"{name} — {price_str} — {ctx_str} ctx"
        models.append({"id": mid, "name": name, "display": display})
    return models


def load_settings() -> dict | None:
    """Load settings from ~/.fastskills/settings.yaml. Returns None if missing/invalid."""
    if not SETTINGS_PATH.exists():
        return None
    try:
        data = yaml.safe_load(SETTINGS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not data or not data.get("api_key"):
        return None
    return data


def save_settings(api_key: str, model: str, skills_dir: str = "", workdir: str = "") -> None:
    """Save settings, preserving any extra keys the user added (like base_url)."""
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    existing: dict = {}
    if SETTINGS_PATH.exists():
        try:
            existing = yaml.safe_load(SETTINGS_PATH.read_text(encoding="utf-8")) or {}
        except Exception:
            pass
    existing["api_key"] = api_key
    existing["model"] = model
    existing["skills_dir"] = skills_dir
    existing["workdir"] = workdir
    existing.setdefault("base_url", "https://openrouter.ai/api/v1")
    SETTINGS_PATH.write_text(
        yaml.dump(existing, default_flow_style=False), encoding="utf-8"
    )
