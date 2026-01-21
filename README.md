# Video-Musique

Application desktop moderne pour le mixage multi-video / multi-audio avec support de l'acceleration GPU.

**Version 2.0** - Reecrite en TypeScript + Tauri pour de meilleures performances et une interface utilisateur moderne.

## Fonctionnalites

- **Assemblage video** : Combinez plusieurs clips video avec des transitions crossfade
- **Mixage audio** : Superposez plusieurs pistes audio avec controle du volume
- **Controles avances** : Mute, Solo, et volume par piste
- **Acceleration GPU** : Support NVIDIA, AMD, Intel QSV et VAAPI
- **Previsualisation** : Preview rapide (60s) ou complete
- **Export flexible** : MKV, MP4 ou WebM
- **Interface moderne** : Theme sombre elegant avec Tailwind CSS
- **Performance native** : Backend Rust via Tauri

## Stack technique

| Composant | Technologie |
|-----------|-------------|
| Frontend | React 18 + TypeScript |
| UI | Tailwind CSS |
| Backend | Rust (Tauri 2.0) |
| Etat | Zustand |
| Build | Vite |

## Prerequis

### Systeme
- Node.js 18+ et npm
- Rust (pour le build)
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
1. Telechargez FFmpeg depuis [ffmpeg.org](https://ffmpeg.org/download.html)
2. Extrayez l'archive
3. Ajoutez le dossier `bin` a votre PATH

### Installation de Rust

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

## Installation

1. **Cloner le depot**:
```bash
git clone https://github.com/Dayti-0/Video-Musique.git
cd Video-Musique
```

2. **Installer les dependances**:
```bash
npm install
```

3. **Lancer en mode developpement**:
```bash
npm run tauri dev
```

4. **Construire l'application**:
```bash
npm run tauri build
```

## Utilisation

### Ajouter des medias

1. Cliquez sur **"+ Ajouter"** dans le panneau Videos ou Musiques
2. Selectionnez vos fichiers
3. Reorganisez l'ordre avec les boutons de deplacement

### Controles audio

- **Volume par piste** : Utilisez le slider pour ajuster le volume (0-110%)
- **Mute (M)** : Desactive une piste
- **Solo (S)** : Joue uniquement les pistes en mode Solo

### Parametres

| Option | Description |
|--------|-------------|
| Audio des videos | Inclure l'audio original des videos |
| Musiques | Inclure les pistes audio ajoutees |
| Couper musique a la fin | Arreter la musique a la fin de la video |
| Cross-fade audio | Duree du fondu enchaine audio (1-20s) |
| Cross-fade video | Duree du fondu enchaine video (0-5s) |
| Acceleration GPU | Utiliser le GPU pour l'encodage |
| Vitesse | Prereglage de vitesse d'encodage |

### Previsualisation

- **Preview 60s** : Genere une previsualisation des 60 premieres secondes
- **Preview complete** : Genere une previsualisation complete

### Export

1. Choisissez le format de sortie (MKV, MP4, WebM)
2. Cliquez sur **"Exporter"**
3. Selectionnez l'emplacement de sauvegarde
4. Cliquez sur **"Annuler"** pour interrompre l'export si necessaire

## Formats supportes

### Video (entree)
- MP4, MKV, MOV, AVI, WebM

### Audio (entree)
- MP3, WAV, FLAC, AAC, OGG

### Export
- MKV (Matroska) - Recommande
- MP4 (H.264/AAC)
- WebM (VP9/Vorbis)

## Acceleration GPU

L'application detecte automatiquement le GPU disponible :

| GPU | Encodeur | Priorite |
|-----|----------|----------|
| NVIDIA | h264_nvenc | 1 (plus haute) |
| Intel | h264_qsv | 2 |
| AMD | h264_amf | 3 |
| VAAPI | h264_vaapi | 4 |

Si l'encodage GPU echoue, l'application bascule automatiquement sur l'encodage CPU.

## Fichiers de projet

Les projets sont sauvegardes au format `.mixproj` (JSON). Ils contiennent :
- Liste des videos et leurs chemins
- Liste des pistes audio avec volume/mute/solo
- Parametres du projet

## Structure du projet

```
Video-Musique/
├── package.json           # Dependances npm
├── vite.config.ts        # Configuration Vite
├── tailwind.config.js    # Configuration Tailwind
├── tsconfig.json         # Configuration TypeScript
├── index.html            # Point d'entree HTML
├── src/
│   ├── main.tsx          # Point d'entree React
│   ├── App.tsx           # Composant principal
│   ├── components/       # Composants React
│   │   ├── Header.tsx
│   │   ├── VideoPanel.tsx
│   │   ├── AudioPanel.tsx
│   │   ├── SettingsPanel.tsx
│   │   ├── ExportPanel.tsx
│   │   └── StatusBar.tsx
│   ├── store/
│   │   └── useStore.ts   # Store Zustand
│   ├── types/
│   │   └── index.ts      # Types TypeScript
│   └── styles/
│       └── index.css     # Styles Tailwind
└── src-tauri/
    ├── Cargo.toml        # Dependances Rust
    ├── tauri.conf.json   # Configuration Tauri
    └── src/
        ├── main.rs       # Point d'entree Rust
        ├── lib.rs        # Module principal
        ├── ffmpeg.rs     # Operations FFmpeg
        └── models.rs     # Modeles de donnees
```

## Depannage

### FFmpeg non trouve
Verifiez que FFmpeg est installe et dans votre PATH :
```bash
ffmpeg -version
```

### Preview ne fonctionne pas
- Verifiez que ffplay est installe
- Consultez la console pour plus de details

### Encodage GPU echoue
- Mettez a jour vos pilotes GPU
- Verifiez que votre GPU supporte l'encodage H.264
- L'application basculera automatiquement sur CPU

### L'export est lent
- Activez l'acceleration GPU si disponible
- Utilisez le prereglage "Rapide" au lieu de "Qualite"

## Scripts npm

| Commande | Description |
|----------|-------------|
| `npm run dev` | Lance le serveur de developpement |
| `npm run build` | Build le frontend |
| `npm run tauri dev` | Lance l'app en mode developpement |
| `npm run tauri build` | Build l'application pour la distribution |

## Licence

MIT License - Voir le fichier LICENSE pour plus de details.

## Contribution

Les contributions sont les bienvenues ! N'hesitez pas a ouvrir une issue ou une pull request.
