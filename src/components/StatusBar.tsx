import { useStore } from '../store/useStore';

function StatusBar() {
  const { statusMessage, gpuInfo, dependencies, videos, audioTracks } = useStore();

  return (
    <footer className="bg-dark-500 border-t border-dark-200 px-4 py-2">
      <div className="flex items-center justify-between text-sm">
        <div className="flex items-center gap-4">
          {/* Status message */}
          <span className="text-gray-400">{statusMessage || 'Pret'}</span>
        </div>

        <div className="flex items-center gap-4">
          {/* Media count */}
          <span className="text-gray-500">
            {videos.length} video{videos.length !== 1 ? 's' : ''} | {audioTracks.length} piste
            {audioTracks.length !== 1 ? 's' : ''} audio
          </span>

          {/* GPU status */}
          {gpuInfo && (
            <span
              className={`flex items-center gap-1 ${
                gpuInfo.available ? 'text-accent-success' : 'text-gray-500'
              }`}
            >
              <span className="w-2 h-2 rounded-full bg-current" />
              {gpuInfo.available ? `GPU: ${gpuInfo.gpu_type?.toUpperCase()}` : 'CPU'}
            </span>
          )}

          {/* FFmpeg status */}
          {dependencies && (
            <span
              className={`flex items-center gap-1 ${
                dependencies.has_ffmpeg ? 'text-accent-success' : 'text-accent-error'
              }`}
            >
              <span className="w-2 h-2 rounded-full bg-current" />
              FFmpeg {dependencies.has_ffmpeg ? 'OK' : 'Manquant'}
            </span>
          )}
        </div>
      </div>
    </footer>
  );
}

export default StatusBar;
