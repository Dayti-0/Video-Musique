"""
Main application for Video-Musique
Modern and intuitive interface
"""

from __future__ import annotations

import os
import subprocess
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Optional

from .theme import Theme, Colors
from .widgets.media_panel import MediaPanel, AudioTrackPanel
from .widgets.volume_slider import DualVolumePanel
from .widgets.progress_panel import ProgressPanel, DurationPanel
from ..core.models import AudioTrack, VideoClip, Project, ProjectSettings
from ..core.ffmpeg import FFmpegProcessor
from ..core.config import Config, ProjectManager
from ..utils.helpers import format_duration, get_file_size, create_tooltip
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

        # Initialize components
        self.config = Config()
        self.ffmpeg = FFmpegProcessor()
        self.project = Project()

        # State
        self.preview_active = False
        self.preview_process: Optional[subprocess.Popen] = None
        self.temp_preview: Optional[str] = None
        self.export_start: Optional[float] = None
        self._elapsed_job: Optional[str] = None
        self._export_cancelled = False
        self._export_process: Optional[subprocess.Popen] = None
        self._logger = get_logger()

        # Cleanup temp files on start
        FFmpegProcessor.cleanup_temp_files()

        # Setup theme
        self.theme = Theme(root)

        # Build UI
        self._build_ui()

        # Set window size from config
        width, height = self.config.window_size
        self.root.geometry(f"{width}x{height}")

        # Protocol handlers
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

        # Setup drag & drop if available
        self._setup_drag_drop()

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

        ttk.Label(
            title_frame,
            text="Mixeur Video Audio",
            style="Title.TLabel"
        ).pack(side=tk.LEFT)

        # Menu buttons
        menu_frame = ttk.Frame(header)
        menu_frame.grid(row=0, column=2, sticky="e")

        self.btn_new = ttk.Button(
            menu_frame,
            text="Nouveau",
            style="Secondary.TButton",
            command=self._new_project
        )
        self.btn_new.pack(side=tk.LEFT, padx=3)

        self.btn_open = ttk.Button(
            menu_frame,
            text="Ouvrir",
            style="Secondary.TButton",
            command=self._load_project
        )
        self.btn_open.pack(side=tk.LEFT, padx=3)

        self.btn_save = ttk.Button(
            menu_frame,
            text="Sauvegarder",
            style="Secondary.TButton",
            command=self._save_project
        )
        self.btn_save.pack(side=tk.LEFT, padx=3)

    def _build_main_content(self) -> None:
        """Build the main content area with media panels."""
        main = ttk.Frame(self.root)
        main.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)

        # Video panel
        self.video_panel = MediaPanel(
            main,
            title="Videos",
            media_type="video",
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
        options_frame = ttk.Frame(controls, style="Card.TFrame", padding=15)
        options_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        ttk.Label(
            options_frame,
            text="Options",
            style="Card.TLabel",
            font=("Segoe UI", 11, "bold"),
            foreground=Colors.ACCENT_PRIMARY
        ).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 10))

        # Checkboxes
        self.var_include_video_audio = tk.BooleanVar(value=True)
        self.var_include_music = tk.BooleanVar(value=True)
        self.var_cut_music = tk.BooleanVar(value=False)

        ttk.Checkbutton(
            options_frame,
            text="Audio des videos",
            variable=self.var_include_video_audio,
            command=self._on_option_change
        ).grid(row=1, column=0, sticky="w", pady=2)

        ttk.Checkbutton(
            options_frame,
            text="Musiques",
            variable=self.var_include_music,
            command=self._on_option_change
        ).grid(row=1, column=1, sticky="w", padx=(15, 0), pady=2)

        ttk.Checkbutton(
            options_frame,
            text="Couper musique a la fin",
            variable=self.var_cut_music,
            command=self._on_option_change
        ).grid(row=1, column=2, sticky="w", padx=(15, 0), pady=2)

        # Crossfade controls
        crossfade_frame = ttk.Frame(options_frame, style="Card.TFrame")
        crossfade_frame.grid(row=2, column=0, columnspan=4, sticky="ew", pady=(10, 0))

        ttk.Label(
            crossfade_frame,
            text="Cross-fade audio (s):",
            style="Card.TLabel",
            font=("Segoe UI", 9)
        ).pack(side=tk.LEFT)

        spinbox_config = Theme.get_spinbox_config()
        self.spin_audio_crossfade = tk.Spinbox(
            crossfade_frame,
            from_=1,
            to=20,
            width=4,
            command=self._on_option_change,
            **spinbox_config
        )
        self.spin_audio_crossfade.delete(0, tk.END)
        self.spin_audio_crossfade.insert(0, "10")
        self.spin_audio_crossfade.pack(side=tk.LEFT, padx=(8, 20))

        ttk.Label(
            crossfade_frame,
            text="Cross-fade video (s):",
            style="Card.TLabel",
            font=("Segoe UI", 9)
        ).pack(side=tk.LEFT)

        self.spin_video_crossfade = tk.Spinbox(
            crossfade_frame,
            from_=0.0,
            to=5.0,
            increment=0.5,
            width=4,
            command=self._on_option_change,
            **spinbox_config
        )
        self.spin_video_crossfade.delete(0, tk.END)
        self.spin_video_crossfade.insert(0, "1.0")
        self.spin_video_crossfade.pack(side=tk.LEFT, padx=(8, 0))

        # Performance settings row
        perf_frame = ttk.Frame(options_frame, style="Card.TFrame")
        perf_frame.grid(row=3, column=0, columnspan=4, sticky="ew", pady=(10, 0))

        # GPU acceleration checkbox
        self.var_use_gpu = tk.BooleanVar(value=True)
        gpu_info = self.ffmpeg.get_gpu_info()
        gpu_text = f"Acceleration GPU ({gpu_info['type'].upper()})" if gpu_info['available'] else "Acceleration GPU (non disponible)"

        self.chk_gpu = ttk.Checkbutton(
            perf_frame,
            text=gpu_text,
            variable=self.var_use_gpu,
            command=self._on_option_change,
            state=tk.NORMAL if gpu_info['available'] else tk.DISABLED
        )
        self.chk_gpu.pack(side=tk.LEFT)

        # Speed preset selector
        ttk.Label(
            perf_frame,
            text="Vitesse:",
            style="Card.TLabel",
            font=("Segoe UI", 9)
        ).pack(side=tk.LEFT, padx=(20, 5))

        self.var_speed_preset = tk.StringVar(value="balanced")
        speed_options = [
            ("Rapide", "fast"),
            ("Equilibre", "balanced"),
            ("Qualite", "quality"),
        ]

        self.speed_combo = ttk.Combobox(
            perf_frame,
            textvariable=self.var_speed_preset,
            values=[opt[0] for opt in speed_options],
            width=12,
            state="readonly"
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
            preview_frame,
            text="Preview 60s",
            style="Secondary.TButton",
            command=lambda: self._play_preview(clip=True),
            state=tk.DISABLED
        )
        self.btn_preview_short.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_preview_full = ttk.Button(
            preview_frame,
            text="Preview complet",
            style="Secondary.TButton",
            command=lambda: self._play_preview(clip=False),
            state=tk.DISABLED
        )
        self.btn_preview_full.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_stop_preview = ttk.Button(
            preview_frame,
            text="Stop",
            style="Danger.TButton",
            command=self._stop_preview,
            state=tk.DISABLED
        )
        self.btn_stop_preview.pack(side=tk.LEFT)

        # Export buttons frame
        export_frame = ttk.Frame(action_frame, style="Card.TFrame")
        export_frame.grid(row=0, column=3, sticky="e")

        self.btn_export = ttk.Button(
            export_frame,
            text="Exporter",
            command=self._export,
            state=tk.DISABLED
        )
        self.btn_export.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_cancel_export = ttk.Button(
            export_frame,
            text="Annuler",
            style="Danger.TButton",
            command=self._cancel_export,
            state=tk.DISABLED
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
        # Guard against callback during initialization
        if not hasattr(self, 'audio_panel'):
            return
        index = self.audio_panel.get_selection()
        if index is not None and index < len(self.project.audio_tracks):
            self.project.audio_tracks[index].volume = volume / 100.0

    def _on_mute_toggle(self) -> None:
        """Handle mute toggle."""
        index = self.audio_panel.get_selection()
        if index is not None and index < len(self.project.audio_tracks):
            track = self.project.audio_tracks[index]
            track.mute = not track.mute
            self._refresh_audio_list()
            self._update_durations()

    def _on_solo_toggle(self) -> None:
        """Handle solo toggle."""
        index = self.audio_panel.get_selection()
        if index is not None and index < len(self.project.audio_tracks):
            track = self.project.audio_tracks[index]
            track.solo = not track.solo
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
        preset_map = {
            "Rapide": "fast",
            "Equilibre": "balanced",
            "Qualite": "quality",
        }
        selected = self.speed_combo.get()
        self.project.settings.speed_preset = preset_map.get(selected, "balanced")

    def _on_drop(self, event) -> None:
        """Handle drag and drop."""
        files = event.data.strip("{}").split("} {")
        for f in files:
            ext = Path(f).suffix.lower()
            if ext in FFmpegProcessor.SUPPORTED_VIDEO:
                duration = self.ffmpeg.get_duration(f)
                self.project.videos.append(VideoClip(path=f, duration=duration))
            elif ext in FFmpegProcessor.SUPPORTED_AUDIO:
                duration = self.ffmpeg.get_duration(f)
                self.project.audio_tracks.append(AudioTrack(path=f, duration=duration))

        self._refresh_video_list()
        self._refresh_audio_list()
        self._update_durations()
        self._update_button_states()

    # ─────────── Media Operations ───────────

    def _add_videos(self) -> None:
        """Add video files with parallel duration detection."""
        files = filedialog.askopenfilenames(
            title="Ajouter des videos",
            filetypes=[("Videos", "*.mp4 *.mkv *.mov *.avi *.webm"), ("Tous", "*.*")],
            initialdir=self.config.last_directory
        )

        if files:
            self.config.last_directory = os.path.dirname(files[0])

            # Use parallel duration detection for multiple files
            if len(files) > 1:
                self.progress_panel.set_status("Analyse des videos...")
                durations = self.ffmpeg.get_durations_parallel(list(files))
                for f, duration in zip(files, durations):
                    self.project.videos.append(VideoClip(path=f, duration=duration))
            else:
                duration = self.ffmpeg.get_duration(files[0])
                self.project.videos.append(VideoClip(path=files[0], duration=duration))

            self._refresh_video_list()
            self._update_durations()
            self._update_button_states()
            self.progress_panel.set_status("Pret")

    def _remove_video(self) -> None:
        """Remove selected video."""
        index = self.video_panel.get_selection()
        if index is not None and index < len(self.project.videos):
            del self.project.videos[index]
            self._refresh_video_list()
            self._update_durations()
            self._update_button_states()

    def _move_video(self, direction: int) -> None:
        """Move video in list."""
        index = self.video_panel.get_selection()
        if index is None:
            return

        new_index = index + direction
        if 0 <= new_index < len(self.project.videos):
            videos = self.project.videos
            videos[index], videos[new_index] = videos[new_index], videos[index]
            self._refresh_video_list()
            self.video_panel.set_selection(new_index)

    def _add_audio(self) -> None:
        """Add audio files with parallel duration detection."""
        files = filedialog.askopenfilenames(
            title="Ajouter des musiques",
            filetypes=[("Audio", "*.mp3 *.wav *.flac *.aac *.ogg"), ("Tous", "*.*")],
            initialdir=self.config.last_directory
        )

        if files:
            self.config.last_directory = os.path.dirname(files[0])

            # Use parallel duration detection for multiple files
            if len(files) > 1:
                self.progress_panel.set_status("Analyse des fichiers audio...")
                durations = self.ffmpeg.get_durations_parallel(list(files))
                for f, duration in zip(files, durations):
                    self.project.audio_tracks.append(AudioTrack(path=f, duration=duration))
            else:
                duration = self.ffmpeg.get_duration(files[0])
                self.project.audio_tracks.append(AudioTrack(path=files[0], duration=duration))

            self._refresh_audio_list()
            self._update_durations()
            self.progress_panel.set_status("Pret")

    def _remove_audio(self) -> None:
        """Remove selected audio track."""
        index = self.audio_panel.get_selection()
        if index is not None and index < len(self.project.audio_tracks):
            del self.project.audio_tracks[index]
            self._refresh_audio_list()
            self._update_durations()

    def _move_audio(self, direction: int) -> None:
        """Move audio track in list."""
        index = self.audio_panel.get_selection()
        if index is None:
            return

        new_index = index + direction
        if 0 <= new_index < len(self.project.audio_tracks):
            tracks = self.project.audio_tracks
            tracks[index], tracks[new_index] = tracks[new_index], tracks[index]
            self._refresh_audio_list()
            self.audio_panel.set_selection(new_index)

    # ─────────── UI Updates ───────────

    def _refresh_video_list(self) -> None:
        """Refresh the video list display."""
        def format_video(v: VideoClip) -> str:
            return f"{v.name}  ({format_duration(v.duration)})"

        self.video_panel.refresh(self.project.videos, format_video)

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
        if self.project.videos or self.project.audio_tracks:
            if not messagebox.askyesno("Nouveau projet", "Voulez-vous creer un nouveau projet? Les modifications non sauvegardees seront perdues."):
                return

        self.project = Project()
        self._refresh_video_list()
        self._refresh_audio_list()
        self._update_durations()
        self._update_button_states()
        self._reset_options()
        self.progress_panel.reset()

    def _save_project(self) -> None:
        """Save the current project."""
        if not self.project.videos:
            messagebox.showinfo("Information", "Ajoutez au moins une video.")
            return

        file_path = filedialog.asksaveasfilename(
            title="Sauvegarder le projet",
            defaultextension=".mixproj",
            filetypes=[("Projet Video-Musique", "*.mixproj")],
            initialdir=self.config.last_directory
        )

        if file_path:
            self._sync_settings()
            if ProjectManager.save_project(self.project, file_path):
                self.progress_panel.set_status(f"Projet sauvegarde: {Path(file_path).name}")
                self._logger.info(f"Project saved successfully: {file_path}")
            else:
                self._logger.error(f"Failed to save project: {file_path}")
                messagebox.showerror(
                    "Erreur de sauvegarde",
                    f"Impossible de sauvegarder le projet.\n\n"
                    f"Verifiez que vous avez les droits d'ecriture\n"
                    f"dans le dossier selectionne."
                )

    def _load_project(self) -> None:
        """Load a project from file."""
        file_path = filedialog.askopenfilename(
            title="Ouvrir un projet",
            defaultextension=".mixproj",
            filetypes=[("Projet Video-Musique", "*.mixproj")],
            initialdir=self.config.last_directory
        )

        if not file_path:
            return

        data = ProjectManager.load_project_data(file_path)
        if not data:
            self._logger.error(f"Failed to load project: {file_path}")
            messagebox.showerror(
                "Erreur de chargement",
                f"Impossible de charger le projet.\n\n"
                f"Le fichier est peut-etre corrompu ou\n"
                f"dans un format non supporte."
            )
            return

        # Load videos
        self.project.videos.clear()
        for vd in data.get("videos", []):
            path = vd["path"]
            if not os.path.exists(path):
                path = filedialog.askopenfilename(
                    title=f"Localiser {os.path.basename(vd['path'])}",
                    filetypes=[("Videos", "*.mp4 *.mkv *.mov *.avi *.webm")]
                )
                if not path:
                    continue

            duration = self.ffmpeg.get_duration(path)
            self.project.videos.append(VideoClip.from_dict({"path": path, "name": vd.get("name", "")}, duration))

        # Load audio tracks
        self.project.audio_tracks.clear()
        for td in data.get("audio_tracks", []):
            path = td["path"]
            if not os.path.exists(path):
                path = filedialog.askopenfilename(
                    title=f"Localiser {os.path.basename(td['path'])}",
                    filetypes=[("Audio", "*.mp3 *.wav *.flac *.aac *.ogg")]
                )
                if not path:
                    continue

            duration = self.ffmpeg.get_duration(path)
            self.project.audio_tracks.append(AudioTrack.from_dict({**td, "path": path}, duration))

        # Load settings
        self.project.settings = ProjectSettings.from_dict(data.get("settings", {}))

        # Update UI
        self._refresh_video_list()
        self._refresh_audio_list()
        self._apply_settings()
        self._update_durations()
        self._update_button_states()
        self.progress_panel.set_status(f"Projet charge: {Path(file_path).name}")

    def _sync_settings(self) -> None:
        """Sync UI values to project settings."""
        self.project.settings.include_video_audio = self.var_include_video_audio.get()
        self.project.settings.include_music = self.var_include_music.get()
        self.project.settings.cut_music_at_end = self.var_cut_music.get()
        self.project.settings.video_volume = self.volume_panel.get_video_volume()
        self.project.settings.music_volume = self.volume_panel.get_music_volume()
        self.project.settings.use_gpu = self.var_use_gpu.get()

        # Map speed preset from UI to internal value
        preset_map = {
            "Rapide": "fast",
            "Equilibre": "balanced",
            "Qualite": "quality",
        }
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

        # GPU and speed settings
        gpu_info = self.ffmpeg.get_gpu_info()
        if gpu_info['available']:
            self.var_use_gpu.set(s.use_gpu)

        preset_map = {
            "fast": "Rapide",
            "balanced": "Equilibre",
            "quality": "Qualite",
        }
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

        # Reset performance settings
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
        if not self.project.videos:
            return

        self._sync_settings()
        self.btn_preview_short.config(state=tk.DISABLED)
        self.btn_preview_full.config(state=tk.DISABLED)
        self.btn_stop_preview.config(state=tk.NORMAL)
        self.progress_panel.set_status("Generation de la preview...")
        self.progress_panel.start_animation()

        threading.Thread(
            target=self._build_preview,
            args=(clip,),
            daemon=True
        ).start()

    def _build_preview(self, clip: bool) -> None:
        """Build and play preview (runs in thread) with GPU acceleration."""
        try:
            self._stop_preview()

            clip_seconds = 60 if clip else None
            # Use GPU acceleration for faster preview generation
            self.temp_preview = self.ffmpeg.create_preview(
                self.project,
                clip_seconds,
                use_gpu=self.project.settings.use_gpu
            )

            if self.temp_preview:
                self.preview_active = True
                self.preview_process = self.ffmpeg.play_preview(self.temp_preview)

                if self.preview_process:
                    threading.Thread(target=self._watch_preview, daemon=True).start()
                else:
                    self.root.after(0, self._reset_preview_ui)

                self.root.after(0, lambda: self.progress_panel.set_status("Preview en cours..."))
            else:
                self._logger.error("Preview generation failed - no temp file created")
                self.root.after(0, lambda: messagebox.showerror(
                    "Erreur de preview",
                    "Impossible de generer la preview.\n\n"
                    "Causes possibles:\n"
                    "- FFmpeg non installe ou non accessible\n"
                    "- Fichiers video corrompus ou non supportes\n"
                    "- Espace disque insuffisant\n\n"
                    "Consultez les logs pour plus de details."
                ))
                self.root.after(0, self._reset_preview_ui)

        except Exception as e:
            self._logger.exception(f"Preview failed with exception: {e}")
            self.root.after(0, lambda: messagebox.showerror(
                "Erreur de preview",
                f"Une erreur inattendue s'est produite:\n{str(e)}"
            ))
            self.root.after(0, self._reset_preview_ui)

        finally:
            self.root.after(0, self.progress_panel.stop_animation)
            self.root.after(0, lambda: (
                self.btn_preview_short.config(state=tk.NORMAL if self.project.videos else tk.DISABLED),
                self.btn_preview_full.config(state=tk.NORMAL if self.project.videos else tk.DISABLED)
            ))

    def _watch_preview(self) -> None:
        """Watch for preview process end."""
        try:
            if self.preview_process:
                self.preview_process.wait()
        finally:
            self.root.after(0, self._stop_preview)

    def _stop_preview(self) -> None:
        """Stop preview playback."""
        self.preview_active = False
        self.btn_stop_preview.config(state=tk.DISABLED)
        self.progress_panel.stop_animation()

        try:
            if self.preview_process:
                self.preview_process.kill()
        except Exception:
            pass
        self.preview_process = None

        if self.temp_preview and os.path.exists(self.temp_preview):
            try:
                os.remove(self.temp_preview)
            except Exception:
                pass
        self.temp_preview = None

        self.progress_panel.set_progress(0)

    def _reset_preview_ui(self) -> None:
        """Reset preview UI state."""
        self._stop_preview()
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
            threading.Thread(
                target=self._run_export,
                args=(output_path,),
                daemon=True
            ).start()

    def _run_export(self, output_path: str) -> None:
        """Run export in background thread with GPU acceleration support."""
        self._export_cancelled = False
        self.export_start = time.time()
        self.root.after(0, self._update_elapsed)

        # Show encoder info in status
        use_gpu = self.project.settings.use_gpu
        gpu_info = self.ffmpeg.get_gpu_info()
        encoder_text = f"GPU {gpu_info['type'].upper()}" if (use_gpu and gpu_info['available']) else "CPU"
        self.root.after(0, lambda: self.progress_panel.set_status(f"Export en cours ({encoder_text})..."))
        self.root.after(0, lambda: self.btn_export.config(state=tk.DISABLED))
        self.root.after(0, lambda: self.btn_cancel_export.config(state=tk.NORMAL))
        self.root.after(0, self.progress_panel.start_animation)

        self._logger.info(f"Starting export to {output_path}")

        def progress_callback(percent: float):
            self.root.after(0, lambda: self.progress_panel.set_progress(percent))

        def cancel_check() -> bool:
            return self._export_cancelled

        # Export with performance settings
        result = self.ffmpeg.export(
            self.project,
            output_path,
            progress_callback,
            use_gpu=self.project.settings.use_gpu,
            speed_preset=self.project.settings.speed_preset,
            cancel_check=cancel_check
        )

        self.root.after(0, self._export_done)

        if result.get("cancelled"):
            self.root.after(0, lambda: self.progress_panel.set_status("Export annule"))
            self._logger.info("Export was cancelled by user")
        elif result.get("success"):
            elapsed = time.time() - self.export_start
            self.root.after(0, lambda: self.progress_panel.set_status(f"Export termine! ({elapsed:.1f}s)"))
            self._logger.log_export_complete(output_path, elapsed, success=True)
        else:
            error_msg = result.get("error", "Erreur inconnue")
            self._logger.log_export_complete(output_path, 0, success=False)

            # Show user-friendly error message
            def show_error():
                messagebox.showerror(
                    "Erreur d'export",
                    f"L'export a echoue.\n\nDetails:\n{error_msg}\n\n"
                    "Consultez les logs pour plus d'informations."
                )
                self.progress_panel.set_status("Export echoue")

            self.root.after(0, show_error)

    def _cancel_export(self) -> None:
        """Cancel the current export."""
        if not self._export_cancelled:
            self._export_cancelled = True
            self._logger.info("Export cancellation requested")
            self.progress_panel.set_status("Annulation en cours...")
            self.btn_cancel_export.config(state=tk.DISABLED)

    def _update_elapsed(self) -> None:
        """Update elapsed time display."""
        if self.export_start is None:
            return

        elapsed = time.time() - self.export_start
        self.progress_panel.set_time(elapsed)
        self._elapsed_job = self.root.after(500, self._update_elapsed)

    def _export_done(self) -> None:
        """Handle export completion."""
        if self._elapsed_job:
            self.root.after_cancel(self._elapsed_job)
            self._elapsed_job = None

        self.export_start = None
        self._export_cancelled = False
        self.progress_panel.stop_animation()
        if not self._export_cancelled:
            self.progress_panel.set_progress(100)
        self.btn_export.config(state=tk.NORMAL if self.project.videos else tk.DISABLED)
        self.btn_cancel_export.config(state=tk.DISABLED)

    # ─────────── Cleanup ───────────

    def _on_closing(self) -> None:
        """Handle window close."""
        self._stop_preview()

        # Save window size
        self.config.window_size = (self.root.winfo_width(), self.root.winfo_height())

        self.root.destroy()
