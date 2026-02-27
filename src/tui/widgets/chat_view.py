"""Chat view — RichLog-based message rendering."""

from __future__ import annotations

from rich.box import ROUNDED
from rich.markdown import Markdown
from rich.padding import Padding
from rich.panel import Panel
from rich.text import Text
from textual.widgets import RichLog


class ChatView(RichLog):
    """Scrollable chat log using Rich renderables for beautiful messages."""

    def __init__(self, **kwargs) -> None:
        super().__init__(wrap=True, highlight=True, markup=True, **kwargs)

    def add_message(self, content: str, role: str = "assistant", label: str = "") -> None:
        if role == "user":
            self._render_user(content, label or "You")
        elif role == "assistant":
            self._render_assistant(content, label or "Assistant")
        elif role == "tool":
            self._render_tool(content, label or "Tool")
        elif role == "error":
            self._render_error(content, label or "Error")
        else:
            self._render_system(content, label or "System")

    def _render_user(self, content: str, label: str) -> None:
        panel = Panel(
            Text(content, style="white"),
            title=f"[bold #79c0ff]{label}[/]",
            title_align="right",
            border_style="#264f78",
            box=ROUNDED,
            padding=(0, 2),
            expand=True,
        )
        self.write(Padding(panel, (0, 0, 0, 12)))
        self.write(Text(""))

    def _render_assistant(self, content: str, label: str) -> None:
        panel = Panel(
            Markdown(content, code_theme="monokai"),
            title=f"[bold #3fb950]{label}[/]",
            title_align="left",
            border_style="#238636",
            box=ROUNDED,
            padding=(0, 2),
            expand=True,
        )
        self.write(panel)
        self.write(Text(""))

    def _render_system(self, content: str, label: str) -> None:
        line = Text(justify="center")
        line.append("── ", style="#30363d")
        line.append(label, style="bold #8b949e")
        line.append(" · ", style="#30363d")
        line.append(content, style="italic #6e7681")
        line.append(" ──", style="#30363d")
        self.write(line)

    def _render_tool(self, content: str, label: str) -> None:
        if label == "Result":
            prefix = Text("    ↳ ", style="dim #484f58")
            body = Text(content, style="#6e7681")
        else:
            prefix = Text("    ⚡ ", style="bold #a371f7")
            body = Text(content, style="#6e7681")
        line = prefix + body
        self.write(line)

    def _render_error(self, content: str, label: str) -> None:
        panel = Panel(
            Text(content, style="#ffa198"),
            title=f"[bold #f85149]{label}[/]",
            title_align="left",
            border_style="#f85149",
            box=ROUNDED,
            padding=(0, 2),
            expand=True,
        )
        self.write(panel)

    def render_welcome(self, model: str, tool_count: int, tool_names: str) -> None:
        """Render a branded welcome card."""
        body = Text()
        body.append("Model: ", style="bold #8b949e")
        body.append(model, style="#e6edf3")
        body.append("\n")
        body.append("Tools: ", style="bold #8b949e")
        body.append(str(tool_count), style="bold #3fb950")
        body.append(" available", style="#8b949e")
        body.append("\n")
        body.append(tool_names, style="dim #6e7681")
        body.append("\n\n")
        body.append("Type a message or ", style="#6e7681")
        body.append("/help", style="bold #58a6ff")
        body.append(" for commands", style="#6e7681")

        panel = Panel(
            body,
            title="[bold #58a6ff]⚡ FastSkills Agent[/]",
            title_align="left",
            border_style="#264f78",
            box=ROUNDED,
            padding=(1, 2),
            expand=True,
        )
        self.write(panel)
        self.write(Text(""))

    def clear_messages(self) -> None:
        self.clear()

    def replay_messages(self, messages: list[dict]) -> None:
        self.clear()
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user" and content:
                self.add_message(content, role="user", label="You")
            elif role == "assistant" and content:
                self.add_message(content, role="assistant", label="Assistant")
