"""Command autocomplete widget — shows matching slash commands."""

from __future__ import annotations

from textual.message import Message
from textual.widgets import OptionList
from textual.widgets.option_list import Option

from tui.constants import SLASH_COMMANDS


class CommandAutocomplete(OptionList):
    """Autocomplete dropdown for slash commands."""

    class CommandSelected(Message):
        """Posted when user selects a command."""
        def __init__(self, command: str) -> None:
            super().__init__()
            self.command = command

    def __init__(self, **kwargs) -> None:
        super().__init__(id="command-autocomplete", **kwargs)
        self.add_class("hidden")

    def update_filter(self, text: str) -> None:
        """Show/hide and filter based on current input text."""
        if not text.startswith("/"):
            self.add_class("hidden")
            return

        query = text.lower()
        self.clear_options()
        matches = [
            (cmd, desc)
            for cmd, desc in SLASH_COMMANDS.items()
            if query in cmd.lower() or (len(query) > 1 and query[1:] in cmd.lower())
        ]

        if not matches:
            self.add_class("hidden")
            return

        for cmd, desc in matches:
            self.add_option(Option(f"{cmd}  {desc}", id=cmd))
        self.remove_class("hidden")

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option_id:
            self.post_message(self.CommandSelected(command=event.option_id))
            self.add_class("hidden")
