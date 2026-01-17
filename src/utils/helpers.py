"""
Utility functions for Video-Musique
"""

from __future__ import annotations

import os
import tkinter as tk
from typing import Optional


def format_duration(seconds: float | int) -> str:
    """
    Format seconds to human readable duration.
    Returns 'H:MM:SS' or 'M:SS' format.
    """
    sec = int(round(seconds))
    m, s = divmod(sec, 60)
    h, m = divmod(m, 60)

    if h:
        return f"{h:d}:{m:02d}:{s:02d}"
    return f"{m:d}:{s:02d}"


def format_size(size_bytes: int) -> str:
    """
    Format bytes to human readable size.
    Returns size with appropriate unit (B, KB, MB, GB).
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    if size_bytes < 1024 ** 3:
        return f"{size_bytes / 1024 ** 2:.1f} MB"
    return f"{size_bytes / 1024 ** 3:.2f} GB"


def get_file_size(path: str) -> str:
    """Get formatted file size for a path."""
    if os.path.exists(path):
        return format_size(os.path.getsize(path))
    return "?"


class ToolTip:
    """Modern tooltip implementation."""

    def __init__(
        self,
        widget: tk.Widget,
        text: str,
        bg: str = "#333333",
        fg: str = "#ffffff",
        font: tuple = ("Segoe UI", 9),
        delay: int = 500
    ):
        self.widget = widget
        self.text = text
        self.bg = bg
        self.fg = fg
        self.font = font
        self.delay = delay
        self.tooltip: Optional[tk.Toplevel] = None
        self.after_id: Optional[str] = None

        widget.bind("<Enter>", self._schedule)
        widget.bind("<Leave>", self._hide)
        widget.bind("<ButtonPress>", self._hide)

    def _schedule(self, event=None):
        """Schedule tooltip display."""
        self._hide()
        self.after_id = self.widget.after(self.delay, self._show)

    def _show(self, event=None):
        """Display the tooltip."""
        if self.tooltip:
            return

        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5

        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")

        label = tk.Label(
            self.tooltip,
            text=self.text,
            background=self.bg,
            foreground=self.fg,
            font=self.font,
            relief="flat",
            padx=8,
            pady=4
        )
        label.pack()

    def _hide(self, event=None):
        """Hide the tooltip."""
        if self.after_id:
            self.widget.after_cancel(self.after_id)
            self.after_id = None

        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None


def create_tooltip(widget: tk.Widget, text: str, **kwargs) -> ToolTip:
    """Create a tooltip for a widget."""
    return ToolTip(widget, text, **kwargs)


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp a value between min and max."""
    return max(min_val, min(value, max_val))


def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation between a and b."""
    return a + (b - a) * clamp(t, 0.0, 1.0)
