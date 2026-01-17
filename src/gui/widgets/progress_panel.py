"""
Progress panel with animated indicator
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional

from ..theme import Colors
from ...utils.helpers import format_duration


class ProgressPanel(ttk.Frame):
    """Modern progress panel with bar and animated indicator."""

    def __init__(self, parent: tk.Widget, **kwargs):
        super().__init__(parent, style="Card.TFrame", **kwargs)

        self.configure(padding=15)
        self._animating = False
        self._rect: Optional[int] = None

        self._create_widgets()

    def _create_widgets(self) -> None:
        """Create the panel widgets."""
        self.columnconfigure(0, weight=1)

        # Progress bar
        self.progress_var = tk.DoubleVar(value=0.0)
        self.progressbar = ttk.Progressbar(
            self,
            variable=self.progress_var,
            mode="determinate",
            style="Horizontal.TProgressbar"
        )
        self.progressbar.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        # Animated indicator canvas
        self.canvas = tk.Canvas(
            self,
            height=6,
            bg=Colors.PROGRESS_BG,
            highlightthickness=0,
            borderwidth=0
        )
        self.canvas.grid(row=1, column=0, sticky="ew")

        # Status row
        status_frame = ttk.Frame(self, style="Card.TFrame")
        status_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        status_frame.columnconfigure(1, weight=1)

        ttk.Label(
            status_frame,
            text="Statut:",
            style="Card.TLabel",
            font=("Segoe UI", 9),
            foreground=Colors.TEXT_SECONDARY
        ).grid(row=0, column=0, sticky="w")

        self.lbl_status = ttk.Label(
            status_frame,
            text="Pret",
            style="Card.TLabel",
            font=("Segoe UI", 9)
        )
        self.lbl_status.grid(row=0, column=1, sticky="w", padx=(8, 0))

        # Time display
        time_frame = ttk.Frame(status_frame, style="Card.TFrame")
        time_frame.grid(row=0, column=2, sticky="e")

        ttk.Label(
            time_frame,
            text="Temps:",
            style="Card.TLabel",
            font=("Segoe UI", 9),
            foreground=Colors.TEXT_SECONDARY
        ).pack(side=tk.LEFT)

        self.lbl_time = ttk.Label(
            time_frame,
            text="0:00",
            style="Card.TLabel",
            font=("Segoe UI", 9, "bold"),
            width=8
        )
        self.lbl_time.pack(side=tk.LEFT, padx=(8, 0))

    def set_progress(self, value: float) -> None:
        """Set progress value (0-100)."""
        self.progress_var.set(value)

    def set_status(self, text: str) -> None:
        """Set status text."""
        self.lbl_status.config(text=text)

    def set_time(self, seconds: float) -> None:
        """Set elapsed time display."""
        self.lbl_time.config(text=format_duration(seconds))

    def start_animation(self) -> None:
        """Start the animated indicator."""
        if self._animating:
            return

        self._animating = True
        if self._rect is None:
            self._rect = self.canvas.create_rectangle(
                0, 0, 30, 6,
                fill=Colors.ACCENT_PRIMARY,
                outline=""
            )
        self._animate()

    def _animate(self) -> None:
        """Animation step."""
        if not self._animating or self._rect is None:
            return

        x1, y1, x2, y2 = self.canvas.coords(self._rect)
        width = self.canvas.winfo_width()
        step = 4

        if x2 + step >= width:
            self.canvas.coords(self._rect, 0, 0, 30, 6)
        else:
            self.canvas.move(self._rect, step, 0)

        self.after(30, self._animate)

    def stop_animation(self) -> None:
        """Stop the animated indicator."""
        self._animating = False
        if self._rect is not None:
            self.canvas.delete(self._rect)
            self._rect = None

    def reset(self) -> None:
        """Reset the panel to initial state."""
        self.stop_animation()
        self.set_progress(0)
        self.set_status("Pret")
        self.set_time(0)


class DurationPanel(ttk.Frame):
    """Panel showing video and music durations."""

    def __init__(self, parent: tk.Widget, **kwargs):
        super().__init__(parent, style="Card.TFrame", **kwargs)

        self.configure(padding=(15, 8))
        self._create_widgets()

    def _create_widgets(self) -> None:
        """Create the panel widgets."""
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        # Video duration
        video_frame = ttk.Frame(self, style="Card.TFrame")
        video_frame.grid(row=0, column=0, sticky="w")

        ttk.Label(
            video_frame,
            text="Duree videos:",
            style="Card.TLabel",
            font=("Segoe UI", 9),
            foreground=Colors.TEXT_SECONDARY
        ).pack(side=tk.LEFT)

        self.lbl_video_duration = ttk.Label(
            video_frame,
            text="0:00",
            style="Card.TLabel",
            font=("Segoe UI", 9, "bold")
        )
        self.lbl_video_duration.pack(side=tk.LEFT, padx=(8, 0))

        # Music duration
        music_frame = ttk.Frame(self, style="Card.TFrame")
        music_frame.grid(row=0, column=1, sticky="e")

        ttk.Label(
            music_frame,
            text="Duree musiques:",
            style="Card.TLabel",
            font=("Segoe UI", 9),
            foreground=Colors.TEXT_SECONDARY
        ).pack(side=tk.LEFT)

        self.lbl_music_duration = ttk.Label(
            music_frame,
            text="0:00",
            style="Card.TLabel",
            font=("Segoe UI", 9, "bold")
        )
        self.lbl_music_duration.pack(side=tk.LEFT, padx=(8, 0))

    def set_video_duration(self, seconds: float) -> None:
        """Set video duration display."""
        self.lbl_video_duration.config(text=format_duration(seconds))

    def set_music_duration(self, seconds: float) -> None:
        """Set music duration display."""
        self.lbl_music_duration.config(text=format_duration(seconds))
