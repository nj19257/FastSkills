"""Status bar widget — shows tokens, messages, skills, and session title."""

from __future__ import annotations

from textual.widgets import Static


class StatusBar(Static):
    """Bottom status bar showing session stats."""

    def __init__(self, **kwargs) -> None:
        super().__init__("", id="status-bar", **kwargs)
        self._tokens = 0
        self._message_count = 0
        self._skill_count = 0
        self._title = ""

    def update_status(
        self,
        tokens: int | None = None,
        message_count: int | None = None,
        skill_count: int | None = None,
        title: str | None = None,
    ) -> None:
        if tokens is not None:
            self._tokens = tokens
        if message_count is not None:
            self._message_count = message_count
        if skill_count is not None:
            self._skill_count = skill_count
        if title is not None:
            self._title = title

        # Format token count nicely
        if self._tokens >= 1000:
            tok = f"{self._tokens / 1000:.1f}K"
        else:
            tok = str(self._tokens)

        left = f" Tokens: {tok}  ·  Msgs: {self._message_count}  ·  Tools: {self._skill_count}"
        right = f"  {self._title}" if self._title else ""
        self.update(left + right)
