"""
Logging system for Video-Musique
Provides structured logging with file and console output
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


class Logger:
    """Centralized logging manager for Video-Musique."""

    _instance: Optional[Logger] = None
    _initialized: bool = False

    # Log levels mapping
    LEVELS = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL,
    }

    # Default log directory
    DEFAULT_LOG_DIR = Path.home() / ".video_musique" / "logs"

    def __new__(cls) -> Logger:
        """Singleton pattern for logger."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the logger (only once due to singleton)."""
        if Logger._initialized:
            return

        self._logger = logging.getLogger("VideoMusique")
        self._logger.setLevel(logging.DEBUG)
        self._log_file: Optional[Path] = None

        # Prevent duplicate handlers
        self._logger.handlers.clear()

        # Setup console handler
        self._setup_console_handler()

        Logger._initialized = True

    def _setup_console_handler(self) -> None:
        """Setup console logging handler."""
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(logging.WARNING)  # Only warnings and above to console

        console_format = logging.Formatter(
            "[%(levelname)s] %(message)s"
        )
        console_handler.setFormatter(console_format)
        self._logger.addHandler(console_handler)

    def enable_file_logging(self, log_dir: Optional[Path] = None) -> Path:
        """
        Enable logging to file.

        Args:
            log_dir: Directory for log files. Uses default if not specified.

        Returns:
            Path to the log file.
        """
        log_dir = log_dir or self.DEFAULT_LOG_DIR

        # Create log directory if needed
        log_dir.mkdir(parents=True, exist_ok=True)

        # Create log file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._log_file = log_dir / f"video_musique_{timestamp}.log"

        # Setup file handler
        file_handler = logging.FileHandler(
            self._log_file, encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)

        file_format = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_format)
        self._logger.addHandler(file_handler)

        self.info(f"Log file created: {self._log_file}")
        return self._log_file

    def set_level(self, level: str) -> None:
        """
        Set the logging level.

        Args:
            level: One of 'debug', 'info', 'warning', 'error', 'critical'
        """
        log_level = self.LEVELS.get(level.lower(), logging.INFO)
        self._logger.setLevel(log_level)

    def debug(self, message: str, *args, **kwargs) -> None:
        """Log a debug message."""
        self._logger.debug(message, *args, **kwargs)

    def info(self, message: str, *args, **kwargs) -> None:
        """Log an info message."""
        self._logger.info(message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs) -> None:
        """Log a warning message."""
        self._logger.warning(message, *args, **kwargs)

    def error(self, message: str, *args, **kwargs) -> None:
        """Log an error message."""
        self._logger.error(message, *args, **kwargs)

    def critical(self, message: str, *args, **kwargs) -> None:
        """Log a critical message."""
        self._logger.critical(message, *args, **kwargs)

    def exception(self, message: str, *args, **kwargs) -> None:
        """Log an exception with traceback."""
        self._logger.exception(message, *args, **kwargs)

    def log_ffmpeg_command(self, cmd: list[str]) -> None:
        """Log an FFmpeg command for debugging."""
        cmd_str = " ".join(cmd)
        self.debug(f"FFmpeg command: {cmd_str}")

    def log_export_start(self, output_path: str, use_gpu: bool, preset: str) -> None:
        """Log export start with settings."""
        self.info(
            f"Export started: output={output_path}, gpu={use_gpu}, preset={preset}"
        )

    def log_export_complete(self, output_path: str, duration_seconds: float, success: bool) -> None:
        """Log export completion."""
        status = "SUCCESS" if success else "FAILED"
        self.info(
            f"Export {status}: output={output_path}, duration={duration_seconds:.1f}s"
        )

    def log_preview_start(self, clip_seconds: Optional[int]) -> None:
        """Log preview generation start."""
        duration = f"{clip_seconds}s" if clip_seconds else "full"
        self.info(f"Preview generation started: duration={duration}")

    def log_gpu_detection(self, gpu_type: Optional[str], encoder: Optional[str]) -> None:
        """Log GPU detection result."""
        if gpu_type:
            self.info(f"GPU detected: type={gpu_type}, encoder={encoder}")
        else:
            self.info("No GPU acceleration available, using CPU encoding")

    def log_file_operation(self, operation: str, path: str, success: bool = True) -> None:
        """Log a file operation."""
        status = "OK" if success else "FAILED"
        self.debug(f"File {operation} [{status}]: {path}")

    def cleanup_old_logs(self, max_days: int = 7) -> int:
        """
        Remove log files older than max_days.

        Args:
            max_days: Maximum age of log files in days.

        Returns:
            Number of files removed.
        """
        if not self.DEFAULT_LOG_DIR.exists():
            return 0

        removed = 0
        cutoff = datetime.now().timestamp() - (max_days * 24 * 60 * 60)

        for log_file in self.DEFAULT_LOG_DIR.glob("video_musique_*.log"):
            try:
                if log_file.stat().st_mtime < cutoff:
                    log_file.unlink()
                    removed += 1
            except OSError:
                pass

        if removed > 0:
            self.info(f"Cleaned up {removed} old log file(s)")

        return removed

    @property
    def log_file_path(self) -> Optional[Path]:
        """Get the current log file path."""
        return self._log_file


# Global logger instance
_logger: Optional[Logger] = None


def get_logger() -> Logger:
    """Get the global logger instance."""
    global _logger
    if _logger is None:
        _logger = Logger()
    return _logger


# Convenience functions for module-level logging
def debug(message: str, *args, **kwargs) -> None:
    """Log a debug message."""
    get_logger().debug(message, *args, **kwargs)


def info(message: str, *args, **kwargs) -> None:
    """Log an info message."""
    get_logger().info(message, *args, **kwargs)


def warning(message: str, *args, **kwargs) -> None:
    """Log a warning message."""
    get_logger().warning(message, *args, **kwargs)


def error(message: str, *args, **kwargs) -> None:
    """Log an error message."""
    get_logger().error(message, *args, **kwargs)


def critical(message: str, *args, **kwargs) -> None:
    """Log a critical message."""
    get_logger().critical(message, *args, **kwargs)


def exception(message: str, *args, **kwargs) -> None:
    """Log an exception with traceback."""
    get_logger().exception(message, *args, **kwargs)
