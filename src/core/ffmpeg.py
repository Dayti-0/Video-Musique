"""
FFmpeg operations for Video-Musique
Optimized for performance with caching, GPU acceleration, and parallel processing
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import wave
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Optional

from .models import AudioTrack, VideoClip, Project


class FFmpegProcessor:
    """Handles all FFmpeg operations for media processing with performance optimizations."""

    SUPPORTED_VIDEO = (".mp4", ".mkv", ".mov", ".avi", ".webm")
    SUPPORTED_AUDIO = (".mp3", ".wav", ".flac", ".aac", ".ogg")

    # GPU encoder configurations
    GPU_ENCODERS = {
        "nvidia": {"encoder": "h264_nvenc", "preset_flag": "-preset", "presets": ["p1", "p4", "p7"]},
        "amd": {"encoder": "h264_amf", "preset_flag": "-quality", "presets": ["speed", "balanced", "quality"]},
        "intel": {"encoder": "h264_qsv", "preset_flag": "-preset", "presets": ["veryfast", "medium", "veryslow"]},
        "vaapi": {"encoder": "h264_vaapi", "preset_flag": None, "presets": []},
    }

    # Preset mappings for speed optimization
    SPEED_PRESETS = {
        "ultrafast": {"cpu": "ultrafast", "nvidia": "p1", "amd": "speed", "intel": "veryfast"},
        "fast": {"cpu": "veryfast", "nvidia": "p4", "amd": "balanced", "intel": "fast"},
        "balanced": {"cpu": "medium", "nvidia": "p5", "amd": "balanced", "intel": "medium"},
        "quality": {"cpu": "slow", "nvidia": "p7", "amd": "quality", "intel": "veryslow"},
    }

    def __init__(self):
        self.time_regex = re.compile(r"out_time_ms=(\d+)")
        self._duration_cache: dict[str, float] = {}
        self._cache_lock = threading.Lock()
        self._available_gpu_encoder: Optional[str] = None
        self._gpu_checked = False
        self._check_dependencies()

    def _check_dependencies(self) -> None:
        """Verify FFmpeg tools are available."""
        self.has_ffmpeg = shutil.which("ffmpeg") is not None
        self.has_ffprobe = shutil.which("ffprobe") is not None
        self.has_ffplay = shutil.which("ffplay") is not None

    def detect_gpu_encoder(self) -> Optional[str]:
        """
        Detect available GPU encoder.
        Returns encoder name (nvidia, amd, intel, vaapi) or None.
        Results are cached after first check.
        """
        if self._gpu_checked:
            return self._available_gpu_encoder

        self._gpu_checked = True

        if not self.has_ffmpeg:
            return None

        # Check for available encoders
        try:
            result = subprocess.run(
                ["ffmpeg", "-hide_banner", "-encoders"],
                capture_output=True, text=True, timeout=10
            )
            encoders_output = result.stdout

            # Check in priority order: NVIDIA > Intel QSV > AMD > VAAPI
            encoder_checks = [
                ("nvidia", "h264_nvenc"),
                ("intel", "h264_qsv"),
                ("amd", "h264_amf"),
                ("vaapi", "h264_vaapi"),
            ]

            for gpu_type, encoder_name in encoder_checks:
                if encoder_name in encoders_output:
                    # Verify encoder actually works with a test
                    if self._test_gpu_encoder(encoder_name, gpu_type):
                        self._available_gpu_encoder = gpu_type
                        return gpu_type

        except Exception:
            pass

        return None

    def _test_gpu_encoder(self, encoder: str, gpu_type: str) -> bool:
        """Test if a GPU encoder actually works."""
        try:
            # Create a minimal test command
            cmd = ["ffmpeg", "-hide_banner", "-f", "lavfi", "-i", "color=black:s=64x64:d=0.1"]

            if gpu_type == "vaapi":
                # VAAPI needs device initialization
                cmd.extend(["-vaapi_device", "/dev/dri/renderD128"])
                cmd.extend(["-vf", "format=nv12,hwupload"])

            cmd.extend(["-c:v", encoder, "-f", "null", "-"])

            result = subprocess.run(cmd, capture_output=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False

    def get_gpu_info(self) -> dict:
        """Get information about available GPU acceleration."""
        gpu = self.detect_gpu_encoder()
        return {
            "available": gpu is not None,
            "type": gpu,
            "encoder": self.GPU_ENCODERS.get(gpu, {}).get("encoder") if gpu else None,
        }

    @staticmethod
    def _sexagesimal(s: str) -> float:
        """Convert 'HH:MM:SS.xx' to seconds."""
        try:
            h, m, sec = s.split(":")
            return int(h) * 3600 + int(m) * 60 + float(sec)
        except Exception:
            return 0.0

    def _get_cache_key(self, path: str) -> str:
        """Generate cache key based on file path and modification time."""
        try:
            mtime = os.path.getmtime(path)
            return f"{path}:{mtime}"
        except Exception:
            return path

    def get_duration(self, path: str) -> float:
        """
        Get media duration in seconds using multiple fallback methods.
        Results are cached to avoid repeated ffprobe calls.
        Returns 0.0 if duration cannot be determined.
        """
        if not os.path.exists(path):
            return 0.0

        # Check cache first (thread-safe)
        cache_key = self._get_cache_key(path)
        with self._cache_lock:
            if cache_key in self._duration_cache:
                return self._duration_cache[cache_key]

        # Method 1: Quick ffprobe
        duration = self._duration_ffprobe_quick(path)
        if duration > 0:
            self._cache_duration(cache_key, duration)
            return duration

        # Method 2: FFprobe JSON
        duration = self._duration_ffprobe_json(path)
        if duration > 0:
            self._cache_duration(cache_key, duration)
            return duration

        # Method 3: Mutagen (if available)
        duration = self._duration_mutagen(path)
        if duration > 0:
            self._cache_duration(cache_key, duration)
            return duration

        # Method 4: Wave module for .wav files
        if path.lower().endswith(".wav"):
            duration = self._duration_wave(path)
            if duration > 0:
                self._cache_duration(cache_key, duration)
                return duration

        # Method 5: FFmpeg output parsing
        duration = self._duration_ffmpeg(path)
        if duration > 0:
            self._cache_duration(cache_key, duration)
            return duration

        return 0.0

    def _cache_duration(self, cache_key: str, duration: float) -> None:
        """Cache a duration value (thread-safe)."""
        with self._cache_lock:
            self._duration_cache[cache_key] = duration

    def get_durations_parallel(self, paths: list[str], max_workers: int = 4) -> list[float]:
        """
        Get durations for multiple files in parallel.
        Significantly faster for large numbers of files.

        Args:
            paths: List of file paths
            max_workers: Maximum number of parallel workers (default 4)

        Returns:
            List of durations in the same order as input paths
        """
        if not paths:
            return []

        # Single file - no need for parallel
        if len(paths) == 1:
            return [self.get_duration(paths[0])]

        # Process in parallel
        results = {}
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_path = {
                executor.submit(self.get_duration, path): (i, path)
                for i, path in enumerate(paths)
            }

            for future in as_completed(future_to_path):
                idx, path = future_to_path[future]
                try:
                    results[idx] = future.result()
                except Exception:
                    results[idx] = 0.0

        # Return results in original order
        return [results.get(i, 0.0) for i in range(len(paths))]

    def clear_cache(self) -> None:
        """Clear the duration cache."""
        with self._cache_lock:
            self._duration_cache.clear()

    def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        with self._cache_lock:
            return {
                "entries": len(self._duration_cache),
                "paths": list(self._duration_cache.keys())[:10],  # First 10 for debugging
            }

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
        preview_seconds: Optional[int] = None,
        use_gpu: bool = True,
        speed_preset: str = "balanced"
    ) -> list[str]:
        """
        Build complete FFmpeg export command with GPU acceleration support.

        Args:
            project: Project to export
            output_path: Output file path
            preview_seconds: Optional duration limit for preview
            use_gpu: Whether to use GPU acceleration if available
            speed_preset: Speed preset (ultrafast, fast, balanced, quality)
        """
        settings = project.settings
        active_tracks = project.get_active_tracks() if settings.include_music else []
        video_volume = settings.video_volume / 100.0

        # Detect GPU encoder if requested
        gpu_type = self.detect_gpu_encoder() if use_gpu else None

        cmd = ["ffmpeg", "-y"]

        # Add hardware acceleration input flags for GPU decoding
        if gpu_type == "nvidia":
            cmd.extend(["-hwaccel", "cuda", "-hwaccel_output_format", "cuda"])
        elif gpu_type == "intel":
            cmd.extend(["-hwaccel", "qsv", "-hwaccel_output_format", "qsv"])
        elif gpu_type == "vaapi":
            cmd.extend(["-vaapi_device", "/dev/dri/renderD128"])

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

        # Codecs based on output format and GPU availability
        if output_path.lower().endswith(".webm"):
            cmd.extend(["-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "30"])
            cmd.extend(["-c:a", "libvorbis"])
        else:
            if must_reencode:
                # Determine preset based on context
                effective_preset = "ultrafast" if preview_seconds else speed_preset

                if gpu_type and gpu_type in self.GPU_ENCODERS:
                    # Use GPU encoder
                    gpu_config = self.GPU_ENCODERS[gpu_type]
                    cmd.extend(["-c:v", gpu_config["encoder"]])

                    # Add GPU-specific preset
                    preset_value = self.SPEED_PRESETS.get(effective_preset, {}).get(
                        gpu_type, self.SPEED_PRESETS["balanced"].get(gpu_type)
                    )

                    if gpu_config["preset_flag"] and preset_value:
                        cmd.extend([gpu_config["preset_flag"], preset_value])

                    # GPU encoders use different rate control
                    if gpu_type == "nvidia":
                        cmd.extend(["-rc", "vbr", "-cq", "20", "-b:v", "0"])
                    elif gpu_type == "amd":
                        cmd.extend(["-rc", "vbr_latency", "-qp_p", "20", "-qp_i", "20"])
                    elif gpu_type == "intel":
                        cmd.extend(["-global_quality", "20", "-look_ahead", "1"])
                    else:
                        cmd.extend(["-qp", "20"])
                else:
                    # CPU encoding with optimized settings
                    cpu_preset = self.SPEED_PRESETS.get(effective_preset, {}).get(
                        "cpu", "medium"
                    )
                    cmd.extend(["-c:v", "libx264", "-preset", cpu_preset, "-crf", "20"])

                    # Additional CPU optimizations
                    if effective_preset in ["ultrafast", "fast"]:
                        cmd.extend(["-tune", "fastdecode"])
                        cmd.extend(["-threads", str(os.cpu_count() or 4)])
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
        progress_callback: Optional[Callable[[float], None]] = None,
        use_gpu: bool = True,
        speed_preset: str = "balanced"
    ) -> bool:
        """
        Export project to file with GPU acceleration support.

        Args:
            project: Project to export
            output_path: Output file path
            progress_callback: Optional callback for progress updates (0-100)
            use_gpu: Whether to use GPU acceleration if available
            speed_preset: Speed preset (ultrafast, fast, balanced, quality)

        Returns:
            True on success, False on failure.
        """
        cmd = self.build_export_command(
            project, output_path,
            use_gpu=use_gpu,
            speed_preset=speed_preset
        )
        cmd.extend(["-progress", "pipe:1", "-nostats"])

        total_ms = project.get_video_duration() * 1000 or 1.0
        last_progress = 0

        try:
            with subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=8192,  # Larger buffer for better performance
                universal_newlines=True,
                encoding="utf-8",
                errors="replace"
            ) as proc:
                # Read stdout for progress
                for line in proc.stdout:
                    if m := self.time_regex.search(line):
                        pos = int(m.group(1))
                        progress = min(pos / total_ms * 100, 100)

                        # Throttle callback to avoid too frequent UI updates
                        if progress_callback and (progress - last_progress >= 0.5 or progress >= 100):
                            progress_callback(progress)
                            last_progress = progress

                return proc.wait() == 0
        except Exception:
            return False

    def export_with_stats(
        self,
        project: Project,
        output_path: str,
        progress_callback: Optional[Callable[[float], None]] = None,
        use_gpu: bool = True,
        speed_preset: str = "balanced"
    ) -> dict:
        """
        Export with detailed statistics.

        Returns dict with:
            - success: bool
            - encoder: str (encoder used)
            - gpu_accelerated: bool
            - duration_seconds: float (time taken)
        """
        import time
        start_time = time.time()

        gpu_type = self.detect_gpu_encoder() if use_gpu else None
        encoder = self.GPU_ENCODERS.get(gpu_type, {}).get("encoder", "libx264") if gpu_type else "libx264"

        success = self.export(
            project, output_path, progress_callback,
            use_gpu=use_gpu, speed_preset=speed_preset
        )

        return {
            "success": success,
            "encoder": encoder,
            "gpu_accelerated": gpu_type is not None,
            "gpu_type": gpu_type,
            "duration_seconds": time.time() - start_time,
        }

    def create_preview(
        self,
        project: Project,
        clip_seconds: Optional[int] = 60,
        use_gpu: bool = True
    ) -> Optional[str]:
        """
        Create a preview file with optimized settings for speed.
        Returns the path to the temporary file, or None on failure.
        """
        fd, temp_path = tempfile.mkstemp(suffix=".mkv")
        os.close(fd)

        # Use ultrafast preset for preview generation
        cmd = self.build_export_command(
            project, temp_path, clip_seconds,
            use_gpu=use_gpu,
            speed_preset="ultrafast"
        )

        try:
            # Use stderr to /dev/null for cleaner output
            result = subprocess.call(
                cmd,
                stderr=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL
            )
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
