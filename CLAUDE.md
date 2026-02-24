# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FastSkills is an MCP server that reimplements Claude's skill engine as a standalone service. It exposes the Agent Skills workflow (discover, read, follow skills) via MCP tools so any MCP-compatible agent can use structured `SKILL.md` playbooks. Built with Python and the FastMCP framework.

## Running the Server

```bash
pip install fastskills
fastskills --skills-dir /path/to/skills   # start the MCP server

# Or run without installing via uvx
uvx fastskills --skills-dir /path/to/skills
```

## Architecture

### MCP Server (`src/mcp_server.py`)

Single-file FastMCP server exposing 7 tools:

| Tool | Purpose |
|------|---------|
| `bash_tool` | Execute bash commands (120s timeout) |
| `str_replace` | Replace a unique string in a file |
| `file_create` | Create a new file with content |
| `view` | View files, directories (2-level tree), or images |
| `search_cloud_skills` | Search the cloud skill catalog by keyword |
| `read_skill` | Read a skill's full SKILL.md content |
| `list_local_skills` | List all locally available skills with descriptions |

Key internals:
- `_base_dir` (from `core.config.WORKSPACE_DIR`) is the working directory; relative paths resolve against it
- `configure(base_dir=...)` sets the working context at startup
- Skill resolution uses `core.skill_engine.skill_resolver` (lazy-imported inside tool functions)
- Cloud catalog search uses `cli.skill_search` (also lazy-imported)

### Skill Format (Agent Skills Standard)

Each skill is a directory under `skills/` containing:

```
skill-name/
├── SKILL.md        # Required — YAML frontmatter (name, description) + markdown instructions
├── scripts/        # Optional — executable Python/Bash/JS the agent can invoke
├── references/     # Optional — supplementary docs loaded on demand
└── assets/         # Optional — templates, images, fonts
```

Skills are loaded from three locations (in priority order):
1. `./skills/` — project-local
2. `~/.fastskills/skills/` — user-global
3. Custom path via `--skills-dir` or `FASTSKILLS_DIR`

### Progressive Disclosure Pattern

The core design principle: metadata is cheap, full instructions are loaded on demand, scripts run only when called. Agents first list skills (metadata only), then read the full SKILL.md for the matched skill, then run scripts as needed.

## Bundled Skills (17 skills in `skills/`)

Document skills: `pptx`, `docx`, `pdf`, `xlsx`
Design skills: `theme-factory`, `brand-guidelines`, `canvas-design`, `frontend-design`, `algorithmic-art`
Authoring skills: `doc-coauthoring`, `internal-comms`, `web-artifacts-builder`, `slack-gif-creator`
Developer skills: `mcp-builder`, `skill-creator`, `webapp-testing`, `serpapi`

## Key Dependencies

- **FastMCP** — MCP protocol framework
- **Python 3** — core server
- Skills may require additional tools: LibreOffice (`soffice`), Poppler (`pdftoppm`), Node.js (pptxgenjs, docx-js), Playwright, pypdf/pdfplumber/reportlab, python-docx, openpyxl
