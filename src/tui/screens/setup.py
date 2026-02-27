"""Setup screen — first-run configuration for API key, model, etc."""

from __future__ import annotations

from pathlib import Path

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, OptionList, Static
from textual.widgets.option_list import Option

from tui.settings import fetch_openrouter_models


class SetupScreen(Screen):
    """First-run / settings screen — collects API key, model, skills_dir, workdir."""

    CSS_PATH = Path(__file__).parent.parent / "styles" / "setup.tcss"

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, existing: dict | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._existing = existing or {}
        self._models: list[dict] = []
        self._selected_model: str = ""

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
                yield Input(
                    id="model-search",
                    placeholder="Search models or enter model ID...",
                )
                yield OptionList(id="model-list")
                yield Static("Skills Directory:", classes="field-label")
                yield Input(
                    id="skills-dir",
                    placeholder="~/.fastskills/skills/",
                )
                yield Static("Leave empty for default (~/.fastskills/skills/)", classes="field-hint")
                yield Static("Working Directory:", classes="field-label")
                yield Input(
                    id="workdir",
                    placeholder="/path/to/workdir",
                )
                yield Static("Leave empty for none", classes="field-hint")
                yield Button("Start Chat", id="start-btn", variant="primary")
        yield Footer()

    def on_mount(self) -> None:
        api_key_input = self.query_one("#api-key", Input)
        if self._existing.get("api_key"):
            api_key_input.value = self._existing["api_key"]
        if self._existing.get("model"):
            self._selected_model = self._existing["model"]
            self.query_one("#model-search", Input).value = self._existing["model"]
        if self._existing.get("skills_dir"):
            self.query_one("#skills-dir", Input).value = self._existing["skills_dir"]
        if self._existing.get("workdir"):
            self.query_one("#workdir", Input).value = self._existing["workdir"]
        api_key_input.focus()

        option_list = self.query_one("#model-list", OptionList)
        option_list.add_option(Option("Loading models...", disabled=True))
        self._fetch_models_async()

    @work(thread=True)
    def _fetch_models_async(self) -> None:
        self._models = fetch_openrouter_models()
        self.call_from_thread(self._populate_models)

    def _populate_models(self) -> None:
        option_list = self.query_one("#model-list", OptionList)
        option_list.clear_options()
        if not self._models:
            option_list.add_option(Option("Failed to load — type model ID above", disabled=True))
            return
        search = self.query_one("#model-search", Input).value.strip().lower()
        self._filter_and_populate(search)

    def _filter_and_populate(self, search: str) -> None:
        option_list = self.query_one("#model-list", OptionList)
        option_list.clear_options()
        for m in self._models:
            if search and search not in m["display"].lower() and search not in m["id"].lower():
                continue
            option_list.add_option(Option(m["display"], id=m["id"]))

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "model-search" and self._models:
            self._filter_and_populate(event.value.strip().lower())

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option_list.id == "model-list" and event.option_id is not None:
            self._selected_model = event.option_id
            self.query_one("#model-search", Input).value = event.option_id

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "start-btn":
            self._submit()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "model-search":
            self._submit()

    def _submit(self) -> None:
        api_key = self.query_one("#api-key", Input).value.strip()
        model = self._selected_model or self.query_one("#model-search", Input).value.strip()
        skills_dir = self.query_one("#skills-dir", Input).value.strip()
        workdir = self.query_one("#workdir", Input).value.strip()

        if not api_key:
            self.notify("Please enter an API key", severity="error")
            return
        if not model:
            self.notify("Please select or enter a model", severity="error")
            return
        self.dismiss({"api_key": api_key, "model": model, "skills_dir": skills_dir, "workdir": workdir})

    def action_cancel(self) -> None:
        self.dismiss(None)
