mod ffmpeg;
mod models;

use std::sync::Mutex;
use tauri::Manager;

pub struct AppState {
    pub ffmpeg: Mutex<ffmpeg::FFmpegProcessor>,
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            app.manage(AppState {
                ffmpeg: Mutex::new(ffmpeg::FFmpegProcessor::new()),
            });
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            ffmpeg::check_dependencies,
            ffmpeg::detect_gpu_encoder,
            ffmpeg::get_duration,
            ffmpeg::get_durations_parallel,
            ffmpeg::get_gpu_info,
            ffmpeg::build_export_command,
            ffmpeg::export_project,
            ffmpeg::create_preview,
            ffmpeg::play_preview,
            ffmpeg::cancel_export,
            models::save_project,
            models::load_project,
            models::get_config,
            models::set_config,
        ])
        .run(tauri::generate_context!())
        .expect("Erreur lors du lancement de l'application");
}
