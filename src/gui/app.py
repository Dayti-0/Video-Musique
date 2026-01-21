"""
Main application for Video-Musique
Modern and intuitive interface
"""

from __future__ import annotations

import os
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Optional

from .theme import Theme, Colors
from .widgets.media_panel import MediaPanel, AudioTrackPanel
from .widgets.volume_slider import DualVolumePanel
from .widgets.progress_panel import ProgressPanel, DurationPanel
from .controllers import (
    PreviewController,
    ExportController,
    ProjectController,
    MediaController,
)
from ..core.models import AudioTrack, VideoClip, Project
from ..core.ffmpeg import FFmpegProcessor
from ..core.config import Config
from ..utils.helpers import format_duration, get_file_size
from ..utils.logger import get_logger


class VideoMusiqueApp:
    """Main application class with modern UI."""

    APP_TITLE = "Mixeur Video Audio"
    MIN_WIDTH = 1100
    MIN_HEIGHT = 700

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(self.APP_TITLE)
        self.root.minsize(self.MIN_WIDTH, self.MIN_HEIGHT)

        # Initialize core components
        self.config = Config()
        self.ffmpeg = FFmpegProcessor()
        self.project = Project()
        self._logger = get_logger()

        # Initialize controllers
        self._init_controllers()

        # Cleanup temp files on start
        FFmpegProcessor.cleanup_temp_files()

        # Setup theme and build UI
        self.theme = Theme(root)
        self._build_ui()

        # Set window size from config
        width, height = self.config.window_size
        self.root.geometry(f"{width}x{height}")

        # Protocol handlers
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

        # Setup drag & drop if available
        self._setup_drag_drop()

    def _init_controllers(self) -> None:
        """Initialize all controllers."""
        ui_callback = lambda func: self.root.after(0, func)

        # Preview controller
        self.preview_ctrl = PreviewController(self.ffmpeg, ui_callback)
        self.preview_ctrl.on_status_change = lambda s: self.progress_panel.set_status(s)
        self.preview_ctrl.on_start = self._on_preview_start
        self.preview_ctrl.on_stop = self._on_preview_stop
        self.preview_ctrl.on_error = lambda t, m: messagebox.showerror(t, m)

        # Export controller
        self.export_ctrl = ExportController(self.ffmpeg, ui_callback)
        self.export_ctrl.set_root(self.root)
        self.export_ctrl.on_progress = lambda p: self.progress_panel.set_progress(p)
        self.export_ctrl.on_status_change = lambda s: self.progress_panel.set_status(s)
        self.export_ctrl.on_time_update = lambda t: self.progress_panel.set_time(t)
        self.export_ctrl.on_start = self._on_export_start
        self.export_ctrl.on_error = lambda t, m: messagebox.showerror(t, m)

        # Project controller
        self.project_ctrl = ProjectController(self.ffmpeg, self.config, ui_callback)
        self.project_ctrl.on_status_change = lambda s: self.progress_panel.set_status(s)
        self.project_ctrl.on_error = lambda t, m: messagebox.showerror(t, m)

        # Media controller
        self.media_ctrl = MediaController(self.ffmpeg, self.config)
        self.media_ctrl.on_status_change = lambda s: self.progress_panel.set_status(s)

    # ─────────── UI Building ───────────

    def _build_ui(self) -> None:
        """Build the main user interface."""
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        self._build_header()
        self._build_main_content()
        self._build_controls()
        self._build_footer()

    def _build_header(self) -> None:
        """Build the header section with title and menu."""
        header = ttk.Frame(self.root)
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(15, 10))
        header.columnconfigure(1, weight=1)

        # App title
        title_frame = ttk.Frame(header)
        title_frame.grid(row=0, column=0, sticky="w")
        ttk.Label(title_frame, text="Mixeur Video Audio", style="Title.TLabel").pack(side=tk.LEFT)

        # Menu buttons
        menu_frame = ttk.Frame(header)
        menu_frame.grid(row=0, column=2, sticky="e")

        ttk.Button(menu_frame, text="Nouveau", style="Secondary.TButton",
                   command=self._new_project).pack(side=tk.LEFT, padx=3)
        ttk.Button(menu_frame, text="Ouvrir", style="Secondary.TButton",
                   command=self._load_project).pack(side=tk.LEFT, padx=3)
        ttk.Button(menu_frame, text="Sauvegarder", style="Secondary.TButton",
                   command=self._save_project).pack(side=tk.LEFT, padx=3)

    def _build_main_content(self) -> None:
        """Build the main content area with media panels."""
        main = ttk.Frame(self.root)
        main.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)

        # Video panel
        self.video_panel = MediaPanel(
            main, title="Videos", media_type="video",
            on_selection_change=self._on_video_select,
            on_add=self._add_videos,
            on_remove=self._remove_video,
            on_move=self._move_video
        )
        self.video_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        # Audio panel
        self.audio_panel = AudioTrackPanel(
            main,
            on_selection_change=self._on_audio_select,
            on_add=self._add_audio,
            on_remove=self._remove_audio,
            on_move=self._move_audio,
            on_volume_change=self._on_track_volume_change,
            on_mute_toggle=self._on_mute_toggle,
            on_solo_toggle=self._on_solo_toggle
        )
        self.audio_panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

    def _build_controls(self) -> None:
        """Build the controls section."""
        controls = ttk.Frame(self.root)
        controls.grid(row=2, column=0, sticky="ew", padx=20, pady=10)
        controls.columnconfigure(0, weight=1)
        controls.columnconfigure(1, weight=1)

        # Left column: Volume controls
        self.volume_panel = DualVolumePanel(
            controls,
            on_music_change=self._on_music_volume_change,
            on_video_change=self._on_video_volume_change
        )
        self.volume_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        # Right column: Options
        self._build_options_panel(controls)

    def _build_options_panel(self, parent: ttk.Frame) -> None:
        """Build the options panel."""
        options_frame = ttk.Frame(parent, style="Card.TFrame", padding=15)
        options_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        ttk.Label(options_frame, text="Options", style="Card.TLabel",
                  font=("Segoe UI", 11, "bold"),
                  foreground=Colors.ACCENT_PRIMARY).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 10))

        # Checkboxes
        self.var_include_video_audio = tk.BooleanVar(value=True)
        self.var_include_music = tk.BooleanVar(value=True)
        self.var_cut_music = tk.BooleanVar(value=False)

        ttk.Checkbutton(options_frame, text="Audio des videos",
                        variable=self.var_include_video_audio,
                        command=self._on_option_change).grid(row=1, column=0, sticky="w", pady=2)
        ttk.Checkbutton(options_frame, text="Musiques",
                        variable=self.var_include_music,
                        command=self._on_option_change).grid(row=1, column=1, sticky="w", padx=(15, 0), pady=2)
        ttk.Checkbutton(options_frame, text="Couper musique a la fin",
                        variable=self.var_cut_music,
                        command=self._on_option_change).grid(row=1, column=2, sticky="w", padx=(15, 0), pady=2)

        # Crossfade controls
        self._build_crossfade_controls(options_frame)

        # Performance settings
        self._build_performance_controls(options_frame)

    def _build_crossfade_controls(self, parent: ttk.Frame) -> None:
        """Build crossfade control widgets."""
        crossfade_frame = ttk.Frame(parent, style="Card.TFrame")
        crossfade_frame.grid(row=2, column=0, columnspan=4, sticky="ew", pady=(10, 0))

        spinbox_config = Theme.get_spinbox_config()

        ttk.Label(crossfade_frame, text="Cross-fade audio (s):", style="Card.TLabel",
                  font=("Segoe UI", 9)).pack(side=tk.LEFT)

        self.spin_audio_crossfade = tk.Spinbox(
            crossfade_frame, from_=1, to=20, width=4,
            command=self._on_option_change, **spinbox_config
        )
        self.spin_audio_crossfade.delete(0, tk.END)
        self.spin_audio_crossfade.insert(0, "10")
        self.spin_audio_crossfade.pack(side=tk.LEFT, padx=(8, 20))

        ttk.Label(crossfade_frame, text="Cross-fade video (s):", style="Card.TLabel",
                  font=("Segoe UI", 9)).pack(side=tk.LEFT)

        self.spin_video_crossfade = tk.Spinbox(
            crossfade_frame, from_=0.0, to=5.0, increment=0.5, width=4,
            command=self._on_option_change, **spinbox_config
        )
        self.spin_video_crossfade.delete(0, tk.END)
        self.spin_video_crossfade.insert(0, "1.0")
        self.spin_video_crossfade.pack(side=tk.LEFT, padx=(8, 0))

    def _build_performance_controls(self, parent: ttk.Frame) -> None:
        """Build performance control widgets."""
        perf_frame = ttk.Frame(parent, style="Card.TFrame")
        perf_frame.grid(row=3, column=0, columnspan=4, sticky="ew", pady=(10, 0))

        # GPU acceleration
        self.var_use_gpu = tk.BooleanVar(value=True)
        gpu_info = self.ffmpeg.get_gpu_info()
        gpu_text = f"Acceleration GPU ({gpu_info['type'].upper()})" if gpu_info['available'] else "Acceleration GPU (non disponible)"

        self.chk_gpu = ttk.Checkbutton(
            perf_frame, text=gpu_text, variable=self.var_use_gpu,
            command=self._on_option_change,
            state=tk.NORMAL if gpu_info['available'] else tk.DISABLED
        )
        self.chk_gpu.pack(side=tk.LEFT)

        # Speed preset
        ttk.Label(perf_frame, text="Vitesse:", style="Card.TLabel",
                  font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(20, 5))

        self.var_speed_preset = tk.StringVar(value="balanced")
        self.speed_combo = ttk.Combobox(
            perf_frame, textvariable=self.var_speed_preset,
            values=["Rapide", "Equilibre", "Qualite"], width=12, state="readonly"
        )
        self.speed_combo.set("Equilibre")
        self.speed_combo.pack(side=tk.LEFT)
        self.speed_combo.bind("<<ComboboxSelected>>", lambda e: self._on_speed_preset_change())

    def _build_footer(self) -> None:
        """Build the footer section with actions and progress."""
        footer = ttk.Frame(self.root)
        footer.grid(row=3, column=0, sticky="ew", padx=20, pady=(10, 15))
        footer.columnconfigure(0, weight=1)

        # Duration info
        self.duration_panel = DurationPanel(footer)
        self.duration_panel.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        # Action buttons
        action_frame = ttk.Frame(footer, style="Card.TFrame", padding=15)
        action_frame.grid(row=1, column=0, sticky="ew")
        action_frame.columnconfigure(2, weight=1)

        # Preview buttons
        preview_frame = ttk.Frame(action_frame, style="Card.TFrame")
        preview_frame.grid(row=0, column=0, sticky="w")

        self.btn_preview_short = ttk.Button(
            preview_frame, text="Preview 60s", style="Secondary.TButton",
            command=lambda: self._play_preview(clip=True), state=tk.DISABLED
        )
        self.btn_preview_short.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_preview_full = ttk.Button(
            preview_frame, text="Preview complet", style="Secondary.TButton",
            command=lambda: self._play_preview(clip=False), state=tk.DISABLED
        )
        self.btn_preview_full.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_stop_preview = ttk.Button(
            preview_frame, text="Stop", style="Danger.TButton",
            command=self._stop_preview, state=tk.DISABLED
        )
        self.btn_stop_preview.pack(side=tk.LEFT)

        # Export buttons
        export_frame = ttk.Frame(action_frame, style="Card.TFrame")
        export_frame.grid(row=0, column=3, sticky="e")

        self.btn_export = ttk.Button(
            export_frame, text="Exporter", command=self._export, state=tk.DISABLED
        )
        self.btn_export.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_cancel_export = ttk.Button(
            export_frame, text="Annuler", style="Danger.TButton",
            command=self._cancel_export, state=tk.DISABLED
        )
        self.btn_cancel_export.pack(side=tk.LEFT)

        # Progress panel
        self.progress_panel = ProgressPanel(footer)
        self.progress_panel.grid(row=2, column=0, sticky="ew", pady=(10, 0))

    def _setup_drag_drop(self) -> None:
        """Setup drag and drop support if available."""
        try:
            import tkinterdnd2
            if isinstance(self.root, tkinterdnd2.TkinterDnD.Tk):
                self.root.drop_target_register("DND_Files")
                self.root.dnd_bind("<<Drop>>", self._on_drop)
        except Exception:
            pass

    # ─────────── Event Handlers ───────────

    def _on_video_select(self, index: Optional[int]) -> None:
        """Handle video selection."""
        if index is None or index >= len(self.project.videos):
            self.video_panel.update_details("Aucune video selectionnee")
            return

        video = self.project.videos[index]
        details = f"{video.name}\nDuree: {format_duration(video.duration)}\nTaille: {get_file_size(video.path)}"
        self.video_panel.update_details(details)

    def _on_audio_select(self, index: Optional[int]) -> None:
        """Handle audio selection."""
        if index is None or index >= len(self.project.audio_tracks):
            self.audio_panel.update_details("Aucune piste selectionnee")
            self.audio_panel.reset_controls()
            return

        track = self.project.audio_tracks[index]
        details = f"{track.name}\nDuree: {format_duration(track.duration)}\nTaille: {get_file_size(track.path)}"
        self.audio_panel.update_details(details)
        self.audio_panel.set_track_state(track.volume, track.mute, track.solo)

    def _on_track_volume_change(self, volume: float) -> None:
        """Handle track volume change."""
        if not hasattr(self, 'audio_panel'):
            return
        index = self.audio_panel.get_selection()
        if index is not None and index < len(self.project.audio_tracks):
            self.project.audio_tracks[index].volume = volume / 100.0

    def _on_mute_toggle(self) -> None:
        """Handle mute toggle."""
        index = self.audio_panel.get_selection()
        if index is not None and index < len(self.project.audio_tracks):
            self.project.audio_tracks[index].mute = not self.project.audio_tracks[index].mute
            self._refresh_audio_list()
            self._update_durations()

    def _on_solo_toggle(self) -> None:
        """Handle solo toggle."""
        index = self.audio_panel.get_selection()
        if index is not None and index < len(self.project.audio_tracks):
            self.project.audio_tracks[index].solo = not self.project.audio_tracks[index].solo
            self._refresh_audio_list()
            self._update_durations()

    def _on_music_volume_change(self, volume: float) -> None:
        """Handle music volume change."""
        self.project.settings.music_volume = volume

    def _on_video_volume_change(self, volume: float) -> None:
        """Handle video audio volume change."""
        self.project.settings.video_volume = volume

    def _on_option_change(self) -> None:
        """Handle option change."""
        self.project.settings.include_video_audio = self.var_include_video_audio.get()
        self.project.settings.include_music = self.var_include_music.get()
        self.project.settings.cut_music_at_end = self.var_cut_music.get()
        self.project.settings.use_gpu = self.var_use_gpu.get()

        try:
            self.project.settings.audio_crossfade = float(self.spin_audio_crossfade.get())
        except ValueError:
            pass

        try:
            self.project.settings.video_crossfade = float(self.spin_video_crossfade.get())
        except ValueError:
            pass

        self._update_durations()

    def _on_speed_preset_change(self) -> None:
        """Handle speed preset change."""
        preset_map = {"Rapide": "fast", "Equilibre": "balanced", "Qualite": "quality"}
        self.project.settings.speed_preset = preset_map.get(self.speed_combo.get(), "balanced")

    def _on_drop(self, event) -> None:
        """Handle drag and drop."""
        if self.media_ctrl.handle_drop(self.project, event):
            self._refresh_all()

    # ─────────── Media Operations ───────────

    def _add_videos(self) -> None:
        """Add video files."""
        if self.media_ctrl.add_videos(self.project):
            self._refresh_all()

    def _remove_video(self) -> None:
        """Remove selected video."""
        if self.media_ctrl.remove_video(self.project, self.video_panel.get_selection()):
            self._refresh_all()

    def _move_video(self, direction: int) -> None:
        """Move video in list."""
        new_index = self.media_ctrl.move_video(self.project, self.video_panel.get_selection(), direction)
        if new_index is not None:
            self._refresh_video_list()
            self.video_panel.set_selection(new_index)

    def _add_audio(self) -> None:
        """Add audio files."""
        if self.media_ctrl.add_audio(self.project):
            self._refresh_audio_list()
            self._update_durations()

    def _remove_audio(self) -> None:
        """Remove selected audio track."""
        if self.media_ctrl.remove_audio(self.project, self.audio_panel.get_selection()):
            self._refresh_audio_list()
            self._update_durations()

    def _move_audio(self, direction: int) -> None:
        """Move audio track in list."""
        new_index = self.media_ctrl.move_audio(self.project, self.audio_panel.get_selection(), direction)
        if new_index is not None:
            self._refresh_audio_list()
            self.audio_panel.set_selection(new_index)

    # ─────────── UI Updates ───────────

    def _refresh_all(self) -> None:
        """Refresh all UI elements."""
        self._refresh_video_list()
        self._refresh_audio_list()
        self._update_durations()
        self._update_button_states()

    def _refresh_video_list(self) -> None:
        """Refresh the video list display."""
        self.video_panel.refresh(
            self.project.videos,
            lambda v: f"{v.name}  ({format_duration(v.duration)})"
        )

    def _refresh_audio_list(self) -> None:
        """Refresh the audio list display."""
        def format_track(t: AudioTrack) -> str:
            tag = "[S]" if t.solo else ("[M]" if t.mute else "   ")
            return f"{tag} {t.name}  ({format_duration(t.duration)})"
        self.audio_panel.refresh(self.project.audio_tracks, format_track)

    def _update_durations(self) -> None:
        """Update duration displays."""
        self.duration_panel.set_video_duration(self.project.get_video_duration())
        self.duration_panel.set_music_duration(self.project.get_music_duration())

    def _update_button_states(self) -> None:
        """Update button enabled states."""
        has_videos = len(self.project.videos) > 0
        state = tk.NORMAL if has_videos else tk.DISABLED
        self.btn_preview_short.config(state=state)
        self.btn_preview_full.config(state=state)
        self.btn_export.config(state=state)

    # ─────────── Project Operations ───────────

    def _new_project(self) -> None:
        """Create a new project."""
        new_project = self.project_ctrl.new_project(self.project)
        if new_project is not None:
            self.project = new_project
            self._refresh_all()
            self._reset_options()
            self.progress_panel.reset()

    def _save_project(self) -> None:
        """Save the current project."""
        self.project_ctrl.save_project(self.project, self._sync_settings)

    def _load_project(self) -> None:
        """Load a project from file."""
        loaded_project = self.project_ctrl.load_project()
        if loaded_project is not None:
            self.project = loaded_project
            self._refresh_all()
            self._apply_settings()

    def _sync_settings(self) -> None:
        """Sync UI values to project settings."""
        self.project.settings.include_video_audio = self.var_include_video_audio.get()
        self.project.settings.include_music = self.var_include_music.get()
        self.project.settings.cut_music_at_end = self.var_cut_music.get()
        self.project.settings.video_volume = self.volume_panel.get_video_volume()
        self.project.settings.music_volume = self.volume_panel.get_music_volume()
        self.project.settings.use_gpu = self.var_use_gpu.get()

        preset_map = {"Rapide": "fast", "Equilibre": "balanced", "Qualite": "quality"}
        self.project.settings.speed_preset = preset_map.get(self.speed_combo.get(), "balanced")

        try:
            self.project.settings.audio_crossfade = float(self.spin_audio_crossfade.get())
        except ValueError:
            pass

        try:
            self.project.settings.video_crossfade = float(self.spin_video_crossfade.get())
        except ValueError:
            pass

    def _apply_settings(self) -> None:
        """Apply project settings to UI."""
        s = self.project.settings
        self.var_include_video_audio.set(s.include_video_audio)
        self.var_include_music.set(s.include_music)
        self.var_cut_music.set(s.cut_music_at_end)
        self.volume_panel.set_video_volume(s.video_volume)
        self.volume_panel.set_music_volume(s.music_volume)

        gpu_info = self.ffmpeg.get_gpu_info()
        if gpu_info['available']:
            self.var_use_gpu.set(s.use_gpu)

        preset_map = {"fast": "Rapide", "balanced": "Equilibre", "quality": "Qualite"}
        self.speed_combo.set(preset_map.get(s.speed_preset, "Equilibre"))

        self.spin_audio_crossfade.delete(0, tk.END)
        self.spin_audio_crossfade.insert(0, str(int(s.audio_crossfade)))

        self.spin_video_crossfade.delete(0, tk.END)
        self.spin_video_crossfade.insert(0, str(s.video_crossfade))

    def _reset_options(self) -> None:
        """Reset options to defaults."""
        self.var_include_video_audio.set(True)
        self.var_include_music.set(True)
        self.var_cut_music.set(False)
        self.volume_panel.set_video_volume(100)
        self.volume_panel.set_music_volume(70)

        gpu_info = self.ffmpeg.get_gpu_info()
        if gpu_info['available']:
            self.var_use_gpu.set(True)
        self.speed_combo.set("Equilibre")

        self.spin_audio_crossfade.delete(0, tk.END)
        self.spin_audio_crossfade.insert(0, "10")
        self.spin_video_crossfade.delete(0, tk.END)
        self.spin_video_crossfade.insert(0, "1.0")

    # ─────────── Preview Operations ───────────

    def _play_preview(self, clip: bool = True) -> None:
        """Start preview playback."""
        self._sync_settings()
        self.preview_ctrl.start_preview(self.project, clip)

    def _on_preview_start(self) -> None:
        """Handle preview start."""
        self.btn_preview_short.config(state=tk.DISABLED)
        self.btn_preview_full.config(state=tk.DISABLED)
        self.btn_stop_preview.config(state=tk.NORMAL)
        self.progress_panel.start_animation()

    def _on_preview_stop(self) -> None:
        """Handle preview stop."""
        has_videos = len(self.project.videos) > 0
        self.btn_preview_short.config(state=tk.NORMAL if has_videos else tk.DISABLED)
        self.btn_preview_full.config(state=tk.NORMAL if has_videos else tk.DISABLED)
        self.btn_stop_preview.config(state=tk.DISABLED)
        self.progress_panel.stop_animation()
        self.progress_panel.set_progress(0)

    def _stop_preview(self) -> None:
        """Stop preview playback."""
        self.preview_ctrl.stop()
        self._on_preview_stop()
        self.progress_panel.set_status("Pret")

    # ─────────── Export Operations ───────────

    def _export(self) -> None:
        """Export the project."""
        if not self.project.videos:
            messagebox.showinfo("Information", "Ajoutez au moins une video.")
            return

        output_path = filedialog.asksaveasfilename(
            title="Exporter",
            defaultextension=".mkv",
            filetypes=[("Matroska", "*.mkv"), ("MP4", "*.mp4"), ("WebM", "*.webm")],
            initialdir=self.config.last_directory
        )

        if output_path:
            self.config.last_directory = os.path.dirname(output_path)
            self._sync_settings()
            self.export_ctrl.start_export(self.project, output_path)

    def _on_export_start(self) -> None:
        """Handle export start."""
        self.btn_export.config(state=tk.DISABLED)
        self.btn_cancel_export.config(state=tk.NORMAL)
        self.progress_panel.start_animation()

    def _cancel_export(self) -> None:
        """Cancel the current export."""
        self.export_ctrl.cancel()
        self.btn_cancel_export.config(state=tk.DISABLED)
        self._on_export_done()

    def _on_export_done(self) -> None:
        """Handle export completion."""
        self.progress_panel.stop_animation()
        self.progress_panel.set_progress(100)
        self.btn_export.config(state=tk.NORMAL if self.project.videos else tk.DISABLED)
        self.btn_cancel_export.config(state=tk.DISABLED)

    # ─────────── Cleanup ───────────

    def _on_closing(self) -> None:
        """Handle window close."""
        self.preview_ctrl.stop()
        self.config.window_size = (self.root.winfo_width(), self.root.winfo_height())
        self.root.destroy()
