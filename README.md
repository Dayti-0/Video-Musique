# Video-Musique

Application GUI moderne pour le mixage multi-vidéo / multi-audio avec support de l'accélération GPU.

## Fonctionnalités

- **Assemblage vidéo** : Combinez plusieurs clips vidéo avec des transitions crossfade
- **Mixage audio** : Superposez plusieurs pistes audio avec contrôle du volume
- **Contrôles avancés** : Mute, Solo, et volume par piste
- **Accélération GPU** : Support NVIDIA, AMD, Intel QSV et VAAPI
- **Prévisualisation** : Preview rapide (60s) ou complète
- **Export flexible** : MKV, MP4 ou WebM

## Prérequis

### Système
- Python 3.10 ou supérieur
- FFmpeg (ffmpeg, ffprobe, ffplay pour la preview)

### Installation de FFmpeg

**Linux (Debian/Ubuntu)**:
```bash
sudo apt update
sudo apt install ffmpeg
```

**Linux (Fedora)**:
```bash
sudo dnf install ffmpeg
```

**macOS (Homebrew)**:
```bash
brew install ffmpeg
```

**Windows**:
1. Téléchargez FFmpeg depuis [ffmpeg.org](https://ffmpeg.org/download.html)
2. Extrayez l'archive
3. Ajoutez le dossier `bin` à votre PATH

## Installation

1. **Cloner le dépôt**:
```bash
git clone https://github.com/Dayti-0/Video-Musique.git
cd Video-Musique
```

2. **Créer un environnement virtuel** (recommandé):
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# ou
venv\Scripts\activate     # Windows
```

3. **Installer les dépendances**:
```bash
pip install -r requirements.txt
```

4. **Lancer l'application**:
```bash
python main.py
```

Ou sous Windows, double-cliquez sur `start.bat`.

## Utilisation

### Ajouter des médias

1. Cliquez sur **"+ Ajouter"** dans le panneau Vidéos ou Musiques
2. Sélectionnez vos fichiers
3. Réorganisez l'ordre avec les boutons **↑** et **↓**

### Contrôles audio

- **Volume par piste** : Utilisez le slider après avoir sélectionné une piste
- **Mute (M)** : Désactive une piste
- **Solo (S)** : Joue uniquement les pistes en mode Solo

### Options

| Option | Description |
|--------|-------------|
| Audio des vidéos | Inclure l'audio original des vidéos |
| Musiques | Inclure les pistes audio ajoutées |
| Couper musique à la fin | Arrêter la musique à la fin de la vidéo |
| Cross-fade audio | Durée du fondu enchaîné audio (1-20s) |
| Cross-fade vidéo | Durée du fondu enchaîné vidéo (0-5s) |
| Accélération GPU | Utiliser le GPU pour l'encodage |
| Vitesse | Préréglage de vitesse d'encodage |

### Prévisualisation

- **Preview 60s** : Génère une prévisualisation des 60 premières secondes
- **Preview complet** : Génère une prévisualisation complète
- **Stop** : Arrête la prévisualisation en cours

### Export

1. Cliquez sur **"Exporter"**
2. Choisissez le format de sortie (MKV, MP4, WebM)
3. Sélectionnez l'emplacement de sauvegarde
4. Cliquez sur **"Annuler"** pour interrompre l'export si nécessaire

## Formats supportés

### Vidéo (entrée)
- MP4, MKV, MOV, AVI, WebM

### Audio (entrée)
- MP3, WAV, FLAC, AAC, OGG

### Export
- MKV (Matroska) - Recommandé
- MP4 (H.264/AAC)
- WebM (VP9/Vorbis)

## Accélération GPU

L'application détecte automatiquement le GPU disponible :

| GPU | Encodeur | Priorité |
|-----|----------|----------|
| NVIDIA | h264_nvenc | 1 (plus haute) |
| Intel | h264_qsv | 2 |
| AMD | h264_amf | 3 |
| VAAPI | h264_vaapi | 4 |

Si l'encodage GPU échoue, l'application bascule automatiquement sur l'encodage CPU.

## Fichiers de projet

Les projets sont sauvegardés au format `.mixproj` (JSON). Ils contiennent :
- Liste des vidéos et leurs chemins
- Liste des pistes audio avec volume/mute/solo
- Paramètres du projet

## Logs

Les fichiers de log sont stockés dans :
- **Linux/macOS** : `~/.video_musique/logs/`
- **Windows** : `%USERPROFILE%\.video_musique\logs\`

Les logs plus anciens que 7 jours sont automatiquement supprimés.

## Tests

Exécuter les tests :
```bash
pytest tests/ -v
```

Avec couverture :
```bash
pytest tests/ -v --cov=src --cov-report=term-missing
```

## Structure du projet

```
Video-Musique/
├── main.py                 # Point d'entrée
├── start.bat              # Lanceur Windows
├── requirements.txt       # Dépendances Python
├── README.md             # Documentation
├── src/
│   ├── core/
│   │   ├── models.py     # Modèles de données
│   │   ├── ffmpeg.py     # Opérations FFmpeg
│   │   └── config.py     # Configuration
│   ├── gui/
│   │   ├── app.py        # Application principale
│   │   ├── theme.py      # Thème visuel
│   │   └── widgets/      # Composants UI
│   └── utils/
│       ├── helpers.py    # Fonctions utilitaires
│       └── logger.py     # Système de logging
└── tests/                # Tests unitaires
```

## Dépannage

### FFmpeg non trouvé
Vérifiez que FFmpeg est installé et dans votre PATH :
```bash
ffmpeg -version
```

### Preview ne fonctionne pas
- Vérifiez que ffplay est installé
- Consultez les logs pour plus de détails

### Encodage GPU échoue
- Mettez à jour vos pilotes GPU
- Vérifiez que votre GPU supporte l'encodage H.264
- L'application basculera automatiquement sur CPU

### L'export est lent
- Activez l'accélération GPU si disponible
- Utilisez le préréglage "Rapide" au lieu de "Qualité"

## Licence

MIT License - Voir le fichier LICENSE pour plus de détails.

## Contribution

Les contributions sont les bienvenues ! N'hésitez pas à ouvrir une issue ou une pull request.
