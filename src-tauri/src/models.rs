use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AudioTrack {
    pub path: String,
    #[serde(default = "default_volume")]
    pub volume: f64,
    #[serde(default)]
    pub name: String,
    #[serde(default)]
    pub duration: f64,
    #[serde(default)]
    pub mute: bool,
    #[serde(default)]
    pub solo: bool,
}

fn default_volume() -> f64 {
    1.0
}

impl AudioTrack {
    pub fn get_effective_volume(&self) -> f64 {
        if self.mute {
            0.0
        } else {
            self.volume.min(1.1)
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VideoClip {
    pub path: String,
    #[serde(default)]
    pub name: String,
    #[serde(default)]
    pub duration: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProjectSettings {
    #[serde(default = "default_true")]
    pub include_video_audio: bool,
    #[serde(default = "default_true")]
    pub include_music: bool,
    #[serde(default = "default_audio_crossfade")]
    pub audio_crossfade: f64,
    #[serde(default = "default_video_crossfade")]
    pub video_crossfade: f64,
    #[serde(default)]
    pub cut_music_at_end: bool,
    #[serde(default = "default_video_volume")]
    pub video_volume: f64,
    #[serde(default = "default_music_volume")]
    pub music_volume: f64,
    #[serde(default = "default_true")]
    pub use_gpu: bool,
    #[serde(default = "default_speed_preset")]
    pub speed_preset: String,
}

fn default_true() -> bool { true }
fn default_audio_crossfade() -> f64 { 10.0 }
fn default_video_crossfade() -> f64 { 1.0 }
fn default_video_volume() -> f64 { 100.0 }
fn default_music_volume() -> f64 { 70.0 }
fn default_speed_preset() -> String { "balanced".to_string() }

impl Default for ProjectSettings {
    fn default() -> Self {
        Self {
            include_video_audio: true,
            include_music: true,
            audio_crossfade: 10.0,
            video_crossfade: 1.0,
            cut_music_at_end: false,
            video_volume: 100.0,
            music_volume: 70.0,
            use_gpu: true,
            speed_preset: "balanced".to_string(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Project {
    #[serde(default)]
    pub videos: Vec<VideoClip>,
    #[serde(default)]
    pub audio_tracks: Vec<AudioTrack>,
    #[serde(default)]
    pub settings: ProjectSettings,
}

impl Default for Project {
    fn default() -> Self {
        Self {
            videos: Vec::new(),
            audio_tracks: Vec::new(),
            settings: ProjectSettings::default(),
        }
    }
}

impl Project {
    pub fn get_active_tracks(&self) -> Vec<&AudioTrack> {
        if self.audio_tracks.is_empty() {
            return vec![];
        }

        let solos: Vec<_> = self.audio_tracks.iter().filter(|t| t.solo).collect();
        if !solos.is_empty() {
            solos.into_iter().filter(|t| !t.mute).collect()
        } else {
            self.audio_tracks.iter().filter(|t| !t.mute).collect()
        }
    }

    pub fn get_video_duration(&self) -> f64 {
        if self.videos.is_empty() {
            return 0.0;
        }

        let base: f64 = self.videos.iter().map(|v| v.duration).sum();
        let overlap = self.settings.video_crossfade * (self.videos.len() as f64 - 1.0).max(0.0);
        (base - overlap).max(0.0)
    }

    pub fn get_music_duration(&self) -> f64 {
        self.get_active_tracks().iter().map(|t| t.duration).sum()
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    #[serde(default = "default_last_directory")]
    pub last_directory: String,
    #[serde(default = "default_theme")]
    pub theme: String,
    #[serde(default = "default_window_width")]
    pub window_width: i32,
    #[serde(default = "default_window_height")]
    pub window_height: i32,
    #[serde(default = "default_audio_crossfade")]
    pub audio_crossfade: f64,
    #[serde(default = "default_video_crossfade")]
    pub video_crossfade: f64,
    #[serde(default = "default_music_volume")]
    pub music_volume: f64,
    #[serde(default = "default_video_volume")]
    pub video_volume: f64,
    #[serde(default = "default_true")]
    pub use_gpu: bool,
    #[serde(default = "default_speed_preset")]
    pub speed_preset: String,
}

fn default_last_directory() -> String {
    dirs::home_dir().map(|p| p.to_string_lossy().to_string()).unwrap_or_default()
}
fn default_theme() -> String { "modern".to_string() }
fn default_window_width() -> i32 { 1100 }
fn default_window_height() -> i32 { 700 }

impl Default for Config {
    fn default() -> Self {
        Self {
            last_directory: default_last_directory(),
            theme: "modern".to_string(),
            window_width: 1100,
            window_height: 700,
            audio_crossfade: 10.0,
            video_crossfade: 1.0,
            music_volume: 70.0,
            video_volume: 100.0,
            use_gpu: true,
            speed_preset: "balanced".to_string(),
        }
    }
}

fn get_config_path() -> PathBuf {
    dirs::home_dir().unwrap_or_default().join(".video_musique_config.json")
}

// Tauri commands

#[tauri::command]
pub fn save_project(project: Project, file_path: String) -> Result<(), String> {
    let json = serde_json::to_string_pretty(&project).map_err(|e| e.to_string())?;
    fs::write(&file_path, json).map_err(|e| format!("Impossible de sauvegarder le projet: {}", e))
}

#[tauri::command]
pub fn load_project(file_path: String) -> Result<Project, String> {
    let content = fs::read_to_string(&file_path).map_err(|e| format!("Impossible de charger le projet: {}", e))?;
    serde_json::from_str(&content).map_err(|e| format!("Format de projet invalide: {}", e))
}

#[tauri::command]
pub fn get_config() -> Config {
    let config_path = get_config_path();
    if config_path.exists() {
        fs::read_to_string(&config_path)
            .ok()
            .and_then(|s| serde_json::from_str(&s).ok())
            .unwrap_or_default()
    } else {
        Config::default()
    }
}

#[tauri::command]
pub fn set_config(config: Config) -> Result<(), String> {
    let config_path = get_config_path();
    let json = serde_json::to_string_pretty(&config).map_err(|e| e.to_string())?;
    fs::write(&config_path, json).map_err(|e| format!("Impossible de sauvegarder la configuration: {}", e))
}
