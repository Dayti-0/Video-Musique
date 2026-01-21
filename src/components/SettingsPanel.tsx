import { useStore } from '../store/useStore';
import type { SpeedPreset } from '../types';

function SettingsPanel() {
  const { settings, updateSettings, gpuInfo } = useStore();

  const speedPresetLabels: Record<SpeedPreset, string> = {
    ultrafast: 'Ultra-rapide',
    fast: 'Rapide',
    balanced: 'Equilibre',
    quality: 'Qualite',
  };

  return (
    <div className="card overflow-y-auto">
      <h2 className="text-lg font-semibold mb-4">Parametres</h2>

      <div className="space-y-4">
        {/* Audio settings */}
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider">Audio</h3>

          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={settings.include_video_audio}
              onChange={(e) => updateSettings({ include_video_audio: e.target.checked })}
              className="w-4 h-4 rounded bg-dark-500 border-dark-200 text-primary-500 focus:ring-primary-500"
            />
            <span>Inclure l'audio des videos</span>
          </label>

          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={settings.include_music}
              onChange={(e) => updateSettings({ include_music: e.target.checked })}
              className="w-4 h-4 rounded bg-dark-500 border-dark-200 text-primary-500 focus:ring-primary-500"
            />
            <span>Inclure les musiques</span>
          </label>

          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={settings.cut_music_at_end}
              onChange={(e) => updateSettings({ cut_music_at_end: e.target.checked })}
              className="w-4 h-4 rounded bg-dark-500 border-dark-200 text-primary-500 focus:ring-primary-500"
            />
            <span>Couper la musique a la fin de la video</span>
          </label>
        </div>

        {/* Volume controls */}
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider">Volumes</h3>

          <div>
            <div className="flex justify-between text-sm mb-1">
              <span>Volume video</span>
              <span className="text-gray-400">{Math.round(settings.video_volume)}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="110"
              value={settings.video_volume}
              onChange={(e) => updateSettings({ video_volume: parseInt(e.target.value) })}
              className="slider"
            />
          </div>

          <div>
            <div className="flex justify-between text-sm mb-1">
              <span>Volume musique</span>
              <span className="text-gray-400">{Math.round(settings.music_volume)}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="110"
              value={settings.music_volume}
              onChange={(e) => updateSettings({ music_volume: parseInt(e.target.value) })}
              className="slider"
            />
          </div>
        </div>

        {/* Crossfade settings */}
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider">
            Transitions
          </h3>

          <div>
            <div className="flex justify-between text-sm mb-1">
              <span>Fondu video</span>
              <span className="text-gray-400">{settings.video_crossfade.toFixed(1)}s</span>
            </div>
            <input
              type="range"
              min="0"
              max="5"
              step="0.1"
              value={settings.video_crossfade}
              onChange={(e) => updateSettings({ video_crossfade: parseFloat(e.target.value) })}
              className="slider"
            />
          </div>

          <div>
            <div className="flex justify-between text-sm mb-1">
              <span>Fondu audio</span>
              <span className="text-gray-400">{Math.round(settings.audio_crossfade)}s</span>
            </div>
            <input
              type="range"
              min="1"
              max="20"
              value={settings.audio_crossfade}
              onChange={(e) => updateSettings({ audio_crossfade: parseInt(e.target.value) })}
              className="slider"
            />
          </div>
        </div>

        {/* Performance settings */}
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider">
            Performance
          </h3>

          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={settings.use_gpu}
              onChange={(e) => updateSettings({ use_gpu: e.target.checked })}
              className="w-4 h-4 rounded bg-dark-500 border-dark-200 text-primary-500 focus:ring-primary-500"
            />
            <span>
              Utiliser le GPU
              {gpuInfo?.available && (
                <span className="text-accent-success text-xs ml-2">
                  ({gpuInfo.gpu_type?.toUpperCase()})
                </span>
              )}
              {gpuInfo && !gpuInfo.available && (
                <span className="text-gray-500 text-xs ml-2">(Non disponible)</span>
              )}
            </span>
          </label>

          <div>
            <label className="text-sm block mb-2">Preset de vitesse</label>
            <select
              value={settings.speed_preset}
              onChange={(e) => updateSettings({ speed_preset: e.target.value as SpeedPreset })}
              className="input w-full"
            >
              {(Object.keys(speedPresetLabels) as SpeedPreset[]).map((preset) => (
                <option key={preset} value={preset}>
                  {speedPresetLabels[preset]}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>
    </div>
  );
}

export default SettingsPanel;
