"""
Tests for data models
"""

import pytest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.models import AudioTrack, VideoClip, ProjectSettings, Project


class TestAudioTrack:
    """Tests for AudioTrack model."""

    def test_create_audio_track(self):
        """Test creating an audio track with default values."""
        track = AudioTrack(path="/path/to/audio.mp3")

        assert track.path == "/path/to/audio.mp3"
        assert track.volume == 1.0
        assert track.name == "audio.mp3"
        assert track.duration == 0.0
        assert track.mute is False
        assert track.solo is False

    def test_create_audio_track_with_values(self):
        """Test creating an audio track with custom values."""
        track = AudioTrack(
            path="/path/to/music.wav",
            volume=0.8,
            name="Custom Name",
            duration=180.5,
            mute=True,
            solo=False
        )

        assert track.path == "/path/to/music.wav"
        assert track.volume == 0.8
        assert track.name == "Custom Name"
        assert track.duration == 180.5
        assert track.mute is True
        assert track.solo is False

    def test_get_effective_volume_normal(self):
        """Test effective volume when not muted."""
        track = AudioTrack(path="/test.mp3", volume=0.7)
        assert track.get_effective_volume() == 0.7

    def test_get_effective_volume_muted(self):
        """Test effective volume when muted."""
        track = AudioTrack(path="/test.mp3", volume=0.7, mute=True)
        assert track.get_effective_volume() == 0.0

    def test_get_effective_volume_capped(self):
        """Test effective volume is capped at 1.1."""
        track = AudioTrack(path="/test.mp3", volume=1.5)
        assert track.get_effective_volume() == 1.1

    def test_to_dict(self):
        """Test serialization to dictionary."""
        track = AudioTrack(
            path="/test.mp3",
            volume=0.8,
            name="Test",
            mute=True,
            solo=True
        )
        data = track.to_dict()

        assert data["path"] == "/test.mp3"
        assert data["volume"] == 0.8
        assert data["name"] == "Test"
        assert data["mute"] is True
        assert data["solo"] is True

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "path": "/test.mp3",
            "volume": 0.9,
            "name": "Loaded Track",
            "mute": False,
            "solo": True
        }
        track = AudioTrack.from_dict(data, duration=120.0)

        assert track.path == "/test.mp3"
        assert track.volume == 0.9
        assert track.name == "Loaded Track"
        assert track.duration == 120.0
        assert track.mute is False
        assert track.solo is True

    def test_from_dict_with_defaults(self):
        """Test deserialization with missing optional fields."""
        data = {"path": "/test.mp3"}
        track = AudioTrack.from_dict(data)

        assert track.path == "/test.mp3"
        assert track.volume == 1.0
        assert track.mute is False
        assert track.solo is False

    def test_from_dict_volume_capped(self):
        """Test volume is capped when loading from dict."""
        data = {"path": "/test.mp3", "volume": 2.0}
        track = AudioTrack.from_dict(data)
        assert track.volume == 1.1


class TestVideoClip:
    """Tests for VideoClip model."""

    def test_create_video_clip(self):
        """Test creating a video clip with default values."""
        clip = VideoClip(path="/path/to/video.mp4")

        assert clip.path == "/path/to/video.mp4"
        assert clip.name == "video.mp4"
        assert clip.duration == 0.0

    def test_create_video_clip_with_values(self):
        """Test creating a video clip with custom values."""
        clip = VideoClip(
            path="/path/to/movie.mkv",
            name="Custom Video",
            duration=3600.0
        )

        assert clip.path == "/path/to/movie.mkv"
        assert clip.name == "Custom Video"
        assert clip.duration == 3600.0

    def test_to_dict(self):
        """Test serialization to dictionary."""
        clip = VideoClip(path="/test.mp4", name="Test Video")
        data = clip.to_dict()

        assert data["path"] == "/test.mp4"
        assert data["name"] == "Test Video"

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {"path": "/test.mp4", "name": "Loaded Video"}
        clip = VideoClip.from_dict(data, duration=300.0)

        assert clip.path == "/test.mp4"
        assert clip.name == "Loaded Video"
        assert clip.duration == 300.0


class TestProjectSettings:
    """Tests for ProjectSettings model."""

    def test_default_settings(self):
        """Test default settings values."""
        settings = ProjectSettings()

        assert settings.include_video_audio is True
        assert settings.include_music is True
        assert settings.audio_crossfade == 10.0
        assert settings.video_crossfade == 1.0
        assert settings.cut_music_at_end is False
        assert settings.video_volume == 100.0
        assert settings.music_volume == 70.0
        assert settings.use_gpu is True
        assert settings.speed_preset == "balanced"

    def test_custom_settings(self):
        """Test custom settings values."""
        settings = ProjectSettings(
            include_video_audio=False,
            include_music=True,
            audio_crossfade=5.0,
            video_crossfade=2.0,
            cut_music_at_end=True,
            video_volume=80.0,
            music_volume=60.0,
            use_gpu=False,
            speed_preset="quality"
        )

        assert settings.include_video_audio is False
        assert settings.audio_crossfade == 5.0
        assert settings.video_crossfade == 2.0
        assert settings.cut_music_at_end is True
        assert settings.video_volume == 80.0
        assert settings.use_gpu is False
        assert settings.speed_preset == "quality"

    def test_to_dict(self):
        """Test serialization to dictionary."""
        settings = ProjectSettings(audio_crossfade=8.0, use_gpu=False)
        data = settings.to_dict()

        assert data["cross_fade_audio"] == 8.0
        assert data["use_gpu"] is False

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "video_audio": False,
            "music_audio": True,
            "cross_fade_audio": 15.0,
            "cross_fade_video": 3.0,
            "cut_music": True,
            "video_volume": 90.0,
            "music_volume": 50.0,
            "use_gpu": True,
            "speed_preset": "fast"
        }
        settings = ProjectSettings.from_dict(data)

        assert settings.include_video_audio is False
        assert settings.audio_crossfade == 15.0
        assert settings.video_crossfade == 3.0
        assert settings.cut_music_at_end is True
        assert settings.video_volume == 90.0
        assert settings.music_volume == 50.0
        assert settings.speed_preset == "fast"

    def test_from_dict_volume_capped(self):
        """Test volumes are capped when loading from dict."""
        data = {"video_volume": 200.0, "music_volume": 150.0}
        settings = ProjectSettings.from_dict(data)

        assert settings.video_volume == 110.0
        assert settings.music_volume == 110.0


class TestProject:
    """Tests for Project model."""

    def test_empty_project(self):
        """Test creating an empty project."""
        project = Project()

        assert len(project.videos) == 0
        assert len(project.audio_tracks) == 0
        assert isinstance(project.settings, ProjectSettings)

    def test_get_active_tracks_no_tracks(self):
        """Test getting active tracks when there are none."""
        project = Project()
        assert project.get_active_tracks() == []

    def test_get_active_tracks_normal(self):
        """Test getting active tracks without solo/mute."""
        project = Project(audio_tracks=[
            AudioTrack(path="/a.mp3"),
            AudioTrack(path="/b.mp3"),
        ])

        active = project.get_active_tracks()
        assert len(active) == 2

    def test_get_active_tracks_with_mute(self):
        """Test muted tracks are excluded."""
        project = Project(audio_tracks=[
            AudioTrack(path="/a.mp3", mute=True),
            AudioTrack(path="/b.mp3"),
        ])

        active = project.get_active_tracks()
        assert len(active) == 1
        assert active[0].path == "/b.mp3"

    def test_get_active_tracks_with_solo(self):
        """Test solo tracks are the only ones included."""
        project = Project(audio_tracks=[
            AudioTrack(path="/a.mp3", solo=True),
            AudioTrack(path="/b.mp3"),
            AudioTrack(path="/c.mp3", solo=True),
        ])

        active = project.get_active_tracks()
        assert len(active) == 2
        assert all(t.solo for t in active)

    def test_get_active_tracks_solo_muted(self):
        """Test solo tracks that are muted are excluded."""
        project = Project(audio_tracks=[
            AudioTrack(path="/a.mp3", solo=True, mute=True),
            AudioTrack(path="/b.mp3", solo=True),
        ])

        active = project.get_active_tracks()
        assert len(active) == 1
        assert active[0].path == "/b.mp3"

    def test_get_video_duration_empty(self):
        """Test video duration with no videos."""
        project = Project()
        assert project.get_video_duration() == 0.0

    def test_get_video_duration_single(self):
        """Test video duration with single video."""
        project = Project(videos=[VideoClip(path="/v.mp4", duration=120.0)])
        assert project.get_video_duration() == 120.0

    def test_get_video_duration_multiple(self):
        """Test video duration with multiple videos and crossfade."""
        project = Project(
            videos=[
                VideoClip(path="/v1.mp4", duration=100.0),
                VideoClip(path="/v2.mp4", duration=100.0),
                VideoClip(path="/v3.mp4", duration=100.0),
            ],
            settings=ProjectSettings(video_crossfade=2.0)
        )

        # Total: 300 - (2 crossfades * 2s) = 296
        assert project.get_video_duration() == 296.0

    def test_get_music_duration_empty(self):
        """Test music duration with no tracks."""
        project = Project()
        assert project.get_music_duration() == 0.0

    def test_get_music_duration_with_tracks(self):
        """Test music duration calculation."""
        project = Project(audio_tracks=[
            AudioTrack(path="/a.mp3", duration=180.0),
            AudioTrack(path="/b.mp3", duration=120.0),
        ])

        assert project.get_music_duration() == 300.0

    def test_to_dict(self):
        """Test full project serialization."""
        project = Project(
            videos=[VideoClip(path="/v.mp4", name="Video")],
            audio_tracks=[AudioTrack(path="/a.mp3", name="Audio")],
        )

        data = project.to_dict()

        assert len(data["videos"]) == 1
        assert len(data["audio_tracks"]) == 1
        assert "settings" in data
