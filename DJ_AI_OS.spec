# -*- mode: python ; coding: utf-8 -*-
"""Lean build spec for DJ AI OS — excludes heavy unused deps."""

import os
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, copy_metadata

project_root = Path(SPECPATH)

# ============================================================
# Data files — exclude large audio files and library output
# ============================================================
datas = [
    # Assets
    ('assets', 'assets'),
]

# Include data/ but EXCLUDE large folders
import fnmatch
data_root = project_root / 'data'
if data_root.exists():
    for item in data_root.rglob('*'):
        if item.is_file():
            # Skip MP3, WAV, FLAC, M4A, OGG, DB, large JSON
            if item.suffix.lower() in ('.mp3', '.wav', '.flac', '.m4a', '.ogg', '.db', '.json'):
                if item.stat().st_size > 1024 * 100:  # Skip files >100KB
                    continue
            # Skip database files entirely (runtime data, not ship-with-app)
            if item.suffix.lower() == '.db':
                continue
            # Skip DJ_LIBRARY_OUTPUT, DJ_EXPORTS, etc.
            rel = str(item.relative_to(data_root))
            if any(rel.startswith(p) for p in ('DJ_LIBRARY', 'DJ_EXPORT', 'DJ_REMIX', 'DJ_CLOUD')):
                continue
            datas.append((str(item), str(item.parent.relative_to(project_root))))

# CustomTkinter themes
datas += collect_data_files('customtkinter')

# ============================================================
# Binaries — tkinter/tcl DLLs
# ============================================================
binaries = []
python_dlls = Path(sys.base_prefix) / 'DLLs'
for pattern in ('tk*.dll', 'tcl*.dll', 'sqlite3.dll'):
    for dll in python_dlls.glob(pattern):
        binaries.append((str(dll), '.'))

# ============================================================
# Hidden imports — only what the app actually needs
# ============================================================
hiddenimports = [
    # tkinter
    'tkinter',
    'tkinter.ttk',
    'tkinter.filedialog',
    'tkinter.messagebox',
    'tkinter.scrolledtext',
    'tkinter.colorchooser',
    'tkinter.font',
    # Audio analysis
    'librosa',
    'numpy',
    'scipy',
    'scipy.signal',
    'scipy.fft',
    'scipy.ndimage',
    'soundfile',
    'audioread',
    'mutagen',
    'msgpack',
    # UI
    'customtkinter',
    'PIL',
    'PIL._tkinter_finder',
    'app.ui.enhancements',
    # AI modules (lazy-loaded)
    'app.ai.dj_profile',
    'app.ai.dj_coach',
    'app.ai.dj_heart',
    'app.ai.emergency_crate',
    'app.ai.feedback_learner',
    'app.ai.set_recorder',
    'app.ai.smart_playlist',
    'app.ai.track_similarity',
    'app.ai.track_dna',
    'app.ai.version_detector',
    'app.ai.audio_brain',
    'app.ai.audio_analyzer',
    'app.ai.ai_ear',
    'app.ai.club_intelligence',
    'app.ai.deck_engine',
    'app.ai.mix_master_doctor',
    'app.ai.mix_master_engine',
    'app.ai.music_ai',
    'app.ai.music_research_assistant',
    'app.ai.performance_planner',
    'app.ai.remix_lab',
    'app.ai.set_engine',
    'app.ai.show_director',
    'app.ai.playback_engine',
    'app.ai.voice_assistant',
    'app.ai.camera_assistant',
    'app.ai.jarvis_assistant',
    'app.ui.song_vault_panel',
    # Serialization
    'sqlite3',
    # Optional backends (graceful if missing)
    'vlc',
    'windnd',
]

# ============================================================
# Excludes — heavy deps not needed by core app
# ============================================================
excludes = [
    # Not needed (optional beat generator uses torch, but core app doesn't require it)
    'torch',
    'torchvision',
    'torchaudio',
    # Cloud heavyweights not used in packaged app
    'grpc',
    'google',
    'googleapiclient',
    'pydantic',
    'rich',
    'fastapi',
    'uvicorn',
    # Browsers / selenium
    'selenium',
    'playwright',
    # ML not used
    'tensorflow',
    'keras',
    'transformers',
    'jax',
    'dask',
    # Not needed
    'matplotlib',
    'PyQt5',
    'PySide2',
    'PySide6',
    'pandas',
]

# ============================================================
# Analysis
# ============================================================
a = Analysis(
    ['main.py'],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='DJ_AI_OS',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[str(project_root / 'assets' / 'icon.ico')],
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DJ_AI_OS',
)
