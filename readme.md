# ⚡ FastSkills — Give Any Agent the Same Skill Engine Behind Claude, OpenClaw & nanobot.
<p align="center">
  <em>The Agent Skills engine — extracted, standalone, and universal.</em>
</p>


<p align="center">
  <a href="https://pypi.org/project/nanobot-ai/"><img src="https://img.shields.io/pypi/v/nanobot-ai" alt="PyPI"></a>
  <img src="https://img.shields.io/badge/python-≥3.11-blue" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
  <a href="https://discord.gg/GepNysMP"><img src="https://img.shields.io/badge/Discord-Community-5865F2?style=flat&logo=discord&logoColor=white" alt="Discord"></a>
</p>

## The Problem

Claude Code, GitHub Copilot, OpenAI Codex, and Cursor all have a skill engine built in — the agent discovers `SKILL.md` playbooks, reads them on demand, and follows structured instructions to produce consistent, high-quality output. That's why they can generate professional documents, presentations, and code without being told how every time.

**But the skill engine is locked inside each product.**

If you're building with LangChain, CrewAI, AutoGen, Smolagents, or any custom agent — you get nothing. No skill discovery, no progressive disclosure, no structured playbooks. You'd have to build the entire engine from scratch.

## The Solution

FastSkills extracts the skill engine into a **standalone MCP server**. One command gives any agent the same capability:

```bash
uvx fastskills --skills-dir ./skills
```

That's it. Your agent can now discover, read, and execute any `SKILL.md` — the same open standard used by Claude Code, Copilot, Codex, OpenClaw, and nanobot.

**No framework adoption. No code changes. No SDK integration. Just MCP.**

---

## Before & After

```
WITHOUT FastSkills:

  Claude Code ──── has skill engine ──── can use 40,000+ skills
  Copilot     ──── has skill engine ──── can use 40,000+ skills
  Codex CLI   ──── has skill engine ──── can use 40,000+ skills
  OpenClaw    ──── has skill engine ──── can use 40,000+ skills
  nanobot     ──── has skill engine ──── can use 40,000+ skills
  ─────────────────────────────────────────────────────────────
  LangChain   ──── nothing           ──── ✗
  CrewAI      ──── nothing           ──── ✗
  AutoGen     ──── nothing           ──── ✗
  Your agent  ──── nothing           ──── ✗


WITH FastSkills:

  Any agent   ──── FastSkills (MCP) ──── can use 40,000+ skills ✓
```

---

## What's New

- **2025-06-xx** — v0.x.x: Initial release with 17 bundled skills and TUI chat interface.

---

## Feature Showcase

<table>
<tr>
<td width="50%" align="center">
<b>Document Generation</b><br/>
<em>Create professional PPTX, DOCX, PDF, and XLSX</em><br/><br/>
<img src="assets/demo-documents.gif" alt="Document generation demo" width="380"/>
</td>
<td width="50%" align="center">
<b>Design & Frontend</b><br/>
<em>Generate themes, brand guidelines, and frontend designs</em><br/><br/>
<img src="assets/demo-design.gif" alt="Design demo" width="380"/>
</td>
</tr>
<tr>
<td width="50%" align="center">
<b>Authoring & Content</b><br/>
<em>Co-author docs, write internal comms, build web artifacts</em><br/><br/>
<img src="assets/demo-authoring.gif" alt="Authoring demo" width="380"/>
</td>
<td width="50%" align="center">
<b>Developer Tools</b><br/>
<em>Build MCP servers, create new skills, test web apps</em><br/><br/>
<img src="assets/demo-developer.gif" alt="Developer tools demo" width="380"/>
</td>
</tr>
</table>

---

## Why Not Just Use OpenClaw or nanobot?

You can — and they're great. But they solve a different problem:

| | OpenClaw | nanobot | FastSkills |
|---|---|---|---|
| **What it is** | Full AI assistant platform | Lightweight AI assistant | Standalone skill engine |
| **To use skills** | Adopt the entire platform (Gateway, config, workspace) | Install the framework, use its agent loop | One command or one JSON block |
| **Lock-in** | High — skills require OpenClaw runtime | Medium — skills require nanobot agent | **None** — standard MCP protocol |
| **Works with your agent?** | No — you use OpenClaw's agent | No — you use nanobot's agent | **Yes** — any MCP client |
| **Lines of code** | 430,000+ | ~4,000 | ~800 |
| **Install** | `npm install -g openclaw && openclaw onboard --install-daemon` | `pip install nanobot && nanobot onboard` | `uvx fastskills --skills-dir ./skills` |

OpenClaw and nanobot are **platforms** — you adopt their agent, their runtime, their ecosystem. FastSkills is a **building block** — it gives your existing agent skill capabilities without replacing anything.

---

## Quick Start

### Connect any agent in 30 seconds

Add one block to your MCP client config (Claude Desktop, Cursor, VS Code, Windsurf, Goose, or any custom agent):

```json
{
  "mcpServers": {
    "fastskills": {
      "command": "uvx",
      "args": ["fastskills", "--skills-dir", "~/.fastskills/skills", "--workdir", "/path/to/output"]
    }
  }
}
```

Your agent now has skill discovery, skill reading, and a full execution toolkit (bash, file creation, string replacement) — matching the tool surface that Claude Code provides natively.

> **What's `uvx`?** It's a tool from [uv](https://docs.astral.sh/uv/) that runs Python packages in isolated environments — no install step needed. Install it with `curl -LsSf https://astral.sh/uv/install.sh | sh` or `brew install uv`.

### Or use the built-in TUI

```bash
# One-liner install
curl -sSL https://raw.githubusercontent.com/nj19257/FastSkills/main/install.sh | bash

# Start chatting
fastskills_cli
```

<p align="center">
  <img src="assets/tui-screenshot.png" alt="FastSkills TUI" width="700"/>
</p>

On first launch you'll be prompted for your **OpenRouter API key** and **model**. The bundled 17 skills are automatically discovered.

| Command | What it does |
|---------|-------------|
| `/help` | Show all commands |
| `/model` | Change AI model |
| `/skills` | List available skills |
| `/status` | Show connection info |
| `Ctrl+H` | Toggle sidebar |

---

## How the Skill Engine Works

The same progressive disclosure pattern used by Claude Code, Copilot, and Codex:

```
 ┌──────┐    ┌──────┐    ┌──────┐    ┌────────┐    ┌─────────┐
 │ Scan │───►│Match │───►│ Read │───►│ Follow │───►│ Deliver │
 └──────┘    └──────┘    └──────┘    └────────┘    └─────────┘
  metadata    best fit    SKILL.md    run scripts    output
   ~100 tok   agent       full body   bash/create    consistent
   per skill  decides     on demand   on demand      quality
```

1. **Scan** — `list_skills` returns names + descriptions (~100 tokens per skill)
2. **Match** — The agent decides which skill fits the task
3. **Read** — `view(path=...)` reads the full `SKILL.md` into context
4. **Follow** — `bash_tool` runs scripts, `file_create` writes output
5. **Deliver** — Consistent, high-quality results every time

The agent only loads what it needs, when it needs it. No context window bloat.

### System Prompt

FastSkills includes a gold-standard system prompt at [`prompt/gold_standard_prompt.yaml`](prompt/gold_standard_prompt.yaml) that teaches any agent the discover → read → execute workflow. Use it directly or reference it to build your own.

---

## Architecture

<p align="center">
  <img src="assets/architecture.png" alt="FastSkills Architecture" width="700"/>
</p>

```
┌─────────────────┐        MCP        ┌──────────────┐      filesystem     ┌──────────────┐
│   Your Agent    │◄────────────────►│  FastSkills   │◄──────────────────►│   skills/    │
│  (any MCP       │     protocol      │  MCP Server   │   read SKILL.md    │  ├── pptx/   │
│   client)       │                   │  (FastMCP)    │   run scripts      │  ├── docx/   │
└─────────────────┘                   └──────────────┘                     │  ├── pdf/    │
                                                                           │  └── ...     │
                                                                           └──────────────┘
```

| Tool | Purpose |
|------|---------|
| `list_skills` | Discover available skills with name, description, and SKILL.md path |
| `view` | Read files (including SKILL.md), list directories, inspect images |
| `bash_tool` | Execute shell commands and skill scripts (120s timeout) |
| `file_create` | Create output files with content |
| `str_replace` | Make targeted string replacements in existing files |

---

## Bundled Skills (17)

| Category | Skills |
|----------|--------|
| **Documents** | `pptx` · `docx` · `pdf` · `xlsx` |
| **Design** | `theme-factory` · `brand-guidelines` · `canvas-design` · `frontend-design` · `algorithmic-art` |
| **Authoring** | `doc-coauthoring` · `internal-comms` · `web-artifacts-builder` · `slack-gif-creator` |
| **Developer** | `mcp-builder` · `skill-creator` · `webapp-testing` · `duckduckgo-websearch` |

### Add Your Own

Drop a folder with a `SKILL.md` into your skills directory. FastSkills picks it up automatically:

```
~/.fastskills/skills/
├── pptx/
│   └── SKILL.md
├── my-custom-skill/
│   ├── SKILL.md
│   ├── scripts/
│   │   └── generate.py
│   └── references/
│       └── style-guide.md
└── ...
```

<details>
<summary>Example SKILL.md</summary>

```markdown
---
name: api-documentation
description: Generate consistent API documentation following team standards.
  Use when writing docs for REST endpoints, SDKs, or internal APIs.
---

# API Documentation Skill

## When to Use
Use this skill when the user asks to document an API, generate endpoint
references, or create SDK documentation.

## Instructions
1. Read the source code or endpoint definitions
2. Extract parameters, return types, and error codes
3. Generate documentation following the template in ./references/template.md
4. Include code examples for each endpoint
```

</details>

### Skill Sources

The **MCP server** loads skills from a single directory specified by `--skills-dir`. The **TUI** (`fastskills_cli`) auto-resolves from two locations:

| Location | Used by | Description |
|----------|---------|-------------|
| `--skills-dir` path | MCP server | The single source of skills for the MCP server (required flag) |
| Repo-bundled `skills/` | TUI | 17 bundled skills shipped with FastSkills |
| `~/.fastskills/skills/` | TUI | User-global skills auto-discovered by the TUI |

You can also use skills from [Anthropic's skills repo](https://github.com/anthropics/skills), [ClawHub](https://clawhub.ai) (3,000+ community skills), or any community source.

---

## The Agent Skills Ecosystem

FastSkills uses the same open standard adopted across the industry:

| Platform | Skills Support | How |
|----------|:-------------:|-----|
| **Claude Code** | ✅ Native | `.claude/skills/` directory |
| **GitHub Copilot** | ✅ Native | `.github/skills/` directory |
| **OpenAI Codex CLI** | ✅ Native | Same SKILL.md format |
| **Cursor** | ✅ Native | Built-in skill engine |
| **OpenClaw** | ✅ Native | AgentSkills-compatible folders |
| **nanobot** | ✅ Native | Bundled + custom skills |
| **LangChain / CrewAI / AutoGen** | ❌ → ✅ | **Via FastSkills** |
| **Any MCP-compatible agent** | ❌ → ✅ | **Via FastSkills** |

Skills are portable. Write once, use everywhere.

---

## Configuration

| Flag | Description | Default |
|------|-------------|---------|
| `--skills-dir` | Root directory containing skill folders | *(required)* |
| `--workdir` | Working directory for command execution and file output | Current directory |

```bash
# Start the MCP server
uvx fastskills --skills-dir /path/to/skills

# With a working directory for file output and command execution
uvx fastskills --skills-dir /path/to/skills --workdir /path/to/output
```

> **Tip:** Pair FastSkills with a web search MCP server (like [mcp-server-fetch](https://github.com/modelcontextprotocol/servers/tree/main/src/fetch)) so your agent can research topics alongside executing skills. Skills handle the "how," web search handles the "what."

---

## What's Next

- **ClawHub Integration** — Browse, search, and install from [ClawHub](https://clawhub.ai) (3,000+ community skills) without leaving your agent

---

## Contributing

Contributions welcome — new skills, core improvements, or docs:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-skill`)
3. Commit your changes
4. Open a Pull Request

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Acknowledgments

- Follows the [Agent Skills](https://agentskills.io) open standard
- Built with [FastMCP](https://github.com/jlowin/fastmcp)
- Inspired by the skill systems in [Claude Code](https://claude.ai), [OpenClaw](https://openclaw.ai), and [nanobot](https://github.com/HKUDS/nanobot)

---

<p align="center">
  <b>The skill engine is locked inside coding agents. FastSkills sets it free.</b><br/>
  <sub>⭐ Star this repo if FastSkills is useful to you</sub>
</p>
