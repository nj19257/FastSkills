"""FastSkills MCP Server.

An MCP server that gives any agent the ability to discover and use
Agent Skills (SKILL.md) — the same skill system used by Claude Code,
OpenClaw, nanobot, GitHub Copilot, and OpenAI Codex.

Usage:
    uvx fastskills --skills-dir /path/to/skills
    uv run fastskills --skills-dir /path/to/skills

The agent workflow:
    1. list_skills()          → see available skills + file paths
    2. view(path=<skill>)     → read the SKILL.md instructions
    3. follow the instructions → execute the task with expertise
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Annotated

from fastmcp import FastMCP

# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="fastskills",
        description="FastSkills MCP Server — Agent Skills for any MCP-compatible agent.",
    )
    parser.add_argument(
        "--skills-dir",
        type=str,
        required=True,
        help="Path to the root directory containing skill folders (each with a SKILL.md).",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Server instructions — surfaced to any connected agent
# ---------------------------------------------------------------------------

SERVER_INSTRUCTIONS = """\
You have access to Agent Skills — an open standard for giving AI agents \
reusable expertise and capabilities.

Skills are folders containing a SKILL.md file with structured instructions, \
best practices, and optional scripts/resources. They teach you how to perform \
specific tasks at a high level of quality — from creating documents and \
presentations to code review, data analysis, and custom workflows.

## How to use skills

Before starting any task, check if a relevant skill exists:

1. Call `list_skills` to see all available skills with descriptions and file paths.
2. If a skill matches your task, call `view` with the skill's path to read its \
SKILL.md instructions.
3. Follow the instructions in the SKILL.md to complete the task. The file will \
contain best practices, step-by-step guidance, and references to any bundled \
scripts or resources you should use.

Skills use progressive disclosure: the SKILL.md may reference additional files \
(scripts/, references/, assets/) in the skill's directory. Only read these when \
the instructions tell you to — this keeps your context focused.

## When to use skills

- ALWAYS check `list_skills` when you receive a task that involves creating \
files, documents, code, or following a specific workflow.
- If a skill exists for the task, read it BEFORE starting work.
- If no matching skill exists, proceed with your own knowledge.
- You can use multiple skills for a single task if needed.

## Available tools

- `list_skills` — Discover available skills and their SKILL.md paths
- `view` — Read SKILL.md files and explore skill directories
- `bash_tool` — Execute shell commands and run bundled scripts
- `file_create` — Create new files
- `str_replace` — Edit existing files
"""

# ---------------------------------------------------------------------------
# Server setup
# ---------------------------------------------------------------------------

mcp = FastMCP("fastskills_mcp", instructions=SERVER_INSTRUCTIONS)

# Resolved at startup via main()
_skills_dir: Path = Path.cwd()


# ---------------------------------------------------------------------------
# SKILL.md frontmatter parser
# ---------------------------------------------------------------------------

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)
_YAML_NAME_RE = re.compile(r"^name:\s*(.+)", re.MULTILINE)
_YAML_DESC_RE = re.compile(r"^description:\s*(.+(?:\n\s+.+)*)", re.MULTILINE)


def _parse_frontmatter(text: str) -> tuple[str, str]:
    """Extract name and description from SKILL.md YAML frontmatter.

    Returns:
        (name, description) — either may be empty if not found.
    """
    fm_match = _FRONTMATTER_RE.match(text)
    if not fm_match:
        return "", ""

    frontmatter = fm_match.group(1)

    name_match = _YAML_NAME_RE.search(frontmatter)
    name = name_match.group(1).strip().strip("'\"") if name_match else ""

    desc_match = _YAML_DESC_RE.search(frontmatter)
    if desc_match:
        raw = desc_match.group(1)
        desc = " ".join(line.strip() for line in raw.splitlines())
        desc = desc.strip().strip("'\"")
    else:
        desc = ""

    return name, desc


# ===================================================================
# Tool 1: list_skills
# ===================================================================

@mcp.tool
def list_skills() -> str:
    """List all available skills with their name, description, and SKILL.md path.

    Returns every skill found in the configured skills directory. Each entry
    includes the skill's name, description (from YAML frontmatter), and the
    full file path to its SKILL.md.

    To use a skill: call the view tool with the skill's path to read its
    SKILL.md before starting the task. The file contains best practices and
    step-by-step instructions the agent should follow.

    Returns:
        str: Formatted list of skills with metadata and file paths.
    """
    if not _skills_dir.exists() or not _skills_dir.is_dir():
        return f"list_skills ERR: skills directory not found: {_skills_dir}"

    skills: list[dict[str, str]] = []

    try:
        for skill_dir in sorted(_skills_dir.iterdir(), key=lambda p: p.name.lower()):
            if not skill_dir.is_dir():
                continue

            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue

            # Parse frontmatter
            try:
                text = skill_md.read_text(encoding="utf-8")
                name, desc = _parse_frontmatter(text)
            except Exception:
                name, desc = "", ""

            skills.append({
                "name": name or skill_dir.name,
                "description": desc,
                "path": str(skill_md),
            })
    except PermissionError:
        return f"list_skills ERR: permission denied reading {_skills_dir}"

    if not skills:
        return f"(no skills found in {_skills_dir})"

    lines: list[str] = [f"Found {len(skills)} skill(s) in {_skills_dir}:\n"]
    for s in skills:
        lines.append(f"- {s['name']}")
        if s["description"]:
            lines.append(f"  description: {s['description']}")
        lines.append(f"  path: {s['path']}")

    lines.append(
        "\nTo use a skill: call view(path=<skill path>) to read its "
        "SKILL.md before starting the task."
    )
    return "\n".join(lines)


# ===================================================================
# Tool 2: view
# ===================================================================

@mcp.tool
def view(
    path: Annotated[str, "Absolute path to a file or directory."],
    view_range: Annotated[
        list[int] | None,
        "Optional [start_line, end_line] range (1-indexed). Use [start, -1] to read from start to end of file.",
    ] = None,
) -> str:
    """Read a file's contents or list a directory's structure.

    Use this tool to read SKILL.md files returned by list_skills, or to
    explore skill directories for bundled scripts, references, and assets.

    Supported path types:
    - Directories: Lists files up to 2 levels deep, ignoring hidden items.
    - Text files: Displays numbered lines. Optionally specify view_range.
    - Image files (.jpg, .png, .gif, .webp): Returns file metadata.

    Args:
        path: Absolute path to the file or directory.
        view_range: Optional line range as [start, end] (1-indexed).

    Returns:
        str: File contents with line numbers, or directory tree listing.
    """
    p = Path(path)

    if not p.exists():
        return f"view ERR: not found: {p}"

    # Directory listing
    if p.is_dir():
        return _view_directory(p, max_depth=2)

    # Image files
    _IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    if p.suffix.lower() in _IMAGE_EXTS:
        size = p.stat().st_size
        return f"[Image file: {p} ({size} bytes)]"

    # Text files
    try:
        content = p.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return f"view ERR: cannot read {p}: {exc}"

    lines = content.splitlines()

    if view_range is not None and len(view_range) == 2:
        start, end = view_range
        start = max(1, start)
        if end == -1:
            end = len(lines)
        end = min(end, len(lines))
        lines = lines[start - 1 : end]
        offset = start
    else:
        offset = 1

    numbered = [f"{offset + i:>6}\t{line}" for i, line in enumerate(lines)]
    return "\n".join(numbered)


def _view_directory(
    path: Path,
    max_depth: int = 2,
    current_depth: int = 0,
    prefix: str = "",
) -> str:
    lines: list[str] = []
    if current_depth == 0:
        lines.append(str(path) + "/")

    try:
        entries = sorted(
            path.iterdir(),
            key=lambda x: (not x.is_dir(), x.name.lower()),
        )
    except PermissionError:
        return f"{prefix}[permission denied]"

    entries = [
        e for e in entries if not e.name.startswith(".") and e.name != "node_modules"
    ]

    for i, entry in enumerate(entries):
        is_last = i == len(entries) - 1
        connector = "└── " if is_last else "├── "
        suffix = "/" if entry.is_dir() else ""
        lines.append(f"{prefix}{connector}{entry.name}{suffix}")
        if entry.is_dir() and current_depth < max_depth:
            extension = "    " if is_last else "│   "
            sub = _view_directory(entry, max_depth, current_depth + 1, prefix + extension)
            if sub:
                lines.append(sub)

    return "\n".join(lines)


# ===================================================================
# Tool 3: bash_tool
# ===================================================================

@mcp.tool
def bash_tool(
    command: Annotated[str, "Bash command to execute."],
) -> str:
    """Run a bash command in the working directory.

    Use this to execute scripts bundled with skills, install dependencies,
    or perform any shell operation the skill instructions require.

    Args:
        command: The bash command to run.

    Returns:
        str: Command stdout/stderr output, or an error message.
    """
    if not command.strip():
        return "bash_tool ERR: empty command"

    env = os.environ.copy()

    try:
        proc = subprocess.run(
            ["bash", "-c", command],
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return f"bash_tool TIMEOUT after 120s: {command}"
    except FileNotFoundError as exc:
        return f"bash_tool ERR: shell not found: {exc}"
    except Exception as exc:
        return f"bash_tool ERR: {exc}"

    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()
    if proc.returncode != 0:
        return f"bash_tool ERR (exit {proc.returncode}):\n{stderr or stdout}"
    return stdout or stderr or "OK"


# ===================================================================
# Tool 4: file_create
# ===================================================================

@mcp.tool
def file_create(
    path: Annotated[str, "Path to the file to create."],
    file_text: Annotated[str, "Content to write to the file."],
) -> str:
    """Create a new file with the given content.

    Creates parent directories if they don't exist. Overwrites if the
    file already exists.

    Args:
        path: Absolute or relative path for the new file.
        file_text: The content to write.

    Returns:
        str: Confirmation message with the created file path.
    """
    p = Path(path)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(file_text, encoding="utf-8")
    except Exception as exc:
        return f"file_create ERR: {exc}"
    return f"file_create OK: {p}"


# ===================================================================
# Tool 5: str_replace
# ===================================================================

@mcp.tool
def str_replace(
    path: Annotated[str, "Path to the file to edit."],
    old_str: Annotated[str, "String to find and replace (must appear exactly once)."],
    new_str: Annotated[str, "Replacement string (empty to delete)."] = "",
) -> str:
    """Replace a unique string in a file.

    The old_str must appear exactly once in the file to avoid ambiguous edits.

    Args:
        path: Path to the file to edit.
        old_str: The string to replace (must be unique in the file).
        new_str: The replacement string. Use empty string to delete.

    Returns:
        str: Confirmation message or error details.
    """
    p = Path(path)

    if not p.exists():
        return f"str_replace ERR: file not found: {p}"
    if not p.is_file():
        return f"str_replace ERR: not a file: {p}"

    content = p.read_text(encoding="utf-8", errors="replace")
    count = content.count(old_str)

    if count == 0:
        return f"str_replace ERR: old_str not found in {p}"
    if count > 1:
        return f"str_replace ERR: old_str appears {count} times in {p} (must be unique)"

    new_content = content.replace(old_str, new_str, 1)
    p.write_text(new_content, encoding="utf-8")
    return f"str_replace OK: {p}"


# ===================================================================
# Entry point
# ===================================================================

def main() -> None:
    """Parse CLI args and start the MCP server via stdio transport."""
    global _skills_dir

    args = _parse_args()
    _skills_dir = Path(args.skills_dir).resolve()

    if not _skills_dir.exists():
        print(f"Warning: skills directory does not exist: {_skills_dir}", file=sys.stderr)
    elif not _skills_dir.is_dir():
        print(f"Error: --skills-dir is not a directory: {_skills_dir}", file=sys.stderr)
        sys.exit(1)

    # Run with stdio transport (standard for local MCP servers)
    mcp.run()


if __name__ == "__main__":
    main()