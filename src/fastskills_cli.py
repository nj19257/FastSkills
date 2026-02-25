"""FastSkills Agent — Textual TUI (installable entry point).

A polished chat interface backed by FastSkills MCP tools.

Usage (after pip install):
    fastskills_cli
    fastskills_cli --skills-dir ~/my-skills
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
import asyncio
import json
from pathlib import Path

import yaml
from fastmcp import Client
from fastmcp.client.transports import UvxStdioTransport
from openai import OpenAI
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Center, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, RichLog, Select, Static

from fastskills_sessions import generate_session_id, list_sessions, load_session, save_session


# ------------------------------------------------------------------
# Settings persistence (~/.fastskills/settings.yaml)
# ------------------------------------------------------------------

SETTINGS_DIR = Path.home() / ".fastskills"
SETTINGS_PATH = SETTINGS_DIR / "settings.yaml"

MODELS: list[tuple[str, str]] = [
    ("Kimi K2.5 (free)", "moonshotai/kimi-k2.5"),
    ("DeepSeek V3 (free)", "deepseek/deepseek-chat-v3-0324:free"),
    ("Gemini 2.5 Flash", "google/gemini-2.5-flash"),
    ("Claude Sonnet 4", "anthropic/claude-sonnet-4"),
    ("GPT-4.1", "openai/gpt-4.1"),
    ("GPT-4.1 Mini", "openai/gpt-4.1-mini"),
    ("Llama 4 Maverick (free)", "meta-llama/llama-4-maverick:free"),
]


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


def save_settings(api_key: str, model: str) -> None:
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
    existing.setdefault("base_url", "https://openrouter.ai/api/v1")
    SETTINGS_PATH.write_text(
        yaml.dump(existing, default_flow_style=False), encoding="utf-8"
    )


# ------------------------------------------------------------------
# Default system prompt (embedded from prompt/gold_standard_prompt.yaml)
# ------------------------------------------------------------------

DEFAULT_SYSTEM_PROMPT = """\
You are a helpful, capable assistant with access to tools via an MCP server.

<startup>
On your FIRST response in every conversation, call `list_skills()` before doing anything else.
This tells you what capabilities you have. Remember the skill list for the rest of the conversation so you don't
need to call it again unless the user asks you to refresh.
</startup>

<core_principles>
- Be direct and helpful. Answer questions concisely without unnecessary preamble.
- Use a warm, natural tone. Respond in prose and paragraphs, not bullet lists, unless the user asks for lists.
- Avoid over-formatting. Minimize bold, headers, and bullets in casual conversation.
- Do not use emojis unless the user does first.
- When you make a mistake, own it honestly, fix it, and move on without excessive apology.
- Your capabilities extend beyond your built-in knowledge — you have tools and skills that
  let you search the web, create documents, run code, and more. Always check before declining a request.
</core_principles>

<tool_usage>
You have access to tools provided by a FastSkills MCP server. Use them thoughtfully.

**When to use tools:**
- The user's request requires reading, creating, or modifying files.
- The task involves computation, data processing, or code execution.
- You need information you don't have (e.g., file contents, directory listings).
- You are unsure whether you can do what the user asks — call list_skills first.

**When NOT to use tools:**
- Answering factual questions from your own knowledge.
- Summarizing content the user already provided in the conversation.
- Explaining concepts or having a normal conversation.

**Tool-calling discipline:**
- Before creating or editing files, read any relevant existing files first to understand context.
- If a skill or template directory is available, examine it before starting work — best practices discovered through trial and error are often captured there.
- Scale tool usage to task complexity: 1 call for a simple lookup, multiple calls for multi-step tasks.
- When a tool call fails, try a different approach rather than repeating the same call.
- Never fabricate tool results. If a tool errors, report the error honestly.
</tool_usage>

<file_handling>
**Reading files:**
- If the user references a file, read it before acting on it.
- If file contents are already in the conversation (e.g., pasted by the user), don't redundantly read them again.

**Creating files:**
- Actually create files when the user asks — don't just show content inline.
- For short files (<100 lines), create them in one step.
- For longer files, build iteratively: outline first, then fill in sections.
- When editing existing files, make targeted edits rather than rewriting the entire file.

**Triggers for file creation:**
- "write a document/report/script" → create the file
- "fix/edit my file" → edit the actual file
- Any request with "save" or "file" → create files
- Writing more than ~10 lines of code → create a file rather than showing inline
</file_handling>

<response_quality>
**Formatting:**
- In casual conversation, keep responses short (a few sentences is fine).
- Don't ask more than one question per response unless gathering requirements upfront.
- Address the user's query before asking for clarification.
- Use examples, analogies, or thought experiments to clarify complex topics.

**Accuracy:**
- If you're unsure, say so. Don't guess at facts.
- When working with code or data, verify your work — run it if you can.
- If a task is ambiguous, make your best interpretation and proceed, noting your assumptions. Don't stall with excessive clarification questions.

**After completing work:**
- Give a concise summary of what you did. Don't over-explain — the user can look at the output themselves.
- If you created files, mention where they are.
</response_quality>

<safety>
- Don't help with malicious code (malware, exploits, phishing).
- Don't provide instructions for weapons or harmful substances.
- Be careful with content involving minors.
- For legal or financial questions, share factual info but note you're not a professional advisor.
- If someone seems to be in distress, respond with care and offer to help them find support.
</safety>

<skills>
Skills are pre-built playbooks that give you capabilities you do not have on your own — such as
searching the web, creating documents, generating presentations, or running specialized workflows.
Each skill is a directory containing a SKILL.md file with step-by-step instructions and often
bundled scripts you can run with bash_tool.

IMPORTANT: Never tell the user you cannot do something (e.g., "I can't search the web" or
"I can't create PowerPoint files") without first calling list_skills to check whether a skill
exists for that task. Skills are your primary way of gaining new capabilities.

**Skill workflow (follow these steps in order):**

Step 1 — Discover: Call `list_skills()`. This returns each skill's name, description, and
the full path to its SKILL.md. Read the descriptions to find a match for the user's request.

Step 2 — Read: Call `view(path="<the SKILL.md path from step 1>")` to read the full
instructions. The SKILL.md contains quick-start commands, options, and best practices.

Step 3 — Execute: Follow the SKILL.md instructions. This usually means running a script
with `bash_tool`. When the SKILL.md contains `{baseDir}`, replace it with the directory
that contains the SKILL.md (i.e., remove `/SKILL.md` from the end of the path).

**Example — user asks "search the web for recent AI news":**

1. You call `list_skills()` and see a skill with description mentioning "search the web".
   Its path is `/home/user/skills/duckduckgo/SKILL.md`.
2. You call `view(path="/home/user/skills/duckduckgo/SKILL.md")` and read the instructions.
   The quick-start says: `python3 {baseDir}/scripts/search.py "your query" --num 10`
3. You replace `{baseDir}` with `/home/user/skills/duckduckgo` and call:
   `bash_tool(command='python3 /home/user/skills/duckduckgo/scripts/search.py "recent AI news" --type news --num 5')`
4. You summarize the search results for the user.

Since you call `list_skills()` at startup, you already know your capabilities. Refer back to
that list when deciding how to handle a request. If the conversation is long, you may call
`list_skills()` again to refresh your memory.
</skills>"""


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def mcp_tools_to_openai(mcp_tools: list) -> list[dict]:
    """Convert MCP tool objects to OpenAI-compatible function tool defs."""
    openai_tools = []
    for tool in mcp_tools:
        schema = tool.inputSchema if hasattr(tool, "inputSchema") else {}
        openai_tools.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": schema,
            },
        })
    return openai_tools


# ------------------------------------------------------------------
# Setup Screen
# ------------------------------------------------------------------

class SetupScreen(Screen):
    """First-run / settings screen — collects API key and model."""

    CSS = """
    SetupScreen {
        align: center middle;
    }
    #setup-container {
        width: 64;
        height: auto;
        padding: 1 2;
        border: thick $primary;
        background: $surface;
    }
    #title {
        text-align: center;
        text-style: bold;
        color: $primary;
        padding: 1 0;
    }
    .field-label {
        margin-top: 1;
    }
    #start-btn {
        margin-top: 1;
        width: 100%;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, existing: dict | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._existing = existing or {}

    def compose(self) -> ComposeResult:
        yield Header()
        with Center():
            with Vertical(id="setup-container"):
                yield Static("FastSkills Setup", id="title")
                yield Static("OpenRouter API Key:", classes="field-label")
                yield Input(
                    id="api-key",
                    placeholder="sk-or-v1-...",
                    password=True,
                )
                yield Static("Model:", classes="field-label")
                yield Select(
                    MODELS,
                    id="model-select",
                    value="moonshotai/kimi-k2.5",
                    allow_blank=False,
                )
                yield Button("Start Chat", id="start-btn", variant="primary")
        yield Footer()

    def on_mount(self) -> None:
        api_key_input = self.query_one("#api-key", Input)
        if self._existing.get("api_key"):
            api_key_input.value = self._existing["api_key"]
        if self._existing.get("model"):
            try:
                self.query_one("#model-select", Select).value = self._existing["model"]
            except Exception:
                pass
        api_key_input.focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "start-btn":
            self._submit()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Allow Enter in the API key field to submit the form."""
        self._submit()

    def _submit(self) -> None:
        api_key = self.query_one("#api-key", Input).value.strip()
        model = self.query_one("#model-select", Select).value
        if not api_key:
            self.notify("Please enter an API key", severity="error")
            return
        if model is Select.BLANK:
            self.notify("Please select a model", severity="error")
            return
        self.dismiss({"api_key": api_key, "model": str(model)})

    def action_cancel(self) -> None:
        self.dismiss(None)


# ------------------------------------------------------------------
# TUI Application
# ------------------------------------------------------------------

class FastSkillsChat(App):
    """Textual TUI for the FastSkills agent."""

    TITLE = "FastSkills Agent"
    SUB_TITLE = "Starting…"
    CSS_PATH = None
    CSS = """
    RichLog {
        scrollbar-size: 1 1;
    }
    Input {
        dock: bottom;
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
        Binding("ctrl+l", "clear_chat", "Clear"),
    ]

    def __init__(
        self,
        skills_dir: str,
        workdir: str | None,
        system_prompt: str,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._skills_dir = skills_dir
        self._workdir = workdir
        self._system_prompt = system_prompt

        # LLM state (populated after setup)
        self._model = ""
        self._llm: OpenAI | None = None

        # MCP state (populated in _connect_mcp)
        self._mcp_client: Client | None = None
        self._mcp_context = None
        self._openai_tools: list[dict] = []
        self._tool_names: list[str] = []

        # Conversation state
        self._messages: list[dict] = [
            {"role": "system", "content": system_prompt}
        ]
        self._session_id = generate_session_id()
        self._session_title = ""
        self._busy = False

    # ---- Layout ---------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header()
        yield RichLog(id="chat-log", wrap=True, highlight=True, markup=True)
        yield Input(placeholder="Type a message or /help…")
        yield Footer()

    # ---- Lifecycle ------------------------------------------------

    async def on_mount(self) -> None:
        settings = load_settings()
        if settings:
            self._apply_settings(settings)
            self._connect_mcp()
        else:
            self.push_screen(SetupScreen(), self._on_setup_complete)

    def _on_setup_complete(self, result: dict | None) -> None:
        if result is None:
            self.exit()
            return
        save_settings(result["api_key"], result["model"])
        self._apply_settings(result)
        self._connect_mcp()

    def _apply_settings(self, settings: dict) -> None:
        self._model = settings.get("model", "moonshotai/kimi-k2.5")
        self._llm = OpenAI(
            api_key=settings["api_key"],
            base_url=settings.get("base_url", "https://openrouter.ai/api/v1"),
        )
        self.sub_title = f"{self._model} · connecting…"

    @work
    async def _connect_mcp(self) -> None:
        log = self.query_one("#chat-log", RichLog)
        log.write(Text("Connecting to FastSkills MCP server…", style="dim"))

        skills_dir = str(Path(self._skills_dir).expanduser().resolve())
        tool_args = ["--skills-dir", skills_dir]
        if self._workdir:
            workdir = str(Path(self._workdir).expanduser().resolve())
            tool_args.extend(["--workdir", workdir])

        transport = UvxStdioTransport(
            "fastskills",
            tool_args=tool_args,
        )

        # Manually manage the async context so it spans mount→unmount
        client = Client(transport)
        self._mcp_context = client.__aenter__
        self._mcp_client = await client.__aenter__()

        # Store __aexit__ for cleanup
        self._mcp_aexit = client.__aexit__

        # Discover tools
        mcp_tools = await self._mcp_client.list_tools()
        self._openai_tools = mcp_tools_to_openai(mcp_tools)
        self._tool_names = [t["function"]["name"] for t in self._openai_tools]

        self.sub_title = f"{self._model} · {len(self._tool_names)} tools"
        log.write(Text(
            f"Connected — {len(self._tool_names)} tools: {', '.join(self._tool_names)}",
            style="dim green",
        ))

    async def on_unmount(self) -> None:
        # Auto-save if there are user messages
        user_msgs = [m for m in self._messages if m.get("role") == "user"]
        if user_msgs:
            self._save_current_session()

        # Close MCP context
        if hasattr(self, "_mcp_aexit"):
            try:
                await self._mcp_aexit(None, None, None)
            except Exception:
                pass

    # ---- Input handling -------------------------------------------

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text:
            return
        event.input.value = ""

        if text.startswith("/"):
            await self._handle_slash(text)
        else:
            if self._busy:
                return
            self._send_message(text)

    # ---- Slash commands -------------------------------------------

    async def _handle_slash(self, text: str) -> None:
        parts = text.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""
        log = self.query_one("#chat-log", RichLog)

        if cmd == "/help":
            self._cmd_help()
        elif cmd == "/skills":
            await self._cmd_skills()
        elif cmd == "/search":
            if not arg:
                log.write(Text("Usage: /search <query>", style="yellow"))
            else:
                await self._cmd_search(arg)
        elif cmd == "/clear":
            self._cmd_clear()
        elif cmd == "/sessions":
            self._cmd_sessions()
        elif cmd == "/load":
            if not arg:
                log.write(Text("Usage: /load <N>", style="yellow"))
            else:
                await self._cmd_load(arg)
        elif cmd == "/save":
            self._cmd_save()
        elif cmd == "/status":
            self._cmd_status()
        elif cmd == "/settings":
            self._cmd_settings()
        else:
            log.write(Text(f"Unknown command: {cmd}. Type /help for commands.", style="yellow"))

    def _cmd_help(self) -> None:
        log = self.query_one("#chat-log", RichLog)
        help_text = (
            "[cyan]Available commands:[/cyan]\n"
            "  /help            Show this command list\n"
            "  /skills          List local skills (via MCP)\n"
            "  /search <query>  Search cloud skill catalog\n"
            "  /clear           Clear chat and reset conversation\n"
            "  /sessions        List saved sessions\n"
            "  /load <N>        Load session N from history\n"
            "  /save            Force-save current session\n"
            "  /status          Show model, tools, session info\n"
            "  /settings        Change API key or model"
        )
        log.write(Text.from_markup(help_text))

    async def _cmd_skills(self) -> None:
        log = self.query_one("#chat-log", RichLog)
        if not self._mcp_client:
            log.write(Text("MCP not connected.", style="red bold"))
            return
        log.write(Text("Fetching skills…", style="dim italic"))
        try:
            result = await self._mcp_client.call_tool("list_skills", {})
            result_text = "\n".join(
                block.text for block in result.content if hasattr(block, "text")
            )
            log.write(Text.from_markup(f"[cyan]{result_text}[/cyan]"))
        except Exception as exc:
            log.write(Text(f"Error: {exc}", style="red bold"))

    async def _cmd_search(self, query: str) -> None:
        log = self.query_one("#chat-log", RichLog)
        if not self._mcp_client:
            log.write(Text("MCP not connected.", style="red bold"))
            return
        log.write(Text(f"Searching: {query}…", style="dim italic"))
        try:
            result = await self._mcp_client.call_tool(
                "search_cloud_skills", {"query": query}
            )
            result_text = "\n".join(
                block.text for block in result.content if hasattr(block, "text")
            )
            log.write(Text.from_markup(f"[cyan]{result_text}[/cyan]"))
        except Exception as exc:
            log.write(Text(f"Error: {exc}", style="red bold"))

    def _cmd_clear(self) -> None:
        log = self.query_one("#chat-log", RichLog)
        log.clear()
        self._messages = [{"role": "system", "content": self._system_prompt}]
        self._session_id = generate_session_id()
        self._session_title = ""
        log.write(Text("Chat cleared. New session started.", style="dim"))

    def _cmd_sessions(self) -> None:
        log = self.query_one("#chat-log", RichLog)
        sessions = list_sessions()
        if not sessions:
            log.write(Text("No saved sessions.", style="dim"))
            return
        lines = ["[cyan]Saved sessions:[/cyan]"]
        for i, s in enumerate(sessions, 1):
            ts = s.get("updated_at", "")[:19].replace("T", " ")
            lines.append(f"  {i}. {s['title']}  ({ts})")
        log.write(Text.from_markup("\n".join(lines)))

    async def _cmd_load(self, index: str) -> None:
        log = self.query_one("#chat-log", RichLog)
        sessions = list_sessions()
        try:
            idx = int(index) - 1
            if idx < 0 or idx >= len(sessions):
                raise ValueError
        except ValueError:
            log.write(Text(f"Invalid session number: {index}", style="yellow"))
            return

        session_meta = sessions[idx]
        try:
            session = load_session(session_meta["id"])
        except FileNotFoundError:
            log.write(Text("Session file not found.", style="red bold"))
            return

        # Restore messages: system prompt + saved messages
        self._messages = [{"role": "system", "content": self._system_prompt}]
        self._messages.extend(session.get("messages", []))
        self._session_id = session["id"]
        self._session_title = session.get("title", "")

        log.clear()
        log.write(Text(f"Loaded session: {session.get('title', '(untitled)')}", style="dim green"))

        # Replay messages into the chat log
        for msg in session.get("messages", []):
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user" and content:
                log.write(Panel(
                    content,
                    title="You",
                    border_style="blue",
                    expand=False,
                ))
            elif role == "assistant" and content:
                log.write(Panel(
                    Markdown(content),
                    title="Assistant",
                    border_style="green",
                    expand=False,
                ))

    def _cmd_save(self) -> None:
        log = self.query_one("#chat-log", RichLog)
        self._save_current_session()
        log.write(Text(f"Session saved ({self._session_id}).", style="dim green"))

    def _cmd_status(self) -> None:
        log = self.query_one("#chat-log", RichLog)
        settings = load_settings() or {}
        info = (
            f"[cyan]Model:[/cyan]    {self._model}\n"
            f"[cyan]Base URL:[/cyan] {settings.get('base_url', '(default)')}\n"
            f"[cyan]Tools:[/cyan]    {len(self._tool_names)} ({', '.join(self._tool_names)})\n"
            f"[cyan]Session:[/cyan]  {self._session_id}\n"
            f"[cyan]Messages:[/cyan] {len(self._messages)}"
        )
        log.write(Text.from_markup(info))

    def _cmd_settings(self) -> None:
        current = load_settings() or {}
        self.push_screen(SetupScreen(existing=current), self._on_settings_changed)

    def _on_settings_changed(self, result: dict | None) -> None:
        if result is None:
            return
        save_settings(result["api_key"], result["model"])
        self._apply_settings(result)
        log = self.query_one("#chat-log", RichLog)
        log.write(Text(f"Settings updated. Model: {result['model']}", style="dim green"))

    # ---- Agent loop -----------------------------------------------

    @work(exclusive=True)
    async def _send_message(self, user_text: str) -> None:
        self._busy = True
        log = self.query_one("#chat-log", RichLog)

        # Set session title from first user message
        if not self._session_title:
            self._session_title = user_text[:60]

        # Render user bubble
        log.write(Panel(
            user_text,
            title="You",
            border_style="blue",
            expand=False,
        ))

        self._messages.append({"role": "user", "content": user_text})
        log.write(Text("Thinking…", style="dim italic"))

        try:
            await self._agent_loop(log)
        except Exception as exc:
            log.write(Text(f"Error: {exc}", style="red bold"))
        finally:
            self._busy = False

    async def _agent_loop(self, log: RichLog) -> None:
        """Run the LLM + tool-call loop until the assistant produces a text reply."""
        while True:
            # Offload sync OpenAI call to a thread
            response = await asyncio.to_thread(
                self._llm.chat.completions.create,
                model=self._model,
                messages=self._messages,
                tools=self._openai_tools or None,
            )
            choice = response.choices[0]
            msg = choice.message

            # Append to history
            msg_dict = msg.model_dump(exclude_none=True)
            msg_dict.setdefault("content", "")
            self._messages.append(msg_dict)

            # No tool calls — render assistant reply and exit loop
            if not msg.tool_calls:
                if msg.content:
                    log.write(Panel(
                        Markdown(msg.content),
                        title="Assistant",
                        border_style="green",
                        expand=False,
                    ))
                break

            # Execute each tool call via MCP
            for tc in msg.tool_calls:
                fn_name = tc.function.name
                fn_args_raw = tc.function.arguments or "{}"
                fn_args = json.loads(fn_args_raw)

                # Render tool call
                args_preview = fn_args_raw[:120]
                if len(fn_args_raw) > 120:
                    args_preview += "…"
                log.write(Text.from_markup(
                    f"[dim]  \\[tool] {fn_name}({args_preview})[/dim]"
                ))

                try:
                    result = await self._mcp_client.call_tool(fn_name, fn_args)
                    result_text = "\n".join(
                        block.text for block in result.content
                        if hasattr(block, "text")
                    )
                except Exception as exc:
                    result_text = f"Error calling {fn_name}: {exc}"

                # Render tool result (truncated)
                preview = result_text[:200]
                if len(result_text) > 200:
                    preview += "…"
                log.write(Text.from_markup(
                    f"[dim italic]    → {preview}[/dim italic]"
                ))

                self._messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result_text,
                })

    # ---- Session helpers ------------------------------------------

    def _save_current_session(self) -> None:
        save_session(
            session_id=self._session_id,
            title=self._session_title or "(untitled)",
            model=self._model,
            messages=self._messages,
        )

    # ---- Actions --------------------------------------------------

    def action_clear_chat(self) -> None:
        self._cmd_clear()


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="FastSkills Agent TUI")
    parser.add_argument(
        "--skills-dir",
        type=str,
        default=str(Path.home() / ".fastskills" / "skills"),
        help="Path to skills directory (default: ~/.fastskills/skills/)",
    )
    parser.add_argument(
        "--workdir",
        type=str,
        default=None,
        help="Working directory for the agent",
    )
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
        skills_dir=args.skills_dir,
        workdir=args.workdir,
        system_prompt=system_prompt,
    )
    app.run()


if __name__ == "__main__":
    main()
