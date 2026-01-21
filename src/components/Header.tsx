import { open, save } from '@tauri-apps/plugin-dialog';
import { useStore } from '../store/useStore';

function Header() {
  const {
    newProject,
    saveProject,
    loadProject,
    currentProjectPath,
    hasUnsavedChanges,
    setStatusMessage,
  } = useStore();

  const handleNew = async () => {
    if (hasUnsavedChanges) {
      const confirmed = window.confirm(
        'Vous avez des modifications non sauvegardees. Voulez-vous continuer?'
      );
      if (!confirmed) return;
    }
    newProject();
  };

  const handleOpen = async () => {
    try {
      const path = await open({
        filters: [{ name: 'Projets Video-Musique', extensions: ['mixproj'] }],
      });
      if (path) {
        await loadProject(path as string);
      }
    } catch (error) {
      setStatusMessage(`Erreur: ${error}`);
    }
  };

  const handleSave = async () => {
    try {
      if (currentProjectPath) {
        await saveProject(currentProjectPath);
      } else {
        await handleSaveAs();
      }
    } catch (error) {
      setStatusMessage(`Erreur: ${error}`);
    }
  };

  const handleSaveAs = async () => {
    try {
      const path = await save({
        filters: [{ name: 'Projets Video-Musique', extensions: ['mixproj'] }],
        defaultPath: 'projet.mixproj',
      });
      if (path) {
        await saveProject(path);
      }
    } catch (error) {
      setStatusMessage(`Erreur: ${error}`);
    }
  };

  const projectName = currentProjectPath
    ? currentProjectPath.split('/').pop()?.split('\\').pop() || 'Projet'
    : 'Nouveau projet';

  return (
    <header className="bg-dark-500 border-b border-dark-200 px-4 py-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h1 className="text-xl font-bold text-primary-500">Video-Musique</h1>
          <span className="text-gray-400 text-sm">
            {projectName}
            {hasUnsavedChanges && ' *'}
          </span>
        </div>

        <nav className="flex items-center gap-2">
          <button onClick={handleNew} className="btn btn-secondary text-sm">
            Nouveau
          </button>
          <button onClick={handleOpen} className="btn btn-secondary text-sm">
            Ouvrir
          </button>
          <button onClick={handleSave} className="btn btn-secondary text-sm">
            Sauvegarder
          </button>
          <button onClick={handleSaveAs} className="btn btn-secondary text-sm">
            Sauvegarder sous...
          </button>
        </nav>
      </div>
    </header>
  );
}

export default Header;
