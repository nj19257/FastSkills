"""Session persistence for FastSkills Agent TUI.

Stores chat sessions as JSON files in ~/.fastskills/sessions/.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

SESSIONS_DIR = Path.home() / ".fastskills" / "sessions"


def generate_session_id() -> str:
    """Generate a new UUID-based session ID."""
    return uuid.uuid4().hex[:12]


def save_session(
    session_id: str,
    title: str,
    model: str,
    messages: list[dict],
) -> Path:
    """Save a session to disk.

    System-prompt messages (role=system) are excluded — they are
    re-injected from the current config on load.

    Returns the path to the saved JSON file.
    """
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    path = SESSIONS_DIR / f"{session_id}.json"

    # Strip system messages
    saved_msgs = [m for m in messages if m.get("role") != "system"]
    if not saved_msgs:
        return path

    now = datetime.now(timezone.utc).isoformat()

    # Preserve created_at if the file already exists
    created_at = now
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
            created_at = existing.get("created_at", now)
        except Exception:
            pass

    data = {
        "id": session_id,
        "title": title[:60],
        "created_at": created_at,
        "updated_at": now,
        "model": model,
        "messages": saved_msgs,
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_session(session_id: str) -> dict:
    """Load a session by ID. Returns the full session dict."""
    path = SESSIONS_DIR / f"{session_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Session not found: {session_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def list_sessions(limit: int = 20) -> list[dict]:
    """List recent sessions (metadata only, no messages).

    Returns a list sorted by updated_at descending.
    """
    if not SESSIONS_DIR.exists():
        return []

    sessions: list[dict] = []
    for f in SESSIONS_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            sessions.append({
                "id": data["id"],
                "title": data.get("title", "(untitled)"),
                "created_at": data.get("created_at", ""),
                "updated_at": data.get("updated_at", ""),
                "model": data.get("model", ""),
            })
        except Exception:
            continue

    sessions.sort(key=lambda s: s.get("updated_at", ""), reverse=True)
    return sessions[:limit]
