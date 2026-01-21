export interface AudioTrack {
  path: string;
  volume: number;
  name: string;
  duration: number;
  mute: boolean;
  solo: boolean;
}

export interface VideoClip {
  path: string;
  name: string;
  duration: number;
}

export interface ProjectSettings {
  include_video_audio: boolean;
  include_music: boolean;
  audio_crossfade: number;
  video_crossfade: number;
  cut_music_at_end: boolean;
  video_volume: number;
  music_volume: number;
  use_gpu: boolean;
  speed_preset: SpeedPreset;
}

export type SpeedPreset = 'ultrafast' | 'fast' | 'balanced' | 'quality';

export interface Project {
  videos: VideoClip[];
  audio_tracks: AudioTrack[];
  settings: ProjectSettings;
}

export interface GpuInfo {
  available: boolean;
  gpu_type: string | null;
  encoder: string | null;
}

export interface Dependencies {
  has_ffmpeg: boolean;
  has_ffprobe: boolean;
  has_ffplay: boolean;
}

export interface ExportResult {
  success: boolean;
  cancelled: boolean;
  error: string | null;
  encoder: string | null;
  gpu_accelerated: boolean;
  duration_seconds: number;
}

export interface Config {
  last_directory: string;
  theme: string;
  window_width: number;
  window_height: number;
  audio_crossfade: number;
  video_crossfade: number;
  music_volume: number;
  video_volume: number;
  use_gpu: boolean;
  speed_preset: SpeedPreset;
}

export const SUPPORTED_VIDEO_EXTENSIONS = ['.mp4', '.mkv', '.mov', '.avi', '.webm'];
export const SUPPORTED_AUDIO_EXTENSIONS = ['.mp3', '.wav', '.flac', '.aac', '.ogg'];

export const DEFAULT_SETTINGS: ProjectSettings = {
  include_video_audio: true,
  include_music: true,
  audio_crossfade: 10,
  video_crossfade: 1,
  cut_music_at_end: false,
  video_volume: 100,
  music_volume: 70,
  use_gpu: true,
  speed_preset: 'balanced',
};

export function createAudioTrack(path: string, duration: number = 0): AudioTrack {
  const name = path.split('/').pop() || path.split('\\').pop() || path;
  return {
    path,
    volume: 1.0,
    name,
    duration,
    mute: false,
    solo: false,
  };
}

export function createVideoClip(path: string, duration: number = 0): VideoClip {
  const name = path.split('/').pop() || path.split('\\').pop() || path;
  return {
    path,
    name,
    duration,
  };
}

export function getActiveTracks(tracks: AudioTrack[]): AudioTrack[] {
  if (tracks.length === 0) return [];

  const solos = tracks.filter((t) => t.solo);
  if (solos.length > 0) {
    return solos.filter((t) => !t.mute);
  }

  return tracks.filter((t) => !t.mute);
}

export function getVideoDuration(videos: VideoClip[], crossfade: number): number {
  if (videos.length === 0) return 0;

  const base = videos.reduce((sum, v) => sum + v.duration, 0);
  const overlap = crossfade * Math.max(videos.length - 1, 0);
  return Math.max(base - overlap, 0);
}

export function getMusicDuration(tracks: AudioTrack[]): number {
  return getActiveTracks(tracks).reduce((sum, t) => sum + t.duration, 0);
}

export function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);

  if (h > 0) {
    return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  }
  return `${m}:${s.toString().padStart(2, '0')}`;
}
