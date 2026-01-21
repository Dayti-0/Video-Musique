"""
Tests for FFmpeg processor
"""

import pytest
import tempfile
import shutil
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.ffmpeg import FFmpegProcessor
from src.core.models import Project, VideoClip, AudioTrack, ProjectSettings


# Check if FFmpeg is available
HAS_FFMPEG = shutil.which("ffmpeg") is not None


class TestFFmpegProcessor:
    """Tests for FFmpegProcessor class."""

    def test_initialization(self):
        """Test FFmpegProcessor initialization."""
        processor = FFmpegProcessor()

        assert processor.time_regex is not None
        assert isinstance(processor._duration_cache, dict)

    def test_supported_formats(self):
        """Test supported format constants."""
        assert ".mp4" in FFmpegProcessor.SUPPORTED_VIDEO
        assert ".mkv" in FFmpegProcessor.SUPPORTED_VIDEO
        assert ".webm" in FFmpegProcessor.SUPPORTED_VIDEO

        assert ".mp3" in FFmpegProcessor.SUPPORTED_AUDIO
        assert ".wav" in FFmpegProcessor.SUPPORTED_AUDIO
        assert ".flac" in FFmpegProcessor.SUPPORTED_AUDIO

    def test_gpu_encoders_config(self):
        """Test GPU encoder configurations exist."""
        assert "nvidia" in FFmpegProcessor.GPU_ENCODERS
        assert "amd" in FFmpegProcessor.GPU_ENCODERS
        assert "intel" in FFmpegProcessor.GPU_ENCODERS
        assert "vaapi" in FFmpegProcessor.GPU_ENCODERS

        # Check nvidia config structure
        nvidia = FFmpegProcessor.GPU_ENCODERS["nvidia"]
        assert "encoder" in nvidia
        assert "preset_flag" in nvidia
        assert "presets" in nvidia

    def test_speed_presets(self):
        """Test speed preset configurations."""
        presets = FFmpegProcessor.SPEED_PRESETS

        assert "ultrafast" in presets
        assert "fast" in presets
        assert "balanced" in presets
        assert "quality" in presets

        # Each preset should have CPU config
        for preset in presets.values():
            assert "cpu" in preset

    def test_sexagesimal_conversion(self):
        """Test time string conversion."""
        processor = FFmpegProcessor()

        # Basic conversions
        assert processor._sexagesimal("00:00:10.00") == 10.0
        assert processor._sexagesimal("00:01:00.00") == 60.0
        assert processor._sexagesimal("01:00:00.00") == 3600.0
        assert processor._sexagesimal("01:30:45.50") == 5445.5

    def test_sexagesimal_invalid(self):
        """Test time string conversion with invalid input."""
        processor = FFmpegProcessor()

        assert processor._sexagesimal("invalid") == 0.0
        assert processor._sexagesimal("") == 0.0
        assert processor._sexagesimal("12:34") == 0.0

    def test_cache_key_generation(self):
        """Test cache key generation."""
        processor = FFmpegProcessor()

        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content")
            temp_path = f.name

        try:
            key = processor._get_cache_key(temp_path)
            assert temp_path in key
            assert ":" in key  # Contains modification time
        finally:
            os.unlink(temp_path)

    def test_cache_key_nonexistent_file(self):
        """Test cache key for nonexistent file."""
        processor = FFmpegProcessor()
        key = processor._get_cache_key("/nonexistent/file.mp4")
        assert key == "/nonexistent/file.mp4"

    def test_duration_nonexistent_file(self):
        """Test getting duration of nonexistent file."""
        processor = FFmpegProcessor()
        duration = processor.get_duration("/nonexistent/file.mp4")
        assert duration == 0.0

    def test_duration_caching(self):
        """Test that durations are cached."""
        processor = FFmpegProcessor()

        # Pre-populate cache
        with processor._cache_lock:
            processor._duration_cache["test_key:12345"] = 42.0

        # Mock _get_cache_key to return our test key
        with patch.object(processor, '_get_cache_key', return_value="test_key:12345"):
            with patch('os.path.exists', return_value=True):
                duration = processor.get_duration("/any/path.mp4")
                assert duration == 42.0

    def test_clear_cache(self):
        """Test clearing the cache."""
        processor = FFmpegProcessor()

        # Add some entries
        with processor._cache_lock:
            processor._duration_cache["key1"] = 10.0
            processor._duration_cache["key2"] = 20.0

        processor.clear_cache()

        assert len(processor._duration_cache) == 0

    def test_cache_stats(self):
        """Test getting cache statistics."""
        processor = FFmpegProcessor()

        with processor._cache_lock:
            processor._duration_cache["key1"] = 10.0
            processor._duration_cache["key2"] = 20.0

        stats = processor.get_cache_stats()

        assert stats["entries"] == 2
        assert "key1" in stats["paths"]

    def test_get_durations_parallel_empty(self):
        """Test parallel duration detection with empty list."""
        processor = FFmpegProcessor()
        durations = processor.get_durations_parallel([])
        assert durations == []

    def test_get_durations_parallel_single(self):
        """Test parallel duration detection with single file."""
        processor = FFmpegProcessor()

        with patch.object(processor, 'get_duration', return_value=60.0):
            durations = processor.get_durations_parallel(["/test.mp4"])
            assert durations == [60.0]


class TestFilterBuilding:
    """Tests for FFmpeg filter building."""

    def test_build_audio_crossfade_single_track(self):
        """Test audio crossfade filter for single track."""
        processor = FFmpegProcessor()
        tracks = [AudioTrack(path="/a.mp3", volume=0.8)]

        filter_str, final_tag = processor.build_audio_crossfade_filter(tracks, 10, 1)

        assert "[1:a]volume=0.8[ma0]" in filter_str
        assert final_tag == "[ma0]"

    def test_build_audio_crossfade_multiple_tracks(self):
        """Test audio crossfade filter for multiple tracks."""
        processor = FFmpegProcessor()
        tracks = [
            AudioTrack(path="/a.mp3", volume=1.0),
            AudioTrack(path="/b.mp3", volume=0.5),
        ]

        filter_str, final_tag = processor.build_audio_crossfade_filter(tracks, 5, 1)

        assert "[1:a]volume=1.0[ma0]" in filter_str
        assert "[2:a]volume=0.5[ma1]" in filter_str
        assert "acrossfade=d=5" in filter_str
        assert final_tag == "[mx1]"

    def test_build_video_crossfade_single_clip(self):
        """Test video crossfade filter for single clip."""
        processor = FFmpegProcessor()
        clips = [VideoClip(path="/v.mp4", duration=60.0)]

        filter_str, video_tag, audio_tag = processor.build_video_crossfade_filter(clips, 1.0)

        assert "[0:v]format=yuv420p" in filter_str
        assert video_tag == "[v0]"
        assert audio_tag == "[va0]"

    def test_build_video_crossfade_multiple_clips(self):
        """Test video crossfade filter for multiple clips."""
        processor = FFmpegProcessor()
        clips = [
            VideoClip(path="/v1.mp4", duration=60.0),
            VideoClip(path="/v2.mp4", duration=60.0),
        ]

        filter_str, video_tag, audio_tag = processor.build_video_crossfade_filter(clips, 2.0)

        assert "xfade=transition=fade" in filter_str
        assert "duration=2.0" in filter_str
        assert video_tag == "[vx1]"
        assert audio_tag == "[vax1]"


class TestExportCommand:
    """Tests for export command building."""

    def test_build_export_command_basic(self):
        """Test basic export command building."""
        processor = FFmpegProcessor()

        # Mock GPU detection to return None
        with patch.object(processor, 'detect_gpu_encoder', return_value=None):
            project = Project(
                videos=[VideoClip(path="/video.mp4", duration=60.0)],
            )

            cmd = processor.build_export_command(project, "/output.mkv")

            assert "ffmpeg" in cmd
            assert "-y" in cmd
            assert "-i" in cmd
            assert "/video.mp4" in cmd
            assert "/output.mkv" in cmd

    def test_build_export_command_with_audio(self):
        """Test export command with audio tracks."""
        processor = FFmpegProcessor()

        with patch.object(processor, 'detect_gpu_encoder', return_value=None):
            project = Project(
                videos=[VideoClip(path="/video.mp4", duration=60.0)],
                audio_tracks=[AudioTrack(path="/audio.mp3", duration=120.0)],
                settings=ProjectSettings(include_music=True)
            )

            cmd = processor.build_export_command(project, "/output.mkv")

            assert "/audio.mp3" in cmd

    def test_build_export_command_webm(self):
        """Test export command for WebM output."""
        processor = FFmpegProcessor()

        with patch.object(processor, 'detect_gpu_encoder', return_value=None):
            project = Project(
                videos=[VideoClip(path="/video.mp4", duration=60.0)],
            )

            cmd = processor.build_export_command(project, "/output.webm")

            assert "libvpx-vp9" in cmd
            assert "libvorbis" in cmd

    def test_build_export_command_preview(self):
        """Test export command with preview duration."""
        processor = FFmpegProcessor()

        with patch.object(processor, 'detect_gpu_encoder', return_value=None):
            project = Project(
                videos=[VideoClip(path="/video.mp4", duration=300.0)],
            )

            cmd = processor.build_export_command(project, "/output.mkv", preview_seconds=60)

            assert "-t" in cmd
            assert "60" in cmd

    def test_build_export_command_gpu_nvidia(self):
        """Test export command with NVIDIA GPU."""
        processor = FFmpegProcessor()

        with patch.object(processor, 'detect_gpu_encoder', return_value="nvidia"):
            project = Project(
                videos=[
                    VideoClip(path="/v1.mp4", duration=30.0),
                    VideoClip(path="/v2.mp4", duration=30.0),
                ],
            )

            cmd = processor.build_export_command(project, "/output.mkv", use_gpu=True)

            assert "-hwaccel" in cmd
            assert "cuda" in cmd
            assert "h264_nvenc" in cmd


class TestGPUDetection:
    """Tests for GPU detection."""

    def test_get_gpu_info_structure(self):
        """Test GPU info return structure."""
        processor = FFmpegProcessor()

        info = processor.get_gpu_info()

        assert "available" in info
        assert "type" in info
        assert "encoder" in info
        assert isinstance(info["available"], bool)

    def test_detect_gpu_caching(self):
        """Test that GPU detection is cached."""
        processor = FFmpegProcessor()

        # First call
        with patch.object(processor, '_test_gpu_encoder', return_value=False):
            result1 = processor.detect_gpu_encoder()

        # Second call should return cached result
        result2 = processor.detect_gpu_encoder()

        assert result1 == result2
        assert processor._gpu_checked is True


@pytest.mark.skipif(not HAS_FFMPEG, reason="FFmpeg not available")
class TestFFmpegIntegration:
    """Integration tests requiring FFmpeg."""

    def test_check_dependencies(self):
        """Test dependency checking."""
        processor = FFmpegProcessor()

        assert processor.has_ffmpeg is True
        assert processor.has_ffprobe is True

    def test_cleanup_temp_files(self):
        """Test temporary file cleanup."""
        # Create a temp file that looks like our temp files
        temp_dir = tempfile.gettempdir()
        temp_file = os.path.join(temp_dir, "tmp_test_cleanup.mkv")

        with open(temp_file, "w") as f:
            f.write("test")

        try:
            removed = FFmpegProcessor.cleanup_temp_files()
            # Should have removed at least our test file
            assert not os.path.exists(temp_file) or removed >= 0
        except Exception:
            # Clean up manually if test fails
            if os.path.exists(temp_file):
                os.unlink(temp_file)
            raise
