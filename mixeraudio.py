#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Muxer Audio/Video – multi-vidéos + multi-pistes audio
• Cross-fade musiques réglable (1-20 s, défaut 10 s)
• Cross-fade vidéo léger entre clips (défaut 1 s)
• Pré-écoute 60 s (ffplay) ou pré-écoute complète (lecteur système)
• Chronomètre + barre de progression + carré vert animé
• Thème clair uniquement, infobulles, volumes individuels (max 110 %)
• Mute / Solo par piste, sauvegarde/chargement projet (JSON)
© 2025 – MIT
"""
from __future__ import annotations

import contextlib
import json
import os
import re
import shutil
import signal
import statistics
import subprocess
import sys
import tempfile
import threading
import time
import wave
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# ───────── paramètres ─────────
DEFAULT_CROSS_FADE_AUDIO = 10      # s
CROSS_MAX_AUDIO          = 20      # Spinbox max
DEFAULT_CROSS_FADE_VIDEO = 1.0     # s (léger fondu vidéo)
TIME_STEP_MS             = 500     # rafraîchissement chrono (ms)
CONFIG_FILE              = Path.home() / ".mixer_config.json"
time_rx                  = re.compile(r"out_time_ms=(\d+)")

# ───────── nettoyage fichiers temporaires ─────────
def cleanup_temp_files():
    """Nettoie les fichiers temporaires créés par l'application (heuristique simple)."""
    temp_dir = tempfile.gettempdir()
    try:
        for file in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, file)
            if os.path.isfile(file_path) and file.endswith(".mkv") and file.startswith("tmp"):
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"Impossible de supprimer {file_path}: {e}")
    except Exception as e:
        print(f"Erreur pendant le nettoyage des fichiers temporaires: {e}")

# ───────── data classes ─────────
@dataclass
class AudioTrack:
    path: str
    volume: float = 1.0
    name: str = ""
    duration: float = 0.0
    mute: bool = False
    solo: bool = False
    def __post_init__(self):
        if not self.name:
            self.name = Path(self.path).name
        if self.duration == 0.0:
            self.duration = ffprobe_duration(self.path)

@dataclass
class VideoClip:
    path: str
    name: str = ""
    duration: float = 0.0
    def __post_init__(self):
        if not self.name:
            self.name = Path(self.path).name
        if self.duration == 0.0:
            self.duration = ffprobe_duration(self.path)

# ───────── utilitaires ─────────
def _sexagesimal(s: str) -> float:
    """convertit 'HH:MM:SS.xx' en secondes"""
    try:
        h, m, sec = s.split(":")
        return int(h) * 3600 + int(m) * 60 + float(sec)
    except Exception:
        return 0.0

def ffprobe_duration(path: str) -> float:
    """
    Durée d'un média en secondes.
    • ffprobe (duration) -> ffprobe JSON -> mutagen -> wave -> parse ffmpeg
    • Retourne 0.0 si indéterminable
    """
    if not os.path.exists(path):
        print(f"Le fichier n'existe pas: {path}")
        return 0.0

    # 1) ffprobe rapide
    cmd1 = ["ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=nw=1:nk=1", path]
    try:
        out = subprocess.check_output(cmd1, text=True, stderr=subprocess.STDOUT).strip()
        if out and out != "N/A":
            duration = float(out)
            if duration > 0:
                return duration
            print(f"ffprobe rapide: Durée nulle pour {path} ({out})")
    except Exception as e:
        print(f"ffprobe rapide a échoué pour {path}: {e}")

    # 2) ffprobe JSON
    cmd2 = ["ffprobe", "-v", "error", "-print_format", "json",
            "-show_entries", "format=duration,stream=duration,stream_tags",
            path]
    try:
        result = subprocess.check_output(cmd2, text=True, stderr=subprocess.STDOUT)
        js = json.loads(result or "{}")
        durations = []

        fdur = js.get("format", {}).get("duration")
        if fdur and fdur != "N/A":
            durations.append(float(fdur))

        for s in js.get("streams", []):
            sd = s.get("duration")
            if sd and sd != "N/A":
                durations.append(float(sd))
            tag_dur = s.get("tags", {}).get("DURATION")
            if tag_dur:
                durations.append(_sexagesimal(tag_dur))

        if durations:
            max_duration = max(durations)
            if max_duration > 0:
                return max_duration
            print(f"ffprobe JSON: Durations trouvées mais nulles pour {path}: {durations}")
        else:
            print(f"ffprobe JSON: Aucune durée trouvée pour {path}")
    except Exception as e:
        print(f"ffprobe JSON a échoué pour {path}: {e}")

    # 3) mutagen (si dispo)
    try:
        from mutagen import File as MutagenFile
        m = MutagenFile(path)
        if m and m.info and hasattr(m.info, "length"):
            duration = float(m.info.length)
            if duration > 0:
                return duration
            print(f"Mutagen: Durée nulle pour {path}")
    except ImportError:
        print("Mutagen n'est pas disponible")
    except Exception as e:
        print(f"Mutagen a échoué pour {path}: {e}")

    # 4) wave pour .wav
    if path.lower().endswith(".wav"):
        try:
            with contextlib.closing(wave.open(path, "rb")) as w:
                frames, rate = w.getnframes(), w.getframerate()
                if rate:
                    duration = frames / float(rate)
                    if duration > 0:
                        return duration
                    print(f"Wave: Durée nulle pour {path} ({frames}/{rate})")
        except Exception as e:
            print(f"Lecture Wave a échoué pour {path}: {e}")

    # 5) Dernière tentative : sortie ffmpeg
    try:
        cmd = ["ffmpeg", "-i", path, "-f", "null", "-"]
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
        duration_match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", output)
        if duration_match:
            h, m, s = map(float, duration_match.groups())
            return h * 3600 + m * 60 + s
    except Exception as e:
        print(f"Dernière tentative (ffmpeg) a échoué pour {path}: {e}")

    print(f"Impossible de déterminer la durée de {path}")
    return 0.0

def fmt(sec: float | int) -> str:
    sec = int(round(sec)); m, s = divmod(sec, 60); h, m = divmod(m, 60)
    return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:d}:{s:02d}"

def format_size(size_bytes: int) -> str:
    if size_bytes < 1024:            return f"{size_bytes} B"
    if size_bytes < 1024 ** 2:       return f"{size_bytes/1024:.1f} KB"
    if size_bytes < 1024 ** 3:       return f"{size_bytes/1024**2:.1f} MB"
    return f"{size_bytes/1024**3:.2f} GB"

def create_tooltip(widget, text):
    tip = tk.Label(widget.master, text=text, relief="solid", borderwidth=1,
                   background="#ffffe0", font=("Segoe UI", 8))
    widget.bind("<Enter>", lambda _:
        (tip.lift(), tip.place(x=widget.winfo_rootx()+25, y=widget.winfo_rooty()+25)))
    widget.bind("<Leave>", lambda _: tip.place_forget())

def build_crossfade_filter(tracks: List[AudioTrack], dur: int, base_input_index: int) -> tuple[str, str]:
    """
    Construit la partie filter_complex pour N pistes audio (cross-fade en chaîne).
    base_input_index : index du premier -i correspondant à la 1ère piste musique.
    Retourne (fc_str, tag_final)
    """
    n = len(tracks)
    parts = [f"[{base_input_index + i}:a]volume={min(tracks[i].volume, 1.1)}[ma{i}]" for i in range(n)]
    if n == 1:
        return ";".join(parts), "[ma0]"
    prev = "ma0"
    for j in range(1, n):
        cur, out = f"ma{j}", f"mx{j}"
        parts.append(f"[{prev}][{cur}]acrossfade=d={dur}:c1=qsin:c2=qsin[{out}]")
        prev = out
    return ";".join(parts), f"[{prev}]"

def build_video_xfade_filter(vclips: List[VideoClip], dvid: float) -> tuple[str, str, str]:
    """
    Construit le filter_complex pour les vidéos:
    - normalise les flux vidéo en yuv420p
    - chaîne xfade=transition=fade:duration=dvid:offset=...
    - chaîne audio parallèle en acrossfade d=dvid
    Retourne (fc_str, tag_video_final, tag_videoaudio_final)
    """
    n = len(vclips)
    parts = []
    # Prépare labels de base
    for i in range(n):
        parts.append(f"[{i}:v]format=yuv420p,setsar=1[v{i}]")
        parts.append(f"[{i}:a]anull[va{i}]")

    if n == 1:
        return ";".join(parts), "[v0]", "[va0]"

    # Chaînage avec offsets
    acc = vclips[0].duration  # durée cumulée du 1er (sans fondu)
    prev_v, prev_a = "v0", "va0"
    for j in range(1, n):
        off = max(acc - dvid, 0.0)
        vo, ao = f"vx{j}", f"vax{j}"
        parts.append(f"[{prev_v}][v{j}]xfade=transition=fade:duration={dvid}:offset={off}[{vo}]")
        parts.append(f"[{prev_a}][va{j}]acrossfade=d={dvid}:c1=qsin:c2=qsin[{ao}]")
        prev_v, prev_a = vo, ao
        acc += max(vclips[j].duration - dvid, 0.0)

    return ";".join(parts), f"[{prev_v}]", f"[{prev_a}]"

def load_config() -> Dict:
    if CONFIG_FILE.exists():
        try:
            return json.load(CONFIG_FILE.open())
        except Exception:
            pass
    return {}

def save_config(cfg: Dict) -> None:
    try:
        json.dump(cfg, CONFIG_FILE.open("w"))
    except Exception:
        pass

# ───────── GUI ─────────
class AudioVideoMuxer:
    def __init__(self, root: tk.Tk) -> None:
        cleanup_temp_files()

        self.master = root
        root.title("Muxer multi-vidéos / multi-audio")
        root.minsize(820, 580)

        # état + config --------------------------------------------------------
        self.config          = load_config()
        self.video_clips     : List[VideoClip]     = []
        self.audio_tracks    : List[AudioTrack]    = []
        self.video_total     = 0.0
        self.audio_total     = 0.0
        self.preview_active  = False
        self.preview_process = None
        self.temp_preview    : Optional[str]       = None
        self.export_start    : Optional[float]     = None
        self.speed_est       = 34.0
        self.speeds_win      = deque(maxlen=3)
        self.last_directory  = self.config.get("last_directory", os.path.expanduser("~"))

        # ─── style clair (seul) ───
        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except Exception:
            pass
        self.apply_light_theme()

        # ─── barre de menu ───
        menubar = tk.Menu(root); root.config(menu=menubar)
        m_file  = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Fichier", menu=m_file)
        m_file.add_command(label="Ajouter vidéo(s)",      command=self.add_videos)
        m_file.add_command(label="Ajouter audio(s)",      command=self.add_audio)
        m_file.add_separator()
        m_file.add_command(label="Sauvegarder projet",    command=self.save_project)
        m_file.add_command(label="Charger projet",        command=self.load_project)
        m_file.add_separator()
        m_file.add_command(label="Exporter",              command=self.export)
        m_file.add_separator()
        m_file.add_command(label="Quitter",               command=root.quit)

        # ─── colonnes principales ───
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)

        # ─── bandeau haut ───
        banner = ttk.Frame(root); banner.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        ttk.Label(banner, text="Vidéos (ordre) • Cross-fade vidéo léger entre clips").pack(side=tk.LEFT)

        # ─── zone listes ───
        main = ttk.Frame(root); main.grid(row=1, column=0, sticky="nsew", padx=8, pady=4)
        main.columnconfigure(0, weight=1); main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)

        # --- liste vidéos
        f_v = ttk.LabelFrame(main, text="Vidéos (ordre)")
        f_v.grid(row=0, column=0, sticky="nsew", padx=(0,6))
        f_v.columnconfigure(0, weight=1); f_v.rowconfigure(0, weight=1)

        vlist_frame = ttk.Frame(f_v); vlist_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        vlist_frame.columnconfigure(0, weight=1); vlist_frame.rowconfigure(0, weight=1)
        self.lst_video = tk.Listbox(vlist_frame, width=48, height=10, exportselection=False, activestyle="dotbox")
        self.lst_video.grid(row=0, column=0, sticky="nsew")
        ttk.Scrollbar(vlist_frame, orient="vertical", command=self.lst_video.yview
                      ).grid(row=0, column=1, sticky="ns")
        self.lst_video.bind("<<ListboxSelect>>", self.on_video_select)

        vcol = ttk.Frame(f_v); vcol.grid(row=0, column=1, sticky="ns", padx=5, pady=5)
        self.btn_v_add    = ttk.Button(vcol, text="➕ Ajouter",    command=self.add_videos);   self.btn_v_add.pack(fill="x", pady=2)
        self.btn_v_up     = ttk.Button(vcol, text="⬆ Monter",     command=lambda: self.move_video(-1)); self.btn_v_up.pack(fill="x", pady=2)
        self.btn_v_down   = ttk.Button(vcol, text="⬇ Descendre",  command=lambda: self.move_video(1));  self.btn_v_down.pack(fill="x", pady=2)
        self.btn_v_del    = ttk.Button(vcol, text="🗑 Supprimer",  command=self.del_video);     self.btn_v_del.pack(fill="x", pady=2)

        vinfo = ttk.LabelFrame(f_v, text="Détails de la vidéo")
        vinfo.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        self.lbl_video_info = ttk.Label(vinfo, text="Aucune vidéo sélectionnée", anchor="w", justify="left")
        self.lbl_video_info.pack(fill="x", padx=6, pady=4)

        # --- liste audios
        f_a = ttk.LabelFrame(main, text="Pistes audio (ordre)")
        f_a.grid(row=0, column=1, sticky="nsew", padx=(6,0))
        f_a.columnconfigure(0, weight=1); f_a.rowconfigure(0, weight=1)

        alist_frame = ttk.Frame(f_a); alist_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        alist_frame.columnconfigure(0, weight=1); alist_frame.rowconfigure(0, weight=1)
        self.lst_audio = tk.Listbox(alist_frame, width=48, height=10, exportselection=False, activestyle="dotbox")
        self.lst_audio.grid(row=0, column=0, sticky="nsew")
        ttk.Scrollbar(alist_frame, orient="vertical", command=self.lst_audio.yview
                      ).grid(row=0, column=1, sticky="ns")
        self.lst_audio.bind("<<ListboxSelect>>", self.on_track_select)

        acol = ttk.Frame(f_a); acol.grid(row=0, column=1, sticky="ns", padx=5, pady=5)
        self.btn_a_add    = ttk.Button(acol, text="➕ Ajouter",    command=self.add_audio);          self.btn_a_add.pack(fill="x", pady=2)
        self.btn_a_up     = ttk.Button(acol, text="⬆ Monter",     command=lambda: self.move_audio(-1)); self.btn_a_up.pack(fill="x", pady=2)
        self.btn_a_down   = ttk.Button(acol, text="⬇ Descendre",  command=lambda: self.move_audio(1));  self.btn_a_down.pack(fill="x", pady=2)
        self.btn_a_del    = ttk.Button(acol, text="🗑 Supprimer",  command=self.del_audio);          self.btn_a_del.pack(fill="x", pady=2)

        track_info = ttk.LabelFrame(f_a, text="Détails de la piste")
        track_info.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        track_info.columnconfigure(1, weight=1)
        self.lbl_track_info = ttk.Label(track_info, text="Aucune piste sélectionnée", anchor="w", justify="left")
        self.lbl_track_info.grid(row=0, column=0, columnspan=3, sticky="ew", padx=6, pady=(4,2))

        volrow = ttk.Frame(track_info); volrow.grid(row=1, column=0, columnspan=3, sticky="ew", padx=6, pady=2)
        ttk.Label(volrow, text="Volume piste (%)").pack(side=tk.LEFT, padx=(0,6))
        self.track_volume_scale = ttk.Scale(volrow, from_=0, to=110, orient=tk.HORIZONTAL,
                                            command=lambda v: self.update_track_volume(v))
        self.track_volume_scale.set(100); self.track_volume_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)

        muterow = ttk.Frame(track_info); muterow.grid(row=2, column=0, columnspan=3, sticky="w", padx=6, pady=4)
        self.var_mute = tk.BooleanVar(value=False)
        self.var_solo = tk.BooleanVar(value=False)
        self.chk_mute = ttk.Checkbutton(muterow, text="Mute", variable=self.var_mute, command=self.toggle_mute)
        self.chk_solo = ttk.Checkbutton(muterow, text="Solo", variable=self.var_solo, command=self.toggle_solo)
        self.chk_mute.pack(side=tk.LEFT, padx=(0,10)); self.chk_solo.pack(side=tk.LEFT, padx=(0,10))
        # (AUCUN bouton "Solo unique" ici)

        # ─── volumes globaux ───
        volume_frame = ttk.Frame(root); volume_frame.grid(row=2, column=0, sticky="ew", padx=8, pady=6)
        volume_frame.columnconfigure(0, weight=1); volume_frame.columnconfigure(1, weight=1)
        vol_music = ttk.LabelFrame(volume_frame, text="Volume global musiques (%)")
        vol_music.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        self.music_scale = ttk.Scale(vol_music, from_=0, to=110, orient=tk.HORIZONTAL, command=self.on_change_wrapper)
        self.music_scale.set(70); self.music_scale.pack(fill=tk.X, expand=True, padx=6, pady=4)
        vol_video = ttk.LabelFrame(volume_frame, text="Volume audio vidéos (%)")
        vol_video.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        self.video_scale = ttk.Scale(vol_video, from_=0, to=110, orient=tk.HORIZONTAL, command=self.on_change_wrapper)
        self.video_scale.set(100); self.video_scale.pack(fill=tk.X, expand=True, padx=6, pady=4)

        # ─── options ───
        opts = ttk.LabelFrame(root, text="Options"); opts.grid(row=3, column=0, sticky="ew", padx=8, pady=6)
        self.video_audio = tk.BooleanVar(value=True)
        self.music_audio = tk.BooleanVar(value=True)
        ttk.Checkbutton(opts, text="Inclure l'audio des vidéos", variable=self.video_audio, command=self.on_change
                       ).grid(row=0, column=0, padx=10, sticky="w")
        ttk.Checkbutton(opts, text="Inclure les musiques", variable=self.music_audio, command=self.on_change
                       ).grid(row=0, column=1, padx=10, sticky="w")

        # Cross-fade audio (musiques)
        cross_a = ttk.Frame(opts); cross_a.grid(row=0, column=2, padx=10, sticky="w")
        ttk.Label(cross_a, text="Cross-fade musiques (s)").pack(side=tk.LEFT, padx=(0, 3))
        self.cross_spin = tk.Spinbox(cross_a, from_=1, to=CROSS_MAX_AUDIO, width=4, command=self.on_change)
        self.cross_spin.delete(0, tk.END); self.cross_spin.insert(0, str(DEFAULT_CROSS_FADE_AUDIO))
        self.cross_spin.pack(side=tk.LEFT)

        # Cross-fade vidéo
        cross_v = ttk.Frame(opts); cross_v.grid(row=0, column=3, padx=10, sticky="w")
        ttk.Label(cross_v, text="Cross-fade vidéo (s)").pack(side=tk.LEFT, padx=(0, 3))
        self.crossv_spin = tk.Spinbox(cross_v, from_=0.0, to=5.0, increment=0.5, width=4, command=self.on_change)
        self.crossv_spin.delete(0, tk.END); self.crossv_spin.insert(0, str(DEFAULT_CROSS_FADE_VIDEO))
        self.crossv_spin.pack(side=tk.LEFT)

        self.cut_music = tk.BooleanVar(value=False)
        ttk.Checkbutton(opts, text="Couper la musique à la fin des vidéos", variable=self.cut_music, command=self.on_change
                       ).grid(row=0, column=4, padx=10, sticky="w")

        # ─── pré-écoute ───
        prev = ttk.LabelFrame(root, text="Prévisualisation"); prev.grid(row=4, column=0, sticky="ew", padx=8, pady=6)
        self.btn_test60 = ttk.Button(prev, text="▶ Tester (60 s)", state=tk.DISABLED,
                                    command=lambda: self.play_preview(clip=True))
        self.btn_test60.pack(side=tk.LEFT, padx=5, pady=5)
        self.btn_test_full = ttk.Button(prev, text="⏩ Preview complet", state=tk.DISABLED,
                                       command=lambda: self.play_preview(clip=False))
        self.btn_test_full.pack(side=tk.LEFT, padx=5, pady=5)
        self.btn_stop_preview = ttk.Button(prev, text="⏹ Arrêter", state=tk.DISABLED,
                                          command=self.stop_preview)
        self.btn_stop_preview.pack(side=tk.LEFT, padx=5, pady=5)

        # ─── progression / chrono ───
        progress_frame = ttk.Frame(root); progress_frame.grid(row=5, column=0, sticky="ew", padx=8, pady=6)
        progress_frame.columnconfigure(0, weight=1)
        self.progress_var = tk.DoubleVar(value=0.0)
        self.pbar = ttk.Progressbar(progress_frame, variable=self.progress_var, mode="determinate")
        self.pbar.pack(fill=tk.X, padx=5, pady=(0,6))

        self.indic = tk.Canvas(progress_frame, height=18, bg="#dddddd", highlightthickness=0)
        self.indic.pack(fill=tk.X, padx=5, pady=(0,2))
        self.rect        = None
        self.animating   = False

        # ─── export + chrono ───
        bar = ttk.Frame(root); bar.grid(row=6, column=0, sticky="ew", padx=8, pady=6)
        bar.columnconfigure(0, weight=1)
        self.btn_export = ttk.Button(bar, text="💾 Exporter", state=tk.DISABLED, command=self.export)
        self.btn_export.grid(row=0, column=0, sticky="ew", padx=5)
        time_frame = ttk.Frame(bar); time_frame.grid(row=0, column=1, padx=5)
        ttk.Label(time_frame, text="Temps écoulé :").pack(side=tk.LEFT)
        self.lbl_elapsed = ttk.Label(time_frame, width=8); self.lbl_elapsed.pack(side=tk.LEFT, padx=6)

        # ─── durées ───
        self.dur_frame = ttk.Frame(root); self.dur_frame.grid(row=7, column=0, sticky="ew", padx=8, pady=2)
        self.lbl_dur_vid = ttk.Label(self.dur_frame, text="Durée vidéos : 0:00")
        self.lbl_dur_vid.pack(side=tk.LEFT, padx=5)
        self.lbl_dur_aud = ttk.Label(self.dur_frame, text="Durée musiques actives : 0:00")
        self.lbl_dur_aud.pack(side=tk.RIGHT, padx=5)

        # ─── statut ───
        status_frame = ttk.Frame(root); status_frame.grid(row=8, column=0, sticky="ew", padx=8, pady=6)
        status_frame.columnconfigure(0, weight=1)
        self.status = ttk.Label(status_frame, text="", anchor="w")
        self.status.pack(fill=tk.X, padx=5)

        # ─── drag & drop éventuel ───
        self.setup_drag_drop()

        # répertoire par défaut
        if self.last_directory and os.path.isdir(self.last_directory):
            os.chdir(self.last_directory)

        self._ready()

    # ───────── thème clair ─────────
    def apply_light_theme(self):
        bg, fg, hl = "#f5f5f5", "#000000", "#e0e0e0"
        try:
            self.style.theme_use("clam")
        except Exception:
            pass
        self.style.configure(".", background=bg, foreground=fg)
        for key in ("TFrame","TLabelframe","TLabelframe.Label","TLabel","TButton","TCheckbutton","TMenubutton"):
            self.style.configure(key, background=bg, foreground=fg)
        self.style.configure("TProgressbar", troughcolor="#dddddd")
        self.style.configure("Horizontal.TScale", background=bg)
        self.style.map("TButton", background=[("active", hl)])

        try:
            self.master.tk_setPalette(background=bg, foreground=fg,
                                      activeBackground=hl, activeForeground=fg,
                                      highlightBackground=hl, highlightColor=hl,
                                      insertBackground=fg, selectBackground="#0078d7",
                                      selectForeground="#ffffff")
        except Exception:
            pass
        if hasattr(self, "indic"):
            self.indic.configure(bg="#dddddd")

        self.config["theme"] = "clair"; save_config(self.config)

    # ───────── carré vert animé ─────────
    def _start_anim(self):
        if self.animating:
            return
        self.animating = True
        if self.rect is None:
            self.rect = self.indic.create_rectangle(0, 0, 20, 18, fill="green", outline="")
        self._animate()

    def _animate(self):
        if not self.animating or self.rect is None:
            return
        canvas = self.indic
        x1, y1, x2, y2 = canvas.coords(self.rect)
        step = 6
        if x2 + step >= canvas.winfo_width():
            canvas.coords(self.rect, 0, 0, 20, 18)
        else:
            canvas.move(self.rect, step, 0)
        self.master.after(50, self._animate)

    def _stop_anim(self):
        self.animating = False
        if self.rect is not None:
            self.indic.delete(self.rect)
            self.rect = None

    # ───────── drag & drop ─────────
    def setup_drag_drop(self):
        try:
            import tkinterdnd2
            if isinstance(self.master, tkinterdnd2.TkinterDnD.Tk):
                self.master.drop_target_register('DND_Files')
                self.master.dnd_bind('<<Drop>>', self.on_drop)
        except Exception:
            pass

    def on_drop(self, event):
        files = event.data.strip('{}').split('} {')
        for f in files:
            ext = Path(f).suffix.lower()
            if ext in ('.mp4', '.mkv', '.mov', '.avi', '.webm'):
                vc = VideoClip(path=f); self.video_clips.append(vc); self._refresh_video_list()
            elif ext in ('.mp3', '.wav', '.flac', '.aac', '.ogg'):
                t = AudioTrack(path=f); self.audio_tracks.append(t); self._refresh_audio_list()
        self._update_totals(); self._ready()

    # ───────── gestion vidéos ─────────
    def add_videos(self):
        fps = filedialog.askopenfilenames(
            title="Vidéo(s)",
            filetypes=[("Vidéos", "*.mp4 *.mkv *.mov *.avi *.webm"), ("Tous", "*.*")],
            initialdir=self.last_directory)
        if fps:
            self.last_directory = os.path.dirname(fps[0]); self.config["last_directory"] = self.last_directory; save_config(self.config)
            for p in fps:
                self.video_clips.append(VideoClip(path=p))
            self._refresh_video_list(); self._update_totals(); self._ready()

    def del_video(self):
        if sel := self.lst_video.curselection():
            idx = sel[0]; del self.video_clips[idx]
            self._refresh_video_list(); self._update_totals(); self._ready()

    def move_video(self, d: int):
        if not (sel := self.lst_video.curselection()): return
        i, j = sel[0], sel[0] + d
        if j < 0 or j >= len(self.video_clips): return
        self.video_clips[i], self.video_clips[j] = self.video_clips[j], self.video_clips[i]
        self._refresh_video_list(select=j)

    def on_video_select(self, _):
        if not (sel := self.lst_video.curselection()):
            self.lbl_video_info.config(text="Aucune vidéo sélectionnée"); return
        idx = sel[0]; v = self.video_clips[idx]
        size_str = format_size(os.path.getsize(v.path)) if os.path.exists(v.path) else "?"
        self.lbl_video_info.config(text=f"Nom : {v.name}\nDurée : {fmt(v.duration)}\nTaille : {size_str}")

    def _refresh_video_list(self, select: Optional[int]=None):
        self.lst_video.delete(0, tk.END)
        for v in self.video_clips:
            self.lst_video.insert(tk.END, f"{v.name}  ({fmt(v.duration)})")
        if select is not None and 0 <= select < len(self.video_clips):
            self.lst_video.selection_clear(0, tk.END)
            self.lst_video.selection_set(select)
            self.lst_video.see(select)

    # ───────── gestion audio ─────────
    def add_audio(self):
        fps = filedialog.askopenfilenames(
            title="Musique(s)",
            filetypes=[("Audio", "*.mp3 *.wav *.flac *.aac *.ogg"), ("Tous", "*.*")],
            initialdir=self.last_directory)
        if fps:
            self.last_directory = os.path.dirname(fps[0]); self.config["last_directory"] = self.last_directory; save_config(self.config)
            for p in fps:
                self.audio_tracks.append(AudioTrack(path=p))
            self._refresh_audio_list(); self._update_totals(); self._ready()

    def del_audio(self):
        if sel := self.lst_audio.curselection():
            idx = sel[0]; del self.audio_tracks[idx]
            self._refresh_audio_list(); self._update_totals(); self._ready()

    def move_audio(self, d: int):
        if not (sel := self.lst_audio.curselection()): return
        i, j = sel[0], sel[0] + d
        if j < 0 or j >= len(self.audio_tracks): return
        self.audio_tracks[i], self.audio_tracks[j] = self.audio_tracks[j], self.audio_tracks[i]
        self._refresh_audio_list(select=j)

    def on_track_select(self, _):
        if not (sel := self.lst_audio.curselection()):
            self.lbl_track_info.config(text="Aucune piste sélectionnée"); self.track_volume_scale.set(100)
            self.var_mute.set(False); self.var_solo.set(False); return
        idx = sel[0]; t = self.audio_tracks[idx]
        size_str = format_size(os.path.getsize(t.path)) if os.path.exists(t.path) else "?"
        self.lbl_track_info.config(text=f"Nom : {t.name}\nDurée : {fmt(t.duration)}\nTaille : {size_str}")
        self.track_volume_scale.set(t.volume * 100)
        self.var_mute.set(t.mute); self.var_solo.set(t.solo)

    def _refresh_audio_list(self, select: Optional[int]=None):
        self.lst_audio.delete(0, tk.END)
        for t in self.audio_tracks:
            tag = "[S]" if t.solo else ("[M]" if t.mute else "   ")
            self.lst_audio.insert(tk.END, f"{tag} {t.name}  ({fmt(t.duration)})")
        if select is not None and 0 <= select < len(self.audio_tracks):
            self.lst_audio.selection_clear(0, tk.END)
            self.lst_audio.selection_set(select)
            self.lst_audio.see(select)

    # ───────── volumes / Mute / Solo ─────────
    def update_track_volume(self, val):
        if not (sel := self.lst_audio.curselection()): return
        self.audio_tracks[sel[0]].volume = float(val) / 100
        self.on_change()

    def toggle_mute(self):
        if not (sel := self.lst_audio.curselection()): return
        idx = sel[0]; t = self.audio_tracks[idx]
        t.mute = not t.mute
        self.var_mute.set(t.mute)
        self._refresh_audio_list(select=idx)
        self.on_change()

    def toggle_solo(self):
        if not (sel := self.lst_audio.curselection()): return
        idx = sel[0]; t = self.audio_tracks[idx]
        t.solo = not t.solo
        self.var_solo.set(t.solo)
        self._refresh_audio_list(select=idx)
        self.on_change()

    # ───────── sauvegarde / chargement ─────────
    def save_project(self):
        if not self.video_clips:
            messagebox.showinfo("Information", "Ajoutez au moins une vidéo."); return
        fp = filedialog.asksaveasfilename(defaultextension=".mixproj",
                                          filetypes=[("Projet Mixer", "*.mixproj")],
                                          initialdir=self.last_directory)
        if not fp: return
        data = {
            "videos": [{"path": v.path, "name": v.name} for v in self.video_clips],
            "audio_tracks": [{
                "path": t.path, "volume": t.volume, "name": t.name,
                "mute": t.mute, "solo": t.solo
            } for t in self.audio_tracks],
            "settings": {
                "video_audio": self.video_audio.get(), "music_audio": self.music_audio.get(),
                "cross_fade_audio": float(self.cross_spin.get()),
                "cross_fade_video": float(self.crossv_spin.get()),
                "cut_music": self.cut_music.get(),
                "video_volume": float(self.video_scale.get()),
                "music_volume": float(self.music_scale.get())
            }}
        try:
            json.dump(data, open(fp, "w"), indent=2)
            self.status.config(text=f"Projet sauvegardé : {os.path.basename(fp)}")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la sauvegarde : {e}")

    def load_project(self):
        fp = filedialog.askopenfilename(defaultextension=".mixproj",
                                        filetypes=[("Projet Mixer", "*.mixproj")],
                                        initialdir=self.last_directory)
        if not fp: return
        try:
            with open(fp) as f: data = json.load(f)

            # vidéos
            self.video_clips.clear(); self.lst_video.delete(0, tk.END)
            for vd in data.get("videos", []):
                path = vd["path"]
                if not os.path.exists(path):
                    path = filedialog.askopenfilename(title=f"Localiser {os.path.basename(vd['path'])}",
                                                      filetypes=[("Vidéos", "*.mp4 *.mkv *.mov *.avi *.webm")])
                    if not path: continue
                self.video_clips.append(VideoClip(path=path, name=vd.get("name", Path(path).name)))
            self._refresh_video_list()

            # audios
            self.audio_tracks.clear(); self.lst_audio.delete(0, tk.END)
            for td in data.get("audio_tracks", []):
                path = td["path"]
                if not os.path.exists(path):
                    path = filedialog.askopenfilename(title=f"Localiser {os.path.basename(path)}",
                                                      filetypes=[("Audio", "*.mp3 *.wav *.flac *.aac *.ogg")])
                    if not path: continue
                self.audio_tracks.append(AudioTrack(
                    path=path,
                    volume=min(td.get("volume", 1.0), 1.1),
                    name=td.get("name", Path(path).name),
                    mute=bool(td.get("mute", False)),
                    solo=bool(td.get("solo", False))
                ))
            self._refresh_audio_list()

            s = data.get("settings", {})
            self.video_audio.set(s.get("video_audio", True))
            self.music_audio.set(s.get("music_audio", True))
            self.cut_music.set(s.get("cut_music", False))
            self.cross_spin.delete(0, tk.END); self.cross_spin.insert(0, str(s.get("cross_fade_audio", DEFAULT_CROSS_FADE_AUDIO)))
            self.crossv_spin.delete(0, tk.END); self.crossv_spin.insert(0, str(s.get("cross_fade_video", DEFAULT_CROSS_FADE_VIDEO)))
            self.video_scale.set(min(s.get("video_volume", 100), 110))
            self.music_scale.set(min(s.get("music_volume", 70), 110))

            self._update_totals(); self._ready()
            self.status.config(text=f"Projet chargé : {os.path.basename(fp)}")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du chargement : {e}")

    # ───────── internes ─────────
    def _update_totals(self):
        # Durée totale vidéos avec fondu(s)
        dvid = float(self.crossv_spin.get())
        if self.video_clips:
            base = sum(v.duration for v in self.video_clips)
            overlap = dvid * max(len(self.video_clips) - 1, 0)
            self.video_total = max(base - overlap, 0.0)
        else:
            self.video_total = 0.0
        self.lbl_dur_vid.config(text=f"Durée vidéos : {fmt(self.video_total)}")

        # Durée musiques actives (même logique Mute/Solo)
        self.audio_total = sum(t.duration for t in self._active_tracks()) if self.audio_tracks else 0.0
        self.lbl_dur_aud.config(text=f"Durée musiques actives : {fmt(self.audio_total)}")

    def _active_tracks(self) -> List[AudioTrack]:
        if not self.audio_tracks:
            return []
        solos = [t for t in self.audio_tracks if t.solo]
        if solos:
            return [t for t in solos if not t.mute] or []
        return [t for t in self.audio_tracks if not t.mute]

    def _ready(self):
        ok = bool(self.video_clips)
        st = tk.NORMAL if ok else tk.DISABLED
        self.btn_test60.config(state=st); self.btn_test_full.config(state=st); self.btn_export.config(state=st)

    # ───────── sliders & check ─────────
    def on_change_wrapper(self, *_): self.on_change()
    def on_change(self, *_):
        if self.preview_active:
            if hasattr(self, "_upd"): self.master.after_cancel(self._upd)
            self._upd = self.master.after(400, self._restart_preview)
        self._update_totals()

    def _restart_preview(self): threading.Thread(target=self._th_restart, daemon=True).start()
    def _th_restart(self):
        self.master.after(0, self.stop_preview); time.sleep(0.2)
        self.master.after(0, lambda: self.play_preview(clip=True))

    # ───────── pré-écoute ─────────
    def play_preview(self, *, clip: bool):
        if not self.video_clips: return
        self.btn_test60.config(state=tk.DISABLED); self.btn_test_full.config(state=tk.DISABLED)
        self.btn_stop_preview.config(state=tk.NORMAL)
        self.status.config(text="Prévisualisation en cours…")
        threading.Thread(target=self._build_preview, args=(clip,), daemon=True).start()

    def _build_preview(self, clip: bool):
        try:
            self.stop_preview()                                   # remise à zéro
            self.master.after(0, self._start_anim)                # ↲ démarre animation
            fd, self.temp_preview = tempfile.mkstemp(suffix=".mkv"); os.close(fd)

            cross_a = int(float(self.cross_spin.get()))
            cross_v = float(self.crossv_spin.get())
            vv = float(self.video_scale.get()) / 100.0

            active_tracks = self._active_tracks() if self.music_audio.get() else []

            # — inputs: d'abord N vidéos, puis M musiques
            cmd = ["ffmpeg", "-y"]
            for v in self.video_clips: cmd.extend(["-i", v.path])
            for t in active_tracks:     cmd.extend(["-i", t.path])

            # — codec vidéo: si plusieurs vidéos, on doit réencoder (xfade). Pour une seule: on peut copier.
            must_reencode = len(self.video_clips) > 1 or cross_v > 0.0

            fc_parts = []

            # • Chaîne vidéo + audio des vidéos (xfade + acrossfade)
            vfc, tag_vout, tag_vaout = build_video_xfade_filter(self.video_clips, cross_v)
            fc_parts.append(vfc)

            # • Volume audio des vidéos
            fc_parts.append(f"{tag_vaout}volume={vv}[va]")  # [va] = audio des vidéos avec volume

            # • Cross-fade des musiques
            tag_music = ""
            if active_tracks:
                base_idx = len(self.video_clips)  # après les vidéos
                cf, tag_music = build_crossfade_filter(active_tracks, cross_a, base_idx)
                fc_parts.append(cf)
                if self.cut_music.get():
                    fc_parts.append(f"{tag_music}atrim=duration={self.video_total}[mus]"); tag_music = "[mus]"

            # • Mix final audio selon options
            tag_final_audio = ""
            if self.video_audio.get() and tag_music:
                fc_parts.append(f"[va]{tag_music}amix=inputs=2:duration=longest:dropout_transition=0[aout]")
                tag_final_audio = "[aout]"
            elif self.video_audio.get():
                tag_final_audio = "[va]"
            elif tag_music:
                tag_final_audio = tag_music
            # sinon: pas d'audio

            if fc_parts:
                cmd.extend(["-filter_complex", ";".join(fc_parts)])

            # — mapping
            cmd.extend(["-map", tag_vout if tag_vout else "0:v:0"])
            if tag_final_audio:
                cmd.extend(["-map", tag_final_audio])
            else:
                cmd.extend(["-an"])

            # — codecs
            if must_reencode:
                cmd.extend(["-c:v", "libx264", "-preset", "veryfast", "-crf", "20"])
            else:
                cmd.extend(["-c:v", "copy"])

            cmd.extend(["-c:a", "aac"])  # preview
            if clip:
                # 60 s max preview
                cmd.extend(["-t", "60"])
            cmd.append(self.temp_preview)

            if subprocess.call(cmd) != 0:
                raise RuntimeError("FFmpeg a échoué pendant la prévisualisation")

            # suivi progression approx
            self.preview_active = True
            threading.Thread(target=self._progress_preview, args=(clip,), daemon=True).start()

            # lecture / ouverture
            if clip and shutil.which("ffplay"):
                self.preview_process = subprocess.Popen(
                    ["ffplay", "-autoexit", "-loglevel", "quiet", "-window_title", "Preview 60 s", self.temp_preview])
                threading.Thread(target=self._watch_preview, daemon=True).start()
            else:
                if os.name == "nt": os.startfile(self.temp_preview)
                elif shutil.which("open"): subprocess.Popen(["open", self.temp_preview])
                else: subprocess.Popen(["xdg-open", self.temp_preview])
                self.master.after(0, self._reset_preview_ui)
        except Exception as e:
            messagebox.showerror("Erreur preview", str(e))
            self.master.after(0, self._stop_anim)
        finally:
            self.master.after(0, lambda: (self.btn_test60.config(state=tk.NORMAL),
                                          self.btn_test_full.config(state=tk.NORMAL),
                                          self.status.config(text="")))

    def _reset_preview_ui(self):
        self.preview_active = False; self.progress_var.set(0); self.btn_stop_preview.config(state=tk.DISABLED); self._stop_anim()

    def _progress_preview(self, clip: bool):
        # Estimation triviale (60 s si clip; sinon durée totale vidéos)
        start = time.time(); dur = 60 if clip else (self.video_total or 1.0)
        while self.preview_active:
            pct = min((time.time() - start) / dur * 100, 100); self.master.after(0, self.progress_var.set, pct)
            if pct >= 100: break; time.sleep(0.1)

    def _watch_preview(self):
        try:
            if self.preview_process: self.preview_process.wait()
        finally:
            self.master.after(0, self.stop_preview)

    def stop_preview(self):
        self.preview_active = False; self.btn_stop_preview.config(state=tk.DISABLED); self._stop_anim()
        try:
            if self.preview_process: self.preview_process.kill()
        except Exception as e:
            print(f"Erreur lors de l'arrêt du processus de prévisualisation: {e}")
        self.preview_process = None

        if self.temp_preview and os.path.exists(self.temp_preview):
            try:
                os.remove(self.temp_preview)
                print(f"Fichier temporaire supprimé: {self.temp_preview}")
            except Exception as e:
                print(f"Impossible de supprimer le fichier temporaire {self.temp_preview}: {e}")
        self.temp_preview = None
        self.progress_var.set(0)

    # ───────── export ─────────
    def export(self):
        if not self.video_clips: 
            messagebox.showinfo("Information", "Ajoutez au moins une vidéo.")
            return
        out = filedialog.asksaveasfilename(
            title="Fichier de sortie", defaultextension=".mkv",
            filetypes=[("Matroska", "*.mkv"), ("MP4", "*.mp4"), ("WebM", "*.webm")],
            initialdir=self.last_directory)
        if out:
            self.last_directory = os.path.dirname(out); self.config["last_directory"] = self.last_directory; save_config(self.config)
            threading.Thread(target=self._run_export, args=(out,), daemon=True).start()

    def _run_export(self, outfile: str):
        self.export_start = time.time(); self._update_elapsed()
        self.status.config(text="Export en cours…")
        self.btn_export.config(state=tk.DISABLED); self.progress_var.set(0)
        self.master.after(0, self._start_anim)

        cross_a = int(float(self.cross_spin.get()))
        cross_v = float(self.crossv_spin.get())
        vv = float(self.video_scale.get()) / 100.0

        active_tracks = self._active_tracks() if self.music_audio.get() else []

        cmd = ["ffmpeg", "-y"]
        for v in self.video_clips: cmd.extend(["-i", v.path])
        for t in active_tracks:     cmd.extend(["-i", t.path])

        must_reencode = len(self.video_clips) > 1 or cross_v > 0.0

        fc_parts = []
        vfc, tag_vout, tag_vaout = build_video_xfade_filter(self.video_clips, cross_v)
        fc_parts.append(vfc)
        fc_parts.append(f"{tag_vaout}volume={vv}[va]")

        tag_music = ""
        if active_tracks:
            base_idx = len(self.video_clips)
            cf, tag_music = build_crossfade_filter(active_tracks, cross_a, base_idx)
            fc_parts.append(cf)
            if self.cut_music.get():
                fc_parts.append(f"{tag_music}atrim=duration={self.video_total}[mus]"); tag_music = "[mus]"

        tag_final_audio = ""
        if self.video_audio.get() and tag_music:
            fc_parts.append(f"[va]{tag_music}amix=inputs=2:duration=longest:dropout_transition=0[aout]")
            tag_final_audio = "[aout]"
        elif self.video_audio.get():
            tag_final_audio = "[va]"
        elif tag_music:
            tag_final_audio = tag_music

        if fc_parts:
            cmd.extend(["-filter_complex", ";".join(fc_parts)])

        cmd.extend(["-map", tag_vout if tag_vout else "0:v:0"])
        if tag_final_audio:
            cmd.extend(["-map", tag_final_audio])
        else:
            cmd.extend(["-an"])

        # codecs
        if outfile.lower().endswith(".webm"):
            # WebM: VP9 + Vorbis/Opus (ici Vorbis pour simplicité)
            cmd.extend(["-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "30"])
            cmd.extend(["-c:a", "libvorbis"])
        else:
            if must_reencode:
                cmd.extend(["-c:v", "libx264", "-preset", "medium", "-crf", "20"])
            else:
                cmd.extend(["-c:v", "copy"])
            cmd.extend(["-c:a", "aac", "-b:a", "192k"])

        cmd.extend(["-progress", "pipe:1", "-nostats", outfile])

        total_ms = self.video_total * 1000 or 1.0
        try:
            with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  text=True, bufsize=1, universal_newlines=True,
                                  encoding='utf-8', errors='replace') as proc:
                for line in proc.stdout:
                    if m := time_rx.search(line):
                        pos = int(m.group(1)); self.master.after(0, self.progress_var.set, pos / total_ms * 100)
                        elapsed = time.time() - self.export_start
                        if elapsed > 0 and pos > 0:
                            inst = (pos / 1000) / elapsed; self.speeds_win.append(inst)
                            self.speed_est = 0.7 * self.speed_est + 0.3 * statistics.mean(self.speeds_win)
                if proc.wait() != 0:
                    raise RuntimeError("FFmpeg a échoué lors de l'export")
        except Exception as e:
            messagebox.showerror("Erreur export", str(e))
        finally:
            self.master.after(0, self._export_done)

    def _export_done(self):
        if hasattr(self, "_elapsed_upd"): self.master.after_cancel(self._elapsed_upd)
        self.lbl_elapsed.config(text="")
        self.progress_var.set(100); self.status.config(text="Export terminé")
        self.btn_export.config(state=tk.NORMAL)
        self._stop_anim()

    # ───────── chrono ─────────
    def _update_elapsed(self):
        if self.export_start is None: return
        self.lbl_elapsed.config(text=fmt(time.time() - self.export_start))
        self._elapsed_upd = self.master.after(TIME_STEP_MS, self._update_elapsed)

    # ───────── fermeture propre ─────────
    def on_closing(self):
        self.stop_preview()
        if hasattr(self, "temp_preview") and self.temp_preview and os.path.exists(self.temp_preview):
            try: os.remove(self.temp_preview)
            except Exception: pass
        self.master.destroy()

# ───────── lancement ─────────
if __name__ == "__main__":
    if os.name == "nt":
        signal.signal(signal.SIGINT, signal.SIG_DFL)

    tk.Tk.report_callback_exception = lambda *e: print("Tk callback error:", *e, file=sys.stderr)

    # Si tkinterdnd2 est installé, instancier sa classe, sinon Tk standard
    try:
        import tkinterdnd2 as dnd
        root = dnd.TkinterDnD.Tk()
    except Exception:
        root = tk.Tk()

    app = AudioVideoMuxer(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
