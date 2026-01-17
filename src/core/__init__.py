"""
Core modules - Models, FFmpeg operations, Configuration
"""

from .models import AudioTrack, VideoClip
from .config import Config
from .ffmpeg import FFmpegProcessor

__all__ = ["AudioTrack", "VideoClip", "Config", "FFmpegProcessor"]
