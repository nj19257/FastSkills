"""Loading indicator widget."""

from __future__ import annotations

from textual.widgets import Static


class LoadingIndicator(Static):
    """Animated-style text indicator that shows/hides via CSS class toggle."""

    def __init__(self, **kwargs) -> None:
        super().__init__("", id="loading-indicator", **kwargs)
        self.add_class("hidden")

    def show(self, text: str = "Thinking...") -> None:
        self.update(f"  ● {text}")
        self.remove_class("hidden")

    def hide(self) -> None:
        self.add_class("hidden")
