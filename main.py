#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Video-Musique - Muxeur multi-videos / multi-audio

Point d'entree de l'application.
Lance l'interface graphique moderne pour mixer videos et pistes audio.

Usage:
    python main.py

Fonctionnalites:
    - Assemblage de plusieurs clips video avec transitions
    - Superposition de pistes audio multiples
    - Cross-fade audio et video reglables
    - Controle du volume par piste (mute/solo)
    - Preview rapide (60s) ou complete
    - Export en MKV, MP4 ou WebM

Requires:
    - Python 3.10+
    - tkinter
    - ffmpeg, ffprobe, ffplay (optionnel pour preview)

(c) 2025 - MIT License
"""

import os
import signal
import sys
import tkinter as tk

# Add src to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.gui.app import VideoMusiqueApp
from src.utils.logger import get_logger


def main():
    """Main entry point."""
    # Initialize logging
    logger = get_logger()
    logger.enable_file_logging()
    logger.cleanup_old_logs(max_days=7)
    logger.info("Video-Musique starting...")

    # Handle SIGINT gracefully on Windows
    if os.name == "nt":
        signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Suppress Tk callback exceptions in console (but log them)
    def handle_tk_error(exc_type, exc_value, exc_tb):
        logger.exception(f"Tk callback error: {exc_value}")
        print("Tk error:", exc_type, exc_value, file=sys.stderr)

    tk.Tk.report_callback_exception = handle_tk_error

    # Try to use tkinterdnd2 for drag-drop support, fallback to standard Tk
    try:
        import tkinterdnd2 as dnd
        root = dnd.TkinterDnD.Tk()
    except ImportError:
        root = tk.Tk()

    # Create and run application
    app = VideoMusiqueApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
