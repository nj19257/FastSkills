"""Modal dialog screens."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, OptionList, Static
from textual.widgets.option_list import Option


class ConfirmDialog(ModalScreen[bool]):
    """Yes/No confirmation dialog."""

    CSS = """
    ConfirmDialog {
        align: center middle;
    }
    #confirm-container {
        width: 50;
        height: auto;
        padding: 1 2;
        border: thick #30363d;
        background: #161b22;
    }
    #confirm-title {
        text-align: center;
        text-style: bold;
        color: #e6edf3;
        padding: 1 0;
    }
    #confirm-buttons {
        height: 3;
        align: center middle;
        margin-top: 1;
    }
    #confirm-buttons Button {
        margin: 0 1;
    }
    """

    def __init__(self, title: str, message: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._title = title
        self._message = message

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-container"):
            yield Static(self._title, id="confirm-title")
            yield Label(self._message)
            with Horizontal(id="confirm-buttons"):
                yield Button("Yes", id="yes-btn", variant="primary")
                yield Button("No", id="no-btn", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "yes-btn")


class SelectDialog(ModalScreen[str | None]):
    """Selection dialog with an OptionList."""

    CSS = """
    SelectDialog {
        align: center middle;
    }
    #select-container {
        width: 60;
        height: auto;
        max-height: 80%;
        padding: 1 2;
        border: thick #30363d;
        background: #161b22;
    }
    #select-title {
        text-align: center;
        text-style: bold;
        color: #e6edf3;
        padding: 1 0;
    }
    #select-list {
        height: 16;
        background: #0d1117;
    }
    #cancel-btn {
        margin-top: 1;
        width: 100%;
    }
    """

    def __init__(self, title: str, options: list[tuple[str, str]], **kwargs) -> None:
        super().__init__(**kwargs)
        self._title = title
        self._options = options  # list of (id, display)

    def compose(self) -> ComposeResult:
        with Vertical(id="select-container"):
            yield Static(self._title, id="select-title")
            yield OptionList(
                *[Option(display, id=oid) for oid, display in self._options],
                id="select-list",
            )
            yield Button("Cancel", id="cancel-btn", variant="default")

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option_id is not None:
            self.dismiss(event.option_id)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-btn":
            self.dismiss(None)
