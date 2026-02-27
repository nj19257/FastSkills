"""FastSkills TUI — main application."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports import UvxStdioTransport
from openai import OpenAI
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Footer, Header

from fastskills_sessions import generate_session_id, list_sessions, load_session, save_session
from tui.constants import DEFAULT_SYSTEM_PROMPT, SLASH_COMMANDS
from tui.helpers import mcp_tools_to_openai
from tui.screens.setup import SetupScreen
from tui.settings import load_settings, save_settings
from tui.widgets.chat_view import ChatView
from tui.widgets.command_palette import CommandAutocomplete
from tui.widgets.conversation_list import ConversationList
from tui.widgets.input_area import ChatInput
from tui.widgets.loading_indicator import LoadingIndicator
from tui.widgets.status_bar import StatusBar


class FastSkillsChat(App):
    """Textual TUI for the FastSkills agent."""

    TITLE = "FastSkills Agent"
    SUB_TITLE = "Starting..."
    CSS_PATH = Path(__file__).parent / "styles" / "main.tcss"

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
        Binding("ctrl+h", "toggle_sidebar", "Sidebar"),
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

        # LLM state
        self._model = ""
        self._llm: OpenAI | None = None

        # MCP state
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
        self._total_tokens = 0

    # ── Layout ──────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Header()
        yield ConversationList()
        with Vertical(id="main-area"):
            yield ChatView(id="chat-view")
            yield LoadingIndicator()
            yield CommandAutocomplete()
            yield ChatInput(id="input-container")
            yield StatusBar()
        yield Footer()

    # ── Lifecycle ───────────────────────────────────────────

    async def on_mount(self) -> None:
        settings = load_settings()
        if settings:
            self._apply_settings(settings)
            self._connect_mcp()
        else:
            self.push_screen(SetupScreen(), self._on_setup_complete)
        self._refresh_sidebar()
        self._update_status_bar()

    def _on_setup_complete(self, result: dict | None) -> None:
        if result is None:
            self.exit()
            return
        save_settings(result["api_key"], result["model"], result.get("skills_dir", ""), result.get("workdir", ""))
        self._apply_settings(result)
        self._connect_mcp()

    def _apply_settings(self, settings: dict) -> None:
        self._model = settings.get("model", "moonshotai/kimi-k2.5")
        self._llm = OpenAI(
            api_key=settings["api_key"],
            base_url=settings.get("base_url", "https://openrouter.ai/api/v1"),
        )
        skills_dir = settings.get("skills_dir", "")
        if skills_dir:
            self._skills_dir = skills_dir
        workdir = settings.get("workdir", "")
        if workdir:
            self._workdir = workdir
        self.sub_title = f"{self._model} · connecting..."

    @work
    async def _connect_mcp(self) -> None:
        chat_view = self.query_one("#chat-view", ChatView)
        loading = self.query_one("#loading-indicator", LoadingIndicator)
        loading.show("Connecting to MCP server...")

        skills_dir = str(Path(self._skills_dir).expanduser().resolve())
        tool_args = ["--skills-dir", skills_dir]
        if self._workdir:
            workdir = str(Path(self._workdir).expanduser().resolve())
            tool_args.extend(["--workdir", workdir])

        transport = UvxStdioTransport(
            "fastskills",
            tool_args=tool_args,
        )

        client = Client(transport)
        self._mcp_context = client.__aenter__
        self._mcp_client = await client.__aenter__()
        self._mcp_aexit = client.__aexit__

        # Discover tools
        mcp_tools = await self._mcp_client.list_tools()
        self._openai_tools = mcp_tools_to_openai(mcp_tools)
        self._tool_names = [t["function"]["name"] for t in self._openai_tools]

        loading.hide()
        self.sub_title = f"{self._model} · {len(self._tool_names)} tools"

        # Welcome message
        tool_list = ", ".join(self._tool_names)
        chat_view.render_welcome(
            model=self._model,
            tool_count=len(self._tool_names),
            tool_names=tool_list,
        )
        self._update_status_bar()

        # Focus the input
        try:
            self.query_one("#input-container", ChatInput).focus_input()
        except Exception:
            pass

    async def on_unmount(self) -> None:
        user_msgs = [m for m in self._messages if m.get("role") == "user"]
        if user_msgs:
            self._save_current_session()
        if hasattr(self, "_mcp_aexit"):
            try:
                await self._mcp_aexit(None, None, None)
            except Exception:
                pass

    # ── Input handling ──────────────────────────────────────

    def on_chat_input_submitted(self, event: ChatInput.Submitted) -> None:
        text = event.text.strip()
        if not text:
            return
        autocomplete = self.query_one("#command-autocomplete", CommandAutocomplete)
        autocomplete.add_class("hidden")

        if text.startswith("/"):
            self._handle_slash(text)
        else:
            if self._busy:
                return
            self._send_message(text)

    def on__chat_text_area_submit(self, event) -> None:
        pass

    # ── Autocomplete ────────────────────────────────────────

    def on_text_area_changed(self, event) -> None:
        if event.text_area.id == "chat-input":
            text = event.text_area.text.strip()
            autocomplete = self.query_one("#command-autocomplete", CommandAutocomplete)
            autocomplete.update_filter(text)

    def on_command_autocomplete_command_selected(self, event: CommandAutocomplete.CommandSelected) -> None:
        try:
            ta = self.query_one("#chat-input")
            ta.clear()
            ta.insert(event.command + " ")
            ta.focus()
        except Exception:
            pass

    # ── Slash commands ──────────────────────────────────────

    @work
    async def _handle_slash(self, text: str) -> None:
        parts = text.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""
        chat_view = self.query_one("#chat-view", ChatView)

        if cmd == "/help":
            self._cmd_help()
        elif cmd == "/skills":
            await self._cmd_skills()
        elif cmd == "/search":
            if not arg:
                chat_view.add_message("Usage: /search <query>", role="system", label="System")
            else:
                await self._cmd_search(arg)
        elif cmd == "/clear":
            self._cmd_clear()
        elif cmd == "/sessions":
            self._cmd_sessions()
        elif cmd == "/load":
            if not arg:
                chat_view.add_message("Usage: /load <N>", role="system", label="System")
            else:
                await self._cmd_load(arg)
        elif cmd == "/save":
            self._cmd_save()
        elif cmd == "/status":
            self._cmd_status()
        elif cmd in ("/settings", "/model"):
            self._cmd_settings()
        else:
            chat_view.add_message(f"Unknown command: {cmd}. Type /help for commands.", role="system", label="System")

    def _cmd_help(self) -> None:
        chat_view = self.query_one("#chat-view", ChatView)
        lines = ["Available commands:"]
        for cmd, desc in SLASH_COMMANDS.items():
            lines.append(f"  {cmd:<16} {desc}")
        chat_view.add_message("\n".join(lines), role="system", label="Help")

    async def _cmd_skills(self) -> None:
        chat_view = self.query_one("#chat-view", ChatView)
        if not self._mcp_client:
            chat_view.add_message("MCP not connected.", role="error", label="Error")
            return
        loading = self.query_one("#loading-indicator", LoadingIndicator)
        loading.show("Fetching skills...")
        try:
            result = await self._mcp_client.call_tool("list_skills", {})
            result_text = "\n".join(
                block.text for block in result.content if hasattr(block, "text")
            )
            chat_view.add_message(result_text, role="system", label="Skills")
        except Exception as exc:
            chat_view.add_message(f"Error: {exc}", role="error", label="Error")
        finally:
            loading.hide()

    async def _cmd_search(self, query: str) -> None:
        chat_view = self.query_one("#chat-view", ChatView)
        if not self._mcp_client:
            chat_view.add_message("MCP not connected.", role="error", label="Error")
            return
        loading = self.query_one("#loading-indicator", LoadingIndicator)
        loading.show(f"Searching: {query}...")
        try:
            result = await self._mcp_client.call_tool(
                "search_cloud_skills", {"query": query}
            )
            result_text = "\n".join(
                block.text for block in result.content if hasattr(block, "text")
            )
            chat_view.add_message(result_text, role="system", label="Search Results")
        except Exception as exc:
            chat_view.add_message(f"Error: {exc}", role="error", label="Error")
        finally:
            loading.hide()

    def _cmd_clear(self) -> None:
        chat_view = self.query_one("#chat-view", ChatView)
        chat_view.clear_messages()
        self._messages = [{"role": "system", "content": self._system_prompt}]
        self._session_id = generate_session_id()
        self._session_title = ""
        self._total_tokens = 0
        chat_view.add_message("New session started.", role="system", label="System")
        self._update_status_bar()
        self._refresh_sidebar()

    def _cmd_sessions(self) -> None:
        chat_view = self.query_one("#chat-view", ChatView)
        sessions = list_sessions()
        if not sessions:
            chat_view.add_message("No saved sessions.", role="system", label="System")
            return
        lines = ["Saved sessions:"]
        for i, s in enumerate(sessions, 1):
            ts = s.get("updated_at", "")[:19].replace("T", " ")
            lines.append(f"  {i}. {s['title']}  ({ts})")
        chat_view.add_message("\n".join(lines), role="system", label="Sessions")

    async def _cmd_load(self, index: str) -> None:
        chat_view = self.query_one("#chat-view", ChatView)
        sessions = list_sessions()
        try:
            idx = int(index) - 1
            if idx < 0 or idx >= len(sessions):
                raise ValueError
        except ValueError:
            chat_view.add_message(f"Invalid session number: {index}", role="system", label="System")
            return

        session_meta = sessions[idx]
        try:
            session = load_session(session_meta["id"])
        except FileNotFoundError:
            chat_view.add_message("Session file not found.", role="error", label="Error")
            return

        self._messages = [{"role": "system", "content": self._system_prompt}]
        self._messages.extend(session.get("messages", []))
        self._session_id = session["id"]
        self._session_title = session.get("title", "")

        chat_view.clear_messages()
        chat_view.add_message(f"Loaded: {session.get('title', '(untitled)')}", role="system", label="System")
        chat_view.replay_messages(session.get("messages", []))
        self._update_status_bar()
        self._refresh_sidebar()

    def _cmd_save(self) -> None:
        chat_view = self.query_one("#chat-view", ChatView)
        self._save_current_session()
        chat_view.add_message(f"Session saved ({self._session_id}).", role="system", label="Saved")
        self._refresh_sidebar()

    def _cmd_status(self) -> None:
        chat_view = self.query_one("#chat-view", ChatView)
        settings = load_settings() or {}
        workdir_display = self._workdir or "not set"
        tok = f"{self._total_tokens / 1000:.1f}K" if self._total_tokens >= 1000 else str(self._total_tokens)
        info = (
            f"Model:      {self._model}\n"
            f"Base URL:   {settings.get('base_url', '(default)')}\n"
            f"Skills Dir: {self._skills_dir}\n"
            f"Work Dir:   {workdir_display}\n"
            f"Tools:      {len(self._tool_names)} ({', '.join(self._tool_names)})\n"
            f"Session:    {self._session_id}\n"
            f"Messages:   {len(self._messages)}\n"
            f"Tokens:     ~{tok}"
        )
        chat_view.add_message(info, role="system", label="Status")

    def _cmd_settings(self) -> None:
        current = load_settings() or {}
        self.push_screen(SetupScreen(existing=current), self._on_settings_changed)

    def _on_settings_changed(self, result: dict | None) -> None:
        if result is None:
            return
        save_settings(result["api_key"], result["model"], result.get("skills_dir", ""), result.get("workdir", ""))
        self._apply_settings(result)
        self.sub_title = f"{self._model} · {len(self._tool_names)} tools"
        chat_view = self.query_one("#chat-view", ChatView)
        chat_view.add_message(f"Settings updated. Model: {result['model']}", role="system", label="Settings")
        self._update_status_bar()

    # ── Agent loop ──────────────────────────────────────────

    @work(exclusive=True)
    async def _send_message(self, user_text: str) -> None:
        self._busy = True
        chat_view = self.query_one("#chat-view", ChatView)
        loading = self.query_one("#loading-indicator", LoadingIndicator)

        if not self._session_title:
            self._session_title = user_text[:60]

        chat_view.add_message(user_text, role="user", label="You")
        self._messages.append({"role": "user", "content": user_text})
        loading.show("Thinking...")

        try:
            await self._agent_loop(chat_view)
        except Exception as exc:
            chat_view.add_message(f"Error: {exc}", role="error", label="Error")
        finally:
            loading.hide()
            self._busy = False
            self._update_status_bar()
            try:
                self.query_one("#input-container", ChatInput).focus_input()
            except Exception:
                pass

    async def _agent_loop(self, chat_view: ChatView) -> None:
        while True:
            response = await asyncio.to_thread(
                self._llm.chat.completions.create,
                model=self._model,
                messages=self._messages,
                tools=self._openai_tools or None,
            )
            choice = response.choices[0]
            msg = choice.message

            if hasattr(response, "usage") and response.usage:
                self._total_tokens += getattr(response.usage, "total_tokens", 0)

            msg_dict = msg.model_dump(exclude_none=True)
            msg_dict.setdefault("content", "")
            self._messages.append(msg_dict)

            if not msg.tool_calls:
                if msg.content:
                    chat_view.add_message(msg.content, role="assistant", label="Assistant")
                break

            for tc in msg.tool_calls:
                fn_name = tc.function.name
                fn_args_raw = tc.function.arguments or "{}"
                fn_args = json.loads(fn_args_raw)

                args_preview = fn_args_raw[:100]
                if len(fn_args_raw) > 100:
                    args_preview += "..."
                chat_view.add_message(
                    f"{fn_name}({args_preview})",
                    role="tool",
                    label="Tool",
                )

                loading = self.query_one("#loading-indicator", LoadingIndicator)
                loading.show(f"Running {fn_name}...")

                try:
                    result = await self._mcp_client.call_tool(fn_name, fn_args)
                    result_text = "\n".join(
                        block.text for block in result.content
                        if hasattr(block, "text")
                    )
                except Exception as exc:
                    result_text = f"Error calling {fn_name}: {exc}"

                preview = result_text[:200]
                if len(result_text) > 200:
                    preview += "..."
                chat_view.add_message(preview, role="tool", label="Result")

                self._messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result_text,
                })

            loading = self.query_one("#loading-indicator", LoadingIndicator)
            loading.show("Thinking...")

    # ── Sidebar ─────────────────────────────────────────────

    def _refresh_sidebar(self) -> None:
        try:
            sidebar = self.query_one("#sidebar", ConversationList)
            sessions = list_sessions()
            sidebar.refresh_sessions(sessions, self._session_id)
        except Exception:
            pass

    def on_conversation_list_selected(self, event: ConversationList.Selected) -> None:
        self._load_session_by_id(event.session_id)

    def on_conversation_list_new_chat(self, event: ConversationList.NewChat) -> None:
        self._cmd_clear()

    @work
    async def _load_session_by_id(self, session_id: str) -> None:
        chat_view = self.query_one("#chat-view", ChatView)
        try:
            session = load_session(session_id)
        except FileNotFoundError:
            chat_view.add_message("Session file not found.", role="error", label="Error")
            return

        self._messages = [{"role": "system", "content": self._system_prompt}]
        self._messages.extend(session.get("messages", []))
        self._session_id = session["id"]
        self._session_title = session.get("title", "")

        chat_view.clear_messages()
        chat_view.replay_messages(session.get("messages", []))
        self._update_status_bar()
        self._refresh_sidebar()

    # ── Status bar ──────────────────────────────────────────

    def _update_status_bar(self) -> None:
        try:
            status = self.query_one("#status-bar", StatusBar)
            status.update_status(
                tokens=self._total_tokens,
                message_count=len(self._messages),
                skill_count=len(self._tool_names),
                title=self._session_title,
            )
        except Exception:
            pass

    # ── Session helpers ─────────────────────────────────────

    def _save_current_session(self) -> None:
        save_session(
            session_id=self._session_id,
            title=self._session_title or "(untitled)",
            model=self._model,
            messages=self._messages,
        )

    # ── Actions ─────────────────────────────────────────────

    def action_toggle_sidebar(self) -> None:
        sidebar = self.query_one("#sidebar", ConversationList)
        sidebar.toggle_class("hidden")

    def action_clear_chat(self) -> None:
        self._cmd_clear()
