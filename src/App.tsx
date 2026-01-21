import { useEffect } from 'react';
import { listen } from '@tauri-apps/api/event';
import { useStore } from './store/useStore';
import Header from './components/Header';
import VideoPanel from './components/VideoPanel';
import AudioPanel from './components/AudioPanel';
import SettingsPanel from './components/SettingsPanel';
import ExportPanel from './components/ExportPanel';
import StatusBar from './components/StatusBar';

function App() {
  const { checkDependencies, detectGpu, setExportProgress, dependencies } = useStore();

  useEffect(() => {
    // Initialize
    checkDependencies();
    detectGpu();

    // Listen for export progress
    const unlisten = listen<number>('export-progress', (event) => {
      setExportProgress(event.payload);
    });

    return () => {
      unlisten.then((fn) => fn());
    };
  }, [checkDependencies, detectGpu, setExportProgress]);

  // Check if FFmpeg is available
  if (dependencies && !dependencies.has_ffmpeg) {
    return (
      <div className="h-full flex items-center justify-center bg-dark-400">
        <div className="card max-w-md text-center">
          <div className="text-4xl mb-4">!</div>
          <h1 className="text-xl font-bold mb-2">FFmpeg non trouve</h1>
          <p className="text-gray-400 mb-4">
            Video-Musique necessite FFmpeg pour fonctionner. Veuillez installer FFmpeg et
            redemarrer l'application.
          </p>
          <a
            href="https://ffmpeg.org/download.html"
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-primary"
          >
            Telecharger FFmpeg
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-dark-400">
      <Header />

      <main className="flex-1 overflow-hidden p-4">
        <div className="h-full grid grid-cols-12 gap-4">
          {/* Left column - Media panels */}
          <div className="col-span-7 flex flex-col gap-4 overflow-hidden">
            <VideoPanel />
            <AudioPanel />
          </div>

          {/* Right column - Settings and Export */}
          <div className="col-span-5 flex flex-col gap-4 overflow-hidden">
            <SettingsPanel />
            <ExportPanel />
          </div>
        </div>
      </main>

      <StatusBar />
    </div>
  );
}

export default App;
