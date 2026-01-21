"""
Configuration management for Video-Musique
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

from ..utils.logger import get_logger


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
        # Performance settings
        "use_gpu": True,
        "speed_preset": "balanced",  # ultrafast, fast, balanced, quality
    }

    def __init__(self, config_file: Optional[Path] = None):
        self.config_file = config_file or self.DEFAULT_CONFIG_FILE
        self._data: dict[str, Any] = {}
        self._logger = get_logger()
        self.load()

    def load(self) -> None:
        """Load configuration from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
                self._logger.debug(f"Configuration loaded from {self.config_file}")
            except json.JSONDecodeError as e:
                self._logger.warning(f"Invalid JSON in config file: {e}")
                self._data = {}
            except OSError as e:
                self._logger.warning(f"Could not read config file: {e}")
                self._data = {}
        else:
            self._data = {}
            self._logger.debug("No existing config file, using defaults")

    def save(self) -> None:
        """Save configuration to file."""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
            self._logger.debug("Configuration saved")
        except OSError as e:
            self._logger.error(f"Could not save config file: {e}")

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
        logger = get_logger()
        try:
            data = project.to_dict()
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.log_file_operation("save", file_path, success=True)
            logger.info(f"Project saved: {file_path}")
            return True
        except (OSError, TypeError) as e:
            logger.log_file_operation("save", file_path, success=False)
            logger.error(f"Failed to save project: {e}")
            return False

    @staticmethod
    def load_project_data(file_path: str) -> Optional[dict]:
        """
        Load project data from file.
        Returns dict on success, None on failure.
        """
        logger = get_logger()
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.log_file_operation("load", file_path, success=True)
            logger.info(f"Project loaded: {file_path}")
            return data
        except json.JSONDecodeError as e:
            logger.log_file_operation("load", file_path, success=False)
            logger.error(f"Invalid project file format: {e}")
            return None
        except OSError as e:
            logger.log_file_operation("load", file_path, success=False)
            logger.error(f"Failed to load project: {e}")
            return None
