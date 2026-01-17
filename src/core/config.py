"""
Configuration management for Video-Musique
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional


class Config:
    """Application configuration manager."""

    DEFAULT_CONFIG_FILE = Path.home() / ".video_musique_config.json"
    PROJECT_EXTENSION = ".mixproj"

    # Default values
    DEFAULTS = {
        "last_directory": str(Path.home()),
        "theme": "modern",
        "window_width": 1100,
        "window_height": 700,
        "audio_crossfade": 10,
        "video_crossfade": 1.0,
        "music_volume": 70,
        "video_volume": 100,
    }

    def __init__(self, config_file: Optional[Path] = None):
        self.config_file = config_file or self.DEFAULT_CONFIG_FILE
        self._data: dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        """Load configuration from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except Exception:
                self._data = {}
        else:
            self._data = {}

    def save(self) -> None:
        """Save configuration to file."""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
        except Exception:
            pass

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        if default is None:
            default = self.DEFAULTS.get(key)
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set configuration value and save."""
        self._data[key] = value
        self.save()

    @property
    def last_directory(self) -> str:
        """Get last used directory."""
        path = self.get("last_directory")
        if path and os.path.isdir(path):
            return path
        return str(Path.home())

    @last_directory.setter
    def last_directory(self, value: str) -> None:
        """Set last used directory."""
        if os.path.isdir(value):
            self.set("last_directory", value)

    @property
    def window_size(self) -> tuple[int, int]:
        """Get window size."""
        return (
            self.get("window_width", 1100),
            self.get("window_height", 700)
        )

    @window_size.setter
    def window_size(self, value: tuple[int, int]) -> None:
        """Set window size."""
        self._data["window_width"] = value[0]
        self._data["window_height"] = value[1]
        self.save()


class ProjectManager:
    """Manages project file operations."""

    @staticmethod
    def save_project(project, file_path: str) -> bool:
        """
        Save project to file.
        Returns True on success, False on failure.
        """
        try:
            data = project.to_dict()
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return True
        except Exception:
            return False

    @staticmethod
    def load_project_data(file_path: str) -> Optional[dict]:
        """
        Load project data from file.
        Returns dict on success, None on failure.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
