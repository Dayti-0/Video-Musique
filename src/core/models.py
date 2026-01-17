"""
Data models for Video-Musique
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class AudioTrack:
    """Represents an audio track with its properties."""

    path: str
    volume: float = 1.0
    name: str = ""
    duration: float = 0.0
    mute: bool = False
    solo: bool = False

    def __post_init__(self):
        if not self.name:
            self.name = Path(self.path).name

    def get_effective_volume(self) -> float:
        """Return the effective volume considering mute state."""
        if self.mute:
            return 0.0
        return min(self.volume, 1.1)

    def to_dict(self) -> dict:
        """Serialize to dictionary for project saving."""
        return {
            "path": self.path,
            "volume": self.volume,
            "name": self.name,
            "mute": self.mute,
            "solo": self.solo
        }

    @classmethod
    def from_dict(cls, data: dict, duration: float = 0.0) -> AudioTrack:
        """Create from dictionary."""
        return cls(
            path=data["path"],
            volume=min(data.get("volume", 1.0), 1.1),
            name=data.get("name", ""),
            duration=duration,
            mute=bool(data.get("mute", False)),
            solo=bool(data.get("solo", False))
        )


@dataclass
class VideoClip:
    """Represents a video clip with its properties."""

    path: str
    name: str = ""
    duration: float = 0.0

    def __post_init__(self):
        if not self.name:
            self.name = Path(self.path).name

    def to_dict(self) -> dict:
        """Serialize to dictionary for project saving."""
        return {
            "path": self.path,
            "name": self.name
        }

    @classmethod
    def from_dict(cls, data: dict, duration: float = 0.0) -> VideoClip:
        """Create from dictionary."""
        return cls(
            path=data["path"],
            name=data.get("name", ""),
            duration=duration
        )


@dataclass
class ProjectSettings:
    """Project settings for export and preview."""

    include_video_audio: bool = True
    include_music: bool = True
    audio_crossfade: float = 10.0
    video_crossfade: float = 1.0
    cut_music_at_end: bool = False
    video_volume: float = 100.0
    music_volume: float = 70.0
    # Performance settings
    use_gpu: bool = True
    speed_preset: str = "balanced"  # ultrafast, fast, balanced, quality

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "video_audio": self.include_video_audio,
            "music_audio": self.include_music,
            "cross_fade_audio": self.audio_crossfade,
            "cross_fade_video": self.video_crossfade,
            "cut_music": self.cut_music_at_end,
            "video_volume": self.video_volume,
            "music_volume": self.music_volume,
            "use_gpu": self.use_gpu,
            "speed_preset": self.speed_preset,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ProjectSettings:
        """Create from dictionary."""
        return cls(
            include_video_audio=data.get("video_audio", True),
            include_music=data.get("music_audio", True),
            audio_crossfade=data.get("cross_fade_audio", 10.0),
            video_crossfade=data.get("cross_fade_video", 1.0),
            cut_music_at_end=data.get("cut_music", False),
            video_volume=min(data.get("video_volume", 100.0), 110.0),
            music_volume=min(data.get("music_volume", 70.0), 110.0),
            use_gpu=data.get("use_gpu", True),
            speed_preset=data.get("speed_preset", "balanced"),
        )


@dataclass
class Project:
    """Complete project state."""

    videos: list[VideoClip] = field(default_factory=list)
    audio_tracks: list[AudioTrack] = field(default_factory=list)
    settings: ProjectSettings = field(default_factory=ProjectSettings)

    def get_active_tracks(self) -> list[AudioTrack]:
        """Get audio tracks that should be included (respecting mute/solo)."""
        if not self.audio_tracks:
            return []

        solos = [t for t in self.audio_tracks if t.solo]
        if solos:
            return [t for t in solos if not t.mute]

        return [t for t in self.audio_tracks if not t.mute]

    def get_video_duration(self) -> float:
        """Calculate total video duration with crossfades."""
        if not self.videos:
            return 0.0

        base = sum(v.duration for v in self.videos)
        overlap = self.settings.video_crossfade * max(len(self.videos) - 1, 0)
        return max(base - overlap, 0.0)

    def get_music_duration(self) -> float:
        """Calculate total active music duration."""
        active = self.get_active_tracks()
        if not active:
            return 0.0
        return sum(t.duration for t in active)

    def to_dict(self) -> dict:
        """Serialize entire project."""
        return {
            "videos": [v.to_dict() for v in self.videos],
            "audio_tracks": [t.to_dict() for t in self.audio_tracks],
            "settings": self.settings.to_dict()
        }
