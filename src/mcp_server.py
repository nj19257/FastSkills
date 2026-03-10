"""FastSkills MCP Server.

An MCP server that gives any agent the ability to discover and use
Agent Skills (SKILL.md) — the same skill system used by Claude Code,
OpenClaw, nanobot, GitHub Copilot, and OpenAI Codex.

Usage:
    uvx fastskills --skills-dir /path/to/skills [--workdir /path/to/workdir]
    uv run fastskills --skills-dir /path/to/skills [--workdir /path/to/workdir]

The agent workflow:
    1. list_skills()          → see available skills + file paths
    2. view(path=<skill>)     → read the SKILL.md instructions
    3. follow the instructions → execute the task with expertise
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
import zipfile
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
    parser.add_argument(
        "--workdir",
        type=str,
        default=None,
        help="Working directory where output files are created and commands run. Defaults to the current working directory.",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Server setup
# ---------------------------------------------------------------------------

# Resolved at startup via main()
_skills_dir: Path = Path.cwd()
_workdir: Path = Path.cwd()

mcp = FastMCP("fastskills_mcp")


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


# ---------------------------------------------------------------------------
# SkillsMP API helper
# ---------------------------------------------------------------------------

_SKILLSMP_API = "https://skillsmp.com/api/v1/skills/ai-search"


def _skillsmp_search(query: str) -> list[dict]:
    """Call the SkillsMP AI-search API, return the list of result dicts."""
    api_key = os.environ["SKILLSMP_API_KEY"]
    url = f"{_SKILLSMP_API}?q={urllib.parse.quote_plus(query)}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "FastSkills/1.0",
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return body.get("data", {}).get("data", [])


def _extract_skill_meta(r: dict) -> tuple[str, str, str, str]:
    """Extract (name, description, skillUrl, githubUrl) from a search result.

    The API returns two formats:
      - Rich: {"skill": {"name", "description", "skillUrl", "githubUrl", ...}}
      - Raw:  {"attributes": {"file": {"skill-name", "skill-id"}}, "content": [...]}
    """
    skill = r.get("skill")
    if skill and skill.get("name"):
        return (
            skill.get("name", "(unnamed)"),
            skill.get("description", ""),
            skill.get("skillUrl", ""),
            skill.get("githubUrl", ""),
        )

    # Fallback: raw vector-search result
    attrs = r.get("attributes", {}).get("file", {})
    name = attrs.get("skill-name", "")
    skill_id = attrs.get("skill-id", "")
    skill_url = f"https://skillsmp.com/skills/{skill_id}" if skill_id else ""

    # Parse description from SKILL.md frontmatter in content
    desc = ""
    content_blocks = r.get("content", [])
    if content_blocks:
        text = content_blocks[0].get("text", "")
        fm_name, fm_desc = _parse_frontmatter(text)
        if not name:
            name = fm_name
        desc = fm_desc

    return (name or "(unnamed)", desc, skill_url, "")


# ===================================================================
# Tool 2: search_cloud_skills
# ===================================================================

def search_cloud_skills(
    query: Annotated[str, "Search query for finding skills in the cloud catalog."],
) -> str:
    """Search the cloud skill catalog (SkillsMP) by keyword.

    Searches the SkillsMP cloud catalog for skills matching the query.
    Requires the SKILLSMP_API_KEY environment variable to be set.

    Use install_cloud_skill with the returned skill URL to install a skill.

    Args:
        query: Search query for finding skills.

    Returns:
        str: Formatted list of matching skills, or an error message.
    """
    try:
        results = _skillsmp_search(query)
    except urllib.error.HTTPError as exc:
        return f"search_cloud_skills ERR: HTTP {exc.code} from SkillsMP API."
    except Exception as exc:
        return f"search_cloud_skills ERR: {exc}"

    if not results:
        return f"No cloud skills found for: {query}"

    # Filter out ghost results with no useful data
    parsed = []
    for r in results:
        name, desc, skill_url, github_url = _extract_skill_meta(r)
        if name == "(unnamed)" and not skill_url:
            continue
        parsed.append((name, desc, skill_url, github_url))

    if not parsed:
        return f"No cloud skills found for: {query}"

    lines: list[str] = [f"Found {len(parsed)} cloud skill(s) for \"{query}\":\n"]
    for i, (name, desc, skill_url, github_url) in enumerate(parsed, 1):
        # Truncate description to first sentence, max 120 chars
        if desc:
            first_sentence = desc.split(". ")[0].split(".\n")[0]
            if len(first_sentence) > 120:
                first_sentence = first_sentence[:117] + "..."
            desc = first_sentence
        lines.append(f"{i}. {name} — {desc}" if desc else f"{i}. {name}")
        lines.append(f"   url: {skill_url}" if skill_url else "")
        if github_url:
            lines.append(f"   github: {github_url}")

    lines.append(
        "\nTo install: call install_cloud_skill(skill_url=<url>)"
    )
    return "\n".join(line for line in lines if line)


# ===================================================================
# Tool 3: install_cloud_skill
# ===================================================================

def _resolve_github_url(skill_url: str) -> str:
    """Resolve a SkillsMP skill URL to its GitHub directory URL."""
    skill_id = skill_url.rstrip("/").split("/")[-1]

    # Build search queries from the skill ID.
    # ID format: "author-repo-...-skills-name-skill-md"
    raw = re.sub(r"-skill-md$", "", skill_id)
    parts = raw.split("-skills-")
    skill_name = parts[-1].replace("-", " ") if len(parts) > 1 else raw.replace("-", " ")

    # Try skill name first, then with author context for better matching
    queries = [skill_name]
    if len(parts) > 1:
        author = parts[0].split("-")[0]
        queries.append(f"{skill_name} {author}")

    for query in queries:
        results = _skillsmp_search(query)
        for r in results:
            skill = r.get("skill", {})
            if skill.get("id") == skill_id:
                gh = skill.get("githubUrl", "")
                if gh:
                    return gh
                raise ValueError(f"Skill found but has no GitHub URL: {skill_id}")

    raise ValueError(
        f"Could not resolve skill: {skill_id}. "
        "Try install_cloud_skill with the GitHub URL instead."
    )


def _parse_github_tree_url(github_url: str) -> tuple[str, str, str, str]:
    """Parse a GitHub tree URL into (owner, repo, branch, path).

    Example: https://github.com/AIDotNet/OpenCowork/tree/main/resources/skills/web-scraper
    Returns: ("AIDotNet", "OpenCowork", "main", "resources/skills/web-scraper")
    """
    # Strip scheme and host
    path = github_url.replace("https://github.com/", "").replace("http://github.com/", "")
    parts = path.split("/")
    # parts: [owner, repo, "tree", branch, ...path_segments]
    if len(parts) < 5 or parts[2] != "tree":
        raise ValueError(f"Not a valid GitHub tree URL: {github_url}")
    owner = parts[0]
    repo = parts[1]
    branch = parts[3]
    sub_path = "/".join(parts[4:])
    return owner, repo, branch, sub_path


def install_cloud_skill(
    skill_url: Annotated[
        str,
        "SkillsMP skill URL (e.g. https://skillsmp.com/skills/<id>) "
        "or GitHub tree URL (e.g. https://github.com/owner/repo/tree/main/skills/name).",
    ],
) -> str:
    """Install a skill from the cloud catalog into the local skills directory.

    Downloads the skill folder from GitHub and extracts it into the
    configured skills directory so it becomes available via list_skills.

    Accepts either a SkillsMP skill URL (from search_cloud_skills output)
    or a direct GitHub tree URL pointing to the skill directory.

    Args:
        skill_url: URL of the skill to install.

    Returns:
        str: Confirmation with the installed skill path, or an error message.
    """
    try:
        # Resolve to GitHub URL if needed
        if "github.com" in skill_url:
            github_url = skill_url
        else:
            github_url = _resolve_github_url(skill_url)

        owner, repo, branch, sub_path = _parse_github_tree_url(github_url)
        skill_name = sub_path.rstrip("/").split("/")[-1]

        # Download repo zip
        zip_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip"
        req = urllib.request.Request(zip_url, headers={"User-Agent": "FastSkills/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            zip_data = resp.read()

        # Extract only the skill subdirectory
        prefix = f"{repo}-{branch}/{sub_path}/"
        dest = _skills_dir / skill_name

        extracted = 0
        with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
            for info in zf.infolist():
                if not info.filename.startswith(prefix):
                    continue
                rel = info.filename[len(prefix):]
                if not rel:
                    continue
                out_path = dest / rel
                if info.is_dir():
                    out_path.mkdir(parents=True, exist_ok=True)
                else:
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    out_path.write_bytes(zf.read(info.filename))
                    extracted += 1

        if extracted == 0:
            return (
                f"install_cloud_skill ERR: no files found under {sub_path}/ "
                f"in {owner}/{repo}@{branch}. The path may be incorrect."
            )

        return f"install_cloud_skill OK: installed {extracted} file(s) to {dest}"

    except ValueError as exc:
        return f"install_cloud_skill ERR: {exc}"
    except urllib.error.HTTPError as exc:
        return f"install_cloud_skill ERR: HTTP {exc.code} downloading from GitHub."
    except Exception as exc:
        return f"install_cloud_skill ERR: {exc}"


# ===================================================================
# Tool 4: view
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
    if not p.is_absolute():
        p = _workdir / p

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
# Tool 5: bash_tool  (registered dynamically in main() with workdir)
# ===================================================================

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
            cwd=str(_workdir),
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
# Tool 6: file_create
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
    if not p.is_absolute():
        p = _workdir / p
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(file_text, encoding="utf-8")
    except Exception as exc:
        return f"file_create ERR: {exc}"
    return f"file_create OK: {p}"


# ===================================================================
# Tool 7: str_replace
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
    if not p.is_absolute():
        p = _workdir / p

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
    global _skills_dir, _workdir

    args = _parse_args()
    _skills_dir = Path(args.skills_dir).resolve()

    if not _skills_dir.exists():
        print(f"Warning: skills directory does not exist: {_skills_dir}", file=sys.stderr)
    elif not _skills_dir.is_dir():
        print(f"Error: --skills-dir is not a directory: {_skills_dir}", file=sys.stderr)
        sys.exit(1)

    if args.workdir:
        _workdir = Path(args.workdir).expanduser().resolve()
    else:
        _workdir = Path.cwd().resolve()
    _workdir.mkdir(parents=True, exist_ok=True)
    print(f"Working directory: {_workdir}", file=sys.stderr)

    # Register bash_tool with the resolved workdir baked into its description
    bash_description = f"""Run a bash command in the working directory.

    Use this to execute scripts bundled with skills, install dependencies,
    or perform any shell operation the skill instructions require.
    Working directory: {_workdir}
    All commands execute with this as cwd.
    Output files go here by default, but new skills must be created in the skills directory ({_skills_dir}) so they are discoverable via list_skills.

    Args:
        command: The bash command to run.

    Returns:
        str: Command stdout/stderr output, or an error message.
    """
    mcp.tool(name="bash_tool", description=bash_description)(bash_tool)

    # Register cloud skill tools only if API key is configured
    if os.environ.get("SKILLSMP_API_KEY"):
        mcp.tool(name="search_cloud_skills")(search_cloud_skills)
        mcp.tool(name="install_cloud_skill")(install_cloud_skill)

    # Run with stdio transport (standard for local MCP servers)
    mcp.run()


if __name__ == "__main__":
    main()