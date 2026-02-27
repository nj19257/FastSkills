"""FastSkills Agent — Textual TUI (installable entry point).

Usage (after pip install):
    fastskills_cli
    fastskills_cli --prompt /path/to/prompt.yaml
"""

from __future__ import annotations

import sys

# Fail-fast guard for missing optional deps
try:
    import textual, openai, yaml  # noqa: F401
except ImportError as e:
    print(f"Missing: {e.name}\n\nInstall with: pip install 'fastskills[cli]'", file=sys.stderr)
    raise SystemExit(1)

import argparse
from pathlib import Path

import yaml

from tui import FastSkillsChat
from tui.constants import DEFAULT_SYSTEM_PROMPT


def _resolve_skills_dir() -> str:
    """Find the best skills directory.

    Priority:
    1. Bundled skills/ in the repo (sibling of src/)
    2. ~/.fastskills/skills/
    """
    # Try repo-bundled skills (script is in src/, skills is at repo root)
    script_dir = Path(__file__).resolve().parent
    repo_skills = script_dir.parent / "skills"
    if repo_skills.is_dir():
        return str(repo_skills)

    # Fall back to user-global
    return str(Path.home() / ".fastskills" / "skills")


def main() -> None:
    parser = argparse.ArgumentParser(description="FastSkills Agent TUI")
    parser.add_argument(
        "--prompt",
        type=str,
        default=None,
        help="Path to a YAML file with a system_prompt key (overrides built-in prompt)",
    )
    args = parser.parse_args()

    # Load system prompt
    if args.prompt:
        prompt_path = Path(args.prompt)
        if not prompt_path.exists():
            print(f"Prompt file not found: {prompt_path}", file=sys.stderr)
            sys.exit(1)
        with open(prompt_path, encoding="utf-8") as f:
            prompt_data = yaml.safe_load(f)
        system_prompt = prompt_data["system_prompt"]
    else:
        system_prompt = DEFAULT_SYSTEM_PROMPT

    app = FastSkillsChat(
        skills_dir=_resolve_skills_dir(),
        workdir=None,
        system_prompt=system_prompt,
    )
    app.run()


if __name__ == "__main__":
    main()
