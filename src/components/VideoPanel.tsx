import { useCallback } from 'react';
import { open } from '@tauri-apps/plugin-dialog';
import { useStore } from '../store/useStore';
import { formatDuration, getVideoDuration, SUPPORTED_VIDEO_EXTENSIONS } from '../types';

function VideoPanel() {
  const { videos, addVideos, removeVideo, moveVideo, clearVideos, settings, setStatusMessage } =
    useStore();

  const handleAddVideos = async () => {
    try {
      const paths = await open({
        multiple: true,
        filters: [
          {
            name: 'Fichiers video',
            extensions: SUPPORTED_VIDEO_EXTENSIONS.map((e) => e.slice(1)),
          },
        ],
      });
      if (paths && Array.isArray(paths)) {
        await addVideos(paths);
      } else if (paths) {
        await addVideos([paths]);
      }
    } catch (error) {
      setStatusMessage(`Erreur: ${error}`);
    }
  };

  const handleDrop = useCallback(
    async (e: React.DragEvent) => {
      e.preventDefault();
      const files = Array.from(e.dataTransfer.files);
      const videoPaths = files
        .filter((f) => SUPPORTED_VIDEO_EXTENSIONS.some((ext) => f.name.toLowerCase().endsWith(ext)))
        .map((f) => f.path);
      if (videoPaths.length > 0) {
        await addVideos(videoPaths);
      }
    },
    [addVideos]
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
      moveVideo(index, index - 1);
    }
  };

  const handleMoveDown = (index: number) => {
    if (index < videos.length - 1) {
      moveVideo(index, index + 1);
    }
  };

  const totalDuration = getVideoDuration(videos, settings.video_crossfade);

  return (
    <div className="card flex-1 flex flex-col overflow-hidden">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-semibold">Videos ({videos.length})</h2>
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-400">Duree: {formatDuration(totalDuration)}</span>
          <button onClick={handleAddVideos} className="btn btn-primary text-sm">
            + Ajouter
          </button>
          {videos.length > 0 && (
            <button onClick={clearVideos} className="btn btn-danger text-sm">
              Vider
            </button>
          )}
        </div>
      </div>

      {videos.length === 0 ? (
        <div
          className="drop-zone flex-1 flex items-center justify-center"
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
        >
          <div className="text-center">
            <div className="text-4xl mb-2 opacity-50">&#128249;</div>
            <p className="text-gray-400">Glissez des videos ici ou cliquez sur Ajouter</p>
            <p className="text-sm text-gray-500 mt-1">
              Formats: {SUPPORTED_VIDEO_EXTENSIONS.join(', ')}
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
          {videos.map((video, index) => (
            <div key={`${video.path}-${index}`} className="media-item group">
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
                  disabled={index === videos.length - 1}
                  className="text-gray-500 hover:text-white disabled:opacity-30 text-xs"
                >
                  &#9660;
                </button>
              </div>

              <div className="w-8 h-8 bg-primary-500/20 rounded flex items-center justify-center text-primary-500">
                {index + 1}
              </div>

              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{video.name}</p>
                <p className="text-xs text-gray-400">{formatDuration(video.duration)}</p>
              </div>

              <button
                onClick={() => removeVideo(index)}
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

export default VideoPanel;
