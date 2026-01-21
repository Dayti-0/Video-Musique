use regex::Regex;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::Path;
use std::process::{Command, Stdio};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::time::Instant;
use tauri::{AppHandle, Emitter, State};

use crate::models::{AudioTrack, Project, VideoClip};
use crate::AppState;

static CANCEL_FLAG: AtomicBool = AtomicBool::new(false);

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GpuInfo {
    pub available: bool,
    pub gpu_type: Option<String>,
    pub encoder: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExportResult {
    pub success: bool,
    pub cancelled: bool,
    pub error: Option<String>,
    pub encoder: Option<String>,
    pub gpu_accelerated: bool,
    pub duration_seconds: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Dependencies {
    pub has_ffmpeg: bool,
    pub has_ffprobe: bool,
    pub has_ffplay: bool,
}

pub struct FFmpegProcessor {
    duration_cache: HashMap<String, f64>,
    available_gpu_encoder: Option<String>,
    gpu_checked: bool,
}

impl FFmpegProcessor {
    pub fn new() -> Self {
        Self {
            duration_cache: HashMap::new(),
            available_gpu_encoder: None,
            gpu_checked: false,
        }
    }

    fn check_command_exists(cmd: &str) -> bool {
        Command::new("which")
            .arg(cmd)
            .output()
            .map(|o| o.status.success())
            .unwrap_or(false)
    }

    pub fn check_dependencies(&self) -> Dependencies {
        Dependencies {
            has_ffmpeg: Self::check_command_exists("ffmpeg"),
            has_ffprobe: Self::check_command_exists("ffprobe"),
            has_ffplay: Self::check_command_exists("ffplay"),
        }
    }

    fn test_gpu_encoder(encoder: &str, gpu_type: &str) -> bool {
        let mut cmd = Command::new("ffmpeg");
        cmd.args(["-hide_banner", "-f", "lavfi", "-i", "color=black:s=256x256:d=0.1"]);

        if gpu_type == "vaapi" {
            cmd.args(["-vaapi_device", "/dev/dri/renderD128"]);
            cmd.args(["-vf", "format=nv12,hwupload"]);
        }

        cmd.args(["-c:v", encoder, "-f", "null", "-"]);
        cmd.stdout(Stdio::null()).stderr(Stdio::null());

        cmd.status().map(|s| s.success()).unwrap_or(false)
    }

    pub fn detect_gpu_encoder(&mut self) -> Option<String> {
        if self.gpu_checked {
            return self.available_gpu_encoder.clone();
        }

        self.gpu_checked = true;

        let output = Command::new("ffmpeg")
            .args(["-hide_banner", "-encoders"])
            .output()
            .ok()?;

        let encoders_output = String::from_utf8_lossy(&output.stdout);

        let checks = [
            ("nvidia", "h264_nvenc"),
            ("intel", "h264_qsv"),
            ("amd", "h264_amf"),
            ("vaapi", "h264_vaapi"),
        ];

        for (gpu_type, encoder_name) in checks {
            if encoders_output.contains(encoder_name) && Self::test_gpu_encoder(encoder_name, gpu_type) {
                self.available_gpu_encoder = Some(gpu_type.to_string());
                return Some(gpu_type.to_string());
            }
        }

        None
    }

    pub fn get_gpu_info(&mut self) -> GpuInfo {
        let gpu = self.detect_gpu_encoder();
        let encoder = gpu.as_ref().map(|g| match g.as_str() {
            "nvidia" => "h264_nvenc",
            "amd" => "h264_amf",
            "intel" => "h264_qsv",
            "vaapi" => "h264_vaapi",
            _ => "libx264",
        });

        GpuInfo {
            available: gpu.is_some(),
            gpu_type: gpu,
            encoder: encoder.map(String::from),
        }
    }

    fn get_cache_key(path: &str) -> String {
        let mtime = fs::metadata(path)
            .and_then(|m| m.modified())
            .map(|t| t.duration_since(std::time::UNIX_EPOCH).unwrap_or_default().as_secs())
            .unwrap_or(0);
        format!("{}:{}", path, mtime)
    }

    fn duration_ffprobe_quick(path: &str) -> Option<f64> {
        let output = Command::new("ffprobe")
            .args(["-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", path])
            .output()
            .ok()?;

        let out = String::from_utf8_lossy(&output.stdout).trim().to_string();
        if !out.is_empty() && out != "N/A" {
            out.parse().ok()
        } else {
            None
        }
    }

    fn duration_ffprobe_json(path: &str) -> Option<f64> {
        let output = Command::new("ffprobe")
            .args(["-v", "error", "-print_format", "json", "-show_entries", "format=duration,stream=duration", path])
            .output()
            .ok()?;

        let json: serde_json::Value = serde_json::from_slice(&output.stdout).ok()?;

        if let Some(dur) = json.get("format").and_then(|f| f.get("duration")).and_then(|d| d.as_str()) {
            if dur != "N/A" {
                return dur.parse().ok();
            }
        }

        if let Some(streams) = json.get("streams").and_then(|s| s.as_array()) {
            for stream in streams {
                if let Some(dur) = stream.get("duration").and_then(|d| d.as_str()) {
                    if dur != "N/A" {
                        if let Ok(d) = dur.parse::<f64>() {
                            return Some(d);
                        }
                    }
                }
            }
        }

        None
    }

    pub fn get_duration(&mut self, path: &str) -> f64 {
        if !Path::new(path).exists() {
            return 0.0;
        }

        let cache_key = Self::get_cache_key(path);
        if let Some(&duration) = self.duration_cache.get(&cache_key) {
            return duration;
        }

        let duration = Self::duration_ffprobe_quick(path)
            .or_else(|| Self::duration_ffprobe_json(path))
            .unwrap_or(0.0);

        self.duration_cache.insert(cache_key, duration);
        duration
    }

    pub fn get_durations_parallel(&mut self, paths: Vec<String>) -> Vec<f64> {
        paths.iter().map(|p| self.get_duration(p)).collect()
    }
}

// Tauri commands

#[tauri::command]
pub fn check_dependencies(state: State<'_, AppState>) -> Dependencies {
    state.ffmpeg.lock().unwrap().check_dependencies()
}

#[tauri::command]
pub fn detect_gpu_encoder(state: State<'_, AppState>) -> Option<String> {
    state.ffmpeg.lock().unwrap().detect_gpu_encoder()
}

#[tauri::command]
pub fn get_duration(state: State<'_, AppState>, path: String) -> f64 {
    state.ffmpeg.lock().unwrap().get_duration(&path)
}

#[tauri::command]
pub fn get_durations_parallel(state: State<'_, AppState>, paths: Vec<String>) -> Vec<f64> {
    state.ffmpeg.lock().unwrap().get_durations_parallel(paths)
}

#[tauri::command]
pub fn get_gpu_info(state: State<'_, AppState>) -> GpuInfo {
    state.ffmpeg.lock().unwrap().get_gpu_info()
}

fn get_encoder_config(gpu_type: &str) -> (&'static str, Option<&'static str>, HashMap<&'static str, &'static str>) {
    let mut presets = HashMap::new();
    match gpu_type {
        "nvidia" => {
            presets.insert("ultrafast", "p1");
            presets.insert("fast", "p4");
            presets.insert("balanced", "p5");
            presets.insert("quality", "p7");
            ("h264_nvenc", Some("-preset"), presets)
        }
        "amd" => {
            presets.insert("ultrafast", "speed");
            presets.insert("fast", "balanced");
            presets.insert("balanced", "balanced");
            presets.insert("quality", "quality");
            ("h264_amf", Some("-quality"), presets)
        }
        "intel" => {
            presets.insert("ultrafast", "veryfast");
            presets.insert("fast", "fast");
            presets.insert("balanced", "medium");
            presets.insert("quality", "veryslow");
            ("h264_qsv", Some("-preset"), presets)
        }
        "vaapi" => ("h264_vaapi", None, presets),
        _ => {
            presets.insert("ultrafast", "ultrafast");
            presets.insert("fast", "veryfast");
            presets.insert("balanced", "medium");
            presets.insert("quality", "slow");
            ("libx264", Some("-preset"), presets)
        }
    }
}

fn build_audio_crossfade_filter(tracks: &[AudioTrack], crossfade_duration: i32, base_input_index: usize) -> (String, String) {
    let n = tracks.len();
    let mut parts: Vec<String> = tracks
        .iter()
        .enumerate()
        .map(|(i, t)| {
            let vol = if t.mute { 0.0 } else { t.volume.min(1.1) };
            format!("[{}:a]volume={}[ma{}]", base_input_index + i, vol, i)
        })
        .collect();

    if n == 1 {
        return (parts.join(";"), "[ma0]".to_string());
    }

    let mut prev = "ma0".to_string();
    for j in 1..n {
        let cur = format!("ma{}", j);
        let out = format!("mx{}", j);
        parts.push(format!(
            "[{}][{}]acrossfade=d={}:c1=qsin:c2=qsin[{}]",
            prev, cur, crossfade_duration, out
        ));
        prev = out;
    }

    (parts.join(";"), format!("[{}]", prev))
}

fn build_video_crossfade_filter(clips: &[VideoClip], crossfade_duration: f64) -> (String, String, String) {
    let n = clips.len();
    let mut parts: Vec<String> = Vec::new();

    for i in 0..n {
        parts.push(format!("[{}:v]format=yuv420p,setsar=1[v{}]", i, i));
        parts.push(format!("[{}:a]anull[va{}]", i, i));
    }

    if n == 1 {
        return (parts.join(";"), "[v0]".to_string(), "[va0]".to_string());
    }

    let mut acc = clips[0].duration;
    let mut prev_v = "v0".to_string();
    let mut prev_a = "va0".to_string();

    for j in 1..n {
        let off = (acc - crossfade_duration).max(0.0);
        let vo = format!("vx{}", j);
        let ao = format!("vax{}", j);
        parts.push(format!(
            "[{}][v{}]xfade=transition=fade:duration={}:offset={}[{}]",
            prev_v, j, crossfade_duration, off, vo
        ));
        parts.push(format!(
            "[{}][va{}]acrossfade=d={}:c1=qsin:c2=qsin[{}]",
            prev_a, j, crossfade_duration, ao
        ));
        prev_v = vo;
        prev_a = ao;
        acc += (clips[j].duration - crossfade_duration).max(0.0);
    }

    (parts.join(";"), format!("[{}]", prev_v), format!("[{}]", prev_a))
}

#[tauri::command]
pub fn build_export_command(
    state: State<'_, AppState>,
    project: Project,
    output_path: String,
    preview_seconds: Option<i32>,
    use_gpu: bool,
    speed_preset: String,
) -> Vec<String> {
    let mut ffmpeg = state.ffmpeg.lock().unwrap();
    let settings = &project.settings;

    let active_tracks: Vec<&AudioTrack> = if settings.include_music {
        let solos: Vec<_> = project.audio_tracks.iter().filter(|t| t.solo).collect();
        if !solos.is_empty() {
            solos.into_iter().filter(|t| !t.mute).collect()
        } else {
            project.audio_tracks.iter().filter(|t| !t.mute).collect()
        }
    } else {
        vec![]
    };

    let video_volume = settings.video_volume / 100.0;
    let gpu_type = if use_gpu { ffmpeg.detect_gpu_encoder() } else { None };

    let mut cmd = vec!["ffmpeg".to_string(), "-y".to_string()];

    // Hardware acceleration flags
    if let Some(ref gt) = gpu_type {
        match gt.as_str() {
            "nvidia" => cmd.extend(["-hwaccel".to_string(), "cuda".to_string()]),
            "intel" => cmd.extend(["-hwaccel".to_string(), "qsv".to_string()]),
            "vaapi" => cmd.extend(["-vaapi_device".to_string(), "/dev/dri/renderD128".to_string()]),
            _ => {}
        }
    }

    // Add inputs
    for v in &project.videos {
        cmd.extend(["-i".to_string(), v.path.clone()]);
    }
    for t in &active_tracks {
        cmd.extend(["-i".to_string(), t.path.clone()]);
    }

    // Build filter complex
    let mut fc_parts: Vec<String> = Vec::new();
    let must_reencode = project.videos.len() > 1 || settings.video_crossfade > 0.0;

    let (vfc, tag_vout, tag_vaout) = build_video_crossfade_filter(&project.videos, settings.video_crossfade);
    fc_parts.push(vfc);
    fc_parts.push(format!("{}volume={}[va]", tag_vaout, video_volume));

    let mut tag_music = String::new();
    if !active_tracks.is_empty() {
        let base_idx = project.videos.len();
        let owned_tracks: Vec<AudioTrack> = active_tracks.iter().map(|t| (*t).clone()).collect();
        let (cf, tm) = build_audio_crossfade_filter(&owned_tracks, settings.audio_crossfade as i32, base_idx);
        fc_parts.push(cf);
        tag_music = tm;

        if settings.cut_music_at_end {
            let video_duration = project.get_video_duration();
            fc_parts.push(format!("{}atrim=duration={}[mus]", tag_music, video_duration));
            tag_music = "[mus]".to_string();
        }
    }

    // Audio mixing
    let tag_final_audio = if settings.include_video_audio && !tag_music.is_empty() {
        fc_parts.push(format!(
            "[va]{}amix=inputs=2:duration=longest:dropout_transition=0[aout]",
            tag_music
        ));
        "[aout]".to_string()
    } else if settings.include_video_audio {
        "[va]".to_string()
    } else if !tag_music.is_empty() {
        tag_music.clone()
    } else {
        String::new()
    };

    if !fc_parts.is_empty() {
        cmd.extend(["-filter_complex".to_string(), fc_parts.join(";")]);
    }

    // Mapping
    cmd.extend(["-map".to_string(), if !tag_vout.is_empty() { tag_vout } else { "0:v:0".to_string() }]);
    if !tag_final_audio.is_empty() {
        cmd.extend(["-map".to_string(), tag_final_audio]);
    } else {
        cmd.push("-an".to_string());
    }

    // Codecs
    if output_path.to_lowercase().ends_with(".webm") {
        cmd.extend(["-c:v".to_string(), "libvpx-vp9".to_string(), "-b:v".to_string(), "0".to_string(), "-crf".to_string(), "30".to_string()]);
        cmd.extend(["-c:a".to_string(), "libvorbis".to_string()]);
    } else {
        if must_reencode {
            let effective_preset = if preview_seconds.is_some() { "ultrafast" } else { &speed_preset };

            if let Some(ref gt) = gpu_type {
                let (encoder, preset_flag, presets) = get_encoder_config(gt);
                cmd.extend(["-c:v".to_string(), encoder.to_string()]);

                if let (Some(flag), Some(preset_val)) = (preset_flag, presets.get(effective_preset)) {
                    cmd.extend([flag.to_string(), preset_val.to_string()]);
                }

                match gt.as_str() {
                    "nvidia" => cmd.extend(["-rc".to_string(), "vbr".to_string(), "-cq".to_string(), "20".to_string(), "-b:v".to_string(), "0".to_string()]),
                    "amd" => cmd.extend(["-rc".to_string(), "vbr_latency".to_string(), "-qp_p".to_string(), "20".to_string(), "-qp_i".to_string(), "20".to_string()]),
                    "intel" => cmd.extend(["-global_quality".to_string(), "20".to_string(), "-look_ahead".to_string(), "1".to_string()]),
                    _ => cmd.extend(["-qp".to_string(), "20".to_string()]),
                }
            } else {
                let (encoder, preset_flag, presets) = get_encoder_config("cpu");
                cmd.extend(["-c:v".to_string(), encoder.to_string()]);
                if let (Some(flag), Some(preset_val)) = (preset_flag, presets.get(effective_preset)) {
                    cmd.extend([flag.to_string(), preset_val.to_string()]);
                }
                cmd.extend(["-crf".to_string(), "20".to_string()]);
            }
        } else {
            cmd.extend(["-c:v".to_string(), "copy".to_string()]);
        }

        cmd.extend(["-c:a".to_string(), "aac".to_string(), "-b:a".to_string(), "192k".to_string()]);
    }

    if let Some(secs) = preview_seconds {
        cmd.extend(["-t".to_string(), secs.to_string()]);
    }

    cmd.push(output_path);
    cmd
}

#[tauri::command]
pub async fn export_project(
    app: AppHandle,
    state: State<'_, AppState>,
    project: Project,
    output_path: String,
    use_gpu: bool,
    speed_preset: String,
) -> Result<ExportResult, String> {
    CANCEL_FLAG.store(false, Ordering::SeqCst);
    let start_time = Instant::now();

    let gpu_type = {
        let mut ffmpeg = state.ffmpeg.lock().unwrap();
        if use_gpu { ffmpeg.detect_gpu_encoder() } else { None }
    };

    let encoder = gpu_type.as_ref().map(|g| match g.as_str() {
        "nvidia" => "h264_nvenc",
        "amd" => "h264_amf",
        "intel" => "h264_qsv",
        "vaapi" => "h264_vaapi",
        _ => "libx264",
    }).unwrap_or("libx264");

    let mut cmd = build_export_command(
        state.clone(),
        project.clone(),
        output_path.clone(),
        None,
        use_gpu,
        speed_preset,
    );
    cmd.extend(["-progress".to_string(), "pipe:1".to_string(), "-nostats".to_string()]);

    let total_ms = project.get_video_duration() * 1000.0;
    let time_regex = Regex::new(r"out_time_ms=(\d+)").unwrap();

    let mut child = Command::new(&cmd[0])
        .args(&cmd[1..])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("Impossible de lancer ffmpeg: {}", e))?;

    let stdout = child.stdout.take().unwrap();
    let reader = std::io::BufReader::new(stdout);

    use std::io::BufRead;
    for line in reader.lines().map_while(Result::ok) {
        if CANCEL_FLAG.load(Ordering::SeqCst) {
            let _ = child.kill();
            if Path::new(&output_path).exists() {
                let _ = fs::remove_file(&output_path);
            }
            return Ok(ExportResult {
                success: false,
                cancelled: true,
                error: None,
                encoder: Some(encoder.to_string()),
                gpu_accelerated: gpu_type.is_some(),
                duration_seconds: start_time.elapsed().as_secs_f64(),
            });
        }

        if let Some(caps) = time_regex.captures(&line) {
            if let Ok(pos) = caps[1].parse::<f64>() {
                let progress = (pos / total_ms * 100.0).min(100.0);
                let _ = app.emit("export-progress", progress);
            }
        }
    }

    let status = child.wait().map_err(|e| e.to_string())?;

    Ok(ExportResult {
        success: status.success(),
        cancelled: false,
        error: if status.success() { None } else { Some(format!("FFmpeg a termine avec le code {}", status.code().unwrap_or(-1))) },
        encoder: Some(encoder.to_string()),
        gpu_accelerated: gpu_type.is_some(),
        duration_seconds: start_time.elapsed().as_secs_f64(),
    })
}

#[tauri::command]
pub fn cancel_export() {
    CANCEL_FLAG.store(true, Ordering::SeqCst);
}

#[tauri::command]
pub async fn create_preview(
    state: State<'_, AppState>,
    project: Project,
    clip_seconds: Option<i32>,
) -> Result<String, String> {
    let temp_dir = std::env::temp_dir();
    let temp_path = temp_dir.join(format!("preview_{}.mkv", std::process::id()));
    let temp_path_str = temp_path.to_string_lossy().to_string();

    let cmd = build_export_command(
        state,
        project,
        temp_path_str.clone(),
        clip_seconds.or(Some(60)),
        true,
        "ultrafast".to_string(),
    );

    let status = Command::new(&cmd[0])
        .args(&cmd[1..])
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .map_err(|e| format!("Impossible de lancer ffmpeg: {}", e))?;

    if status.success() {
        Ok(temp_path_str)
    } else {
        Err("La generation de la preview a echoue".to_string())
    }
}

#[tauri::command]
pub fn play_preview(path: String) -> Result<(), String> {
    Command::new("ffplay")
        .args(["-autoexit", "-loglevel", "quiet", "-window_title", "Preview", &path])
        .spawn()
        .map_err(|e| format!("Impossible de lancer ffplay: {}", e))?;
    Ok(())
}
