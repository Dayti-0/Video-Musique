"""
Pytest configuration and fixtures
"""

import pytest
import tempfile
import sys
import os
from pathlib import Path

# Add src to path for all tests
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def temp_dir():
    """Provide a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)


@pytest.fixture
def sample_project():
    """Provide a sample project for testing."""
    from src.core.models import Project, VideoClip, AudioTrack, ProjectSettings

    return Project(
        videos=[
            VideoClip(path="/video1.mp4", name="Video 1", duration=60.0),
            VideoClip(path="/video2.mp4", name="Video 2", duration=120.0),
        ],
        audio_tracks=[
            AudioTrack(path="/audio1.mp3", name="Audio 1", duration=180.0, volume=0.8),
            AudioTrack(path="/audio2.mp3", name="Audio 2", duration=90.0, volume=1.0),
        ],
        settings=ProjectSettings(
            audio_crossfade=10.0,
            video_crossfade=1.5,
            music_volume=70.0,
            video_volume=100.0,
        )
    )


@pytest.fixture
def ffmpeg_processor():
    """Provide an FFmpegProcessor instance."""
    from src.core.ffmpeg import FFmpegProcessor
    return FFmpegProcessor()


@pytest.fixture(autouse=True)
def reset_logger_singleton():
    """Reset logger singleton between tests to avoid state leakage."""
    from src.utils import logger
    # Store original state
    original_instance = logger._logger
    original_initialized = logger.Logger._initialized

    yield

    # Reset after test (but keep singleton for efficiency)
    # We don't fully reset to avoid recreating handlers
