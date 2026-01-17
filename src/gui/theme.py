"""
Modern theme for Video-Musique
Clean and intuitive design
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional


class Colors:
    """Modern color palette."""

    # Main colors
    BG_PRIMARY = "#1a1a2e"      # Dark blue background
    BG_SECONDARY = "#16213e"    # Slightly lighter
    BG_CARD = "#1f2940"         # Card background
    BG_INPUT = "#2a3f5f"        # Input fields

    # Accent colors
    ACCENT_PRIMARY = "#4f8cff"   # Blue accent
    ACCENT_HOVER = "#6ba3ff"     # Lighter blue
    ACCENT_SUCCESS = "#4ade80"   # Green
    ACCENT_WARNING = "#fbbf24"   # Yellow
    ACCENT_DANGER = "#f87171"    # Red

    # Text colors
    TEXT_PRIMARY = "#f1f5f9"     # Main text
    TEXT_SECONDARY = "#94a3b8"   # Secondary text
    TEXT_MUTED = "#64748b"       # Muted text

    # Border colors
    BORDER = "#334155"
    BORDER_FOCUS = "#4f8cff"

    # Progress
    PROGRESS_BG = "#334155"
    PROGRESS_FG = "#4f8cff"


class Theme:
    """Modern theme manager for the application."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.style = ttk.Style()
        self._setup_theme()

    def _setup_theme(self) -> None:
        """Configure the modern theme."""
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        self._configure_root()
        self._configure_frames()
        self._configure_labels()
        self._configure_buttons()
        self._configure_entries()
        self._configure_listbox()
        self._configure_scrollbar()
        self._configure_scale()
        self._configure_checkbutton()
        self._configure_progressbar()
        self._configure_spinbox()
        self._configure_menu()

    def _configure_root(self) -> None:
        """Configure root window."""
        self.root.configure(bg=Colors.BG_PRIMARY)
        try:
            self.root.tk_setPalette(
                background=Colors.BG_PRIMARY,
                foreground=Colors.TEXT_PRIMARY,
                activeBackground=Colors.ACCENT_PRIMARY,
                activeForeground=Colors.TEXT_PRIMARY,
                highlightBackground=Colors.BORDER,
                highlightColor=Colors.BORDER_FOCUS,
                insertBackground=Colors.TEXT_PRIMARY,
                selectBackground=Colors.ACCENT_PRIMARY,
                selectForeground=Colors.TEXT_PRIMARY
            )
        except Exception:
            pass

    def _configure_frames(self) -> None:
        """Configure frame styles."""
        self.style.configure(
            "TFrame",
            background=Colors.BG_PRIMARY
        )

        self.style.configure(
            "Card.TFrame",
            background=Colors.BG_CARD,
            relief="flat"
        )

        self.style.configure(
            "TLabelframe",
            background=Colors.BG_CARD,
            foreground=Colors.TEXT_PRIMARY,
            borderwidth=0,
            relief="flat"
        )

        self.style.configure(
            "TLabelframe.Label",
            background=Colors.BG_CARD,
            foreground=Colors.ACCENT_PRIMARY,
            font=("Segoe UI", 10, "bold")
        )

    def _configure_labels(self) -> None:
        """Configure label styles."""
        self.style.configure(
            "TLabel",
            background=Colors.BG_PRIMARY,
            foreground=Colors.TEXT_PRIMARY,
            font=("Segoe UI", 10)
        )

        self.style.configure(
            "Card.TLabel",
            background=Colors.BG_CARD,
            foreground=Colors.TEXT_PRIMARY
        )

        self.style.configure(
            "Title.TLabel",
            background=Colors.BG_PRIMARY,
            foreground=Colors.TEXT_PRIMARY,
            font=("Segoe UI", 16, "bold")
        )

        self.style.configure(
            "Subtitle.TLabel",
            background=Colors.BG_PRIMARY,
            foreground=Colors.TEXT_SECONDARY,
            font=("Segoe UI", 10)
        )

        self.style.configure(
            "Status.TLabel",
            background=Colors.BG_PRIMARY,
            foreground=Colors.TEXT_SECONDARY,
            font=("Segoe UI", 9)
        )

        self.style.configure(
            "Success.TLabel",
            background=Colors.BG_PRIMARY,
            foreground=Colors.ACCENT_SUCCESS
        )

    def _configure_buttons(self) -> None:
        """Configure button styles."""
        # Primary button
        self.style.configure(
            "TButton",
            background=Colors.ACCENT_PRIMARY,
            foreground=Colors.TEXT_PRIMARY,
            font=("Segoe UI", 10),
            padding=(12, 6),
            borderwidth=0,
            relief="flat"
        )

        self.style.map(
            "TButton",
            background=[
                ("active", Colors.ACCENT_HOVER),
                ("disabled", Colors.BG_INPUT)
            ],
            foreground=[
                ("disabled", Colors.TEXT_MUTED)
            ]
        )

        # Secondary button
        self.style.configure(
            "Secondary.TButton",
            background=Colors.BG_INPUT,
            foreground=Colors.TEXT_PRIMARY
        )

        self.style.map(
            "Secondary.TButton",
            background=[
                ("active", Colors.BORDER),
                ("disabled", Colors.BG_SECONDARY)
            ]
        )

        # Danger button
        self.style.configure(
            "Danger.TButton",
            background=Colors.ACCENT_DANGER,
            foreground=Colors.TEXT_PRIMARY
        )

        self.style.map(
            "Danger.TButton",
            background=[("active", "#ef4444")]
        )

        # Icon button (smaller)
        self.style.configure(
            "Icon.TButton",
            background=Colors.BG_INPUT,
            foreground=Colors.TEXT_PRIMARY,
            padding=(8, 4),
            font=("Segoe UI", 10)
        )

        self.style.map(
            "Icon.TButton",
            background=[
                ("active", Colors.BORDER),
                ("disabled", Colors.BG_SECONDARY)
            ]
        )

    def _configure_entries(self) -> None:
        """Configure entry styles."""
        self.style.configure(
            "TEntry",
            fieldbackground=Colors.BG_INPUT,
            foreground=Colors.TEXT_PRIMARY,
            insertcolor=Colors.TEXT_PRIMARY,
            borderwidth=0,
            padding=8
        )

        self.style.map(
            "TEntry",
            fieldbackground=[("focus", Colors.BG_CARD)]
        )

    def _configure_listbox(self) -> None:
        """Configure listbox colors (native tk widget)."""
        # Listbox is configured directly on creation
        pass

    def _configure_scrollbar(self) -> None:
        """Configure scrollbar styles."""
        self.style.configure(
            "Vertical.TScrollbar",
            background=Colors.BG_INPUT,
            troughcolor=Colors.BG_SECONDARY,
            borderwidth=0,
            arrowsize=0
        )

        self.style.map(
            "Vertical.TScrollbar",
            background=[("active", Colors.ACCENT_PRIMARY)]
        )

    def _configure_scale(self) -> None:
        """Configure scale (slider) styles."""
        self.style.configure(
            "TScale",
            background=Colors.BG_PRIMARY,
            troughcolor=Colors.PROGRESS_BG,
            sliderthickness=16,
            borderwidth=0
        )

        self.style.configure(
            "Horizontal.TScale",
            background=Colors.BG_CARD,
            troughcolor=Colors.PROGRESS_BG
        )

    def _configure_checkbutton(self) -> None:
        """Configure checkbutton styles."""
        self.style.configure(
            "TCheckbutton",
            background=Colors.BG_CARD,
            foreground=Colors.TEXT_PRIMARY,
            font=("Segoe UI", 10),
            indicatorbackground=Colors.BG_INPUT,
            indicatorforeground=Colors.ACCENT_PRIMARY
        )

        self.style.map(
            "TCheckbutton",
            background=[("active", Colors.BG_CARD)],
            indicatorbackground=[
                ("selected", Colors.ACCENT_PRIMARY),
                ("active", Colors.BG_INPUT)
            ]
        )

    def _configure_progressbar(self) -> None:
        """Configure progressbar styles."""
        self.style.configure(
            "TProgressbar",
            background=Colors.PROGRESS_FG,
            troughcolor=Colors.PROGRESS_BG,
            borderwidth=0,
            thickness=8
        )

        self.style.configure(
            "Horizontal.TProgressbar",
            background=Colors.ACCENT_PRIMARY,
            troughcolor=Colors.PROGRESS_BG
        )

    def _configure_spinbox(self) -> None:
        """Configure spinbox styles."""
        self.style.configure(
            "TSpinbox",
            fieldbackground=Colors.BG_INPUT,
            foreground=Colors.TEXT_PRIMARY,
            background=Colors.BG_INPUT,
            arrowcolor=Colors.TEXT_SECONDARY,
            borderwidth=0,
            padding=4
        )

    def _configure_menu(self) -> None:
        """Configure menu styles."""
        self.style.configure(
            "TMenubutton",
            background=Colors.BG_INPUT,
            foreground=Colors.TEXT_PRIMARY,
            padding=(12, 6)
        )

    @staticmethod
    def get_listbox_config() -> dict:
        """Get configuration dict for Listbox widgets."""
        return {
            "bg": Colors.BG_INPUT,
            "fg": Colors.TEXT_PRIMARY,
            "selectbackground": Colors.ACCENT_PRIMARY,
            "selectforeground": Colors.TEXT_PRIMARY,
            "highlightthickness": 0,
            "borderwidth": 0,
            "relief": "flat",
            "font": ("Segoe UI", 10),
            "activestyle": "none"
        }

    @staticmethod
    def get_canvas_config() -> dict:
        """Get configuration dict for Canvas widgets."""
        return {
            "bg": Colors.BG_CARD,
            "highlightthickness": 0,
            "borderwidth": 0
        }

    @staticmethod
    def get_spinbox_config() -> dict:
        """Get configuration dict for Spinbox widgets."""
        return {
            "bg": Colors.BG_INPUT,
            "fg": Colors.TEXT_PRIMARY,
            "buttonbackground": Colors.BG_INPUT,
            "highlightthickness": 0,
            "borderwidth": 0,
            "relief": "flat",
            "font": ("Segoe UI", 10),
            "insertbackground": Colors.TEXT_PRIMARY,
            "selectbackground": Colors.ACCENT_PRIMARY,
            "selectforeground": Colors.TEXT_PRIMARY
        }

    @staticmethod
    def get_menu_config() -> dict:
        """Get configuration dict for Menu widgets."""
        return {
            "bg": Colors.BG_CARD,
            "fg": Colors.TEXT_PRIMARY,
            "activebackground": Colors.ACCENT_PRIMARY,
            "activeforeground": Colors.TEXT_PRIMARY,
            "borderwidth": 0,
            "relief": "flat",
            "font": ("Segoe UI", 10)
        }
