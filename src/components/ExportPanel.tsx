import { useState } from 'react';
import { save } from '@tauri-apps/plugin-dialog';
import { useStore } from '../store/useStore';
import { getVideoDuration, formatDuration } from '../types';

type OutputFormat = 'mkv' | 'mp4' | 'webm';

const formatInfo: Record<OutputFormat, { label: string; description: string }> = {
  mkv: { label: 'MKV', description: 'Recommande - Meilleure compatibilite' },
  mp4: { label: 'MP4', description: 'Compatible partout' },
  webm: { label: 'WebM', description: 'Pour le web' },
};

function ExportPanel() {
  const {
    videos,
    settings,
    isExporting,
    exportProgress,
    isGeneratingPreview,
    startExport,
    cancelExport,
    generatePreview,
    playPreview,
    setStatusMessage,
  } = useStore();

  const [outputFormat, setOutputFormat] = useState<OutputFormat>('mkv');

  const totalDuration = getVideoDuration(videos, settings.video_crossfade);
  const canExport = videos.length > 0 && !isExporting && !isGeneratingPreview;

  const handleExport = async () => {
    try {
      const path = await save({
        filters: [{ name: formatInfo[outputFormat].label, extensions: [outputFormat] }],
        defaultPath: `export.${outputFormat}`,
      });

      if (path) {
        const result = await startExport(path);
        if (result.success) {
          setStatusMessage(
            `Export termine en ${result.duration_seconds.toFixed(1)}s (${result.encoder})`
          );
        } else if (result.cancelled) {
          setStatusMessage('Export annule');
        } else {
          setStatusMessage(`Erreur: ${result.error}`);
        }
      }
    } catch (error) {
      setStatusMessage(`Erreur: ${error}`);
    }
  };

  const handlePreview = async (fullLength: boolean) => {
    const path = await generatePreview(fullLength);
    if (path) {
      await playPreview(path);
    }
  };

  return (
    <div className="card flex flex-col">
      <h2 className="text-lg font-semibold mb-4">Export</h2>

      {videos.length === 0 ? (
        <div className="flex-1 flex items-center justify-center text-gray-400">
          <p>Ajoutez des videos pour exporter</p>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Duration info */}
          <div className="bg-dark-400 rounded-lg p-3">
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Duree totale</span>
              <span className="font-medium">{formatDuration(totalDuration)}</span>
            </div>
          </div>

          {/* Output format */}
          <div>
            <label className="text-sm block mb-2">Format de sortie</label>
            <div className="grid grid-cols-3 gap-2">
              {(Object.keys(formatInfo) as OutputFormat[]).map((format) => (
                <button
                  key={format}
                  onClick={() => setOutputFormat(format)}
                  className={`p-2 rounded-lg text-center transition-colors ${
                    outputFormat === format
                      ? 'bg-primary-500 text-white'
                      : 'bg-dark-400 text-gray-300 hover:bg-dark-300'
                  }`}
                >
                  <div className="font-medium">{formatInfo[format].label}</div>
                  <div className="text-xs opacity-75">{formatInfo[format].description}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Preview buttons */}
          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={() => handlePreview(false)}
              disabled={!canExport}
              className="btn btn-secondary"
            >
              {isGeneratingPreview ? 'Generation...' : 'Preview 60s'}
            </button>
            <button
              onClick={() => handlePreview(true)}
              disabled={!canExport}
              className="btn btn-secondary"
            >
              {isGeneratingPreview ? 'Generation...' : 'Preview complete'}
            </button>
          </div>

          {/* Export progress */}
          {isExporting && (
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>Export en cours...</span>
                <span>{Math.round(exportProgress)}%</span>
              </div>
              <div className="progress-bar">
                <div
                  className="progress-bar-fill"
                  style={{ width: `${exportProgress}%` }}
                />
              </div>
              <button onClick={cancelExport} className="btn btn-danger w-full">
                Annuler
              </button>
            </div>
          )}

          {/* Export button */}
          {!isExporting && (
            <button
              onClick={handleExport}
              disabled={!canExport}
              className="btn btn-success w-full text-lg py-3"
            >
              Exporter
            </button>
          )}
        </div>
      )}
    </div>
  );
}

export default ExportPanel;
