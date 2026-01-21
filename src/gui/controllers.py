"""
Controllers for Video-Musique application
Handles business logic separated from UI
"""

from __future__ import annotations

import os
import subprocess
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Callable, Optional, Protocol

from ..core.models import AudioTrack, VideoClip, Project, ProjectSettings
from ..core.ffmpeg import FFmpegProcessor
from ..core.config import ProjectManager
from ..utils.logger import get_logger


class UICallback(Protocol):
    """Protocol for UI update callbacks."""
    def schedule(self, func: Callable[[], None]) -> None:
        """Schedule a function to run on the main thread."""
        ...


class PreviewController:
    """Controller for preview generation and playback."""

    def __init__(
        self,
        ffmpeg: FFmpegProcessor,
        ui_callback: Callable[[Callable], None]
    ):
        self.ffmpeg = ffmpeg
        self._schedule_ui = ui_callback
        self._logger = get_logger()

        # State
        self.preview_active = False
        self.preview_process: Optional[subprocess.Popen] = None
        self.temp_preview: Optional[str] = None

        # UI callbacks (to be set by app)
        self.on_status_change: Optional[Callable[[str], None]] = None
        self.on_start: Optional[Callable[[], None]] = None
        self.on_stop: Optional[Callable[[], None]] = None
        self.on_error: Optional[Callable[[str, str], None]] = None

    def start_preview(self, project: Project, clip: bool = True) -> None:
        """Start preview generation and playback."""
        if not project.videos:
            return

        if self.on_start:
            self._schedule_ui(self.on_start)

        if self.on_status_change:
            self._schedule_ui(lambda: self.on_status_change("Generation de la preview..."))

        threading.Thread(
            target=self._build_preview,
            args=(project, clip),
            daemon=True
        ).start()

    def _build_preview(self, project: Project, clip: bool) -> None:
        """Build and play preview (runs in thread)."""
        try:
            self.stop()

            clip_seconds = 60 if clip else None
            self.temp_preview = self.ffmpeg.create_preview(
                project,
                clip_seconds,
                use_gpu=project.settings.use_gpu
            )

            if self.temp_preview:
                self.preview_active = True
                self.preview_process = self.ffmpeg.play_preview(self.temp_preview)

                if self.preview_process:
                    threading.Thread(target=self._watch_preview, daemon=True).start()
                    if self.on_status_change:
                        self._schedule_ui(lambda: self.on_status_change("Preview en cours..."))
                else:
                    self._schedule_ui(self._reset_ui)
            else:
                self._logger.error("Preview generation failed - no temp file created")
                if self.on_error:
                    self._schedule_ui(lambda: self.on_error(
                        "Erreur de preview",
                        "Impossible de generer la preview.\n\n"
                        "Causes possibles:\n"
                        "- FFmpeg non installe ou non accessible\n"
                        "- Fichiers video corrompus ou non supportes\n"
                        "- Espace disque insuffisant\n\n"
                        "Consultez les logs pour plus de details."
                    ))
                self._schedule_ui(self._reset_ui)

        except Exception as e:
            self._logger.exception(f"Preview failed with exception: {e}")
            if self.on_error:
                self._schedule_ui(lambda: self.on_error(
                    "Erreur de preview",
                    f"Une erreur inattendue s'est produite:\n{str(e)}"
                ))
            self._schedule_ui(self._reset_ui)

        finally:
            if self.on_stop:
                self._schedule_ui(self.on_stop)

    def _watch_preview(self) -> None:
        """Watch for preview process end."""
        try:
            if self.preview_process:
                self.preview_process.wait()
        finally:
            self._schedule_ui(self.stop)

    def _reset_ui(self) -> None:
        """Reset preview UI state."""
        self.stop()
        if self.on_status_change:
            self.on_status_change("Pret")

    def stop(self) -> None:
        """Stop preview playback and cleanup."""
        self.preview_active = False

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

    @property
    def is_active(self) -> bool:
        """Check if preview is currently active."""
        return self.preview_active


class ExportController:
    """Controller for video export operations."""

    def __init__(
        self,
        ffmpeg: FFmpegProcessor,
        ui_callback: Callable[[Callable], None]
    ):
        self.ffmpeg = ffmpeg
        self._schedule_ui = ui_callback
        self._logger = get_logger()

        # State
        self._cancelled = False
        self._start_time: Optional[float] = None
        self._elapsed_job: Optional[str] = None

        # UI callbacks
        self.on_progress: Optional[Callable[[float], None]] = None
        self.on_status_change: Optional[Callable[[str], None]] = None
        self.on_time_update: Optional[Callable[[float], None]] = None
        self.on_start: Optional[Callable[[], None]] = None
        self.on_complete: Optional[Callable[[bool], None]] = None
        self.on_error: Optional[Callable[[str, str], None]] = None

        # For elapsed time updates
        self._root: Optional[tk.Tk] = None

    def set_root(self, root: tk.Tk) -> None:
        """Set the root window for after() calls."""
        self._root = root

    def start_export(self, project: Project, output_path: str) -> None:
        """Start export process."""
        self._cancelled = False
        self._start_time = time.time()

        # Start elapsed time updates
        if self._root:
            self._schedule_ui(self._update_elapsed)

        # Get encoder info
        use_gpu = project.settings.use_gpu
        gpu_info = self.ffmpeg.get_gpu_info()
        encoder_text = f"GPU {gpu_info['type'].upper()}" if (use_gpu and gpu_info['available']) else "CPU"

        if self.on_status_change:
            self._schedule_ui(lambda: self.on_status_change(f"Export en cours ({encoder_text})..."))

        if self.on_start:
            self._schedule_ui(self.on_start)

        self._logger.info(f"Starting export to {output_path}")

        threading.Thread(
            target=self._run_export,
            args=(project, output_path),
            daemon=True
        ).start()

    def _run_export(self, project: Project, output_path: str) -> None:
        """Run export in background thread."""
        def progress_callback(percent: float):
            if self.on_progress:
                self._schedule_ui(lambda p=percent: self.on_progress(p))

        def cancel_check() -> bool:
            return self._cancelled

        result = self.ffmpeg.export(
            project,
            output_path,
            progress_callback,
            use_gpu=project.settings.use_gpu,
            speed_preset=project.settings.speed_preset,
            cancel_check=cancel_check
        )

        self._schedule_ui(self._export_done)

        if result.get("cancelled"):
            if self.on_status_change:
                self._schedule_ui(lambda: self.on_status_change("Export annule"))
            self._logger.info("Export was cancelled by user")
        elif result.get("success"):
            elapsed = time.time() - self._start_time if self._start_time else 0
            if self.on_status_change:
                self._schedule_ui(lambda: self.on_status_change(f"Export termine! ({elapsed:.1f}s)"))
            self._logger.log_export_complete(output_path, elapsed, success=True)
            if self.on_complete:
                self._schedule_ui(lambda: self.on_complete(True))
        else:
            error_msg = result.get("error", "Erreur inconnue")
            self._logger.log_export_complete(output_path, 0, success=False)

            if self.on_error:
                self._schedule_ui(lambda: self.on_error(
                    "Erreur d'export",
                    f"L'export a echoue.\n\nDetails:\n{error_msg}\n\n"
                    "Consultez les logs pour plus d'informations."
                ))
            if self.on_status_change:
                self._schedule_ui(lambda: self.on_status_change("Export echoue"))

    def cancel(self) -> None:
        """Cancel the current export."""
        if not self._cancelled:
            self._cancelled = True
            self._logger.info("Export cancellation requested")
            if self.on_status_change:
                self.on_status_change("Annulation en cours...")

    def _update_elapsed(self) -> None:
        """Update elapsed time display."""
        if self._start_time is None or not self._root:
            return

        elapsed = time.time() - self._start_time
        if self.on_time_update:
            self.on_time_update(elapsed)
        self._elapsed_job = self._root.after(500, self._update_elapsed)

    def _export_done(self) -> None:
        """Handle export completion."""
        if self._elapsed_job and self._root:
            self._root.after_cancel(self._elapsed_job)
            self._elapsed_job = None

        self._start_time = None
        self._cancelled = False

    @property
    def is_cancelled(self) -> bool:
        """Check if export was cancelled."""
        return self._cancelled


class ProjectController:
    """Controller for project operations."""

    def __init__(
        self,
        ffmpeg: FFmpegProcessor,
        config,  # Config type
        ui_callback: Callable[[Callable], None]
    ):
        self.ffmpeg = ffmpeg
        self.config = config
        self._schedule_ui = ui_callback
        self._logger = get_logger()

        # UI callbacks
        self.on_project_loaded: Optional[Callable[[Project], None]] = None
        self.on_status_change: Optional[Callable[[str], None]] = None
        self.on_error: Optional[Callable[[str, str], None]] = None

    def new_project(self, current_project: Project) -> Optional[Project]:
        """Create a new project. Returns new Project or None if cancelled."""
        if current_project.videos or current_project.audio_tracks:
            if not messagebox.askyesno(
                "Nouveau projet",
                "Voulez-vous creer un nouveau projet? Les modifications non sauvegardees seront perdues."
            ):
                return None

        return Project()

    def save_project(self, project: Project, sync_settings_func: Callable[[], None]) -> bool:
        """Save the current project. Returns True on success."""
        if not project.videos:
            messagebox.showinfo("Information", "Ajoutez au moins une video.")
            return False

        file_path = filedialog.asksaveasfilename(
            title="Sauvegarder le projet",
            defaultextension=".mixproj",
            filetypes=[("Projet Video-Musique", "*.mixproj")],
            initialdir=self.config.last_directory
        )

        if not file_path:
            return False

        sync_settings_func()

        if ProjectManager.save_project(project, file_path):
            if self.on_status_change:
                self.on_status_change(f"Projet sauvegarde: {Path(file_path).name}")
            self._logger.info(f"Project saved successfully: {file_path}")
            return True
        else:
            self._logger.error(f"Failed to save project: {file_path}")
            if self.on_error:
                self.on_error(
                    "Erreur de sauvegarde",
                    "Impossible de sauvegarder le projet.\n\n"
                    "Verifiez que vous avez les droits d'ecriture\n"
                    "dans le dossier selectionne."
                )
            return False

    def load_project(self) -> Optional[Project]:
        """Load a project from file. Returns Project or None."""
        file_path = filedialog.askopenfilename(
            title="Ouvrir un projet",
            defaultextension=".mixproj",
            filetypes=[("Projet Video-Musique", "*.mixproj")],
            initialdir=self.config.last_directory
        )

        if not file_path:
            return None

        data = ProjectManager.load_project_data(file_path)
        if not data:
            self._logger.error(f"Failed to load project: {file_path}")
            if self.on_error:
                self.on_error(
                    "Erreur de chargement",
                    "Impossible de charger le projet.\n\n"
                    "Le fichier est peut-etre corrompu ou\n"
                    "dans un format non supporte."
                )
            return None

        project = Project()

        # Load videos
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
            project.videos.append(VideoClip.from_dict({"path": path, "name": vd.get("name", "")}, duration))

        # Load audio tracks
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
            project.audio_tracks.append(AudioTrack.from_dict({**td, "path": path}, duration))

        # Load settings
        project.settings = ProjectSettings.from_dict(data.get("settings", {}))

        if self.on_status_change:
            self.on_status_change(f"Projet charge: {Path(file_path).name}")

        return project


class MediaController:
    """Controller for media operations (add, remove, move)."""

    def __init__(
        self,
        ffmpeg: FFmpegProcessor,
        config,  # Config type
    ):
        self.ffmpeg = ffmpeg
        self.config = config
        self._logger = get_logger()

        # UI callbacks
        self.on_status_change: Optional[Callable[[str], None]] = None

    def add_videos(self, project: Project) -> bool:
        """Add video files to project. Returns True if files were added."""
        files = filedialog.askopenfilenames(
            title="Ajouter des videos",
            filetypes=[("Videos", "*.mp4 *.mkv *.mov *.avi *.webm"), ("Tous", "*.*")],
            initialdir=self.config.last_directory
        )

        if not files:
            return False

        self.config.last_directory = os.path.dirname(files[0])

        if len(files) > 1:
            if self.on_status_change:
                self.on_status_change("Analyse des videos...")
            durations = self.ffmpeg.get_durations_parallel(list(files))
            for f, duration in zip(files, durations):
                project.videos.append(VideoClip(path=f, duration=duration))
        else:
            duration = self.ffmpeg.get_duration(files[0])
            project.videos.append(VideoClip(path=files[0], duration=duration))

        if self.on_status_change:
            self.on_status_change("Pret")

        return True

    def remove_video(self, project: Project, index: Optional[int]) -> bool:
        """Remove video at index. Returns True if removed."""
        if index is not None and index < len(project.videos):
            del project.videos[index]
            return True
        return False

    def move_video(self, project: Project, index: Optional[int], direction: int) -> Optional[int]:
        """Move video in list. Returns new index or None."""
        if index is None:
            return None

        new_index = index + direction
        if 0 <= new_index < len(project.videos):
            project.videos[index], project.videos[new_index] = \
                project.videos[new_index], project.videos[index]
            return new_index
        return None

    def add_audio(self, project: Project) -> bool:
        """Add audio files to project. Returns True if files were added."""
        files = filedialog.askopenfilenames(
            title="Ajouter des musiques",
            filetypes=[("Audio", "*.mp3 *.wav *.flac *.aac *.ogg"), ("Tous", "*.*")],
            initialdir=self.config.last_directory
        )

        if not files:
            return False

        self.config.last_directory = os.path.dirname(files[0])

        if len(files) > 1:
            if self.on_status_change:
                self.on_status_change("Analyse des fichiers audio...")
            durations = self.ffmpeg.get_durations_parallel(list(files))
            for f, duration in zip(files, durations):
                project.audio_tracks.append(AudioTrack(path=f, duration=duration))
        else:
            duration = self.ffmpeg.get_duration(files[0])
            project.audio_tracks.append(AudioTrack(path=files[0], duration=duration))

        if self.on_status_change:
            self.on_status_change("Pret")

        return True

    def remove_audio(self, project: Project, index: Optional[int]) -> bool:
        """Remove audio track at index. Returns True if removed."""
        if index is not None and index < len(project.audio_tracks):
            del project.audio_tracks[index]
            return True
        return False

    def move_audio(self, project: Project, index: Optional[int], direction: int) -> Optional[int]:
        """Move audio track in list. Returns new index or None."""
        if index is None:
            return None

        new_index = index + direction
        if 0 <= new_index < len(project.audio_tracks):
            project.audio_tracks[index], project.audio_tracks[new_index] = \
                project.audio_tracks[new_index], project.audio_tracks[index]
            return new_index
        return None

    def handle_drop(self, project: Project, event) -> bool:
        """Handle drag and drop. Returns True if files were added."""
        files = event.data.strip("{}").split("} {")
        added = False

        for f in files:
            ext = Path(f).suffix.lower()
            if ext in FFmpegProcessor.SUPPORTED_VIDEO:
                duration = self.ffmpeg.get_duration(f)
                project.videos.append(VideoClip(path=f, duration=duration))
                added = True
            elif ext in FFmpegProcessor.SUPPORTED_AUDIO:
                duration = self.ffmpeg.get_duration(f)
                project.audio_tracks.append(AudioTrack(path=f, duration=duration))
                added = True

        return added
