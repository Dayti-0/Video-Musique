import { create } from 'zustand';
import { invoke } from '@tauri-apps/api/core';
import {
  AudioTrack,
  VideoClip,
  ProjectSettings,
  Project,
  GpuInfo,
  Dependencies,
  ExportResult,
  DEFAULT_SETTINGS,
  createAudioTrack,
  createVideoClip,
} from '../types';

interface AppState {
  // Media
  videos: VideoClip[];
  audioTracks: AudioTrack[];
  settings: ProjectSettings;

  // Status
  isExporting: boolean;
  exportProgress: number;
  isGeneratingPreview: boolean;
  statusMessage: string;

  // GPU Info
  gpuInfo: GpuInfo | null;
  dependencies: Dependencies | null;

  // Project
  currentProjectPath: string | null;
  hasUnsavedChanges: boolean;

  // Actions - Videos
  addVideos: (paths: string[]) => Promise<void>;
  removeVideo: (index: number) => void;
  moveVideo: (fromIndex: number, toIndex: number) => void;
  clearVideos: () => void;

  // Actions - Audio
  addAudioTracks: (paths: string[]) => Promise<void>;
  removeAudioTrack: (index: number) => void;
  updateAudioTrack: (index: number, updates: Partial<AudioTrack>) => void;
  moveAudioTrack: (fromIndex: number, toIndex: number) => void;
  clearAudioTracks: () => void;

  // Actions - Settings
  updateSettings: (updates: Partial<ProjectSettings>) => void;

  // Actions - Export
  startExport: (outputPath: string) => Promise<ExportResult>;
  cancelExport: () => void;
  setExportProgress: (progress: number) => void;

  // Actions - Preview
  generatePreview: (fullLength?: boolean) => Promise<string | null>;
  playPreview: (path: string) => Promise<void>;

  // Actions - Project
  newProject: () => void;
  saveProject: (path: string) => Promise<void>;
  loadProject: (path: string) => Promise<void>;
  setCurrentProjectPath: (path: string | null) => void;

  // Actions - System
  checkDependencies: () => Promise<void>;
  detectGpu: () => Promise<void>;
  setStatusMessage: (message: string) => void;
}

export const useStore = create<AppState>((set, get) => ({
  // Initial state
  videos: [],
  audioTracks: [],
  settings: DEFAULT_SETTINGS,
  isExporting: false,
  exportProgress: 0,
  isGeneratingPreview: false,
  statusMessage: '',
  gpuInfo: null,
  dependencies: null,
  currentProjectPath: null,
  hasUnsavedChanges: false,

  // Videos
  addVideos: async (paths) => {
    try {
      const durations = await invoke<number[]>('get_durations_parallel', { paths });
      const newVideos = paths.map((path, i) => createVideoClip(path, durations[i]));
      set((state) => ({
        videos: [...state.videos, ...newVideos],
        hasUnsavedChanges: true,
      }));
    } catch (error) {
      console.error('Erreur lors de l\'ajout des videos:', error);
    }
  },

  removeVideo: (index) => {
    set((state) => ({
      videos: state.videos.filter((_, i) => i !== index),
      hasUnsavedChanges: true,
    }));
  },

  moveVideo: (fromIndex, toIndex) => {
    set((state) => {
      const videos = [...state.videos];
      const [removed] = videos.splice(fromIndex, 1);
      videos.splice(toIndex, 0, removed);
      return { videos, hasUnsavedChanges: true };
    });
  },

  clearVideos: () => set({ videos: [], hasUnsavedChanges: true }),

  // Audio
  addAudioTracks: async (paths) => {
    try {
      const durations = await invoke<number[]>('get_durations_parallel', { paths });
      const newTracks = paths.map((path, i) => createAudioTrack(path, durations[i]));
      set((state) => ({
        audioTracks: [...state.audioTracks, ...newTracks],
        hasUnsavedChanges: true,
      }));
    } catch (error) {
      console.error('Erreur lors de l\'ajout des pistes audio:', error);
    }
  },

  removeAudioTrack: (index) => {
    set((state) => ({
      audioTracks: state.audioTracks.filter((_, i) => i !== index),
      hasUnsavedChanges: true,
    }));
  },

  updateAudioTrack: (index, updates) => {
    set((state) => ({
      audioTracks: state.audioTracks.map((track, i) =>
        i === index ? { ...track, ...updates } : track
      ),
      hasUnsavedChanges: true,
    }));
  },

  moveAudioTrack: (fromIndex, toIndex) => {
    set((state) => {
      const tracks = [...state.audioTracks];
      const [removed] = tracks.splice(fromIndex, 1);
      tracks.splice(toIndex, 0, removed);
      return { audioTracks: tracks, hasUnsavedChanges: true };
    });
  },

  clearAudioTracks: () => set({ audioTracks: [], hasUnsavedChanges: true }),

  // Settings
  updateSettings: (updates) => {
    set((state) => ({
      settings: { ...state.settings, ...updates },
      hasUnsavedChanges: true,
    }));
  },

  // Export
  startExport: async (outputPath) => {
    const { videos, audioTracks, settings } = get();
    set({ isExporting: true, exportProgress: 0, statusMessage: 'Export en cours...' });

    try {
      const project: Project = { videos, audio_tracks: audioTracks, settings };
      const result = await invoke<ExportResult>('export_project', {
        project,
        outputPath,
        useGpu: settings.use_gpu,
        speedPreset: settings.speed_preset,
      });

      set({
        isExporting: false,
        exportProgress: 100,
        statusMessage: result.success ? 'Export termine!' : (result.error || 'Erreur'),
      });

      return result;
    } catch (error) {
      set({ isExporting: false, statusMessage: `Erreur: ${error}` });
      throw error;
    }
  },

  cancelExport: () => {
    invoke('cancel_export');
    set({ isExporting: false, statusMessage: 'Export annule' });
  },

  setExportProgress: (progress) => set({ exportProgress: progress }),

  // Preview
  generatePreview: async (fullLength = false) => {
    const { videos, audioTracks, settings } = get();
    set({ isGeneratingPreview: true, statusMessage: 'Generation de la preview...' });

    try {
      const project: Project = { videos, audio_tracks: audioTracks, settings };
      const path = await invoke<string>('create_preview', {
        project,
        clipSeconds: fullLength ? null : 60,
      });

      set({ isGeneratingPreview: false, statusMessage: 'Preview generee' });
      return path;
    } catch (error) {
      set({ isGeneratingPreview: false, statusMessage: `Erreur: ${error}` });
      return null;
    }
  },

  playPreview: async (path) => {
    try {
      await invoke('play_preview', { path });
    } catch (error) {
      console.error('Erreur lors de la lecture:', error);
    }
  },

  // Project
  newProject: () => {
    set({
      videos: [],
      audioTracks: [],
      settings: DEFAULT_SETTINGS,
      currentProjectPath: null,
      hasUnsavedChanges: false,
      statusMessage: 'Nouveau projet',
    });
  },

  saveProject: async (path) => {
    const { videos, audioTracks, settings } = get();
    const project: Project = { videos, audio_tracks: audioTracks, settings };

    try {
      await invoke('save_project', { project, filePath: path });
      set({
        currentProjectPath: path,
        hasUnsavedChanges: false,
        statusMessage: 'Projet sauvegarde',
      });
    } catch (error) {
      set({ statusMessage: `Erreur de sauvegarde: ${error}` });
      throw error;
    }
  },

  loadProject: async (path) => {
    try {
      const project = await invoke<Project>('load_project', { filePath: path });
      set({
        videos: project.videos,
        audioTracks: project.audio_tracks,
        settings: project.settings,
        currentProjectPath: path,
        hasUnsavedChanges: false,
        statusMessage: 'Projet charge',
      });
    } catch (error) {
      set({ statusMessage: `Erreur de chargement: ${error}` });
      throw error;
    }
  },

  setCurrentProjectPath: (path) => set({ currentProjectPath: path }),

  // System
  checkDependencies: async () => {
    try {
      const deps = await invoke<Dependencies>('check_dependencies');
      set({ dependencies: deps });
    } catch (error) {
      console.error('Erreur lors de la verification des dependances:', error);
    }
  },

  detectGpu: async () => {
    try {
      const info = await invoke<GpuInfo>('get_gpu_info');
      set({ gpuInfo: info });
      if (info.available) {
        set({ statusMessage: `GPU detecte: ${info.gpu_type}` });
      }
    } catch (error) {
      console.error('Erreur lors de la detection GPU:', error);
    }
  },

  setStatusMessage: (message) => set({ statusMessage: message }),
}));
