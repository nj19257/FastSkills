"""Input area widget — multi-line TextArea with Enter-to-send."""

from __future__ import annotations

from textual.containers import Vertical
from textual.message import Message
from textual.widgets import Static, TextArea


class _ChatTextArea(TextArea):
    """TextArea that sends on Enter and inserts newline on Shift+Enter."""

    class Submit(Message):
        """Posted when user presses Enter (without Shift)."""
        def __init__(self, text: str) -> None:
            super().__init__()
            self.text = text

    async def _on_key(self, event) -> None:
        if event.key == "enter":
            event.prevent_default()
            event.stop()
            text = self.text.strip()
            if text:
                self.post_message(self.Submit(text))
                self.clear()
            return
        if event.key == "shift+enter":
            event.prevent_default()
            event.stop()
            self.insert("\n")
            return
        await super()._on_key(event)


class ChatInput(Vertical):
    """Container wrapping the chat text area with a hint label."""

    class Submitted(Message):
        """Posted when a message is submitted."""
        def __init__(self, text: str) -> None:
            super().__init__()
            self.text = text

    def compose(self):
        yield _ChatTextArea(id="chat-input")
        yield Static(
            "Enter to send  ·  Shift+Enter for newline  ·  /help for commands",
            id="input-hint",
        )

    def on_mount(self) -> None:
        ta = self.query_one("#chat-input", _ChatTextArea)
        ta.styles.height = 3

    def on__chat_text_area_submit(self, event: _ChatTextArea.Submit) -> None:
        event.stop()
        self.post_message(self.Submitted(event.text))

    def focus_input(self) -> None:
        self.query_one("#chat-input", _ChatTextArea).focus()
