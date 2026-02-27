"""Conversation list sidebar widget."""

from __future__ import annotations

from textual.containers import Vertical
from textual.message import Message
from textual.widgets import Button, Label, ListItem, ListView, Static


class ConversationList(Vertical):
    """Sidebar showing saved sessions and a New Chat button."""

    class Selected(Message):
        """Posted when user clicks a session."""
        def __init__(self, session_id: str) -> None:
            super().__init__()
            self.session_id = session_id

    class NewChat(Message):
        """Posted when user clicks New Chat."""
        pass

    def __init__(self, **kwargs) -> None:
        super().__init__(id="sidebar", **kwargs)
        self._sessions: list[dict] = []

    def compose(self):
        yield Static(" Conversations", id="sidebar-title")
        yield Button("+ New Chat", id="new-chat-btn", variant="primary")
        yield ListView(id="session-list")
        yield Static("Ctrl+H to toggle", id="sidebar-hint")

    def refresh_sessions(self, sessions: list[dict], current_id: str = "") -> None:
        """Refresh the session list."""
        self._sessions = sessions
        lv = self.query_one("#session-list", ListView)
        lv.clear()
        for s in sessions:
            title = s.get("title", "(untitled)")
            ts = s.get("updated_at", "")[:10]
            display = f" {title[:26]}"
            if ts:
                display += f"\n   {ts}"
            item = ListItem(Label(display), name=s["id"])
            if s["id"] == current_id:
                item.add_class("current-session")
            lv.append(item)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "new-chat-btn":
            self.post_message(self.NewChat())

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        name = event.item.name
        if name:
            self.post_message(self.Selected(session_id=name))
