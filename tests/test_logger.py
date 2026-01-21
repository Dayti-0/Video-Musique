"""
Tests for logging system
"""

import pytest
import tempfile
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.logger import Logger, get_logger


class TestLogger:
    """Tests for Logger class."""

    def test_singleton_pattern(self):
        """Test that Logger is a singleton."""
        logger1 = Logger()
        logger2 = Logger()
        assert logger1 is logger2

    def test_get_logger(self):
        """Test get_logger returns the same instance."""
        logger1 = get_logger()
        logger2 = get_logger()
        assert logger1 is logger2

    def test_set_level(self):
        """Test setting log level."""
        logger = get_logger()

        # Should not raise
        logger.set_level("debug")
        logger.set_level("info")
        logger.set_level("warning")
        logger.set_level("error")
        logger.set_level("critical")

    def test_log_methods_dont_raise(self):
        """Test that all log methods don't raise exceptions."""
        logger = get_logger()

        # These should not raise
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")

    def test_enable_file_logging(self):
        """Test enabling file logging."""
        logger = get_logger()

        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            log_file = logger.enable_file_logging(log_dir)

            assert log_file.exists()
            assert log_file.parent == log_dir
            assert "video_musique_" in log_file.name
            assert log_file.suffix == ".log"

    def test_log_file_content(self):
        """Test that logs are written to file."""
        # Create a fresh logger for this test
        logger = get_logger()

        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            log_file = logger.enable_file_logging(log_dir)

            test_message = f"Test message {datetime.now().isoformat()}"
            logger.info(test_message)

            # Read log file
            content = log_file.read_text()
            assert test_message in content

    def test_log_ffmpeg_command(self):
        """Test logging FFmpeg commands."""
        logger = get_logger()

        # Should not raise
        logger.log_ffmpeg_command(["ffmpeg", "-i", "input.mp4", "output.mkv"])

    def test_log_export_start(self):
        """Test logging export start."""
        logger = get_logger()

        # Should not raise
        logger.log_export_start("/output/video.mkv", use_gpu=True, preset="balanced")

    def test_log_export_complete(self):
        """Test logging export completion."""
        logger = get_logger()

        # Should not raise
        logger.log_export_complete("/output/video.mkv", duration_seconds=45.5, success=True)
        logger.log_export_complete("/output/video.mkv", duration_seconds=0.0, success=False)

    def test_log_preview_start(self):
        """Test logging preview start."""
        logger = get_logger()

        # Should not raise
        logger.log_preview_start(clip_seconds=60)
        logger.log_preview_start(clip_seconds=None)

    def test_log_gpu_detection(self):
        """Test logging GPU detection."""
        logger = get_logger()

        # Should not raise
        logger.log_gpu_detection("nvidia", "h264_nvenc")
        logger.log_gpu_detection(None, None)

    def test_log_file_operation(self):
        """Test logging file operations."""
        logger = get_logger()

        # Should not raise
        logger.log_file_operation("save", "/path/to/file.mixproj", success=True)
        logger.log_file_operation("load", "/path/to/file.mixproj", success=False)

    def test_cleanup_old_logs(self):
        """Test cleaning up old log files."""
        logger = get_logger()

        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)

            # Create some fake old log files
            old_time = datetime.now() - timedelta(days=10)

            for i in range(3):
                old_log = log_dir / f"video_musique_old_{i}.log"
                old_log.write_text(f"Old log {i}")
                # Set modification time to old date
                os.utime(old_log, (old_time.timestamp(), old_time.timestamp()))

            # Create a recent log file
            recent_log = log_dir / "video_musique_recent.log"
            recent_log.write_text("Recent log")

            # Temporarily change the default log directory
            original_log_dir = Logger.DEFAULT_LOG_DIR
            Logger.DEFAULT_LOG_DIR = log_dir

            try:
                removed = logger.cleanup_old_logs(max_days=7)
                assert removed == 3

                # Recent log should still exist
                assert recent_log.exists()
            finally:
                Logger.DEFAULT_LOG_DIR = original_log_dir

    def test_log_file_path_property(self):
        """Test log_file_path property."""
        logger = get_logger()

        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            log_file = logger.enable_file_logging(log_dir)

            assert logger.log_file_path == log_file


class TestModuleLevelFunctions:
    """Tests for module-level convenience functions."""

    def test_debug(self):
        """Test module-level debug function."""
        from src.utils.logger import debug
        # Should not raise
        debug("Debug message")

    def test_info(self):
        """Test module-level info function."""
        from src.utils.logger import info
        # Should not raise
        info("Info message")

    def test_warning(self):
        """Test module-level warning function."""
        from src.utils.logger import warning
        # Should not raise
        warning("Warning message")

    def test_error(self):
        """Test module-level error function."""
        from src.utils.logger import error
        # Should not raise
        error("Error message")

    def test_critical(self):
        """Test module-level critical function."""
        from src.utils.logger import critical
        # Should not raise
        critical("Critical message")

    def test_exception(self):
        """Test module-level exception function."""
        from src.utils.logger import exception

        try:
            raise ValueError("Test error")
        except ValueError:
            # Should not raise
            exception("Caught an exception")
