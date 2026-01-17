"""
FFmpeg operations for Video-Musique
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import wave
from typing import Callable, Optional

from .models import AudioTrack, VideoClip, Project


class FFmpegProcessor:
    """Handles all FFmpeg operations for media processing."""

    SUPPORTED_VIDEO = (".mp4", ".mkv", ".mov", ".avi", ".webm")
    SUPPORTED_AUDIO = (".mp3", ".wav", ".flac", ".aac", ".ogg")

    def __init__(self):
        self.time_regex = re.compile(r"out_time_ms=(\d+)")
        self._check_dependencies()

    def _check_dependencies(self) -> None:
        """Verify FFmpeg tools are available."""
        self.has_ffmpeg = shutil.which("ffmpeg") is not None
        self.has_ffprobe = shutil.which("ffprobe") is not None
        self.has_ffplay = shutil.which("ffplay") is not None

    @staticmethod
    def _sexagesimal(s: str) -> float:
        """Convert 'HH:MM:SS.xx' to seconds."""
        try:
            h, m, sec = s.split(":")
            return int(h) * 3600 + int(m) * 60 + float(sec)
        except Exception:
            return 0.0

    def get_duration(self, path: str) -> float:
        """
        Get media duration in seconds using multiple fallback methods.
        Returns 0.0 if duration cannot be determined.
        """
        if not os.path.exists(path):
            return 0.0

        # Method 1: Quick ffprobe
        duration = self._duration_ffprobe_quick(path)
        if duration > 0:
            return duration

        # Method 2: FFprobe JSON
        duration = self._duration_ffprobe_json(path)
        if duration > 0:
            return duration

        # Method 3: Mutagen (if available)
        duration = self._duration_mutagen(path)
        if duration > 0:
            return duration

        # Method 4: Wave module for .wav files
        if path.lower().endswith(".wav"):
            duration = self._duration_wave(path)
            if duration > 0:
                return duration

        # Method 5: FFmpeg output parsing
        duration = self._duration_ffmpeg(path)
        if duration > 0:
            return duration

        return 0.0

    def _duration_ffprobe_quick(self, path: str) -> float:
        """Quick ffprobe duration check."""
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=nw=1:nk=1", path
        ]
        try:
            out = subprocess.check_output(
                cmd, text=True, stderr=subprocess.STDOUT
            ).strip()
            if out and out != "N/A":
                return float(out)
        except Exception:
            pass
        return 0.0

    def _duration_ffprobe_json(self, path: str) -> float:
        """FFprobe JSON duration check."""
        cmd = [
            "ffprobe", "-v", "error", "-print_format", "json",
            "-show_entries", "format=duration,stream=duration,stream_tags",
            path
        ]
        try:
            result = subprocess.check_output(
                cmd, text=True, stderr=subprocess.STDOUT
            )
            js = json.loads(result or "{}")
            durations = []

            fdur = js.get("format", {}).get("duration")
            if fdur and fdur != "N/A":
                durations.append(float(fdur))

            for s in js.get("streams", []):
                sd = s.get("duration")
                if sd and sd != "N/A":
                    durations.append(float(sd))
                tag_dur = s.get("tags", {}).get("DURATION")
                if tag_dur:
                    durations.append(self._sexagesimal(tag_dur))

            if durations:
                return max(durations)
        except Exception:
            pass
        return 0.0

    def _duration_mutagen(self, path: str) -> float:
        """Get duration using mutagen library."""
        try:
            from mutagen import File as MutagenFile
            m = MutagenFile(path)
            if m and m.info and hasattr(m.info, "length"):
                return float(m.info.length)
        except ImportError:
            pass
        except Exception:
            pass
        return 0.0

    def _duration_wave(self, path: str) -> float:
        """Get duration for WAV files."""
        try:
            with contextlib.closing(wave.open(path, "rb")) as w:
                frames, rate = w.getnframes(), w.getframerate()
                if rate:
                    return frames / float(rate)
        except Exception:
            pass
        return 0.0

    def _duration_ffmpeg(self, path: str) -> float:
        """Get duration by parsing ffmpeg output."""
        try:
            cmd = ["ffmpeg", "-i", path, "-f", "null", "-"]
            output = subprocess.check_output(
                cmd, stderr=subprocess.STDOUT, text=True
            )
            match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", output)
            if match:
                h, m, s = map(float, match.groups())
                return h * 3600 + m * 60 + s
        except Exception:
            pass
        return 0.0

    def build_audio_crossfade_filter(
        self,
        tracks: list[AudioTrack],
        crossfade_duration: int,
        base_input_index: int
    ) -> tuple[str, str]:
        """
        Build filter_complex for N audio tracks with crossfade chain.
        Returns (filter_string, final_tag)
        """
        n = len(tracks)
        parts = [
            f"[{base_input_index + i}:a]volume={tracks[i].get_effective_volume()}[ma{i}]"
            for i in range(n)
        ]

        if n == 1:
            return ";".join(parts), "[ma0]"

        prev = "ma0"
        for j in range(1, n):
            cur, out = f"ma{j}", f"mx{j}"
            parts.append(
                f"[{prev}][{cur}]acrossfade=d={crossfade_duration}:c1=qsin:c2=qsin[{out}]"
            )
            prev = out

        return ";".join(parts), f"[{prev}]"

    def build_video_crossfade_filter(
        self,
        clips: list[VideoClip],
        crossfade_duration: float
    ) -> tuple[str, str, str]:
        """
        Build filter_complex for videos with crossfade.
        Returns (filter_string, video_tag, audio_tag)
        """
        n = len(clips)
        parts = []

        # Prepare base labels
        for i in range(n):
            parts.append(f"[{i}:v]format=yuv420p,setsar=1[v{i}]")
            parts.append(f"[{i}:a]anull[va{i}]")

        if n == 1:
            return ";".join(parts), "[v0]", "[va0]"

        # Chain with offsets
        acc = clips[0].duration
        prev_v, prev_a = "v0", "va0"

        for j in range(1, n):
            off = max(acc - crossfade_duration, 0.0)
            vo, ao = f"vx{j}", f"vax{j}"
            parts.append(
                f"[{prev_v}][v{j}]xfade=transition=fade:duration={crossfade_duration}:offset={off}[{vo}]"
            )
            parts.append(
                f"[{prev_a}][va{j}]acrossfade=d={crossfade_duration}:c1=qsin:c2=qsin[{ao}]"
            )
            prev_v, prev_a = vo, ao
            acc += max(clips[j].duration - crossfade_duration, 0.0)

        return ";".join(parts), f"[{prev_v}]", f"[{prev_a}]"

    def build_export_command(
        self,
        project: Project,
        output_path: str,
        preview_seconds: Optional[int] = None
    ) -> list[str]:
        """Build complete FFmpeg export command."""
        settings = project.settings
        active_tracks = project.get_active_tracks() if settings.include_music else []
        video_volume = settings.video_volume / 100.0

        cmd = ["ffmpeg", "-y"]

        # Add inputs
        for v in project.videos:
            cmd.extend(["-i", v.path])
        for t in active_tracks:
            cmd.extend(["-i", t.path])

        # Build filter complex
        fc_parts = []
        must_reencode = len(project.videos) > 1 or settings.video_crossfade > 0.0

        # Video crossfade
        vfc, tag_vout, tag_vaout = self.build_video_crossfade_filter(
            project.videos, settings.video_crossfade
        )
        fc_parts.append(vfc)
        fc_parts.append(f"{tag_vaout}volume={video_volume}[va]")

        # Music crossfade
        tag_music = ""
        if active_tracks:
            base_idx = len(project.videos)
            cf, tag_music = self.build_audio_crossfade_filter(
                active_tracks, int(settings.audio_crossfade), base_idx
            )
            fc_parts.append(cf)

            if settings.cut_music_at_end:
                video_duration = project.get_video_duration()
                fc_parts.append(f"{tag_music}atrim=duration={video_duration}[mus]")
                tag_music = "[mus]"

        # Audio mixing
        tag_final_audio = ""
        if settings.include_video_audio and tag_music:
            fc_parts.append(
                f"[va]{tag_music}amix=inputs=2:duration=longest:dropout_transition=0[aout]"
            )
            tag_final_audio = "[aout]"
        elif settings.include_video_audio:
            tag_final_audio = "[va]"
        elif tag_music:
            tag_final_audio = tag_music

        if fc_parts:
            cmd.extend(["-filter_complex", ";".join(fc_parts)])

        # Mapping
        cmd.extend(["-map", tag_vout if tag_vout else "0:v:0"])
        if tag_final_audio:
            cmd.extend(["-map", tag_final_audio])
        else:
            cmd.extend(["-an"])

        # Codecs based on output format
        if output_path.lower().endswith(".webm"):
            cmd.extend(["-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "30"])
            cmd.extend(["-c:a", "libvorbis"])
        else:
            if must_reencode:
                preset = "veryfast" if preview_seconds else "medium"
                cmd.extend(["-c:v", "libx264", "-preset", preset, "-crf", "20"])
            else:
                cmd.extend(["-c:v", "copy"])
            cmd.extend(["-c:a", "aac", "-b:a", "192k"])

        # Preview duration limit
        if preview_seconds:
            cmd.extend(["-t", str(preview_seconds)])

        cmd.append(output_path)
        return cmd

    def export(
        self,
        project: Project,
        output_path: str,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> bool:
        """
        Export project to file.
        Returns True on success, False on failure.
        """
        cmd = self.build_export_command(project, output_path)
        cmd.extend(["-progress", "pipe:1", "-nostats"])

        total_ms = project.get_video_duration() * 1000 or 1.0

        try:
            with subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                encoding="utf-8",
                errors="replace"
            ) as proc:
                for line in proc.stdout:
                    if m := self.time_regex.search(line):
                        pos = int(m.group(1))
                        if progress_callback:
                            progress_callback(pos / total_ms * 100)

                return proc.wait() == 0
        except Exception:
            return False

    def create_preview(
        self,
        project: Project,
        clip_seconds: Optional[int] = 60
    ) -> Optional[str]:
        """
        Create a preview file.
        Returns the path to the temporary file, or None on failure.
        """
        fd, temp_path = tempfile.mkstemp(suffix=".mkv")
        os.close(fd)

        cmd = self.build_export_command(project, temp_path, clip_seconds)

        try:
            result = subprocess.call(cmd)
            if result == 0:
                return temp_path
            else:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return None
        except Exception:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return None

    def play_preview(self, file_path: str) -> Optional[subprocess.Popen]:
        """Play a preview file using ffplay or system default."""
        if self.has_ffplay:
            return subprocess.Popen([
                "ffplay", "-autoexit", "-loglevel", "quiet",
                "-window_title", "Preview", file_path
            ])
        else:
            # Use system default
            if os.name == "nt":
                os.startfile(file_path)
            elif shutil.which("open"):
                subprocess.Popen(["open", file_path])
            else:
                subprocess.Popen(["xdg-open", file_path])
            return None

    @staticmethod
    def cleanup_temp_files() -> None:
        """Clean up temporary files created by the application."""
        temp_dir = tempfile.gettempdir()
        try:
            for file in os.listdir(temp_dir):
                file_path = os.path.join(temp_dir, file)
                if (
                    os.path.isfile(file_path)
                    and file.endswith(".mkv")
                    and file.startswith("tmp")
                ):
                    try:
                        os.remove(file_path)
                    except Exception:
                        pass
        except Exception:
            pass
