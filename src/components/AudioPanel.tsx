import { useCallback } from 'react';
import { open } from '@tauri-apps/plugin-dialog';
import { useStore } from '../store/useStore';
import { formatDuration, getMusicDuration, SUPPORTED_AUDIO_EXTENSIONS } from '../types';

function AudioPanel() {
  const {
    audioTracks,
    addAudioTracks,
    removeAudioTrack,
    updateAudioTrack,
    moveAudioTrack,
    clearAudioTracks,
    setStatusMessage,
  } = useStore();

  const handleAddTracks = async () => {
    try {
      const paths = await open({
        multiple: true,
        filters: [
          {
            name: 'Fichiers audio',
            extensions: SUPPORTED_AUDIO_EXTENSIONS.map((e) => e.slice(1)),
          },
        ],
      });
      if (paths && Array.isArray(paths)) {
        await addAudioTracks(paths);
      } else if (paths) {
        await addAudioTracks([paths]);
      }
    } catch (error) {
      setStatusMessage(`Erreur: ${error}`);
    }
  };

  const handleDrop = useCallback(
    async (e: React.DragEvent) => {
      e.preventDefault();
      const files = Array.from(e.dataTransfer.files);
      const audioPaths = files
        .filter((f) => SUPPORTED_AUDIO_EXTENSIONS.some((ext) => f.name.toLowerCase().endsWith(ext)))
        .map((f) => f.path);
      if (audioPaths.length > 0) {
        await addAudioTracks(audioPaths);
      }
    },
    [addAudioTracks]
  );

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.currentTarget.classList.add('active');
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.currentTarget.classList.remove('active');
  };

  const handleMoveUp = (index: number) => {
    if (index > 0) {
      moveAudioTrack(index, index - 1);
    }
  };

  const handleMoveDown = (index: number) => {
    if (index < audioTracks.length - 1) {
      moveAudioTrack(index, index + 1);
    }
  };

  const totalDuration = getMusicDuration(audioTracks);

  return (
    <div className="card flex-1 flex flex-col overflow-hidden">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-semibold">Musiques ({audioTracks.length})</h2>
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-400">Duree: {formatDuration(totalDuration)}</span>
          <button onClick={handleAddTracks} className="btn btn-primary text-sm">
            + Ajouter
          </button>
          {audioTracks.length > 0 && (
            <button onClick={clearAudioTracks} className="btn btn-danger text-sm">
              Vider
            </button>
          )}
        </div>
      </div>

      {audioTracks.length === 0 ? (
        <div
          className="drop-zone flex-1 flex items-center justify-center"
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
        >
          <div className="text-center">
            <div className="text-4xl mb-2 opacity-50">&#127925;</div>
            <p className="text-gray-400">Glissez des fichiers audio ici ou cliquez sur Ajouter</p>
            <p className="text-sm text-gray-500 mt-1">
              Formats: {SUPPORTED_AUDIO_EXTENSIONS.join(', ')}
            </p>
          </div>
        </div>
      ) : (
        <div
          className="media-list flex-1"
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
        >
          {audioTracks.map((track, index) => (
            <div
              key={`${track.path}-${index}`}
              className={`media-item group ${track.mute ? 'opacity-50' : ''}`}
            >
              <div className="flex flex-col gap-1">
                <button
                  onClick={() => handleMoveUp(index)}
                  disabled={index === 0}
                  className="text-gray-500 hover:text-white disabled:opacity-30 text-xs"
                >
                  &#9650;
                </button>
                <button
                  onClick={() => handleMoveDown(index)}
                  disabled={index === audioTracks.length - 1}
                  className="text-gray-500 hover:text-white disabled:opacity-30 text-xs"
                >
                  &#9660;
                </button>
              </div>

              <div className="w-8 h-8 bg-accent-success/20 rounded flex items-center justify-center text-accent-success">
                &#9835;
              </div>

              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{track.name}</p>
                <p className="text-xs text-gray-400">{formatDuration(track.duration)}</p>
              </div>

              {/* Volume slider */}
              <div className="flex items-center gap-2 w-32">
                <input
                  type="range"
                  min="0"
                  max="110"
                  value={track.volume * 100}
                  onChange={(e) =>
                    updateAudioTrack(index, { volume: parseInt(e.target.value) / 100 })
                  }
                  className="slider flex-1"
                />
                <span className="text-xs text-gray-400 w-8">
                  {Math.round(track.volume * 100)}%
                </span>
              </div>

              {/* Mute button */}
              <button
                onClick={() => updateAudioTrack(index, { mute: !track.mute })}
                className={`toggle-btn ${track.mute ? 'active bg-accent-error' : 'inactive'}`}
                title={track.mute ? 'Activer' : 'Muter'}
              >
                M
              </button>

              {/* Solo button */}
              <button
                onClick={() => updateAudioTrack(index, { solo: !track.solo })}
                className={`toggle-btn ${track.solo ? 'active bg-accent-warning' : 'inactive'}`}
                title={track.solo ? 'Desactiver solo' : 'Solo'}
              >
                S
              </button>

              <button
                onClick={() => removeAudioTrack(index)}
                className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-accent-error transition-opacity"
              >
                &#10005;
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default AudioPanel;
