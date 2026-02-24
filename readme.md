# ⚡ FastSkills

**The Agent Skills engine, as an MCP server.**

FastSkills reimplements the skill system used by Claude — where the agent discovers, reads, and follows structured `SKILL.md` playbooks — and exposes it as an MCP server that any agent can connect to.

Same pattern. Same format. Any agent.

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
┌─────────────────┐        MCP         ┌──────────────┐       filesystem      ┌──────────────┐
│   Your Agent    │◄──────────────────►│  FastSkills   │◄────────────────────►│   skills/    │
│  (any MCP       │     protocol       │  MCP Server   │    read SKILL.md     │  ├── pptx/   │
│   client)       │                    │  (FastMCP)    │    run scripts       │  ├── docx/   │
└─────────────────┘                    └──────────────┘                      │  ├── pdf/    │
                                                                             │  └── ...     │
                                                                             └──────────────┘
```

Your agent connects to FastSkills via MCP and gets tools to:

- **List skills** — Get all available skills with their metadata
- **Match skills** — Find the right skill for a given task
- **Read skills** — Load full `SKILL.md` instructions into context
- **Run scripts** — Execute bundled scripts from a skill's directory
- **Create skills** — Author new skills following the Agent Skills standard

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
```

### Connect Your Agent

Add FastSkills to any MCP-compatible client. The easiest way is with [`uvx`](https://docs.astral.sh/uv/), which runs the server directly without installing anything:

```json
{
  "mcpServers": {
    "fastskills": {
      "command": "uvx",
      "args": ["fastskills", "--skills-dir", "~/.fastskills/skills"]
    }
  }
}
```

> **What's `uvx`?** It's a tool from [uv](https://docs.astral.sh/uv/) that runs Python packages in isolated environments — no install step needed. Install it with `curl -LsSf https://astral.sh/uv/install.sh | sh` or `brew install uv`.

If you prefer a manual install:

```bash
pip install fastskills
```

Then use `fastskills` directly in your MCP config:

```json
{
  "mcpServers": {
    "fastskills": {
      "command": "fastskills",
      "args": ["--skills-dir", "~/.fastskills/skills"]
    }
  }
}
```

Works with Claude Desktop, Cursor, VS Code, Goose, or any custom agent that supports MCP.

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
- **✏️ Skill Authoring** — Create new skills through MCP tools
- **📁 Flexible Loading** — Local directories, project-scoped, or global skills
- **🐍 Built with FastMCP** — Lightweight, fast, Pythonic

---

## Skill Sources

| Location | Description |
|---|---|
| `./skills/` | Project-local skills |
| `~/.fastskills/skills/` | User-global skills |
| Custom path | Via `--skills-dir` or `FASTSKILLS_DIR` env var |

You can use skills from [Anthropic's skills repo](https://github.com/anthropics/skills), community repos, or write your own. Any folder with a valid `SKILL.md` works.

---

## Configuration

```bash
# Start with a custom skills directory
fastskills --skills-dir /path/to/skills

# Or run without installing via uvx
uvx fastskills --skills-dir /path/to/skills
```

### Environment Variables

| Variable | Description | Default |
|---|---|---|
| `FASTSKILLS_DIR` | Custom skills directory | `~/.fastskills/skills/` |
| `FASTSKILLS_PORT` | Server port | `8080` |
| `FASTSKILLS_LOG_LEVEL` | Logging verbosity | `info` |

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