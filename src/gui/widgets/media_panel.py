"""
Media panel widget for displaying and managing media files
"""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional, List, Any

from ..theme import Colors
from ...utils.helpers import format_duration, get_file_size, create_tooltip


class MediaPanel(ttk.Frame):
    """
    Modern panel for displaying media files (videos or audio tracks).
    Features: selection, reordering, add/remove, details display.
    """

    def __init__(
        self,
        parent: tk.Widget,
        title: str,
        media_type: str = "video",
        on_selection_change: Optional[Callable] = None,
        on_add: Optional[Callable] = None,
        on_remove: Optional[Callable] = None,
        on_move: Optional[Callable[[int], None]] = None,
        **kwargs
    ):
        super().__init__(parent, style="Card.TFrame", **kwargs)

        self.media_type = media_type
        self.on_selection_change = on_selection_change
        self.on_add = on_add
        self.on_remove = on_remove
        self.on_move = on_move
        self.items: List[Any] = []

        self._create_widgets(title)

    def _create_widgets(self, title: str) -> None:
        """Create the panel widgets."""
        self.configure(padding=15)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # Header
        header = ttk.Frame(self, style="Card.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header.columnconfigure(0, weight=1)

        ttk.Label(
            header,
            text=title,
            style="Card.TLabel",
            font=("Segoe UI", 11, "bold"),
            foreground=Colors.ACCENT_PRIMARY
        ).grid(row=0, column=0, sticky="w")

        # Buttons frame
        btn_frame = ttk.Frame(header, style="Card.TFrame")
        btn_frame.grid(row=0, column=1, sticky="e")

        self.btn_add = ttk.Button(
            btn_frame,
            text="+",
            style="Icon.TButton",
            width=3,
            command=self._on_add
        )
        self.btn_add.pack(side=tk.LEFT, padx=2)
        create_tooltip(self.btn_add, "Ajouter")

        self.btn_up = ttk.Button(
            btn_frame,
            text="\u2191",
            style="Icon.TButton",
            width=3,
            command=lambda: self._on_move(-1)
        )
        self.btn_up.pack(side=tk.LEFT, padx=2)
        create_tooltip(self.btn_up, "Monter")

        self.btn_down = ttk.Button(
            btn_frame,
            text="\u2193",
            style="Icon.TButton",
            width=3,
            command=lambda: self._on_move(1)
        )
        self.btn_down.pack(side=tk.LEFT, padx=2)
        create_tooltip(self.btn_down, "Descendre")

        self.btn_remove = ttk.Button(
            btn_frame,
            text="\u2715",
            style="Icon.TButton",
            width=3,
            command=self._on_remove
        )
        self.btn_remove.pack(side=tk.LEFT, padx=2)
        create_tooltip(self.btn_remove, "Supprimer")

        # Listbox with scrollbar
        list_frame = ttk.Frame(self, style="Card.TFrame")
        list_frame.grid(row=1, column=0, sticky="nsew")
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        # Custom listbox styling
        listbox_config = {
            "bg": Colors.BG_INPUT,
            "fg": Colors.TEXT_PRIMARY,
            "selectbackground": Colors.ACCENT_PRIMARY,
            "selectforeground": Colors.TEXT_PRIMARY,
            "highlightthickness": 0,
            "borderwidth": 0,
            "relief": "flat",
            "font": ("Segoe UI", 10),
            "activestyle": "none",
            "exportselection": False
        }

        self.listbox = tk.Listbox(list_frame, height=8, **listbox_config)
        self.listbox.grid(row=0, column=0, sticky="nsew")
        self.listbox.bind("<<ListboxSelect>>", self._on_selection)

        scrollbar = ttk.Scrollbar(
            list_frame,
            orient="vertical",
            command=self.listbox.yview
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.listbox.config(yscrollcommand=scrollbar.set)

        # Details section
        self.details_frame = ttk.Frame(self, style="Card.TFrame")
        self.details_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))

        self.lbl_details = ttk.Label(
            self.details_frame,
            text="Aucun fichier selectionne",
            style="Card.TLabel",
            foreground=Colors.TEXT_SECONDARY,
            font=("Segoe UI", 9)
        )
        self.lbl_details.pack(fill=tk.X)

    def _on_selection(self, event=None) -> None:
        """Handle selection change."""
        if self.on_selection_change:
            self.on_selection_change(self.get_selection())

    def _on_add(self) -> None:
        """Handle add button click."""
        if self.on_add:
            self.on_add()

    def _on_remove(self) -> None:
        """Handle remove button click."""
        if self.on_remove:
            self.on_remove()

    def _on_move(self, direction: int) -> None:
        """Handle move button click."""
        if self.on_move:
            self.on_move(direction)

    def get_selection(self) -> Optional[int]:
        """Get currently selected index."""
        sel = self.listbox.curselection()
        return sel[0] if sel else None

    def set_selection(self, index: int) -> None:
        """Set selection to specific index."""
        self.listbox.selection_clear(0, tk.END)
        if 0 <= index < self.listbox.size():
            self.listbox.selection_set(index)
            self.listbox.see(index)

    def clear(self) -> None:
        """Clear all items."""
        self.listbox.delete(0, tk.END)
        self.items.clear()
        self.lbl_details.config(text="Aucun fichier selectionne")

    def refresh(self, items: List[Any], format_func: Callable[[Any], str]) -> None:
        """Refresh the list with new items."""
        current_sel = self.get_selection()
        self.listbox.delete(0, tk.END)
        self.items = items

        for item in items:
            self.listbox.insert(tk.END, format_func(item))

        # Restore selection if possible
        if current_sel is not None and current_sel < len(items):
            self.set_selection(current_sel)

    def update_details(self, text: str) -> None:
        """Update the details label."""
        self.lbl_details.config(text=text)


class AudioTrackPanel(MediaPanel):
    """Specialized panel for audio tracks with volume/mute/solo controls."""

    def __init__(
        self,
        parent: tk.Widget,
        on_volume_change: Optional[Callable[[float], None]] = None,
        on_mute_toggle: Optional[Callable] = None,
        on_solo_toggle: Optional[Callable] = None,
        **kwargs
    ):
        super().__init__(parent, title="Pistes Audio", media_type="audio", **kwargs)

        self.on_volume_change = on_volume_change
        self.on_mute_toggle = on_mute_toggle
        self.on_solo_toggle = on_solo_toggle

        self._create_audio_controls()

    def _create_audio_controls(self) -> None:
        """Create audio-specific controls."""
        controls_frame = ttk.Frame(self.details_frame, style="Card.TFrame")
        controls_frame.pack(fill=tk.X, pady=(10, 0))

        # Volume control
        vol_frame = ttk.Frame(controls_frame, style="Card.TFrame")
        vol_frame.pack(fill=tk.X, pady=5)

        ttk.Label(
            vol_frame,
            text="Volume",
            style="Card.TLabel",
            font=("Segoe UI", 9)
        ).pack(side=tk.LEFT, padx=(0, 10))

        self.volume_scale = ttk.Scale(
            vol_frame,
            from_=0,
            to=110,
            orient=tk.HORIZONTAL,
            command=self._on_volume_change
        )
        self.volume_scale.set(100)
        self.volume_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.lbl_volume = ttk.Label(
            vol_frame,
            text="100%",
            style="Card.TLabel",
            width=5
        )
        self.lbl_volume.pack(side=tk.LEFT, padx=(10, 0))

        # Mute/Solo buttons
        btn_frame = ttk.Frame(controls_frame, style="Card.TFrame")
        btn_frame.pack(fill=tk.X, pady=5)

        self.var_mute = tk.BooleanVar(value=False)
        self.var_solo = tk.BooleanVar(value=False)

        self.chk_mute = ttk.Checkbutton(
            btn_frame,
            text="Mute",
            variable=self.var_mute,
            command=self._on_mute_toggle
        )
        self.chk_mute.pack(side=tk.LEFT, padx=(0, 15))

        self.chk_solo = ttk.Checkbutton(
            btn_frame,
            text="Solo",
            variable=self.var_solo,
            command=self._on_solo_toggle
        )
        self.chk_solo.pack(side=tk.LEFT)

    def _on_volume_change(self, value: str) -> None:
        """Handle volume change."""
        vol = float(value)
        self.lbl_volume.config(text=f"{int(vol)}%")
        if self.on_volume_change:
            self.on_volume_change(vol)

    def _on_mute_toggle(self) -> None:
        """Handle mute toggle."""
        if self.on_mute_toggle:
            self.on_mute_toggle()

    def _on_solo_toggle(self) -> None:
        """Handle solo toggle."""
        if self.on_solo_toggle:
            self.on_solo_toggle()

    def set_track_state(self, volume: float, mute: bool, solo: bool) -> None:
        """Set the current track's controls state."""
        self.volume_scale.set(volume * 100)
        self.lbl_volume.config(text=f"{int(volume * 100)}%")
        self.var_mute.set(mute)
        self.var_solo.set(solo)

    def reset_controls(self) -> None:
        """Reset controls to default state."""
        self.volume_scale.set(100)
        self.lbl_volume.config(text="100%")
        self.var_mute.set(False)
        self.var_solo.set(False)
