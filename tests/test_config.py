"""
Tests for configuration management
"""

import json
import pytest
import tempfile
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.config import Config, ProjectManager
from src.core.models import Project, VideoClip, AudioTrack, ProjectSettings


class TestConfig:
    """Tests for Config class."""

    def test_default_values(self):
        """Test that default values are returned when no config exists."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            config_path = Path(f.name)

        # Remove the file to simulate no existing config
        config_path.unlink()

        config = Config(config_file=config_path)

        assert config.get("last_directory") == str(Path.home())
        assert config.get("window_width") == 1100
        assert config.get("window_height") == 700
        assert config.get("use_gpu") is True

    def test_set_and_get(self):
        """Test setting and getting values."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            config_path = Path(f.name)

        try:
            config = Config(config_file=config_path)
            config.set("test_key", "test_value")

            assert config.get("test_key") == "test_value"
        finally:
            config_path.unlink(missing_ok=True)

    def test_persistence(self):
        """Test that config persists across instances."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            config_path = Path(f.name)

        try:
            # Set value in first instance
            config1 = Config(config_file=config_path)
            config1.set("persistent_key", 42)

            # Create new instance and check value
            config2 = Config(config_file=config_path)
            assert config2.get("persistent_key") == 42
        finally:
            config_path.unlink(missing_ok=True)

    def test_window_size_property(self):
        """Test window_size property."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            config_path = Path(f.name)

        try:
            config = Config(config_file=config_path)
            config.window_size = (1200, 800)

            assert config.window_size == (1200, 800)
        finally:
            config_path.unlink(missing_ok=True)

    def test_last_directory_property(self):
        """Test last_directory property with valid directory."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            config_path = Path(f.name)

        try:
            config = Config(config_file=config_path)

            # Use temp directory which should exist
            temp_dir = tempfile.gettempdir()
            config.last_directory = temp_dir

            assert config.last_directory == temp_dir
        finally:
            config_path.unlink(missing_ok=True)

    def test_last_directory_invalid(self):
        """Test last_directory returns home for invalid path."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            config_path = Path(f.name)

        try:
            config = Config(config_file=config_path)
            config.set("last_directory", "/nonexistent/path/12345")

            assert config.last_directory == str(Path.home())
        finally:
            config_path.unlink(missing_ok=True)

    def test_load_invalid_json(self):
        """Test loading invalid JSON file."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            f.write("invalid json {{{")
            config_path = Path(f.name)

        try:
            config = Config(config_file=config_path)
            # Should not raise, should use defaults
            assert config.get("window_width") == 1100
        finally:
            config_path.unlink(missing_ok=True)


class TestProjectManager:
    """Tests for ProjectManager class."""

    def test_save_and_load_project(self):
        """Test saving and loading a project."""
        # Create a project
        project = Project(
            videos=[
                VideoClip(path="/video1.mp4", name="Video 1", duration=100.0),
                VideoClip(path="/video2.mp4", name="Video 2", duration=200.0),
            ],
            audio_tracks=[
                AudioTrack(path="/audio1.mp3", name="Audio 1", duration=300.0, volume=0.8),
                AudioTrack(path="/audio2.mp3", name="Audio 2", duration=150.0, mute=True),
            ],
            settings=ProjectSettings(
                audio_crossfade=8.0,
                video_crossfade=2.5,
                use_gpu=False,
                speed_preset="quality"
            )
        )

        with tempfile.NamedTemporaryFile(suffix=".mixproj", delete=False) as f:
            project_path = f.name

        try:
            # Save project
            result = ProjectManager.save_project(project, project_path)
            assert result is True

            # Load project data
            data = ProjectManager.load_project_data(project_path)
            assert data is not None

            # Verify data
            assert len(data["videos"]) == 2
            assert len(data["audio_tracks"]) == 2
            assert data["videos"][0]["name"] == "Video 1"
            assert data["audio_tracks"][0]["volume"] == 0.8
            assert data["audio_tracks"][1]["mute"] is True
            assert data["settings"]["cross_fade_audio"] == 8.0
            assert data["settings"]["use_gpu"] is False
        finally:
            os.unlink(project_path)

    def test_save_project_to_invalid_path(self):
        """Test saving to an invalid path returns False."""
        project = Project()
        result = ProjectManager.save_project(project, "/nonexistent/path/project.mixproj")
        assert result is False

    def test_load_nonexistent_project(self):
        """Test loading a nonexistent project returns None."""
        data = ProjectManager.load_project_data("/nonexistent/project.mixproj")
        assert data is None

    def test_load_invalid_json_project(self):
        """Test loading an invalid JSON file returns None."""
        with tempfile.NamedTemporaryFile(suffix=".mixproj", delete=False, mode="w") as f:
            f.write("not valid json")
            project_path = f.name

        try:
            data = ProjectManager.load_project_data(project_path)
            assert data is None
        finally:
            os.unlink(project_path)

    def test_project_file_format(self):
        """Test that saved project file is valid JSON."""
        project = Project(
            videos=[VideoClip(path="/test.mp4", duration=60.0)],
            settings=ProjectSettings(music_volume=50.0)
        )

        with tempfile.NamedTemporaryFile(suffix=".mixproj", delete=False) as f:
            project_path = f.name

        try:
            ProjectManager.save_project(project, project_path)

            # Read and parse manually
            with open(project_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            assert "videos" in data
            assert "audio_tracks" in data
            assert "settings" in data
            assert data["settings"]["music_volume"] == 50.0
        finally:
            os.unlink(project_path)
