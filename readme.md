# ⚡ FastSkills — Give Any Agent the Same Skill Engine Behind Claude, OpenClaw & nanobot.

**The Agent Skills engine, as an MCP server.**

FastSkills reimplements the skill system used by Claude — where the agent discovers, reads, and follows structured `SKILL.md` playbooks — and exposes it as an MCP server that any agent can connect to.

Same pattern. Same format. Any agent.

FastSkills gives any MCP-compatible agent the same skill abilities that Claude, OpenClaw, and nanobot have built in — without changing a single line of your agent's code.

---

## 🚀 Quick Install

One-liner installation:

```bash
curl -sSL https://raw.githubusercontent.com/nj19257/FastSkills/main/install.sh | bash
```

### 📦 What the installer does

1. Installs [uv](https://docs.astral.sh/uv/) (if not already present)
2. Clones the FastSkills repository
3. Installs Python dependencies (`uv sync --extra cli`)
4. Creates a `fastskills_cli` launcher and symlinks it to your PATH

### After installation

```bash
# Start the TUI chat interface
fastskills_cli

# Or run manually from the repo
cd fastskills && uv run python -m fastskills_cli
```

On first launch you'll be prompted for your **OpenRouter API key** and **model**. The bundled 19 skills are automatically discovered.

### Quick commands inside the TUI

| Command | What it does |
|---|---|
| `/help` | Show all commands |
| `/model` | Change AI model |
| `/skills` | List available skills |
| `/status` | Show connection info |
| `Ctrl+H` | Toggle sidebar |
| `Ctrl+C` | Quit |

---

## What Does Claude's Skill System Actually Do?

When Claude encounters a task like "create a PowerPoint," it doesn't improvise. It follows a specific workflow:

1. **Scan** — Check available skills by reading their metadata (name + description)
2. **Match** — Decide which skill is relevant to the current task
3. **Read** — Load the full `SKILL.md` instructions into context
4. **Follow** — Execute the skill's best practices, run bundled scripts if needed
5. **Deliver** — Produce output that's consistently high quality

This is called **progressive disclosure** — the agent only loads what it needs, when it needs it. Metadata is cheap. Full instructions are loaded on demand. Scripts run only when called.

It's the reason Claude can produce professional documents, presentations, and spreadsheets without being explicitly told how every time. The expertise lives in skills.

**FastSkills packages this entire workflow as MCP tools**, so any agent that speaks MCP can do the same thing.

---

## How It Works

```
┌─────────────────┐        MCP        ┌──────────────┐      filesystem     ┌──────────────┐
│   Your Agent    │◄────────────────►│  FastSkills   │◄──────────────────►│   skills/    │
│  (any MCP       │     protocol      │  MCP Server   │   read SKILL.md    │  ├── pptx/   │
│   client)       │                   │  (FastMCP)    │   run scripts      │  ├── docx/   │
└─────────────────┘                   └──────────────┘                     │  ├── pdf/    │
                                                                           │  └── ...     │
                                                                           └──────────────┘
```

Your agent connects to FastSkills via MCP and gets tools to:

- **`list_skills`** — Discover available skills with name, description, and file path
- **`view`** — Read a skill's SKILL.md instructions or explore its directory
- **`bash_tool`** — Execute shell commands and skill scripts in the working directory
- **`file_create`** — Create output files (documents, scripts, configs)
- **`str_replace`** — Make targeted edits to existing files

The agent decides when and how to use these tools — just like Claude does.

---

## Quick Start

### Installation

```bash
pip install fastskills
```

### Start the MCP Server

```bash
fastskills --skills-dir ~/.fastskills/skills

# Optionally set a working directory for file output and command execution
fastskills --skills-dir ~/.fastskills/skills --workdir ~/projects/my-project
```

### Connect Your Agent

Add FastSkills to any MCP-compatible client. The easiest way is with [`uvx`](https://docs.astral.sh/uv/), which runs the server directly without installing anything:

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

> **What's `uvx`?** It's a tool from [uv](https://docs.astral.sh/uv/) that runs Python packages in isolated environments — no install step needed. Install it with `curl -LsSf https://astral.sh/uv/install.sh | sh` or `brew install uv`.

If you prefer a manual install (via `pip install fastskills`), use `fastskills` directly in your MCP config:

```json
{
  "mcpServers": {
    "fastskills": {
      "command": "fastskills",
      "args": ["--skills-dir", "~/.fastskills/skills", "--workdir", "/path/to/output"]
    }
  }
}
```

Works with Claude Desktop, Cursor, VS Code, Goose, or any custom agent that supports MCP.

> **That's it.** One JSON block in your MCP config transforms any agent into a skill-powered agent — no code changes, no framework adoption, no SDK integration.

> **Best Practice:** Pair FastSkills with a web search MCP server (like [mcp-server-fetch](https://github.com/modelcontextprotocol/servers/tree/main/src/fetch) or a DuckDuckGo search server) so your agent can research topics alongside executing skills. Skills handle the "how," web search handles the "what" — together they cover most real-world tasks.

### System Prompt

FastSkills includes a gold-standard system prompt that teaches your agent how to discover, read, and execute skills. You can find it at [`prompt/gold_standard_prompt.yaml`](prompt/gold_standard_prompt.yaml).

Use it directly as your agent's system prompt, or reference it to build your own. It covers:

- **Startup behavior** — automatically calling `list_skills()` on first message
- **Skill workflow** — the discover → read → execute pattern with a worked example
- **Tool-calling discipline** — when to use tools vs. answer from knowledge
- **File handling** — reading before editing, creating files when appropriate

### Add Skills

Drop skill folders into your skills directory:

```bash
~/.fastskills/skills/
├── pptx/
│   └── SKILL.md
├── docx/
│   └── SKILL.md
├── pdf/
│   ├── SKILL.md
│   └── scripts/
│       └── extract_text.py
└── my-custom-skill/
    └── SKILL.md
```

FastSkills picks them up automatically.

---

## What's a Skill?

A skill is a folder with a `SKILL.md` file — the [Agent Skills open standard](https://agentskills.io). The same format used by Claude Code, OpenClaw, nanobot, GitHub Copilot, and OpenAI Codex.

```
my-skill/
├── SKILL.md           # Instructions with YAML frontmatter
├── scripts/           # Executable code the agent can run
├── references/        # Documentation loaded into context on demand
└── assets/            # Templates, images, and other resources
```

### Example Skill

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

## Style Guide
- Use present tense ("Returns a list of..." not "Will return...")
- Include curl examples for REST endpoints
- Document error responses alongside success responses
```

Skills are portable. Write them once, use them in FastSkills, Claude Code, OpenClaw, nanobot, or any other compatible agent.

---

## The Agent Skills Ecosystem

FastSkills implements the same open standard that's being adopted across the industry:

| Platform | Skills Support | How |
|---|---|---|
| **Claude** | ✅ Native | Built-in skill engine |
| **Claude Code** | ✅ Native | `.claude/skills/` directory |
| **GitHub Copilot** | ✅ Native | Agent Skills in VS Code |
| **OpenAI Codex CLI** | ✅ Native | Same SKILL.md format |
| **OpenClaw** | ✅ Native | AgentSkills-compatible folders |
| **nanobot** | ✅ Native | Bundled + custom skills |
| **Your agent** | ✅ **Via FastSkills** | MCP server — no code changes needed |

---

## Key Features

- **🔌 MCP Server** — Drop-in skills support for any MCP-compatible agent
- **📋 Agent Skills Standard** — Same `SKILL.md` format used by Claude, OpenClaw, nanobot, Copilot, and Codex
- **🔍 Smart Discovery** — Agents match skills to tasks using metadata, same as Claude does
- **📂 Progressive Disclosure** — Metadata first, full instructions on demand, scripts only when needed
- **📁 Flexible Loading** — Local directories, project-scoped, or global skills
- **🐍 Built with FastMCP** — Lightweight, fast, Pythonic

---

## Skill Sources

| Location | Description |
|---|---|
| `./skills/` | Project-local skills |
| `~/.fastskills/skills/` | User-global skills |
| Custom path | Via `--skills-dir` flag |

You can use skills from [Anthropic's skills repo](https://github.com/anthropics/skills), community repos, or write your own. Any folder with a valid `SKILL.md` works.

---

## Configuration

```bash
# Start with a custom skills directory
fastskills --skills-dir /path/to/skills

# Set a working directory (defaults to cwd if omitted)
fastskills --skills-dir /path/to/skills --workdir /path/to/output

# Or run without installing via uvx
uvx fastskills --skills-dir /path/to/skills --workdir /path/to/output
```

### CLI Flags

| Flag | Description | Default |
|---|---|---|
| `--skills-dir` | Path to the root directory containing skill folders | *(required)* |
| `--workdir` | Working directory for command execution and file output | Current working directory |

The `--workdir` path is automatically communicated to agents via the `bash_tool` tool description — agents discover it through `list_tools` without any system prompt configuration.

---

## Why FastSkills?

OpenClaw and nanobot have skills built in. Claude, Copilot, and Codex support them natively. But if you're building your own agent — with LangChain, CrewAI, AutoGen, Smolagents, or a custom setup — you don't get skills out of the box.

FastSkills is the missing piece: a standalone MCP server that gives any agent the same skill engine Claude uses internally. No framework adoption required. No code changes to your agent. Just connect via MCP and your agent can discover and use skills.

---

## What's Next

- **🦞 ClawHub Integration** — Browse, search, and install skills directly from [ClawHub](https://clawhub.ai) (3,000+ community skills) without leaving your agent

---

## Contributing

Contributions welcome — whether it's new skills, core improvements, or docs:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-skill`)
3. Commit your changes (`git commit -m 'Add amazing skill'`)
4. Push to the branch (`git push origin feature/amazing-skill`)
5. Open a Pull Request

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Acknowledgments

- Reimplements the skill system from [Claude](https://claude.ai) by [Anthropic](https://www.anthropic.com)
- Follows the [Agent Skills](https://agentskills.io) open standard
- Built with [FastMCP](https://github.com/jlowin/fastmcp)

---

<p align="center">
  <b>Any agent. Any skill. One MCP server.</b>
</p>
