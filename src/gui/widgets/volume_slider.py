"""
Volume slider widget with label
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from ..theme import Colors


class VolumeSlider(ttk.Frame):
    """Modern volume slider with label and value display."""

    def __init__(
        self,
        parent: tk.Widget,
        label: str,
        initial_value: float = 100,
        min_value: float = 0,
        max_value: float = 110,
        on_change: Optional[Callable[[float], None]] = None,
        **kwargs
    ):
        super().__init__(parent, style="Card.TFrame", **kwargs)

        self.on_change = on_change
        self.min_value = min_value
        self.max_value = max_value

        self._create_widgets(label, initial_value)

    def _create_widgets(self, label: str, initial_value: float) -> None:
        """Create the slider widgets."""
        self.columnconfigure(1, weight=1)

        # Label
        ttk.Label(
            self,
            text=label,
            style="Card.TLabel",
            font=("Segoe UI", 9)
        ).grid(row=0, column=0, sticky="w", padx=(0, 10))

        # Scale
        self.scale = ttk.Scale(
            self,
            from_=self.min_value,
            to=self.max_value,
            orient=tk.HORIZONTAL,
            command=self._on_change
        )
        self.scale.set(initial_value)
        self.scale.grid(row=0, column=1, sticky="ew")

        # Value label
        self.lbl_value = ttk.Label(
            self,
            text=f"{int(initial_value)}%",
            style="Card.TLabel",
            width=5
        )
        self.lbl_value.grid(row=0, column=2, sticky="e", padx=(10, 0))

    def _on_change(self, value: str) -> None:
        """Handle value change."""
        val = float(value)
        self.lbl_value.config(text=f"{int(val)}%")
        if self.on_change:
            self.on_change(val)

    def get(self) -> float:
        """Get current value."""
        return self.scale.get()

    def set(self, value: float) -> None:
        """Set value."""
        self.scale.set(value)
        self.lbl_value.config(text=f"{int(value)}%")


class DualVolumePanel(ttk.Frame):
    """Panel with two volume sliders (music and video audio)."""

    def __init__(
        self,
        parent: tk.Widget,
        on_music_change: Optional[Callable[[float], None]] = None,
        on_video_change: Optional[Callable[[float], None]] = None,
        **kwargs
    ):
        super().__init__(parent, style="Card.TFrame", **kwargs)

        self.configure(padding=15)
        self._create_widgets(on_music_change, on_video_change)

    def _create_widgets(
        self,
        on_music_change: Optional[Callable[[float], None]],
        on_video_change: Optional[Callable[[float], None]]
    ) -> None:
        """Create the panel widgets."""
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        # Title
        ttk.Label(
            self,
            text="Volumes Globaux",
            style="Card.TLabel",
            font=("Segoe UI", 11, "bold"),
            foreground=Colors.ACCENT_PRIMARY
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        # Music volume
        music_frame = ttk.Frame(self, style="Card.TFrame")
        music_frame.grid(row=1, column=0, sticky="ew", padx=(0, 10))
        music_frame.columnconfigure(0, weight=1)

        ttk.Label(
            music_frame,
            text="Musiques",
            style="Card.TLabel",
            foreground=Colors.TEXT_SECONDARY,
            font=("Segoe UI", 9)
        ).grid(row=0, column=0, sticky="w")

        self.music_slider = VolumeSlider(
            music_frame,
            label="",
            initial_value=70,
            on_change=on_music_change
        )
        self.music_slider.grid(row=1, column=0, sticky="ew")

        # Video audio volume
        video_frame = ttk.Frame(self, style="Card.TFrame")
        video_frame.grid(row=1, column=1, sticky="ew", padx=(10, 0))
        video_frame.columnconfigure(0, weight=1)

        ttk.Label(
            video_frame,
            text="Audio des videos",
            style="Card.TLabel",
            foreground=Colors.TEXT_SECONDARY,
            font=("Segoe UI", 9)
        ).grid(row=0, column=0, sticky="w")

        self.video_slider = VolumeSlider(
            video_frame,
            label="",
            initial_value=100,
            on_change=on_video_change
        )
        self.video_slider.grid(row=1, column=0, sticky="ew")

    def get_music_volume(self) -> float:
        """Get music volume."""
        return self.music_slider.get()

    def get_video_volume(self) -> float:
        """Get video volume."""
        return self.video_slider.get()

    def set_music_volume(self, value: float) -> None:
        """Set music volume."""
        self.music_slider.set(value)

    def set_video_volume(self, value: float) -> None:
        """Set video volume."""
        self.video_slider.set(value)
