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

Single-file FastMCP server exposing 5 tools:

| Tool | Purpose |
|------|---------|
| `list_skills` | Discover available skills with name, description, and SKILL.md path |
| `view` | Read files (including SKILL.md), list directories (2-level tree), inspect images |
| `bash_tool` | Execute shell commands and skill scripts (120s timeout) |
| `file_create` | Create a new file with content |
| `str_replace` | Replace a unique string in a file |

Key internals:
- `_skills_dir` is set via `--skills-dir` CLI flag; `_workdir` defaults to cwd or `--workdir`
- `list_skills` parses YAML frontmatter from each `SKILL.md` in `_skills_dir`
- Agents read skill instructions via `view(path=<SKILL.md>)`

### Skill Format (Agent Skills Standard)

Each skill is a directory under `skills/` containing:

```
skill-name/
├── SKILL.md        # Required — YAML frontmatter (name, description) + markdown instructions
├── scripts/        # Optional — executable Python/Bash/JS the agent can invoke
├── references/     # Optional — supplementary docs loaded on demand
└── assets/         # Optional — templates, images, fonts
```

The MCP server loads skills from a single directory specified by the `--skills-dir` CLI flag. The TUI (`fastskills_cli`) auto-resolves from repo-bundled skills and `~/.fastskills/skills/`.

### Progressive Disclosure Pattern

The core design principle: metadata is cheap, full instructions are loaded on demand, scripts run only when called. Agents first list skills (metadata only), then read the full SKILL.md for the matched skill, then run scripts as needed.

## Bundled Skills (17 skills in `skills/`)

Document skills: `pptx`, `docx`, `pdf`, `xlsx`
Design skills: `theme-factory`, `brand-guidelines`, `canvas-design`, `frontend-design`, `algorithmic-art`
Authoring skills: `doc-coauthoring`, `internal-comms`, `web-artifacts-builder`, `slack-gif-creator`
Developer skills: `mcp-builder`, `skill-creator`, `webapp-testing`, `duckduckgo-websearch`

## Key Dependencies

- **FastMCP** — MCP protocol framework
- **Python 3** — core server
- Skills may require additional tools: LibreOffice (`soffice`), Poppler (`pdftoppm`), Node.js (pptxgenjs, docx-js), Playwright, pypdf/pdfplumber/reportlab, python-docx, openpyxl
