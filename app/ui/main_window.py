import os
import math
import time
import threading
from importlib.util import find_spec
import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog, StringVar

try:
    import windnd
except Exception:
    windnd = None

from app.core.i18n import t, get_language, set_language, available_languages

from app.ui.sidebar import Sidebar
from app.ui.track_table import TrackTable
from app.ui.ai_log_panel import AILogPanel
from app.ui.ai_dashboard import AIDashboard
from app.ui.animated_cockpit import AnimatedArchiveCockpit
from app.ui.command_palette import CommandPalette
from app.ui.neon_booth_panel import NeonBoothPanel
from app.ui.waveform_view import WaveformView
from app.ui.views.account_view import AccountView
from app.ui.views.genre_review_view import GenreReviewView
from app.ui.views.settings_view import SettingsView
from app.ui.dj_booth_view import DJBoothView
from app.ui.theme import *

from app.core.audio_scanner import AudioScanner
from app.core.archive_brain import ArchiveBrain
from app.core.archive_auditor import ArchiveAuditor
from app.core.archive_reconciler import ArchiveReconciler
from app.core.track_queue import TrackQueue
from app.core.library_doctor import LibraryDoctor
from app.core.organizer import Organizer
from app.core.export_center import ExportCenter
from app.core.rekordbox_bridge import RekordboxBridge
from app.core.gig_pack_builder import GigPackBuilder
from app.core.fl_studio_bridge import FLStudioBridge
from app.cloud.trend_recommender import TrendRecommender
from app.cloud.dj_archive_cloud import DJArchiveCloud
from app.cloud.commercial_api import CommercialAPIClient

from app.ai.audio_brain import AudioBrain
from app.ai.audio_analyzer import AudioAnalyzer
from app.ai.ai_ear import AIEar
from app.ai.club_intelligence import ClubIntelligence
from app.ai.deck_engine import DeckEngine
from app.ai.dj_heart import DJHeart
from app.ai.feedback_learner import FeedbackLearner
from app.ai.genre_review import GenreReviewStudio
from app.ai.mix_master_doctor import MixMasterDoctor
from app.ai.mix_master_engine import MixMasterEngine
from app.ai.music_ai import MusicAI
from app.ai.music_research_assistant import MusicResearchAssistant
from app.ai.performance_planner import PerformancePlanner
from app.ai.remix_lab import RemixLab
from app.ai.set_engine import SetEngine
from app.ai.show_director import ShowDirector
from app.ai.playback_engine import PlaybackEngine
from app.ai.voice_assistant import VoiceAssistant
from app.ai.camera_assistant import CameraAssistant
from app.ai.jarvis_assistant import AstraAssistant
from app.ai.version_detector import detect_version
from app.ai.emergency_crate import EmergencyCrate
from app.ai.track_dna import generate_dna, dna_to_string
from app.ai.dj_coach import DJCoach
from app.ui.library_map import LibraryMap
from app.ai.set_recorder import SetRecorder
from app.ai.smart_playlist import SmartPlaylistGenerator
from app.ui.beat_grid_view import BeatGridView
from app.ai.track_similarity import TrackSimilarityEngine
from app.ai.dj_profile import DJProfile
from app.ui.enhancements import MiniPlayer, QuickStatsBar, ThemeSwitcher, show_toast

from data.db.ai_library_db import AILibraryDB
from app.license.license_manager import LicenseManager

ctk.set_appearance_mode("dark")


class MainWindow(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.app_version = "v24 ULTRA PRODUCER"

        # ================= WINDOW =================
        self.title(f"DJ AI OS {self.app_version}")
        self.geometry("1780x1000")
        self.minsize(1450, 850)
        self.configure(fg_color=BACKGROUND)

        # ================= AI CORE =================
        self.brain = AudioBrain()
        self.analyzer = AudioAnalyzer()
        self.ai_ear = AIEar()
        self.club_intelligence = ClubIntelligence()
        self.dj_heart = DJHeart()
        self.music_ai = MusicAI()
        self.research = MusicResearchAssistant()
        self.performance_planner = PerformancePlanner()
        self.remix_lab = RemixLab()
        self.mix_master_doctor = MixMasterDoctor()
        self.mix_master_engine = MixMasterEngine()
        self.show_director = ShowDirector()
        self.set_engine = SetEngine(self.brain)
        self.voice_assistant = VoiceAssistant()
        self.astra_assistant = AstraAssistant(runtime=self.voice_assistant.runtime)
        self.camera_assistant = CameraAssistant()
        self.astra_listener_running = False
        self.astra_listener_thread = None
        self.astra_active = False
        self.astra_passive = False

        # ================= SYSTEM =================
        self.scanner = AudioScanner()
        self.archive_brain = ArchiveBrain()
        self.archive_auditor = ArchiveAuditor()
        self.archive_reconciler = ArchiveReconciler("DJ_LIBRARY_OUTPUT")
        self.doctor = LibraryDoctor()
        self.organizer = Organizer("DJ_LIBRARY_OUTPUT")
        self.export_center = ExportCenter()
        self.rekordbox_bridge = RekordboxBridge()
        self.gig_pack_builder = GigPackBuilder()
        self.fl_studio_bridge = FLStudioBridge()
        self.trends = TrendRecommender()
        self.cloud_archive = DJArchiveCloud()
        self.commercial_api = CommercialAPIClient()
        self.queue = TrackQueue()
        self.playback = PlaybackEngine(callback=self.on_now_playing)
        self.deck_engine = DeckEngine()
        self.feedback_learner = FeedbackLearner()
        self.emergency_crate = EmergencyCrate()
        self.dj_coach = DJCoach()
        self.set_recorder = SetRecorder()
        self.smart_playlist = SmartPlaylistGenerator()
        self.similarity_engine = TrackSimilarityEngine()
        self.dj_profile = DJProfile()
        self.genre_review = GenreReviewStudio()

        # ================= DB =================
        self.db = AILibraryDB()
        self.license = LicenseManager()
        self.plan = self.license.get_plan()

        # ================= DATA =================
        self.library = []
        self.current_set = []
        saved_tracks = self.db.load_all()
        self.saved_tracks = saved_tracks
        self.archived_ids = {
            t.get("id")
            for t in saved_tracks
            if t.get("id")
        }
        self.processed_source_index = self.build_processed_source_index(saved_tracks)
        self.doctor.build_index(saved_tracks)
        self.ai_messages = []
        self.duplicate_reviews = []
        self.total_archived = len(self.archived_ids)
        self.archive_output_folder = os.path.abspath("DJ_LIBRARY_OUTPUT")

        # ================= STATE =================
        self.current_view = "dashboard"
        self.views = {}
        self.is_playing = False
        self.filter_search = None
        self.filter_bpm_min = None
        self.filter_bpm_max = None
        self.filter_genre = None
        self.filter_mix = None
        self.filter_issue = None
        self.active_table_source = []
        self.selected_track = None
        self.deck_status_label = None
        self.drag_drop_targets = set()
        self.waveform_analysis_pending = set()
        self.scan_cancel_event = threading.Event()
        self.scan_thread = None
        self.is_scanning_library = False
        self._shutting_down = False

        # ================= UI =================
        self.build()

        self.after(900, self.welcome_captain)

        self.after(50, self.ui_consumer)
        # Astra listener disabled by default (PyAudio GIL crash on some systems)
        # Enable manually via Settings or Ctrl+Shift+A
        # self.after(500, self.start_astra_listener)

        # ASTRA speaks a farewell when the captain shuts down the cabin
        self.protocol("WM_DELETE_WINDOW", self._on_app_close)

        # HUD entrance overlay peels away to reveal the live cabin
        self.after(100, self._show_online_overlay)

    # =====================================================
    # ASTRA POWER DOWN — animated shutdown + farewell
    # =====================================================
    def _on_app_close(self):
        """Cinematic power-down: a full-window overlay animates the cabin
        shutting down while ASTRA speaks her farewell, then the window
        tears down."""
        if self._shutting_down:
            return
        self._shutting_down = True
        self._speak_farewell()
        try:
            self._build_powerdown_overlay()
        except Exception:
            self.destroy()
            return
        self.after(1700, self.destroy)

    def _speak_farewell(self):
        """Fire-and-forget Turkish farewell through Windows SAPI so the
        window can close instantly while the voice finishes on its own."""
        try:
            import subprocess
            ps = (
                "Add-Type -AssemblyName System.Speech;"
                "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
                "try{$s.SelectVoiceByHints([System.Speech.Synthesis.VoiceGender]::Female)}catch{};"
                "$s.Rate=1;$s.Volume=90;"
                "$s.Speak('Sistem kapaniyor kaptan. Gorusmek uzere.')"
            )
            subprocess.Popen(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                creationflags=0x08000000, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass

    def _build_powerdown_overlay(self):
        """Full-window dark overlay: descending scanline + blinking status
        while the cabin powers down."""
        cv = tk.Canvas(self.main, bg="#07070C", highlightthickness=0)
        cv.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._power_canvas = cv
        self._pw_frame = 0
        w = cv.winfo_width() or self.winfo_width() or 900
        h = cv.winfo_height() or self.winfo_height() or 600
        if w < 50 or h < 50:
            w, h = 900, 600
        self._pw_w, self._pw_h = w, h
        cv.create_rectangle(10, 10, w - 10, h - 10, outline=RED, width=1)
        cv.create_text(w // 2, h // 2 - 80, text="◈ ASTRA POWER DOWN ◈",
                       fill=RED, font=("Segoe UI", 22, "bold"))
        cv.create_text(w // 2, h // 2 - 44, text="SİSTEM KAPANIYOR",
                       fill="#8A8A9A", font=("Consolas", 12, "bold"))
        self._animate_power_down()

    def _animate_power_down(self):
        cv = getattr(self, "_power_canvas", None)
        if cv is None:
            return
        try:
            if not cv.winfo_exists():
                return
            w = max(cv.winfo_width(), 50)
            h = max(cv.winfo_height(), 50)
        except Exception:
            return
        cv.delete("pw_dyn")
        f = self._pw_frame + 1
        self._pw_frame = f

        # descending scanline
        y = (f * 12) % (h - 60) + 30
        cv.create_rectangle(14, y, w - 14, y + 3, fill="#E63946",
                            stipple="gray50", tags="pw_dyn")
        cv.create_line(14, y - 12, w - 14, y - 12, fill="#5A0A12",
                       tags="pw_dyn")

        # blinking status
        if (f // 5) % 2 == 0:
            cv.create_text(w // 2, h // 2 + 24, text="● GÜÇ KESİLİYOR",
                           fill=RED if (f // 3) % 2 else AMBER,
                           font=("Consolas", 11, "bold"), tags="pw_dyn")
        else:
            cv.create_text(w // 2, h // 2 + 24, text="● GÜÇ KESİLİYOR",
                           fill="#3A3A46", font=("Consolas", 11, "bold"),
                           tags="pw_dyn")

        cv.after(30, self._animate_power_down)

    # =====================================================
    # ASTRA ONLINE — HUD entrance overlay after boot
    # =====================================================
    def _show_online_overlay(self):
        """Brief HUD-styled 'ASTRA ONLINE' reveal that peels away to
        expose the live cabin + captain greeting."""
        try:
            ov = tk.Canvas(self.main, bg="#07070C", highlightthickness=0)
            ov.place(relx=0, rely=0, relwidth=1, relheight=1)
            self._online_canvas = ov
            self._online_frame = 0
            try:
                self.update_idletasks()
                w = ov.winfo_width()
                h = ov.winfo_height()
            except Exception:
                w, h = 0, 0
            if w < 50 or h < 50:
                w = self.winfo_width() or 900
                h = self.winfo_height() or 600
            self._animate_online_overlay()
        except Exception:
            pass

    def _animate_online_overlay(self):
        ov = getattr(self, "_online_canvas", None)
        if ov is None:
            return
        try:
            if not ov.winfo_exists():
                return
            w = max(ov.winfo_width(), 50)
            h = max(ov.winfo_height(), 50)
        except Exception:
            return
        f = self._online_frame + 1
        self._online_frame = f
        ov.delete("all")
        cx, cy = w // 2, h // 2

        # HUD corner brackets inherited from the boot frame
        b = 34
        for x1, y1, x2, y2 in ((10, 10, b, 10), (10, 10, 10, b),
                               (w - 10, 10, w - b, 10), (w - 10, 10, w - 10, b),
                               (10, h - 10, b, h - 10), (10, h - 10, 10, h - b),
                               (w - 10, h - 10, w - b, h - 10),
                               (w - 10, h - 10, w - 10, h - b)):
            ov.create_line(x1, y1, x2, y2, fill=RED, width=2)

        # pulsing ring around the wordmark
        pulse = 0.6 + 0.4 * math.sin(f * 0.14)
        ov.create_oval(cx - 130 * pulse, cy - 64 * pulse,
                       cx + 130 * pulse, cy + 64 * pulse,
                       outline="#E63946" if (f // 12) % 2 else "#5A0A12",
                       width=2)

        # glow text (underglow layer first, bright on top)
        glow = 0.5 + 0.5 * math.sin(f * 0.18)
        ov.create_text(cx, cy - 6, text="ASTRA ONLINE",
                       fill="#5A0A12", font=("Segoe UI", 40, "bold"))
        ov.create_text(cx, cy - 6, text="ASTRA ONLINE",
                       fill=f"#{int(150 + 105 * glow):02x}"
                            f"{int(20 + 30 * glow):02x}"
                            f"{int(26 + 34 * glow):02x}",
                       font=("Segoe UI", 38, "bold"))
        ov.create_text(cx, cy + 40, text="◈ TÜM SİSTEMLER ÇEVRİMİÇİ ◈",
                       fill=GREEN, font=("Consolas", 11, "bold"))
        ov.create_text(cx, cy + 68, text="Kaptan, kabin hazır.",
                       fill="#8A8A9A", font=("Consolas", 10))
        ov.create_text(20, 22, anchor="w", text="ASTRA OS  ▸ v3",
                       fill="#5A5A6A", font=("Consolas", 9))

        if f < 60:
            ov.after(30, self._animate_online_overlay)
        else:
            # peel: brief green flash, then the canvas vanishes and the
            # live cabin (with the captain greeting) is revealed
            ov.delete("all")
            ov.create_rectangle(0, 0, w, h, fill="#07070C")
            ov.create_text(cx, cy, text="ÇEVRİMİÇİ",
                           fill=GREEN, font=("Segoe UI", 26, "bold"))
            ov.after(140, ov.destroy)

    # =====================================================
    # PERSISTENT HUD — live telemetry frame (runs forever)
    # =====================================================
    def _animate_hud(self):
        """Persistent sci-fi HUD: corner brackets, scanline sweep, clock,
        system telemetry strip, view indicator, audio engine status,
        network status, GPU metrics, mini waveform, particle field.
        Runs continuously as long as the window exists."""
        cv = getattr(self, "_hud_canvas", None)
        if cv is None:
            return
        try:
            if not cv.winfo_exists():
                return
            w = max(cv.winfo_width(), 100)
            h = max(cv.winfo_height(), 100)
        except Exception:
            return

        f = self._hud_frame + 1
        self._hud_frame = f
        cv.delete("hud")

        # In stage mode, collapse the HUD to a minimal pulse dot so the
        # fullscreen performance view stays clean (F11 toggles).
        if getattr(self, "_stage_mode", False):
            pulse_dot = 0.5 + 0.5 * math.sin(f * 0.15)
            dot_col = f"#{int(46 + 209 * pulse_dot):02x}{int(204 + 51 * pulse_dot):02x}{int(113 + 142 * pulse_dot):02x}"
            cv.create_oval(w - 14, 14, w - 4, 24, fill=dot_col,
                           outline="", tags="hud")
            cv.create_text(w - 12, 30, text="STAGE", fill="#4A4A5A",
                           font=("Consolas", 7), anchor="e", tags="hud")
            cv.after(50, self._animate_hud)
            return

        # Initialize particle field on first frame
        if not hasattr(self, "_hud_particles"):
            self._hud_particles = []
            import random
            for _ in range(24):
                self._hud_particles.append({
                    'x': random.uniform(20, w - 20),
                    'y': random.uniform(20, h - 20),
                    'vx': random.uniform(-0.3, 0.3),
                    'vy': random.uniform(-0.2, 0.2),
                    'size': random.uniform(1, 3),
                    'alpha': random.uniform(0.15, 0.45),
                    'color': random.choice(['#E63946', '#2ECC71', '#3498DB', '#F39C12', '#9B59B6'])
                })

        # corner targeting brackets (boot HUD style) - with animated corners
        b = 34 + int(3 * math.sin(f * 0.08))
        for x1, y1, x2, y2 in ((10, 10, b, 10), (10, 10, 10, b),
                               (w - 10, 10, w - b, 10), (w - 10, 10, w - 10, b),
                               (10, h - 10, b, h - 10), (10, h - 10, 10, h - b),
                               (w - 10, h - 10, w - b, h - 10),
                               (w - 10, h - 10, w - 10, h - b)):
            cv.create_line(x1, y1, x2, y2, fill=RED, width=2, tags="hud")

        # secondary inner brackets (dimmed)
        ib = 22
        for x1, y1, x2, y2 in ((18, 18, ib + 18, 18), (18, 18, 18, ib + 18),
                               (w - 18, 18, w - ib - 18, 18), (w - 18, 18, w - 18, ib + 18),
                               (18, h - 18, ib + 18, h - 18), (18, h - 18, 18, h - ib - 18),
                               (w - 18, h - 18, w - ib - 18, h - 18),
                               (w - 18, h - 18, w - 18, h - ib - 18)):
            cv.create_line(x1, y1, x2, y2, fill="#3A1A1A", width=1, tags="hud")

        # animated particle field (subtle atmospheric effect)
        import random
        for p in self._hud_particles:
            p['x'] += p['vx']
            p['y'] += p['vy']
            # wrap around
            if p['x'] < 15: p['x'] = w - 15
            if p['x'] > w - 15: p['x'] = 15
            if p['y'] < 15: p['y'] = h - 15
            if p['y'] > h - 15: p['y'] = 15
            # subtle pulsing
            pulse = 0.5 + 0.5 * math.sin(f * 0.03 + p['x'] * 0.01)
            alpha = int(p['alpha'] * 255 * pulse)
            r = int(p['color'][1:3], 16)
            g = int(p['color'][3:5], 16)
            b_col = int(p['color'][5:7], 16)
            col = f"#{r:02x}{g:02x}{b_col:02x}"
            cv.create_oval(p['x'] - p['size'], p['y'] - p['size'],
                           p['x'] + p['size'], p['y'] + p['size'],
                           fill=col, outline="", tags="hud")

        # horizontal scanline sweep (subtle, boot aesthetic)
        self._hud_scanline_y = (self._hud_scanline_y + 2) % (h - 20) + 10
        cv.create_line(14, self._hud_scanline_y, w - 14, self._hud_scanline_y,
                       fill="#E63946", stipple="gray25", tags="hud")

        # secondary scanline (faster, dimmer)
        self._hud_scanline_y2 = getattr(self, '_hud_scanline_y2', h - 20)
        self._hud_scanline_y2 = (self._hud_scanline_y2 + 3) % (h - 20) + 10
        cv.create_line(14, self._hud_scanline_y2, w - 14, self._hud_scanline_y2,
                       fill="#2ECC71", stipple="gray12", tags="hud")

        # live clock top-center
        import time
        clock = time.strftime("%H:%M:%S")
        date_str = time.strftime("%d.%m.%Y")
        cv.create_text(w // 2, 14, text=date_str, fill="#5A5A6A",
                       font=("Consolas", 8), tags="hud")
        cv.create_text(w // 2, 26, text=clock, fill="#8A8A9A",
                       font=("Consolas", 11, "bold"), tags="hud")

        # telemetry strip top-right (CPU, MEM, NET, GPU)
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory().percent
            # network
            net_io = psutil.net_io_counters()
            net_sent = net_io.bytes_sent / 1024 if net_io else 0
            net_recv = net_io.bytes_recv / 1024 if net_io else 0
            tel = f"CPU {cpu:4.1f}%  MEM {mem:4.1f}%"
            net_str = f"↑{net_sent:.0f}KB ↓{net_recv:.0f}KB"
        except Exception:
            tel = "CPU ----  MEM ----"
            net_str = "NET ----"

        cv.create_text(w - 16, 14, text=tel, fill="#6A6A7A",
                       font=("Consolas", 8), anchor="e", tags="hud")
        cv.create_text(w - 16, 26, text=net_str, fill="#4A6A5A",
                       font=("Consolas", 8), anchor="e", tags="hud")

        # audio engine status top-left
        audio_status = "AUDIO: READY"
        audio_color = "#2ECC71"
        try:
            if hasattr(self, 'playback') and self.playback:
                if getattr(self.playback, 'playing', False):
                    audio_status = "AUDIO: PLAYING"
                    audio_color = "#3498DB"
                elif getattr(self.playback, 'index', 0) > 0:
                    audio_status = "AUDIO: QUEUED"
                    audio_color = "#F39C12"
        except Exception:
            audio_status = "AUDIO: ----"
            audio_color = "#6A6A7A"

        cv.create_text(16, 14, text=audio_status, fill=audio_color,
                       font=("Consolas", 8, "bold"), anchor="w", tags="hud")

        # deck status (if available)
        deck_str = "DECKS: A:--- B:---"
        deck_color = "#5A5A6A"
        try:
            if hasattr(self, 'deck_engine') and self.deck_engine:
                deck_a = self.deck_engine.decks.get("A", {}).get("track") if hasattr(self.deck_engine, 'decks') else None
                deck_b = self.deck_engine.decks.get("B", {}).get("track") if hasattr(self.deck_engine, 'decks') else None
                a_name = (deck_a.get('name') or '---')[:12] if deck_a else '---'
                b_name = (deck_b.get('name') or '---')[:12] if deck_b else '---'
                deck_str = f"DECKS: A:{a_name} B:{b_name}"
                if deck_a or deck_b:
                    deck_color = "#2ECC71"
        except Exception:
            pass
        cv.create_text(16, 26, text=deck_str, fill=deck_color,
                       font=("Consolas", 8), anchor="w", tags="hud")

        # current view indicator bottom-left
        view = getattr(self, "current_view", "dashboard").upper()
        cv.create_text(16, h - 28, text=f"VIEW: {view}", fill="#5A5A6A",
                       font=("Consolas", 9), anchor="w", tags="hud")

        # library stats bottom-left (above view)
        lib_count = len(getattr(self, 'library', []))
        archived = getattr(self, 'total_archived', 0)
        cv.create_text(16, h - 42, text=f"LIB: {lib_count}  ARC: {archived}", fill="#4A4A5A",
                       font=("Consolas", 8), anchor="w", tags="hud")

        # frame time bottom-right (ms)
        frame_ms = getattr(self, "_frame_ms", 0)
        cv.create_text(w - 16, h - 16, text=f"{frame_ms:.1f} ms", fill="#5A5A6A",
                       font=("Consolas", 9), anchor="e", tags="hud")

        # FPS indicator
        fps = 1000.0 / frame_ms if frame_ms > 0 else 0
        cv.create_text(w - 16, h - 30, text=f"{fps:.0f} FPS", fill="#4A4A5A",
                       font=("Consolas", 8), anchor="e", tags="hud")

        # ASTRA status bottom-center (pulsing with more sophisticated animation)
        pulse = 0.5 + 0.5 * math.sin(f * 0.12)
        pulse2 = 0.5 + 0.5 * math.sin(f * 0.07 + 1.5)
        r = int(46 + 209 * pulse)
        g = int(204 + 51 * pulse2)
        b_col = int(113 + 142 * pulse)
        col = f"#{r:02x}{g:02x}{b_col:02x}"

        # status text changes based on system state
        if hasattr(self, 'is_playing') and self.is_playing:
            status_text = "◈ ASTRA LIVE ◈"
        elif hasattr(self, 'astra_active') and self.astra_active:
            status_text = "◈ ASTRA ACTIVE ◈"
        else:
            status_text = "◈ ASTRA ONLINE ◈"

        cv.create_text(w // 2, h - 16, text=status_text, fill=col,
                       font=("Consolas", 9, "bold"), tags="hud")

        # current language bottom-center (above ASTRA status)
        lang = get_language().upper()
        cv.create_text(w // 2, h - 32, text=f"LANG: {lang}", fill="#4A4A5A",
                       font=("Consolas", 8), tags="hud")

        # mini waveform preview (bottom-center, above lang) - shows current track waveform
        if hasattr(self, 'selected_track') and self.selected_track:
            wf = self.selected_track.get('waveform')
            if wf and len(wf) > 10:
                # draw mini waveform
                pts = wf[::max(1, len(wf) // 120)]  # downsample to ~120 points
                cx = w // 2
                cy = h - 58
                for i, v in enumerate(pts):
                    x = cx - 60 + i
                    h_bar = int(v * 20)
                    cv.create_line(x, cy, x, cy - h_bar, fill="#E63946", width=1, tags="hud")
                    cv.create_line(x, cy, x, cy + h_bar, fill="#E63946", width=1, tags="hud")

        # BPM/Key indicator if track selected
        if hasattr(self, 'selected_track') and self.selected_track:
            bpm = self.selected_track.get('bpm', 0)
            key = self.selected_track.get('key', '')
            if bpm:
                cv.create_text(w // 2, h - 72, text=f"BPM: {bpm:.1f}  KEY: {key}", fill="#3498DB",
                               font=("Consolas", 8, "bold"), tags="hud")

        # Energy meter (circular, right side)
        try:
            energy = 0.5 + 0.3 * math.sin(f * 0.15)
            if hasattr(self, 'selected_track') and self.selected_track:
                energy = self.selected_track.get('energy', 0.5)
            cx_e = w - 40
            cy_e = h // 2
            r_outer = 28
            r_inner = 22
            # background ring
            cv.create_oval(cx_e - r_outer, cy_e - r_outer,
                           cx_e + r_outer, cy_e + r_outer,
                           outline="#2A2A3A", width=2, tags="hud")
            # energy arc
            angle = int(energy * 360)
            cv.create_arc(cx_e - r_outer, cy_e - r_outer,
                          cx_e + r_outer, cy_e + r_outer,
                          start=90, extent=-angle, outline="#2ECC71", width=3, style="arc", tags="hud")
            cv.create_text(cx_e, cy_e, text=f"{int(energy*100)}%", fill="#2ECC71",
                           font=("Consolas", 8, "bold"), tags="hud")
            cv.create_text(cx_e, cy_e + 36, text="ENERGY", fill="#4A4A5A",
                           font=("Consolas", 7), tags="hud")
        except Exception:
            pass

        cv.after(50, self._animate_hud)

    # =====================================================
    # VIEW TRANSITION — HUD light sweep on view change
    # =====================================================
    def _play_view_transition(self):
        """Brief HUD-style horizontal light sweep across the screen
        whenever the captain switches views. Fast, non-blocking."""
        try:
            parent = getattr(self, "main", None)
            if parent is None or not parent.winfo_exists():
                return
            w = parent.winfo_width() or self.winfo_width() or 900
            h = parent.winfo_height() or self.winfo_height() or 600
            if w < 50 or h < 50:
                return

            if getattr(self, "_view_transition_canvas", None):
                try:
                    self._view_transition_canvas.destroy()
                except Exception:
                    pass

            cv = tk.Canvas(parent, bg=BG, highlightthickness=0)
            cv.place(relx=0, rely=0, relwidth=1, relheight=1)
            self._view_transition_canvas = cv
            self._vt_frame = 0
            self._vt_w, self._vt_h = w, h
            self._animate_view_transition()
        except Exception:
            pass

    def _animate_view_transition(self):
        cv = getattr(self, "_view_transition_canvas", None)
        if cv is None:
            return
        try:
            if not cv.winfo_exists():
                return
        except Exception:
            return
        f = self._vt_frame + 1
        self._vt_frame = f
        cv.delete("all")
        w, h = self._vt_w, self._vt_h

        # expanding horizontal light bar sweeping left → right
        sweep_x = (f * w) / 24
        cv.create_rectangle(0, 0, w, h, fill=BG)
        cv.create_rectangle(sweep_x, 0, sweep_x + 6, h, fill="#E63946")
        cv.create_rectangle(sweep_x - 40, 0, sweep_x, h, fill="#8B2530")
        cv.create_rectangle(sweep_x + 6, 0, sweep_x + 46, h, fill="#8B2530")

        # thin green tracer line behind
        cv.create_line(max(0, sweep_x - 90), h // 2,
                       max(0, sweep_x - 20), h // 2,
                       fill="#2ECC71", width=1)

        # view name caption riding with the sweep
        view = getattr(self, "current_view", "dashboard").upper()
        cv.create_text(min(sweep_x, w - 20), h // 2, text=view,
                       fill="#8A8A9A", font=("Consolas", 12, "bold"),
                       anchor="e")

        if f < 24:
            cv.after(16, self._animate_view_transition)
        else:
            cv.destroy()
            self._view_transition_canvas = None

    # =====================================================
    # LOG SYSTEM
    # =====================================================
    def log(self, msg):
        print("[AI]", msg)
        self.ai_messages.append(str(msg))
        activity = str(msg)

        if len(activity) > 170:
            activity = activity[:167] + "..."

        if hasattr(self, "ai_activity") and self.ai_activity.winfo_exists():
            self.after(
                0,
                lambda m=activity: self.ai_activity.configure(
                    text=f"{m}"
                )
            )

        if hasattr(self, "log_panel") and self.log_panel.winfo_exists():
            log_panel = self.log_panel
            self.after(0, lambda m=msg, panel=log_panel: panel.log(m) if panel.winfo_exists() else None)

    def set_status(self, text):
        if hasattr(self, "status"):
            self.status.configure(text=text)
        self.log(text)

    def get_ready_status(self):

        if self.plan["licensed"]:
            return (
                f"{self.plan['plan']} READY | "
                f"ARCHIVED: {self.total_archived}"
            )

        return (
            "DEMO READY | "
            f"ARCHIVED: {self.total_archived}/{self.plan['max_tracks']}"
        )

    # =====================================================
    # CAPTAIN GREETING — boot result handed over in style
    # =====================================================
    def welcome_captain(self):
        """Transient overlay card: real boot stats + hand the console
        transcript into the AI log so the boot story continues in-app."""
        try:
            from app.core import system_probe as probe

            # boot console transcript -> persistent log (continuity)
            seen = getattr(self, "_boot_logged", 0)
            lines = probe.transcript_lines()
            for line, _color in lines[seen:]:
                self.log(line)
            self._boot_logged = len(lines)
        except Exception:
            pass

        try:
            self._build_welcome_card()
        except Exception:
            pass

    def _build_welcome_card(self):
        card = ctk.CTkFrame(self.main, fg_color=SURFACE, corner_radius=10,
                            border_width=1, border_color=RED)
        card.place(relx=0.5, rely=0.05, anchor="n", relwidth=0.64, relheight=0.34)
        self._welcome_card = card

        hdr = ctk.CTkFrame(card, fg_color="transparent")
        hdr.pack(fill="x", padx=14, pady=(10, 2))
        ctk.CTkLabel(hdr, text="✦ ASTRA", font=F_H3, text_color=BLUE_BRIGHT
                     ).pack(side="left")
        ctk.CTkLabel(hdr, text="SİSTEM AÇILIŞ RAPORU", font=F_H4,
                     text_color=TEXT_SECONDARY).pack(side="left", padx=10)
        ctk.CTkLabel(hdr, text="● ÇEVRİMİÇİ", font=F_META, text_color=GREEN
                     ).pack(side="right")

        ctk.CTkLabel(card, text="HOŞ GELDİN KAPTAN 🎧",
                     font=("Segoe UI", 26, "bold"), text_color=TEXT_PRIMARY
                     ).pack(anchor="w", padx=16, pady=(4, 2))
        ctk.CTkLabel(card, text="Nöral çekirdek açıldı, kabin hazır. "
                                "Kütüphanen ve donanımın seni bekliyor.",
                     font=F_BODY, text_color=TEXT_SECONDARY
                     ).pack(anchor="w", padx=16, pady=(0, 8))

        # live stats row
        stats = self._boot_stats()
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=12)
        for label, value, ok in stats:
            cell = ctk.CTkFrame(row, fg_color=BG, corner_radius=6,
                                border_width=1, border_color=BORDER)
            cell.pack(side="left", fill="x", expand=True, padx=4)
            ctk.CTkLabel(cell, text=label, font=F_META, text_color=TEXT_DIM
                         ).pack(anchor="w", padx=8, pady=(6, 0))
            ctk.CTkLabel(cell, text=value, font=("Consolas", 11, "bold"),
                         text_color=GREEN if ok else AMBER
                         ).pack(anchor="w", padx=8, pady=(0, 6))

        ctk.CTkLabel(card, text="— Astro ile sohbet et, sahneyi kur ya da "
                                "sıradaki parçayı sür. Karar senin. —",
                     font=F_META, text_color=RED_DIM
                     ).pack(anchor="w", padx=16, pady=(10, 8))

        card.after(11000, card.destroy)

    def _boot_stats(self):
        """Cheap real stats for the greeting card (no blocking probes)."""
        out = []

        lib_n = len(self.saved_tracks or [])
        out.append(("KÜTÜPHANE", f"{lib_n} parça", lib_n > 0))

        plan = self.plan.get("plan", "DEMO")
        licensed = bool(self.plan.get("licensed"))
        out.append(("LİSANS", plan if licensed else "DEMO", licensed))

        try:
            import sounddevice as sd
            dev = None
            for d in sd.query_devices():
                if d.get("max_output_channels", 0) > 0:
                    dev = d.get("name", "ses")
                    break
            out.append(("SES", (dev or "—")[:22], dev is not None))
        except Exception:
            out.append(("SES", "—", False))

        try:
            import mido
            ports = mido.get_input_names() + mido.get_output_names()
            out.append(("MIDI", f"{len(ports)} port", len(ports) > 0))
        except Exception:
            out.append(("MIDI", "—", False))

        from app.core.system_probe import _neural_model_path
        if _neural_model_path():
            out.append(("NÖRAL MODEL", "önbellekte", True))
        else:
            out.append(("NÖRAL MODEL", "ilk kullanımda eğitilecek", True))

        return out

    # =====================================================
    # UI BUILD
    # =====================================================
    def build(self):

        # SIDEBAR
        self.sidebar = Sidebar(self)
        self.sidebar.pack(side="left", fill="y")

        # MAIN
        self.main = ctk.CTkFrame(self, fg_color=BG)
        self.main.pack(side="right", fill="both", expand=True)

        # =====================================================
        # PERSISTENT HUD OVERLAY — sci-fi telemetry frame
        # =====================================================
        self._hud_canvas = tk.Canvas(self.main, bg=BG, highlightthickness=0)
        self._hud_canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._hud_frame = 0
        self._hud_scanline_y = 0
        self._animate_hud()

        # =====================================================
        # HEADER — Pro DJ style (clean, single-line)
        # =====================================================
        header = ctk.CTkFrame(self.main, fg_color=SURFACE, corner_radius=0, height=48)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        # Left: Logo + version
        left = ctk.CTkFrame(header, fg_color="transparent")
        left.pack(side="left", padx=16, pady=8)

        ctk.CTkLabel(
            left, text="DJ AI OS", font=F_H3, text_color=RED
        ).pack(side="left")

        ctk.CTkLabel(
            left, text=f"  {self.app_version}", font=F_META, text_color=TEXT_DIM
        ).pack(side="left", padx=(4, 0))

        # Separator
        sep = ctk.CTkFrame(header, width=1, height=24, fg_color=BORDER)
        sep.pack(side="left", padx=12)

        # Center: Now playing info
        self.now_playing_label = ctk.CTkLabel(
            header, text="No track loaded", font=F_BODY, text_color=TEXT_SECONDARY
        )
        self.now_playing_label.pack(side="left", padx=8)

        # Right: Status
        self.status = ctk.CTkLabel(
            header, text=self.get_ready_status(), font=F_META, text_color=TEXT_DIM
        )
        self.status.pack(side="right", padx=16)

        # Activity line
        self.ai_activity = ctk.CTkLabel(
            header, text="", font=F_META, text_color=TEXT_DIM, anchor="w"
        )
        self.ai_activity.pack(side="right", padx=8)

        # Bottom separator
        sep_bottom = ctk.CTkFrame(self.main, height=1, fg_color=BORDER)
        sep_bottom.pack(fill="x", side="top")

        # =====================================================
        # CONTENT AREA
        # =====================================================
        self.content = ctk.CTkScrollableFrame(self.main, fg_color="transparent",
                                                scrollbar_button_color=SURFACE_RAISED,
                                                scrollbar_button_hover_color=BORDER)
        self.content.pack(fill="both", expand=True, padx=10, pady=(8, 0))

        # =====================================================
        # MINI PLAYER (persistent bottom bar)
        # =====================================================
        self.mini_player = MiniPlayer(
            self.main,
            on_play=self.toggle_playback,
            on_stop=self.stop_playback,
            on_next=self.next_track,
        )
        self.mini_player.pack(fill="x", side="bottom")

        # QUICK STATS BAR
        self.stats_bar = QuickStatsBar(self.main)
        self.stats_bar.pack(fill="x", side="bottom")

        self.bind_global_shortcuts()
        self.enable_global_drag_drop()
        self.build_dashboard()

    def enable_global_drag_drop(self):

        self.enable_drag_drop(self, quiet=True)

    def clear_content(self):

        for child in self.content.winfo_children():
            child.destroy()

    def bind_global_shortcuts(self):

        shortcuts = {
            "<Control-l>": self.load_library,
            "<Control-g>": self.generate_set,
            "<Control-p>": self.play_set,
            "<space>": self.toggle_playback,
            "<Control-s>": lambda: self.set_view("show_director"),
            "<Control-d>": lambda: self.set_view("deck_studio"),
            "<Control-e>": lambda: self.set_view("export_center"),
            "<Control-r>": lambda: self.set_view("genre_review"),
            "<Control-f>": self.focus_filter_search,
            "<Control-k>": self.open_command_palette,
            "<Control-Shift-D>": self.open_next_duplicate_review,
            "<Control-Shift-Key-D>": self.open_next_duplicate_review,
            "<Control-Key-1>": lambda: self.load_selected_to_deck("A"),
            "<Control-Key-2>": lambda: self.load_selected_to_deck("B"),
            "<Control-m>": self.build_auto_mix_from_decks,
            "<F5>": self.refresh_current_view,
            "<Control-b>": lambda: self.set_view("dj_booth"),
            "<Control-F11>": self.toggle_stage_mode,
            "<F11>": self.toggle_stage_mode,
        }

        for key, command in shortcuts.items():
            self.bind_all(key, lambda _e, c=command: self.run_shortcut(c))

    # =====================================================
    # STAGE MODE — immersive fullscreen DJ performance
    # =====================================================
    def toggle_stage_mode(self):
        """Enter/exit immersive fullscreen performance mode. In stage
        mode the sidebar and header chrome collapse, leaving only the
        DJ booth as a cinematic full-screen stage."""
        self._stage_mode = not getattr(self, "_stage_mode", False)

        if self._stage_mode:
            # switch to DJ booth, hide chrome, go fullscreen
            self.set_view("dj_booth")
            try:
                if hasattr(self, "sidebar") and self.sidebar.winfo_exists():
                    self.sidebar.pack_forget()
            except Exception:
                pass
            try:
                self.attributes("-fullscreen", True)
            except Exception:
                try:
                    self.state("zoomed")
                except Exception:
                    pass
            self.set_status("STAGE MODE ENGAGED — F11 ile cik")
        else:
            # restore chrome and window
            try:
                if hasattr(self, "sidebar") and self.sidebar.winfo_exists():
                    self.sidebar.pack(side="left", fill="y")
            except Exception:
                pass
            try:
                self.attributes("-fullscreen", False)
            except Exception:
                pass
            try:
                self.state("normal")
            except Exception:
                pass
            self.set_status("STAGE MODE EXITED")

    def run_shortcut(self, command):

        try:
            command()
        except Exception as e:
            self.set_status(f"SHORTCUT ERROR: {e}")

        return "break"

    def toggle_playback(self):

        if self.is_playing:
            self.stop_playback()
        else:
            self.play_set()

    def focus_filter_search(self):

        widget = getattr(self, "filter_search_entry", None)

        if widget and widget.winfo_exists():
            widget.focus_set()

    def refresh_current_view(self):

        self.set_view(self.current_view)

    def open_command_palette(self):

        CommandPalette(self, self.get_command_palette_items())

    def get_command_palette_items(self):

        return [
            {
                "title": "Load Library",
                "subtitle": "Yeni muzik klasoru sec ve analiz baslat.",
                "shortcut": "Ctrl+L",
                "keywords": "load library analyze scan folder",
                "action": self.load_library,
            },
            {
                "title": "Generate AI Set",
                "subtitle": "BPM, enerji ve harmoniye gore set olustur.",
                "shortcut": "Ctrl+G",
                "keywords": "set builder playlist performans",
                "action": self.generate_set,
            },
            {
                "title": "Play / Stop",
                "subtitle": "Aktif seti cal veya durdur.",
                "shortcut": "Space",
                "keywords": "play stop live",
                "action": self.toggle_playback,
            },
            {
                "title": "Next Duplicate Review",
                "subtitle": "Muzik Doktoru duplicate karar penceresini ac.",
                "shortcut": "Ctrl+Shift+D",
                "keywords": "doctor duplicate eskiyi sil",
                "action": self.open_next_duplicate_review,
            },
            {
                "title": "Audit DJ Library Output",
                "subtitle": "Sifir dosya, eski discovered klasor ve BPM risklerini tara.",
                "shortcut": "",
                "keywords": "audit doctor output zero discovered bpm archive",
                "action": self.run_archive_audit,
            },
            {
                "title": "Focus Search",
                "subtitle": "Aktif tablo aramasina odaklan.",
                "shortcut": "Ctrl+F",
                "keywords": "search filter bpm genre",
                "action": self.focus_filter_search,
            },
            {
                "title": "Show Director",
                "subtitle": "4 saatlik gece akis planini yonet.",
                "shortcut": "Ctrl+S",
                "keywords": "director performance timeline",
                "action": lambda: self.set_view("show_director"),
            },
            {
                "title": "DJ Heart",
                "subtitle": "Setin duygusal nabzini, kalp skorunu ve crowd anini gor.",
                "shortcut": "",
                "keywords": "heart emotion crowd pulse duygu kalp",
                "action": lambda: self.set_view("dj_heart"),
            },
            {
                "title": "Voice Assistant",
                "subtitle": "Sesli DJ AI mimarisini ve entegrasyon gereksinimlerini gor.",
                "shortcut": "",
                "keywords": "voice speech realtime microphone chatgpt ses",
                "action": lambda: self.set_view("settings"),
            },
            {
                "title": "Deck Studio",
                "subtitle": "Deck A/B, otomatik mix ve crossfade planini ac.",
                "shortcut": "Ctrl+D",
                "keywords": "deck automix crossfade",
                "action": lambda: self.set_view("deck_studio"),
            },
            {
                "title": "Remix Lab",
                "subtitle": "Vocal ayir, remix blueprint olustur ve stem akisini planla.",
                "shortcut": "",
                "keywords": "remix vocal stems demucs acapella beat",
                "action": lambda: self.set_view("remix_lab"),
            },
            {
                "title": "Export Center",
                "subtitle": "M3U, manifest ve Rekordbox export ekranini ac.",
                "shortcut": "Ctrl+E",
                "keywords": "export rekordbox playlist m3u",
                "action": lambda: self.set_view("export_center"),
            },
            {
                "title": "Genre Review",
                "subtitle": "Unknown/discovered tarzlari akademik aileye bagla.",
                "shortcut": "Ctrl+R",
                "keywords": "genre unknown discovered review",
                "action": lambda: self.set_view("genre_review"),
            },
            {
                "title": "Global Trends",
                "subtitle": "Trend ve DJ arsiv onerileri ekranina git.",
                "shortcut": "",
                "keywords": "trend beatport spotify cloud archive",
                "action": lambda: self.set_view("global_trends"),
            },
            {
                "title": "Refresh View",
                "subtitle": "Aktif ekrani yeniden yukle.",
                "shortcut": "F5",
                "keywords": "refresh reload",
                "action": self.refresh_current_view,
            },
            {
                "title": "DJ Booth",
                "subtitle": "Gelecekten gelmis DJ kabini — vinyl, BPM scope, harmonik cark.",
                "shortcut": "Ctrl+B",
                "keywords": "booth cockpit vinyl bpm scope harmonic wheel deck",
                "action": lambda: self.set_view("dj_booth"),
            },
            {
                "title": "DJ Coach",
                "subtitle": "Setini degerlendir, guclu ve zayif noktalari ogren.",
                "shortcut": "",
                "keywords": "coach analyze set performance grade",
                "action": lambda: self.set_view("dj_coach"),
            },
            {
                "title": "Library Map",
                "subtitle": "Kutuphaneni scatter plot'ta kesfet.",
                "shortcut": "",
                "keywords": "map scatter library dna energy brightness",
                "action": lambda: self.set_view("library_map"),
            },
            {
                "title": "Smart Set",
                "subtitle": "Mekan tipine gore enerji egrisi ile otomatik set olustur.",
                "shortcut": "",
                "keywords": "smart set wedding club festival template",
                "action": lambda: self.set_view("smart_set"),
            },
            {
                "title": "DJ Profile",
                "subtitle": "DJ stil DNA'ni olustur, benzer parcalari bul.",
                "shortcut": "",
                "keywords": "profile dna style similarity genre energy",
                "action": lambda: self.set_view("dj_profile"),
            },
        ]

    def open_next_duplicate_review(self):

        pending = [
            track
            for track in self.get_visible_tracks()
            if track.get("duplicate_status") == "POSSIBLE_DUPLICATE"
        ]

        if not pending:
            self.set_status("Muzik Doktoru: bekleyen duplicate bulunamadi.")
            return

        self.show_duplicate_review(pending[0])

    def set_view(self, view):

        if getattr(self, "current_view", None) != view:
            self._play_view_transition()
        self.current_view = view
        if view != "astra_chat":
            self.astra_active = False
        self.clear_content()

        builders = {
            "performance_dash": self.build_performance_dashboard,
            "dashboard": self.build_dashboard,
            "library": self.build_library_view,
            "archive_guardian": self.build_archive_guardian_view,
            "analyze": self.build_analyze_view,
            "set_builder": self.build_set_builder_view,
            "performance": self.build_performance_view,
            "set_show": self.build_set_show_view,
            "dj_heart": self.build_dj_heart_view,
            "show_director": self.build_show_director_view,
            "deck_studio": self.build_deck_studio_view,
            "remix_lab": self.build_remix_lab_view,
            "astra_chat": self.build_astra_chat_view,
            "export_center": self.build_export_center_view,
            "cloud_export": self.build_cloud_export_view,
            "genre_review": self.build_genre_review_view,
            "global_trends": self.build_global_trends_view,
            "crate_builder": self.build_crate_builder_view,
            "live": self.build_live_view,
            "ai_memory": self.build_ai_memory_view,
            "account": self.build_account_view,
            "settings": self.build_settings_view,
            "dj_booth": self.build_dj_booth_view,
            "beat_studio": self.build_beat_studio_view,
            "neural_synth": self.build_neural_synth_view,
            "neural_bridge": self.build_neural_bridge_view,
            "pioneer_link": self.build_pioneer_link_view,
            "dj_coach": self.build_dj_coach_view,
            "library_map": self.build_library_map_view,
            "smart_set": self.build_smart_set_view,
            "dj_profile": self.build_dj_profile_view,
        }

        builder = builders.get(view, self.build_dashboard)
        builder()

    def make_section_title(self, parent, title, subtitle=""):

        box = ctk.CTkFrame(parent, fg_color="transparent")
        box.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            box,
            text=title,
            font=F_H2,
            text_color=TEXT_PRIMARY
        ).pack(anchor="w")

        if subtitle:
            ctk.CTkLabel(
                box,
                text=subtitle,
                font=F_META,
                text_color=TEXT_SECONDARY
            ).pack(anchor="w", pady=(2, 0))

    def make_metric(self, parent, label, value):

        card = ctk.CTkFrame(parent, fg_color=SURFACE, corner_radius=8, border_width=1, border_color=BORDER)
        card.pack(side="left", fill="x", expand=True, padx=5)

        ctk.CTkLabel(
            card,
            text=str(value),
            font=F_H2,
            text_color=RED
        ).pack(anchor="w", padx=14, pady=(12, 0))

        ctk.CTkLabel(
            card,
            text=label,
            font=F_META,
            text_color=TEXT_SECONDARY
        ).pack(anchor="w", padx=14, pady=(0, 12))

    def build_filter_bar(self, parent, tracks):

        self.active_table_source = list(tracks)

        bar = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=8)
        bar.pack(fill="x", pady=(0, 10))

        self.filter_search = StringVar(value="")
        self.filter_bpm_min = StringVar(value="")
        self.filter_bpm_max = StringVar(value="")
        self.filter_genre = StringVar(value="ALL")
        self.filter_mix = StringVar(value="ALL")
        self.filter_issue = StringVar(value="ALL")

        self.filter_search_entry = ctk.CTkEntry(
            bar,
            textvariable=self.filter_search,
            placeholder_text="Search track / artist / genre",
            width=260
        )
        self.filter_search_entry.pack(side="left", padx=(12, 6), pady=10)

        ctk.CTkEntry(
            bar,
            textvariable=self.filter_bpm_min,
            placeholder_text="Min BPM",
            width=90
        ).pack(side="left", padx=6, pady=10)

        ctk.CTkEntry(
            bar,
            textvariable=self.filter_bpm_max,
            placeholder_text="Max BPM",
            width=90
        ).pack(side="left", padx=6, pady=10)

        ctk.CTkComboBox(
            bar,
            variable=self.filter_genre,
            values=self.options_for(tracks, "genre"),
            width=170,
            command=lambda _v: self.apply_table_filters()
        ).pack(side="left", padx=6, pady=10)

        ctk.CTkComboBox(
            bar,
            variable=self.filter_mix,
            values=self.options_for(tracks, "mix_strategy"),
            width=150,
            command=lambda _v: self.apply_table_filters()
        ).pack(side="left", padx=6, pady=10)

        ctk.CTkComboBox(
            bar,
            variable=self.filter_issue,
            values=[
                "ALL",
                "NEEDS_RESEARCH",
                "DUPLICATES",
                "LOW_BITRATE",
                "ANALYSIS_FALLBACK",
                "LOW_AI_EAR",
                "VOCAL_RISK"
            ],
            width=160,
            command=lambda _v: self.apply_table_filters()
        ).pack(side="left", padx=6, pady=10)

        ctk.CTkButton(
            bar,
            text="APPLY",
            width=82,
            command=self.apply_table_filters
        ).pack(side="left", padx=6, pady=10)

        ctk.CTkButton(
            bar,
            text="RESET",
            width=82,
            command=self.reset_table_filters
        ).pack(side="left", padx=6, pady=10)

    def options_for(self, tracks, field):

        values = {
            str(track.get(field) or "").strip()
            for track in tracks
            if str(track.get(field) or "").strip()
        }

        return ["ALL"] + sorted(values)

    def apply_table_filters(self):

        if not hasattr(self, "table") or not self.table.winfo_exists():
            return

        tracks = self.filtered_tracks(self.active_table_source)
        self.table.set_tracks(tracks)
        self.log(f"Filter applied: {len(tracks)} tracks visible.")

    def reset_table_filters(self):

        for var in (
            self.filter_search,
            self.filter_bpm_min,
            self.filter_bpm_max
        ):
            if var:
                var.set("")

        for var in (
            self.filter_genre,
            self.filter_mix,
            self.filter_issue
        ):
            if var:
                var.set("ALL")

        self.apply_table_filters()

    def build_music_doctor_bar(self, parent, tracks):

        bar = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=8)
        bar.pack(fill="x", pady=(0, 10))

        duplicate_count = self.count_value(
            tracks,
            "duplicate_status",
            "POSSIBLE_DUPLICATE"
        )
        research_count = self.count_value(
            tracks,
            "research_status",
            "NEEDS_REVIEW"
        )
        low_bitrate_count = len([
            track
            for track in tracks
            if (self.safe_float(track.get("bitrate")) or 0) < 256
        ])

        ctk.CTkLabel(
            bar,
            text=(
                "MUSIC DOCTOR | "
                f"Duplicates: {duplicate_count} | "
                f"Needs research: {research_count} | "
                f"Low bitrate: {low_bitrate_count}"
            ),
            text_color=ACCENT,
            font=("Segoe UI", 13, "bold")
        ).pack(side="left", padx=12, pady=10)

        ctk.CTkButton(
            bar,
            text="NEXT DUPLICATE",
            width=135,
            command=self.open_next_duplicate_review
        ).pack(side="right", padx=(6, 12), pady=10)

        ctk.CTkButton(
            bar,
            text="AUDIT OUTPUT",
            width=125,
            command=self.run_archive_audit
        ).pack(side="right", padx=6, pady=10)

        ctk.CTkButton(
            bar,
            text="SHOW LOW BITRATE",
            width=140,
            command=lambda: self.show_issue_filter("LOW_BITRATE")
        ).pack(side="right", padx=6, pady=10)

        ctk.CTkButton(
            bar,
            text="SHOW RESEARCH",
            width=130,
            command=lambda: self.show_issue_filter("NEEDS_RESEARCH")
        ).pack(side="right", padx=6, pady=10)

        ctk.CTkButton(
            bar,
            text="SHOW DUPLICATES",
            width=140,
            command=lambda: self.show_issue_filter("DUPLICATES")
        ).pack(side="right", padx=6, pady=10)

    def show_issue_filter(self, issue):

        if not self.filter_issue:
            self.set_status("Filter hazir degil. Once tablo ekranini ac.")
            return

        self.filter_issue.set(issue)
        self.apply_table_filters()

    def run_archive_audit(self):

        report = self.archive_auditor.audit(self.archive_output_folder)
        report_path = self.archive_auditor.write_report(report)
        cleanup_plan = self.archive_reconciler.build_cleanup_plan()
        cleanup_path = self.archive_reconciler.write_plan(cleanup_plan)
        self.last_archive_audit = report
        self.last_archive_cleanup_plan = cleanup_plan
        self.set_status(
            f"{report['summary']} | cleanup={cleanup_plan['summary']} | "
            f"report={report_path}"
        )

        for path in report["zero_byte_files"][:5]:
            self.log(f"Archive Audit ZERO BYTE: {path}")

        for path in report["legacy_discovered_folders"][:5]:
            self.log(f"Archive Audit LEGACY DISCOVERED: {path}")

        for item in report["tempo_anomalies"][:5]:
            self.log(
                "Archive Audit TEMPO RISK: "
                f"{item.get('bpms')} | {item.get('path')}"
            )

        for group in report.get("duplicate_name_groups", [])[:5]:
            self.log(
                "Archive Audit RENAME DUPLICATE RISK: "
                f"{group.get('count')} files | {group.get('key')}"
            )

        for group in cleanup_plan.get("duplicate_groups", [])[:5]:
            self.log(
                "Archive Cleanup EXACT DUPLICATE: keep="
                f"{group.get('keep')} | duplicates={len(group.get('duplicates', []))}"
            )

        self.log(f"Archive cleanup plan: {cleanup_path}")

    def build_voice_command_bar(self, parent):

        bar = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=8)
        bar.pack(fill="x", pady=(0, 10))

        self.voice_command_text = StringVar(value="")

        ctk.CTkLabel(
            bar,
            text="VOICE AI",
            text_color=ACCENT,
            font=("Segoe UI", 13, "bold")
        ).pack(side="left", padx=(12, 8), pady=10)

        ctk.CTkEntry(
            bar,
            textvariable=self.voice_command_text,
            placeholder_text="Ornek: set olustur, cal, dur, kalp ekranini ac...",
            width=420
        ).pack(side="left", padx=6, pady=10)

        ctk.CTkButton(
            bar,
            text="RUN COMMAND",
            width=125,
            command=self.run_voice_text_command
        ).pack(side="left", padx=6, pady=10)

        ctk.CTkButton(
            bar,
            text="LISTEN MIC",
            width=105,
            command=self.run_voice_mic_once
        ).pack(side="left", padx=6, pady=10)

        ctk.CTkButton(
            bar,
            text="SPEAK LAST",
            width=105,
            command=self.speak_last_voice_reply
        ).pack(side="left", padx=6, pady=10)

        ctk.CTkButton(
            bar,
            text="VOICE TEST",
            width=105,
            command=self.run_voice_diagnostics
        ).pack(side="left", padx=6, pady=10)

        ctk.CTkButton(
            bar,
            text="VOICE SETUP",
            width=115,
            command=lambda: self.set_view("settings")
        ).pack(side="left", padx=6, pady=10)

    def run_voice_text_command(self):

        text = ""

        if hasattr(self, "voice_command_text"):
            text = self.voice_command_text.get()

        # Build context for AstraBrain
        context = {
            "library": self.library or self.saved_tracks,
            "tracks": self.current_set or self.library or self.saved_tracks,
            "track": self.selected_track,
            "path": self.selected_track.get("path") if self.selected_track else None,
        }

        result = self.voice_assistant.interpret_command(text, context=context)
        self.execute_voice_intent(result)

    def run_voice_mic_once(self):

        self.set_status("VOICE AI: Mikrofon dinleniyor...")

        threading.Thread(
            target=self.voice_mic_worker,
            daemon=True
        ).start()

    def voice_mic_worker(self):

        heard = self.voice_assistant.listen_once() or {
            "ok": False,
            "text": "",
            "error": "Mikrofon motoru sonuc dondurmedi.",
        }

        if not heard.get("ok"):
            self.after(
                0,
                lambda e=heard.get("error"): self.set_status(
                    f"VOICE AI MIC ERROR: {e}"
                )
            )
            self.after(
                0,
                lambda e=heard.get("error"): self.voice_assistant.speak_reply(
                    f"Mikrofon hatasi. {e}"
                )
            )
            return

        text = heard.get("text", "")
        result = self.voice_assistant.interpret_command(text)

        self.after(
            0,
            lambda t=text, r=result: self.apply_voice_mic_result(t, r)
        )

    def apply_voice_mic_result(self, text, result):

        if hasattr(self, "voice_command_text"):
            self.voice_command_text.set(text)

        self.execute_voice_intent(result)

    def start_astra_listener(self):

        if self.astra_listener_running:
            return

        self.astra_listener_running = True
        self.astra_listener_thread = threading.Thread(
            target=self.astra_listener_worker,
            daemon=True
        )
        self.astra_listener_thread.start()
        self.set_status("Astra: sürekli dinleme başlatıldı.")

    def stop_astra_listener(self):

        self.astra_listener_running = False

        if self.astra_listener_thread:
            self.astra_listener_thread.join(timeout=1)
            self.astra_listener_thread = None

    def astra_listener_worker(self):

        while self.astra_listener_running:
            heard = self.voice_assistant.listen_once(timeout=6, phrase_time_limit=5) or {
                "ok": False,
                "text": "",
            }

            if not heard.get("ok"):
                continue

            text = str(heard.get("text", "")).strip()
            normalized = text.lower()

            if not normalized:
                continue

            # If Astra is active, speak naturally without requiring the wake word.
            if not self.current_view == "astra_chat" and not self.astra_active:
                direct_command = self.voice_assistant.interpret_command(text)
                if direct_command.get("intent") != "UNKNOWN":
                    self.after(0, lambda t=text, r=direct_command: self.apply_voice_mic_result(t, r))
                    continue

            wake_words = ["astra aç", "astra open", "astra başlat", "astra dinle"]
            is_wake = normalized in wake_words or any(normalized.startswith(wake + " ") for wake in wake_words)
            command_text = self.strip_astra_wake(text)

            if self.current_view == "astra_chat" or self.astra_active:
                if command_text:
                    command_result = self.voice_assistant.interpret_command(command_text)
                    if command_result.get("intent") != "UNKNOWN":
                        self.after(0, lambda t=command_text, r=command_result: self.apply_voice_mic_result(t, r))
                        continue

                    self.after(0, lambda t=command_text: self.process_astra_chat_text(t))
                    continue

                if is_wake:
                    self.after(0, lambda: self.process_astra_wake(text))
                    continue

                continue

            if self.astra_passive:
                command_result = self.voice_assistant.interpret_command(text)
                if command_result.get("intent") != "UNKNOWN":
                    self.after(0, lambda t=text, r=command_result: self.apply_voice_mic_result(t, r))
                    continue

                self.after(0, lambda t=text: self.process_astra_passive_text(t))
                continue

            if is_wake:
                if command_text:
                    command_result = self.voice_assistant.interpret_command(command_text)
                    if command_result.get("intent") != "UNKNOWN":
                        self.after(0, lambda t=command_text, r=command_result: self.apply_voice_mic_result(t, r))
                        continue

                    self.after(0, lambda t=command_text: self.process_astra_chat_text(t))
                    continue

                self.after(0, lambda t=text: self.process_astra_wake(t))

    def process_astra_wake(self, text):

        if self.current_view == "astra_chat" or self.astra_active:
            self.set_status("Astra: zaten açık, doğrudan komutunu verebilirsin.")
            self.render_jarvis_chat_message(
                "Astra",
                "Zaten açığım. Doğrudan isteğini söyle; her seferinde beni adımlaman gerekmez."
            )
            self.astra_assistant.speak(
                "Zaten açığım. Doğrudan isteğini söyle; her seferinde beni adımlaman gerekmez."
            )
            return

        self.astra_active = True
        self.set_view("astra_chat")
        self.set_status("Astra: sesi aldım, ikimiz de sahnedeyiz.")
        self.render_jarvis_chat_message(
            "Astra",
            "Seni duyuyorum. Ne yapmak istersin? Set, remix veya kamera kontrolü için hazırım."
        )
        self.astra_assistant.speak(
            "Seni duyuyorum. Ne yapmak istersin? Set, remix veya kamera kontrolü için hazırım."
        )

    def strip_astra_wake(self, text):

        if not text:
            return ""

        normalized = str(text or "").strip().lower()
        wake_phrases = ["astra aç", "astra open", "astra başlat", "astra dinle", "astra"]

        for wake in wake_phrases:
            if normalized.startswith(wake):
                cleaned = normalized[len(wake):].strip(" ,.!?\"'“”")
                return cleaned

        return text.strip()

    def process_astra_chat_text(self, text):

        self.astra_active = True
        self.astra_passive = False
        self.set_view("astra_chat")
        self.render_jarvis_chat_message("Sen", text)
        self.set_status("Astra: konuşmanı işliyorum...")

        threading.Thread(
            target=self.jarvis_chat_worker,
            args=(text,),
            daemon=True
        ).start()

    def process_astra_passive_text(self, text):

        self.astra_passive = True
        self.astra_active = False

        self.astra_assistant.memory.remember("user", text)
        self.astra_assistant.memory.log_unknown_terms(
            self.astra_assistant.memory.extract_candidate_terms(text)
        )

        self.set_status("Astra: konuşmanı sessizce hafızama alıyorum.")

    def process_astra_enable_passive(self, text=None):

        if self.astra_passive:
            self.set_status("Astra: zaten sessiz moddayım.")
            return

        self.astra_passive = True
        self.astra_active = False
        self.set_status(
            "Astra: şimdi sessizce dinliyorum. Konuşmalarını hafızama alacağım."
        )
        self.astra_assistant.memory.remember(
            "assistant",
            "Sessiz mod etkin. Normal konuşmaları dinliyorum."
        )

    def process_astra_disable_passive(self, text=None):

        if not self.astra_passive:
            self.set_status("Astra: sessiz mod zaten kapalı.")
            return

        self.astra_passive = False
        self.set_status("Astra: sessiz mod kapandı. Komutlarını bekliyorum.")

    def run_voice_diagnostics(self):

        summary = self.voice_assistant.capability_summary()
        tests = [
            f"TTS={summary.get('tts_engine')} ({'READY' if summary.get('tts_available') else 'MISSING'})",
            f"STT={summary.get('stt_engine')} ({'READY' if summary.get('stt_available') else 'MISSING'})",
            f"Turkish voice={summary.get('turkish_voice') or 'NOT FOUND'}",
            f"Turkish TTS={'YES' if summary.get('turkish_tts_ready') else 'NO'}",
        ]
        result_text = (
            "Sesli asistan testi tamamlandi. "
            + " | ".join(tests)
        )

        self.set_status(f"VOICE AI: {result_text}")
        self.last_voice_reply = result_text
        self.voice_assistant.speak_reply(result_text)

    def speak_last_voice_reply(self):

        text = getattr(self, "last_voice_reply", "")

        if not text:
            text = "DJ AI hazir. Komut bekliyorum."

        self.voice_assistant.speak_reply(text)

    def execute_voice_intent(self, result):

        intent = result.get("intent")
        self.log(f"Voice AI heard: {result.get('heard')} -> {intent}")

        actions = {
            "LOAD_LIBRARY": self.load_library,
            "GENERATE_SET": self.generate_set,
            "PLAY": self.play_set,
            "STOP": self.stop_playback,
            "NEXT": self.next_track,
            "OPEN_HEART": lambda: self.set_view("dj_heart"),
            "AUDIT_ARCHIVE": self.run_archive_audit,
            "OPEN_DECKS": lambda: self.set_view("deck_studio"),
            "OPEN_CLOUD_EXPORT": lambda: self.set_view("cloud_export"),
            "OPEN_REMIX_LAB": lambda: self.set_view("remix_lab"),
            "OPEN_TRENDS": lambda: self.set_view("global_trends"),
            "OPEN_SETTINGS": lambda: self.set_view("settings"),
            "SET_LANGUAGE": lambda: self.voice_reply("Lütfen Türkçe veya İngilizce olarak hangi dili istediğini söyle."),
            "SET_LANGUAGE_TR": lambda: self.set_voice_language("tr"),
            "SET_LANGUAGE_EN": lambda: self.set_voice_language("en"),
            "OPEN_ACCOUNT": lambda: self.set_view("account"),
            "OPEN_CRATE_BUILDER": lambda: self.set_view("crate_builder"),
            "OPEN_LIVE_VIEW": lambda: self.set_view("live"),
            "OPEN_AI_MEMORY": lambda: self.set_view("ai_memory"),
            "OPEN_ARCHIVE_GUARDIAN": lambda: self.set_view("archive_guardian"),
            "OPEN_DUPLICATE_REVIEW": self.open_next_duplicate_review,
            "OPEN_ASTRA": lambda: self.process_astra_wake(result.get("heard", "astra")),
            "ENABLE_PASSIVE_LISTEN": lambda: self.process_astra_enable_passive(result.get("heard", "sadece dinle")),
            "DISABLE_PASSIVE_LISTEN": lambda: self.process_astra_disable_passive(result.get("heard", "artık dinleme")),
            "VOICE_TEST": self.run_voice_diagnostics,
            "COACH_SELECTED_TRACK": self.voice_coach_selected_track,
            "COACH_CURRENT_SET": self.voice_coach_current_set,
            "AUTO_MIX_COACH": self.voice_coach_auto_mix,
            "MIX_MASTER_ANALYZE": self.analyze_selected_mix_master_audio,
            "BUILD_SHOW": self.build_show_director_plan,
        }

        action = actions.get(intent)

        if action:
            if intent in {
                "COACH_SELECTED_TRACK",
                "COACH_CURRENT_SET",
                "AUTO_MIX_COACH",
                "MIX_MASTER_ANALYZE",
                "BUILD_SHOW"
            }:
                action()
                return

            self.set_status(f"VOICE AI: {result.get('reply')}")
            self.last_voice_reply = result.get("reply", "")
            self.voice_assistant.speak_reply(self.last_voice_reply)
            action()
            return

        self.set_status(f"VOICE AI: {result.get('reply')}")
        self.last_voice_reply = result.get("reply", "")
        self.voice_assistant.speak_reply(self.last_voice_reply)

    def voice_coach_selected_track(self):

        track = self.selected_track

        if not track:
            self.voice_reply("Once bir parca sec. Sonra sana net DJ yorumu vereyim.")
            return

        name = track.get("name", "secili parca")
        bpm = track.get("bpm", "-")
        key = track.get("camelot", track.get("key", "-"))
        role = track.get("role", "-")
        heart = track.get("heart_score", 0)
        color = track.get("emotional_color", "-")
        moment = track.get("crowd_moment", "-")
        advice = track.get("heart_advice") or track.get("transition_advice") or ""

        text = (
            f"{name}. BPM {bpm}, ton {key}, rol {role}. "
            f"Kalp skoru {heart}, duygu {color}, crowd ani {moment}. "
            f"{advice}"
        )
        self.voice_reply(text)

    def voice_coach_current_set(self):

        source = self.current_set or self.library or self.saved_tracks

        if not source:
            self.voice_reply("Set veya arsiv bos. Once muzik klasoru yukle.")
            return

        heart_map = self.dj_heart.build_heart_map(source)
        avg_bpm = self.average_number(source, "bpm")
        avg_energy = self.average_number(source, "energy")
        first = source[0].get("name", "ilk parca")

        text = (
            f"Sette {len(source)} parca var. Ortalama BPM {avg_bpm}, "
            f"ortalama enerji {avg_energy}. Kalp pulse {heart_map.get('pulse')}, "
            f"akis {heart_map.get('shape')}. Ilk guvenli baslangic: {first}. "
            f"{heart_map.get('advice')}"
        )
        self.voice_reply(text)

    def voice_coach_auto_mix(self):

        deck_a = self.deck_engine.decks.get("A", {}).get("track")
        deck_b = self.deck_engine.decks.get("B", {}).get("track")

        if deck_a and deck_b:
            plan = self.deck_engine.auto_mix_plan(deck_a, deck_b)
            self.voice_reply(plan.get("instruction", "Mix plani hazir."))
            return

        track = self.selected_track

        if track and track.get("transition_advice"):
            self.voice_reply(track["transition_advice"])
            return

        self.voice_reply(
            "Mix tavsiyesi icin Deck A ve Deck B'ye parca yukle veya setten bir parca sec."
        )

    def voice_reply(self, text):

        self.last_voice_reply = str(text or "")
        self.set_status(f"VOICE AI: {self.last_voice_reply}")
        self.log(f"Voice AI reply: {self.last_voice_reply}")
        self.voice_assistant.speak_reply(self.last_voice_reply)

    def set_voice_language(self, language_code):

        result = self.voice_assistant.set_language(language_code)

        if result.get("ok"):
            self.voice_reply(
                "Dil " + ("Türkçe" if language_code == "tr" else "İngilizce") + " olarak ayarlandı."
            )
            self.set_status(f"VOICE AI: Şu anki dil {self.voice_assistant.runtime.language}")
            return

        self.voice_reply("Dil ayarı yapılamadı. Lütfen Türkçe veya İngilizce seçin.")

    def filtered_tracks(self, tracks):

        query = (self.filter_search.get() if self.filter_search else "").lower()
        genre = self.filter_genre.get() if self.filter_genre else "ALL"
        mix = self.filter_mix.get() if self.filter_mix else "ALL"
        issue = self.filter_issue.get() if self.filter_issue else "ALL"
        bpm_min = self.safe_float(self.filter_bpm_min.get() if self.filter_bpm_min else "")
        bpm_max = self.safe_float(self.filter_bpm_max.get() if self.filter_bpm_max else "")

        result = []

        for track in tracks:
            bpm = self.safe_float(track.get("bpm"))
            bpm = bpm if bpm is not None else 0

            haystack = " ".join([
                str(track.get("name", "")),
                str(track.get("artist", "")),
                str(track.get("genre", "")),
                str(track.get("parent_genre", "")),
                str(track.get("role", "")),
            ]).lower()

            if query and query not in haystack:
                continue

            if bpm_min is not None and bpm < bpm_min:
                continue

            if bpm_max is not None and bpm > bpm_max:
                continue

            if genre != "ALL" and track.get("genre") != genre:
                continue

            if mix != "ALL" and track.get("mix_strategy") != mix:
                continue

            if issue != "ALL" and not self.matches_issue_filter(track, issue):
                continue

            result.append(track)

        return result

    def matches_issue_filter(self, track, issue):

        if issue == "NEEDS_RESEARCH":
            return track.get("research_status") == "NEEDS_REVIEW"

        if issue == "DUPLICATES":
            return track.get("duplicate_status") == "POSSIBLE_DUPLICATE"

        if issue == "LOW_BITRATE":
            bitrate = self.safe_float(track.get("bitrate"))
            return bitrate is not None and bitrate < 256

        if issue == "ANALYSIS_FALLBACK":
            return track.get("analysis_status") == "FALLBACK"

        if issue == "LOW_AI_EAR":
            score = self.safe_float(track.get("ai_ear_score"))
            return score is not None and score < 0.62

        if issue == "VOCAL_RISK":
            risk = self.safe_float(track.get("vocal_risk"))
            return risk is not None and risk >= 0.6

        return True

    def safe_float(self, value):

        if value in (None, ""):
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    # =====================================================
    # DASHBOARD
    # =====================================================
    def build_dashboard(self):

        self.make_section_title(
            self.content,
            "ARCHIVE CONTROL DASHBOARD",
            "Professional archive governance, AI insight and operational health"
        )

        # TOP ACTIONS
        top = ctk.CTkFrame(self.content, fg_color="transparent")
        top.pack(fill="x", pady=5)

        ctk.CTkButton(top, text="KUTUPHANE YUKLE", command=self.load_library).pack(side="left", padx=5)
        ctk.CTkButton(
            top,
            text="TARAMAYI DURDUR",
            command=self.cancel_library_scan,
            fg_color=WARNING,
            text_color=BACKGROUND
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            top,
            text="ARSIV SAGLIK",
            command=self.run_archive_health_check
        ).pack(side="left", padx=5)
        ctk.CTkButton(top, text="SET HAZIRLA", command=self.generate_set).pack(side="left", padx=5)
        ctk.CTkButton(top, text="CAL", command=self.play_set).pack(side="left", padx=5)
        ctk.CTkButton(top, text="DUR", command=self.stop_playback).pack(side="left", padx=5)
        ctk.CTkButton(top, text="SONRAKI", command=self.next_track).pack(side="left", padx=5)
        ctk.CTkButton(top, text="MIX MASTER DOKTORU", command=self.inspect_selected_mix_master).pack(side="left", padx=5)

        metrics = ctk.CTkFrame(self.content, fg_color="transparent")
        metrics.pack(fill="x", pady=(0, 12))
        source = self.library or self.saved_tracks
        archive_health = self.archive_auditor.audit(self.archive_output_folder).get("health_score", 0)
        duplicate_count = self.count_value(source, "duplicate_status", "POSSIBLE_DUPLICATE")
        self.make_metric(metrics, "TOTAL TRACKS", len(source))
        self.make_metric(metrics, "DUPLICATE RISK", duplicate_count)
        self.make_metric(metrics, "ARCHIVE HEALTH", f"{archive_health}/100")
        self.make_metric(metrics, "LICENSE PLAN", self.plan.get("plan", "DEMO"))

        # DJ DNA Quick Stats
        if source:
            profile = self.dj_profile.build_profile(source[:200])  # Sample for speed
            dna = profile.get("dna", "E00-B00-G00-P000")
            dna_frame = ctk.CTkFrame(self.content, fg_color=CARD, corner_radius=8)
            dna_frame.pack(fill="x", pady=(0, 10))

            ctk.CTkLabel(
                dna_frame,
                text=f"DJ DNA: {dna}",
                font=F_H3,
                text_color=ACCENT
            ).pack(side="left", padx=14, pady=8)

            ctk.CTkLabel(
                dna_frame,
                text=f"Ort. Enerji: {profile.get('avg_energy', 0):.2f} | "
                     f"Ort. BPM: {profile.get('avg_bpm', 0):.0f} | "
                     f"Tur: {profile.get('genre_count', 0)}",
                font=F_META,
                text_color=TEXT
            ).pack(side="left", padx=14, pady=8)

            insight = profile.get("insights", [""])[0] if profile.get("insights") else ""
            if insight:
                ctk.CTkLabel(
                    dna_frame,
                    text=insight[:80] + "..." if len(insight) > 80 else insight,
                    font=F_META,
                    text_color=MUTED,
                    wraplength=600,
                    justify="left"
                ).pack(side="left", padx=14, pady=8)

        panel_row = ctk.CTkFrame(self.content, fg_color="transparent")
        panel_row.pack(fill="both", pady=(0, 10), expand=True)

        left_panel = ctk.CTkFrame(panel_row, fg_color="transparent")
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 6))

        right_panel = ctk.CTkFrame(panel_row, fg_color="transparent")
        right_panel.pack(side="left", fill="both", expand=True, padx=(6, 0))

        self.archive_cockpit = AnimatedArchiveCockpit(left_panel)
        self.archive_cockpit.pack(fill="both", expand=True)
        self.archive_cockpit.update_stats(
            tracks=len(source),
            issues=duplicate_count,
            locked=True,
            mode="ARCHIVE FLOW",
            missing=0,
            relinked=0
        )

        self.ai_dashboard = AIDashboard(right_panel)
        self.ai_dashboard.pack(fill="both", expand=True)

        self.neon_booth = NeonBoothPanel(self.content)
        self.neon_booth.pack(fill="x", pady=(0, 10))

        self.build_drop_zone(self.content)

        self.primary_waveform = WaveformView(self.content)
        self.primary_waveform.pack(fill="x", pady=(0, 10))

        self.build_filter_bar(self.content, self.library or self.saved_tracks)
        self.build_music_doctor_bar(
            self.content,
            self.library or self.saved_tracks
        )
        self.build_voice_command_bar(self.content)

        # PROGRESS
        self.progress = ctk.CTkProgressBar(self.content)
        self.progress.set(0)
        self.progress.pack(fill="x", pady=5)

        # MAIN AREA
        body = ctk.CTkFrame(self.content, fg_color="transparent")
        body.pack(fill="both", expand=True)

        # TABLE
        table_frame = ctk.CTkFrame(body, fg_color=PANEL)
        table_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

        self.table = TrackTable(
            table_frame,
            on_select=self.on_track_selected,
            on_double_click=self.on_track_double_click,
            on_right_click_action=self.on_track_right_click,
        )
        self.table.pack(fill="both", expand=True, padx=6, pady=6)

        # RIGHT PANEL
        right_panel = ctk.CTkFrame(body, fg_color="transparent", width=360)
        right_panel.pack(side="right", fill="y")
        right_panel.pack_propagate(False)

        self.ai_dashboard = AIDashboard(right_panel)
        self.ai_dashboard.pack(fill="x", pady=(0, 10))

        self.waveform = WaveformView(right_panel)
        self.waveform.pack(fill="both", expand=False, pady=(0, 10))

        self.log_panel = AILogPanel(right_panel)
        self.log_panel.pack(fill="both", expand=True)

        for message in self.ai_messages:
            self.log_panel.log(message)

        self.after(
            100,
            lambda: self.log(
                "Muzik Doktoru hazir. Klasor secince tur, enerji, "
                "duplicate ve dosya adi sagligini kontrol edecegim."
            )
        )
        self.after(300, self.report_audio_runtime_status)

    def report_audio_runtime_status(self):

        status = self.audio_runtime_status()

        if status["full_analysis"]:
            self.log(
                "AUDIO RUNTIME: MP3/WAV/FLAC waveform analizi hazir "
                f"({', '.join(status['available'])})."
            )
            return

        missing = ", ".join(status["missing"])
        self.log(
            "AUDIO RUNTIME: WAV paketsiz analiz edilir; MP3/FLAC/M4A "
            f"waveform icin eksik paket: {missing}"
        )

    def audio_runtime_status(self):

        required = ("librosa", "numpy", "soundfile")
        available = [
            package
            for package in required
            if find_spec(package) is not None
        ]
        missing = [
            package
            for package in required
            if package not in available
        ]

        return {
            "available": available,
            "missing": missing,
            "full_analysis": not missing,
        }

    def build_drop_zone(self, parent):

        drop = ctk.CTkFrame(
            parent,
            fg_color=CARD,
            corner_radius=8,
            border_width=1,
            border_color=NEON_PURPLE
        )
        drop.pack(fill="x", pady=(0, 10))

        left = ctk.CTkFrame(drop, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True, padx=14, pady=12)

        ctk.CTkLabel(
            left,
            text="DROP ANALYZER",
            font=("Segoe UI", 15, "bold"),
            text_color=NEON_BLUE
        ).pack(anchor="w")

        self.drop_status = ctk.CTkLabel(
            left,
            text=(
                "MP3/WAV/FLAC/M4A dosyalarini buraya surukle. "
                "Analiz ve waveform olusturur; otomatik arsiv kopyasi yazmaz."
            ),
            text_color=MUTED,
            wraplength=980,
            justify="left"
        )
        self.drop_status.pack(anchor="w", pady=(2, 0))

        ctk.CTkButton(
            drop,
            text="DOSYA SEC",
            width=110,
            command=self.select_files_for_preview
        ).pack(side="right", padx=14, pady=12)

        self.enable_drag_drop(drop)

    def enable_drag_drop(self, widget, quiet=False):

        if windnd is None:
            if not quiet and hasattr(self, "drop_status"):
                self.drop_status.configure(
                    text=(
                        "Surukle-birak icin windnd paketi gerekli. "
                        "Simdilik DOSYA SEC ile ayni analiz akisini kullanabilirsin."
                    ),
                    text_color=WARNING
                )
            return

        try:
            widget_key = self.drag_drop_widget_key(widget)

            if widget_key in self.drag_drop_targets:
                return

            windnd.hook_dropfiles(widget, func=self.safe_handle_dropped_files)
            self.drag_drop_targets.add(widget_key)
        except Exception as exc:
            if not quiet:
                self.log(f"Drag-drop etkinlestirilemedi: {exc}")

    def drag_drop_widget_key(self, widget):

        try:
            return int(widget.winfo_id())
        except Exception:
            return str(widget)

    def select_files_for_preview(self):

        files = filedialog.askopenfilenames(
            filetypes=[
                ("Audio files", "*.mp3 *.wav *.flac *.m4a *.aiff *.aif"),
                ("All files", "*.*"),
            ]
        )

        if files:
            self.import_dropped_files(list(files))

    def safe_handle_dropped_files(self, files):

        paths = [
            self.normalize_drop_path(item)
            for item in files
        ]

        try:
            self.after(0, lambda p=paths: self.handle_dropped_files(p))
        except Exception:
            pass

    def handle_dropped_files(self, paths):

        self.import_dropped_files(paths)

    def normalize_drop_path(self, value):

        if isinstance(value, bytes):
            for encoding in ("utf-8", "mbcs", "latin-1"):
                try:
                    return value.decode(encoding)
                except Exception:
                    continue

            return value.decode(errors="ignore")

        return str(value or "")

    def import_dropped_files(self, paths):

        expanded_paths = self.expand_drop_paths(paths)

        audio_paths = [
            path
            for path in expanded_paths
            if self.is_supported_audio_path(path)
        ]

        if not audio_paths:
            self.set_status("DROP ANALYZER: Desteklenen ses dosyasi bulunamadi.")
            return

        self.set_status(
            "DROP ANALYZER: "
            f"{len(audio_paths)} dosya analiz ediliyor..."
        )

        threading.Thread(
            target=self.import_dropped_files_worker,
            args=(audio_paths,),
            daemon=True
        ).start()

    def expand_drop_paths(self, paths):

        expanded = []

        for path in paths:
            if not path:
                continue

            if os.path.isdir(path):
                expanded.extend(self.collect_audio_files_from_folder(path))
            else:
                expanded.append(path)

        return expanded

    def collect_audio_files_from_folder(self, folder):

        audio_files = []

        try:
            if self.scanner.is_excluded_path(folder):
                self.log(
                    "DROP ANALYZER: uretilmis arsiv klasoru atlandi: "
                    f"{folder}"
                )
                return audio_files

            for root, dirs, files in os.walk(folder):
                dirs[:] = [
                    item
                    for item in dirs
                    if item.upper() not in self.scanner.excluded_folder_names
                ]

                if self.scanner.is_excluded_path(root):
                    dirs[:] = []
                    continue

                for filename in files:
                    path = os.path.join(root, filename)

                    if self.is_supported_audio_path(path):
                        audio_files.append(path)
        except Exception as exc:
            self.log(f"DROP ANALYZER KLASOR HATASI: {folder} | {exc}")

        return audio_files

    def is_supported_audio_path(self, path):

        return (
            path and
            os.path.exists(path) and
            os.path.splitext(path)[1].lower() in {
                ".mp3",
                ".wav",
                ".flac",
                ".m4a",
                ".aiff",
                ".aif",
            }
        )

    def resolve_track_audio_path(self, track):

        if not track:
            return ""

        playable = self.archive_brain.playable_path(track)

        if playable:
            track["path"] = playable
            track["path_status"] = self.archive_brain.path_status(track)
            return playable

        track["path_status"] = "MISSING_FILE"

        return (
            track.get("path") or
            track.get("archived_path") or
            track.get("id") or
            ""
        )

    def import_dropped_files_worker(self, paths):

        imported = []

        for path in paths:
            try:
                track = self.scanner.process_file(path) or self.build_basic_track(path)
                track["import_mode"] = "DROP_PREVIEW"
                self.enrich_track(track, archive=False, show_duplicate=False)
                self.ensure_waveform_analysis(track, force=True, log_errors=True)
                imported.append(track)
                self.queue.push(track)
            except Exception as exc:
                self.log(f"DROP ANALYZER ERROR: {path} | {exc}")

        if imported:
            self.library = imported + [
                track
                for track in self.library
                if track.get("id") not in {item.get("id") for item in imported}
            ]
            self.after(0, lambda t=imported[0]: self.on_track_selected(t))

        self.after(
            0,
            lambda: self.set_status(
                f"DROP ANALYZER: {len(imported)} dosya analiz edildi."
            )
        )

    def ensure_waveform_analysis(self, track, force=False, log_errors=False):

        if not track:
            return False

        if track.get("waveform") and not force:
            return True

        path = self.resolve_track_audio_path(track)

        if not self.is_supported_audio_path(path):
            return False

        result = self.mix_master_engine.analyze_file(path)

        if not result.get("ok"):
            if log_errors:
                self.log(
                    "WAVEFORM ANALIZ HATASI: "
                    f"{os.path.basename(path)} | {result.get('reason')}"
                )

            track["waveform_error"] = result.get("reason", "")
            return False

        self.apply_waveform_result_to_track(track, result)
        return bool(track.get("waveform"))

    def apply_waveform_result_to_track(self, track, result):

        track["waveform"] = result.get("waveform", track.get("waveform", []))
        track["phrase_points"] = result.get(
            "phrase_points",
            track.get("phrase_points", [])
        )
        track["hot_cues"] = self.build_ai_hot_cues(
            track.get("phrase_points", []),
            result.get("duration", track.get("duration", 0))
        )
        track["waveform_engine"] = result.get("engine", "")

        if result.get("duration") and not track.get("duration"):
            track["duration"] = result.get("duration")

        transient = result.get("transient", {})
        dynamics = result.get("dynamics", {})
        spectrum = result.get("spectrum", {})
        stereo = result.get("stereo", {})

        if transient.get("tempo") and not track.get("bpm"):
            track["bpm"] = transient.get("tempo")

        mapped_fields = (
            (dynamics, "energy", "energy"),
            (spectrum, "brightness", "brightness"),
            (spectrum, "harshness", "waveform_harshness"),
            (transient, "punch", "drop_strength"),
            (transient, "groove_confidence", "danceability"),
            (stereo, "width", "stereo_width"),
            (stereo, "correlation", "phase_correlation"),
        )

        for source, source_field, target_field in mapped_fields:
            value = source.get(source_field)

            if value not in (None, ""):
                track[target_field] = value

    def build_ai_hot_cues(self, phrase_points, duration):

        duration = self.safe_float(duration) or 0
        cues = []

        for point in phrase_points or []:
            label = str(point.get("label") or "CUE").upper()
            position = self.safe_float(point.get("position")) or 0
            seconds = round(duration * max(0, min(1, position)), 2)
            color = {
                "START": "GREEN",
                "BUILD": "YELLOW",
                "PEAK": "MAGENTA",
                "OUTRO": "BLUE",
            }.get(label, "CYAN")
            cues.append({
                "label": label,
                "seconds": seconds,
                "color": color,
                "position": round(position, 3),
            })

        return cues

    def build_basic_track(self, path):

        size = 0

        try:
            size = os.path.getsize(path)
        except OSError:
            pass

        return {
            "id": path,
            "path": path,
            "name": os.path.basename(path),
            "artist": "UNKNOWN",
            "genre": "UNKNOWN",
            "duration": 0,
            "bitrate": 0,
            "file_size": size,
            "energy": 0.5,
            "brightness": 0.5,
        }

    def build_library_view(self):

        self.make_section_title(
            self.content,
            "Library",
            "Kaydedilmis arsivi, tarama sonuclarini ve DJ etiketlerini gor."
        )

        actions = ctk.CTkFrame(self.content, fg_color="transparent")
        actions.pack(fill="x", pady=(0, 8))

        ctk.CTkButton(
            actions,
            text="REFRESH ARCHIVE",
            command=self.refresh_library_from_db
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            actions,
            text="LOAD NEW FOLDER",
            command=self.load_library
        ).pack(side="left", padx=6)

        stats = ctk.CTkFrame(self.content, fg_color="transparent")
        stats.pack(fill="x", pady=(0, 12))

        tracks = self.get_visible_tracks()
        self.make_metric(stats, "TRACKS", len(tracks))
        self.make_metric(stats, "GENRES", len(self.count_by_field(tracks, "genre")))
        self.make_metric(stats, "NEEDS RESEARCH", self.count_value(tracks, "research_status", "NEEDS_REVIEW"))
        self.make_metric(stats, "DUPLICATES", self.count_value(tracks, "duplicate_status", "POSSIBLE_DUPLICATE"))

        self.build_filter_bar(self.content, tracks)
        self.build_music_doctor_bar(self.content, tracks)

        table_frame = ctk.CTkFrame(self.content, fg_color=PANEL)
        table_frame.pack(fill="both", expand=True)

        self.table = TrackTable(
            table_frame,
            on_select=self.on_track_selected,
            on_double_click=self.on_track_double_click,
            on_right_click_action=self.on_track_right_click,
        )
        self.table.pack(fill="both", expand=True, padx=6, pady=6)
        self.populate_table(tracks)

    def build_archive_guardian_view(self):

        self.make_section_title(
            self.content,
            "Archive Guardian",
            "Arsivini koru: exact duplicate, renamed copy, alan israfi ve temizlik planini tek yerde gor."
        )

        actions = ctk.CTkFrame(self.content, fg_color=CARD, corner_radius=8)
        actions.pack(fill="x", pady=(0, 10))

        ctk.CTkButton(
            actions,
            text="ARSIVI TARA",
            command=self.refresh_archive_guardian
        ).pack(side="left", padx=12, pady=12)

        ctk.CTkButton(
            actions,
            text="CLEANUP PLANI YAZ",
            command=self.write_archive_guardian_plan
        ).pack(side="left", padx=6, pady=12)

        ctk.CTkLabel(
            actions,
            text="Guvenli mod: dosya silmez, tasimaz; sadece plan ve kanit uretir.",
            text_color=MUTED
        ).pack(side="left", padx=12, pady=12)

        self.archive_guardian_status = ctk.CTkLabel(
            self.content,
            text="Arsiv taramasi bekleniyor.",
            text_color=MUTED,
            anchor="w"
        )
        self.archive_guardian_status.pack(fill="x", pady=(0, 10))

        self.archive_guardian_body = ctk.CTkFrame(
            self.content,
            fg_color="transparent"
        )
        self.archive_guardian_body.pack(fill="both", expand=True)
        self.refresh_archive_guardian()

    def refresh_archive_guardian(self):

        report = self.archive_auditor.audit(self.archive_output_folder)
        cleanup_plan = self.archive_reconciler.build_cleanup_plan()
        self.last_archive_audit = report
        self.last_archive_cleanup_plan = cleanup_plan

        if hasattr(self, "archive_guardian_status"):
            self.archive_guardian_status.configure(
                text=f"{report['summary']} | {cleanup_plan['summary']}"
            )

        if not hasattr(self, "archive_guardian_body"):
            return

        for child in self.archive_guardian_body.winfo_children():
            child.destroy()

        stats = ctk.CTkFrame(self.archive_guardian_body, fg_color="transparent")
        stats.pack(fill="x", pady=(0, 12))
        self.make_metric(stats, "HEALTH", report.get("health_score", 0))
        self.make_metric(stats, "AUDIO FILES", report.get("total_audio_files", 0))
        self.make_metric(stats, "EXACT DUPES", cleanup_plan.get("duplicate_file_count", 0))
        self.make_metric(stats, "SAVE MB", cleanup_plan.get("reclaimable_mb", 0))

        self.render_archive_guardian_section(
            "Exact Duplicate Cleanup Plan",
            cleanup_plan.get("duplicate_groups", []),
            self.archive_exact_duplicate_text
        )
        self.render_archive_guardian_section(
            "Renamed Copy Risk",
            report.get("duplicate_name_groups", []),
            self.archive_renamed_duplicate_text
        )
        self.render_archive_guardian_section(
            "Tempo Risk",
            report.get("tempo_anomalies", []),
            self.archive_tempo_risk_text
        )

    def write_archive_guardian_plan(self):

        report = getattr(self, "last_archive_audit", None)
        cleanup_plan = getattr(self, "last_archive_cleanup_plan", None)

        if not report or not cleanup_plan:
            report = self.archive_auditor.audit(self.archive_output_folder)
            cleanup_plan = self.archive_reconciler.build_cleanup_plan()

        report_path = self.archive_auditor.write_report(report)
        cleanup_path = self.archive_reconciler.write_plan(cleanup_plan)
        quarantine_path = self.archive_reconciler.write_quarantine_manifest(
            cleanup_plan
        )
        self.set_status(
            "ARCHIVE GUARDIAN PLAN READY: "
            f"report={report_path} cleanup={cleanup_path} quarantine={quarantine_path}"
        )

        if hasattr(self, "archive_guardian_status"):
            self.archive_guardian_status.configure(
                text=f"Plan yazildi: {cleanup_path} | quarantine manifest: {quarantine_path}"
            )

    def render_archive_guardian_section(self, title, items, formatter):

        box = ctk.CTkFrame(
            self.archive_guardian_body,
            fg_color=PANEL,
            corner_radius=8
        )
        box.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            box,
            text=f"{title} ({len(items)})",
            font=("Segoe UI", 15, "bold"),
            text_color=ACCENT
        ).pack(anchor="w", padx=12, pady=(12, 6))

        if not items:
            ctk.CTkLabel(
                box,
                text="Temiz gorunuyor.",
                text_color=MUTED
            ).pack(anchor="w", padx=12, pady=(0, 12))
            return

        for item in items[:8]:
            ctk.CTkLabel(
                box,
                text=formatter(item),
                text_color=TEXT,
                wraplength=1200,
                justify="left"
            ).pack(anchor="w", padx=12, pady=3)

        if len(items) > 8:
            ctk.CTkLabel(
                box,
                text=f"... {len(items) - 8} kayit daha var. Tam plan JSON raporunda.",
                text_color=WARNING
            ).pack(anchor="w", padx=12, pady=(4, 12))

    def archive_exact_duplicate_text(self, item):

        return (
            f"KEEP: {item.get('keep')} | "
            f"DUPES: {item.get('duplicate_count')} | "
            f"SAVE: {round(item.get('reclaimable_bytes', 0) / (1024 * 1024), 2)} MB"
        )

    def archive_renamed_duplicate_text(self, item):

        return (
            f"{item.get('count')} files | {item.get('key')} | "
            "isimle cogalmis kopya riski"
        )

    def archive_tempo_risk_text(self, item):

        return (
            f"{item.get('issue')} | BPM {item.get('bpms')} | {item.get('path')}"
        )

    def build_analyze_view(self):

        self.make_section_title(
            self.content,
            "Music Import",
            "Klasor veya surukle-birak ile ses dosyalarini analiz et; arsiv kopyasi kontrollu ve tek seferlidir."
        )

        controls = ctk.CTkFrame(self.content, fg_color=CARD, corner_radius=8)
        controls.pack(fill="x", pady=(0, 10))

        ctk.CTkButton(
            controls,
            text="KLASOR SEC VE ANALIZ ET",
            command=self.load_library
        ).pack(side="left", padx=12, pady=12)

        ctk.CTkLabel(
            controls,
            text=self.get_ready_status(),
            text_color=MUTED
        ).pack(side="left", padx=12)

        self.progress = ctk.CTkProgressBar(self.content)
        self.progress.set(0)
        self.progress.pack(fill="x", pady=(0, 10))

        self.build_filter_bar(self.content, self.library)
        self.build_music_doctor_bar(self.content, self.library)

        body = ctk.CTkFrame(self.content, fg_color="transparent")
        body.pack(fill="both", expand=True)

        table_frame = ctk.CTkFrame(body, fg_color=PANEL)
        table_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

        self.table = TrackTable(
            table_frame,
            on_select=self.on_track_selected,
            on_double_click=self.on_track_double_click,
            on_right_click_action=self.on_track_right_click,
        )
        self.table.pack(fill="both", expand=True, padx=6, pady=6)
        self.populate_table(self.library)

        self.log_panel = AILogPanel(body)
        self.log_panel.pack(side="right", fill="both", padx=(0, 0))

        for message in self.ai_messages[-80:]:
            self.log_panel.log(message)

    def build_set_builder_view(self):

        self.make_section_title(
            self.content,
            "Set Builder",
            "Arsivden enerji, BPM ve harmoniye gore sirali bir set olustur."
        )

        controls = ctk.CTkFrame(self.content, fg_color="transparent")
        controls.pack(fill="x", pady=(0, 10))

        ctk.CTkButton(
            controls,
            text="GENERATE SET",
            command=self.generate_set
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            controls,
            text="PLAY SET",
            command=self.play_set
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            controls,
            text="STOP",
            command=self.stop_playback
        ).pack(side="left", padx=6)

        source = self.current_set or self.library or self.saved_tracks

        self.transition_box = ctk.CTkLabel(
            self.content,
            text="Set olusturunca secili parca icin mix onerisi burada gorunur.",
            text_color=MUTED,
            anchor="w"
        )
        self.transition_box.pack(fill="x", pady=(0, 10))

        stats = ctk.CTkFrame(self.content, fg_color="transparent")
        stats.pack(fill="x", pady=(0, 12))
        self.make_metric(stats, "SET TRACKS", len(source))
        self.make_metric(stats, "AVG BPM", self.average_number(source, "bpm"))
        self.make_metric(stats, "AVG ENERGY", self.average_number(source, "energy"))

        self.build_filter_bar(self.content, source)

        table_frame = ctk.CTkFrame(self.content, fg_color=PANEL)
        table_frame.pack(fill="both", expand=True)

        self.table = TrackTable(
            table_frame,
            on_select=self.on_track_selected,
            on_double_click=self.on_track_double_click,
            on_right_click_action=self.on_track_right_click,
        )
        self.table.pack(fill="both", expand=True, padx=6, pady=6)
        self.populate_table(source)

    def build_set_show_view(self):

        self.make_section_title(
            self.content,
            "Set & Show",
            "Set kur, performans planla ve gece dramaturjisini tek yerden yonet."
        )

        controls = ctk.CTkFrame(self.content, fg_color=CARD, corner_radius=8)
        controls.pack(fill="x", pady=(0, 10))

        self.performance_style = StringVar(value="AFRO HOUSE")
        self.performance_hours = StringVar(value="4")

        ctk.CTkComboBox(
            controls,
            variable=self.performance_style,
            values=["AFRO HOUSE", "HOUSE", "TECH HOUSE", "MELODIC", "WEDDING"],
            width=160
        ).pack(side="left", padx=12, pady=12)

        ctk.CTkEntry(
            controls,
            textvariable=self.performance_hours,
            placeholder_text="Hours",
            width=90
        ).pack(side="left", padx=6, pady=12)

        ctk.CTkButton(
            controls,
            text="GENERATE SET",
            command=self.generate_set
        ).pack(side="left", padx=6, pady=12)

        ctk.CTkButton(
            controls,
            text="PLAN PERFORMANCE",
            command=self.plan_performance
        ).pack(side="left", padx=6, pady=12)

        ctk.CTkButton(
            controls,
            text="SHOW DIRECTOR",
            command=self.open_show_director_from_set_show
        ).pack(side="left", padx=6, pady=12)

        ctk.CTkButton(
            controls,
            text="GIG PACK HAZIRLA",
            command=self.prepare_gig_pack
        ).pack(side="left", padx=6, pady=12)

        ctk.CTkButton(
            controls,
            text="PLAY",
            command=self.play_set
        ).pack(side="left", padx=6, pady=12)

        self.performance_summary = ctk.CTkLabel(
            self.content,
            text="Tarz ve sure sec; AI set, acilis ve show akisini hazirlasin.",
            text_color=MUTED,
            anchor="w"
        )
        self.performance_summary.pack(fill="x", pady=(0, 10))

        source = self.current_set or self.library or self.saved_tracks
        stats = ctk.CTkFrame(self.content, fg_color="transparent")
        stats.pack(fill="x", pady=(0, 12))
        self.make_metric(stats, "TRACKS", len(source))
        self.make_metric(stats, "AVG BPM", self.average_number(source, "bpm"))
        self.make_metric(stats, "AVG HEART", self.average_number(source, "heart_score"))

        self.build_filter_bar(self.content, source)

        table_frame = ctk.CTkFrame(self.content, fg_color=PANEL)
        table_frame.pack(fill="both", expand=True)

        self.table = TrackTable(
            table_frame,
            on_select=self.on_track_selected,
            on_double_click=self.on_track_double_click,
            on_right_click_action=self.on_track_right_click,
        )
        self.table.pack(fill="both", expand=True, padx=6, pady=6)
        self.populate_table(source)

    def open_show_director_from_set_show(self):

        self.set_view("show_director")

    def build_performance_view(self):

        self.make_section_title(
            self.content,
            "Performance",
            "Tarza gore acilis parcasi, set akisi ve uzun performans plani."
        )

        controls = ctk.CTkFrame(self.content, fg_color=CARD, corner_radius=8)
        controls.pack(fill="x", pady=(0, 10))

        self.performance_style = StringVar(value="AFRO HOUSE")
        self.performance_hours = StringVar(value="4")

        ctk.CTkComboBox(
            controls,
            variable=self.performance_style,
            values=["AFRO HOUSE", "HOUSE", "TECH HOUSE", "MELODIC", "WEDDING"],
            width=160
        ).pack(side="left", padx=12, pady=12)

        ctk.CTkEntry(
            controls,
            textvariable=self.performance_hours,
            placeholder_text="Hours",
            width=90
        ).pack(side="left", padx=6, pady=12)

        ctk.CTkButton(
            controls,
            text="PLAN PERFORMANCE",
            command=self.plan_performance
        ).pack(side="left", padx=6, pady=12)

        self.performance_summary = ctk.CTkLabel(
            self.content,
            text="Tarz ve sure sec, AI acilis parcasi ve akisi onersin.",
            text_color=MUTED,
            anchor="w"
        )
        self.performance_summary.pack(fill="x", pady=(0, 10))

        source = self.library or self.saved_tracks
        self.build_filter_bar(self.content, source)

        table_frame = ctk.CTkFrame(self.content, fg_color=PANEL)
        table_frame.pack(fill="both", expand=True)

        self.table = TrackTable(
            table_frame,
            on_select=self.on_track_selected,
            on_double_click=self.on_track_double_click,
            on_right_click_action=self.on_track_right_click,
        )
        self.table.pack(fill="both", expand=True, padx=6, pady=6)
        self.populate_table(source)

    def plan_performance(self):

        source = self.library or self.saved_tracks
        hours = self.safe_float(self.performance_hours.get()) or 4
        style = self.performance_style.get()
        plan = self.performance_planner.build_performance(
            source,
            style,
            hours
        )

        opening = plan.get("opening")

        if opening:
            self.performance_summary.configure(
                text=(
                    f"Acilis onerisi: {opening.get('name')} | "
                    f"{opening.get('opening_reason', '')} | "
                    f"{plan.get('message')}"
                )
            )
            self.current_set = plan["tracks"]
            self.active_table_source = list(self.current_set)
            self.table.set_tracks(self.filtered_tracks(self.active_table_source))
            self.set_status(f"PERFORMANCE PLAN READY: {style}")
        else:
            self.performance_summary.configure(text=plan.get("message"))
            self.set_status("PERFORMANCE PLAN NEEDS MORE TRACKS")

    def build_dj_heart_view(self):

        self.make_section_title(
            self.content,
            "DJ Heart",
            "Setin duygusal nabzini, crowd anini ve muziksel empati haritasini gor."
        )

        controls = ctk.CTkFrame(self.content, fg_color=CARD, corner_radius=8)
        controls.pack(fill="x", pady=(0, 10))

        ctk.CTkButton(
            controls,
            text="BUILD HEART MAP",
            command=self.refresh_dj_heart_map
        ).pack(side="left", padx=12, pady=12)

        ctk.CTkButton(
            controls,
            text="USE CURRENT SET",
            command=lambda: self.set_status("DJ Heart aktif seti okuyor.")
        ).pack(side="left", padx=6, pady=12)

        self.heart_summary = ctk.CTkLabel(
            self.content,
            text="Kalp haritasi icin set veya arsiv hazir.",
            text_color=MUTED,
            anchor="w"
        )
        self.heart_summary.pack(fill="x", pady=(0, 10))

        self.heart_area = ctk.CTkScrollableFrame(
            self.content,
            fg_color="transparent"
        )
        self.heart_area.pack(fill="both", expand=True)

        self.refresh_dj_heart_map()

    def refresh_dj_heart_map(self):

        if not hasattr(self, "heart_area") or not self.heart_area.winfo_exists():
            return

        for child in self.heart_area.winfo_children():
            child.destroy()

        source = self.current_set or self.library or self.saved_tracks
        heart_map = self.dj_heart.build_heart_map(source)

        self.heart_summary.configure(
            text=(
                f"Pulse {heart_map.get('pulse')} | "
                f"Shape {heart_map.get('shape')} | "
                f"{heart_map.get('advice')}"
            )
        )

        stats = ctk.CTkFrame(self.heart_area, fg_color="transparent")
        stats.pack(fill="x", pady=(0, 12))
        self.make_metric(stats, "HEART PULSE", heart_map.get("pulse", 0))
        self.make_metric(stats, "ARC SHAPE", heart_map.get("shape", "-"))
        self.make_metric(stats, "MOMENTS", len(heart_map.get("moments", [])))

        for moment in heart_map.get("moments", []):
            card = ctk.CTkFrame(self.heart_area, fg_color=PANEL, corner_radius=8)
            card.pack(fill="x", pady=5)

            ctk.CTkLabel(
                card,
                text=(
                    f"{moment.get('position')}. {moment.get('name')} | "
                    f"{moment.get('color')} | {moment.get('moment')} | "
                    f"heart {moment.get('heart_score')}"
                ),
                font=("Segoe UI", 14, "bold"),
                text_color=ACCENT
            ).pack(anchor="w", padx=12, pady=(10, 2))

            ctk.CTkLabel(
                card,
                text=moment.get("advice", ""),
                text_color=TEXT,
                wraplength=1200,
                justify="left"
            ).pack(anchor="w", padx=12, pady=(0, 10))

    def build_show_director_view(self):

        self.make_section_title(
            self.content,
            "Show Director",
            "Geceyi dramaturji, risk ve rescue crate ile yoneten AI sahne beyni."
        )

        controls = ctk.CTkFrame(self.content, fg_color=CARD, corner_radius=8)
        controls.pack(fill="x", pady=(0, 10))

        self.show_style = StringVar(value="AFRO HOUSE")
        self.show_hours = StringVar(value="4")

        ctk.CTkComboBox(
            controls,
            variable=self.show_style,
            values=["AFRO HOUSE", "HOUSE", "TECH HOUSE", "MELODIC", "WEDDING"],
            width=160
        ).pack(side="left", padx=12, pady=12)

        ctk.CTkEntry(
            controls,
            textvariable=self.show_hours,
            placeholder_text="Hours",
            width=90
        ).pack(side="left", padx=6, pady=12)

        ctk.CTkButton(
            controls,
            text="BUILD SHOW",
            command=self.build_show_director_plan
        ).pack(side="left", padx=6, pady=12)

        self.show_note = ctk.CTkLabel(
            self.content,
            text="Show Director hazir. Tarz sec, geceyi segmentlere bolsun.",
            text_color=MUTED,
            anchor="w"
        )
        self.show_note.pack(fill="x", pady=(0, 10))

        self.show_area = ctk.CTkScrollableFrame(
            self.content,
            fg_color="transparent"
        )
        self.show_area.pack(fill="both", expand=True)

    def build_show_director_plan(self):

        for child in self.show_area.winfo_children():
            child.destroy()

        source = self.library or self.saved_tracks
        hours = self.safe_float(self.show_hours.get()) or 4
        style = self.show_style.get()
        show = self.show_director.build_show(source, style, hours)

        self.show_note.configure(text=show.get("director_note", ""))
        self.current_set = []

        for segment in show.get("segments", []):
            self.render_show_segment(segment)
            self.current_set.extend(segment.get("tracks", []))

        self.render_rescue_crate(show.get("rescue_tracks", []))
        self.set_status(f"SHOW DIRECTOR READY: {style} / {hours}h")

    def render_show_segment(self, segment):

        card = ctk.CTkFrame(self.show_area, fg_color=PANEL, corner_radius=8)
        card.pack(fill="x", pady=6)

        ctk.CTkLabel(
            card,
            text=(
                f"{segment.get('name')} | Risk: {segment.get('risk')} | "
                f"Energy: {segment.get('target_energy')}"
            ),
            font=("Segoe UI", 15, "bold"),
            text_color=ACCENT
        ).pack(anchor="w", padx=12, pady=(10, 0))

        ctk.CTkLabel(
            card,
            text=segment.get("instruction", ""),
            text_color=TEXT,
            wraplength=1100,
            justify="left"
        ).pack(anchor="w", padx=12, pady=(4, 8))

        for track in segment.get("tracks", [])[:8]:
            ctk.CTkLabel(
                card,
                text=(
                    f"- {track.get('name')} | "
                    f"score {track.get('show_score')} | "
                    f"{track.get('director_cue')}"
                ),
                text_color=MUTED,
                wraplength=1200,
                justify="left"
            ).pack(anchor="w", padx=18, pady=2)

    def render_rescue_crate(self, rescue_tracks):

        card = ctk.CTkFrame(self.show_area, fg_color=CARD, corner_radius=8)
        card.pack(fill="x", pady=8)

        ctk.CTkLabel(
            card,
            text="RESCUE CRATE",
            font=("Segoe UI", 15, "bold"),
            text_color=WARNING
        ).pack(anchor="w", padx=12, pady=(10, 0))

        if not rescue_tracks:
            ctk.CTkLabel(
                card,
                text="Kurtarma parcasi bulunamadi; arsiv genisledikce burasi guclenecek.",
                text_color=MUTED
            ).pack(anchor="w", padx=12, pady=10)
            return

        for track in rescue_tracks:
            ctk.CTkLabel(
                card,
                text=(
                    f"- {track.get('name')} | rescue {track.get('rescue_score')} | "
                    f"{track.get('director_cue')}"
                ),
                text_color=TEXT,
                wraplength=1200,
                justify="left"
            ).pack(anchor="w", padx=18, pady=2)

    def build_deck_studio_view(self):
        """4-deck Virtual DJ / Rekordbox studio with Pioneer HID support."""
        try:
            from app.ui.deck_studio import DeckStudioPanel
            self.deck_studio_panel = DeckStudioPanel(self.content, win=self)
            self.deck_studio_panel.pack(fill="both", expand=True)
            # make selected track load into the panel's selected deck
            if hasattr(self, "selected_track") and self.selected_track:
                try:
                    self.deck_studio_panel.load_to_deck(
                        self.deck_studio_panel.selected_deck, self.selected_track)
                except Exception:
                    pass
        except Exception as exc:
            import traceback
            traceback.print_exc()
            self.make_section_title(self.content, "Deck Studio",
                                    f"Hata: {exc}")

    def load_selected_to_deck(self, deck_id):

        if not self.selected_track:
            self.set_status("SELECT A TRACK FIRST")
            return

        deck = self.deck_engine.load(deck_id, self.selected_track)
        self.set_status(
            f"DECK {deck_id} LOADED: {deck['track'].get('name')}"
        )
        self.update_deck_status()

    def build_auto_mix_from_decks(self):

        deck_a = self.deck_engine.decks["A"].get("track")
        deck_b = self.deck_engine.decks["B"].get("track")

        if not deck_a or not deck_b:
            self.set_status("LOAD BOTH DECKS FIRST")
            return

        plan = self.deck_engine.auto_mix_plan(deck_a, deck_b)
        self.deck_status_label.configure(
            text=(
                f"{plan['instruction']} | curve={plan['crossfade_curve']}"
            )
        )
        self.set_status(f"AUTO MIX READY: {plan['mode']}")

    def update_deck_status(self):

        if not self.deck_status_label:
            return

        deck_a = self.deck_engine.decks["A"].get("track")
        deck_b = self.deck_engine.decks["B"].get("track")
        name_a = deck_a.get("name") if deck_a else "EMPTY"
        name_b = deck_b.get("name") if deck_b else "EMPTY"

        self.deck_status_label.configure(
            text=f"Deck A: {name_a} | Deck B: {name_b}"
        )

    def build_dj_booth_view(self):

        self.dj_booth = DJBoothView(self)
        self.dj_booth.build(self.content)

    def build_dj_coach_view(self):

        self.make_section_title(
            self.content,
            "DJ Coach AI",
            "Setini degerlendir, guclu ve zayif noktalari ogren."
        )

        controls = ctk.CTkFrame(self.content, fg_color=CARD, corner_radius=8)
        controls.pack(fill="x", pady=(0, 10))

        self.coach_style = StringVar(value="CLUB")
        self.coach_hours = StringVar(value="4")

        ctk.CTkComboBox(
            controls,
            variable=self.coach_style,
            values=["CLUB", "WEDDING", "FESTIVAL", "LOUNGE"],
            width=140
        ).pack(side="left", padx=12, pady=12)

        ctk.CTkEntry(
            controls,
            textvariable=self.coach_hours,
            placeholder_text="Hours",
            width=80
        ).pack(side="left", padx=6, pady=12)

        ctk.CTkButton(
            controls,
            text="ANALYZE SET",
            command=self.run_dj_coach_analysis
        ).pack(side="left", padx=6, pady=12)

        self.coach_result = ctk.CTkScrollableFrame(
            self.content, fg_color=PANEL, corner_radius=8
        )
        self.coach_result.pack(fill="both", expand=True, pady=(0, 10))

        ctk.CTkLabel(
            self.coach_result,
            text="Set olustur veya yukle, sonra ANALYZE SET'e bas.",
            text_color=MUTED
        ).pack(anchor="w", padx=12, pady=12)

    def run_dj_coach_analysis(self):

        source = self.current_set or self.library or self.saved_tracks
        venue = self.coach_style.get()

        result = self.dj_coach.analyze_set(source, venue)

        for child in self.coach_result.winfo_children():
            child.destroy()

        # Grade
        grade = result.get("grade", "N/A")
        grade_colors = {"S": "#00FFA3", "A": "#22D3FF", "B": "#9B5CFF", "C": "#FFB020", "D": "#FF4D6D"}
        ctk.CTkLabel(
            self.coach_result,
            text=f"DERECE: {grade}",
            font=("Segoe UI", 36, "bold"),
            text_color=grade_colors.get(grade, MUTED)
        ).pack(anchor="w", padx=12, pady=(12, 0))

        ctk.CTkLabel(
            self.coach_result,
            text=result.get("summary", ""),
            text_color=TEXT,
            font=F_BODY_BOLD,
            wraplength=1000,
            justify="left"
        ).pack(anchor="w", padx=12, pady=(4, 12))

        # Score breakdown
        scores = result.get("scores", {})
        if scores:
            score_frame = ctk.CTkFrame(self.coach_result, fg_color=CARD, corner_radius=8)
            score_frame.pack(fill="x", padx=12, pady=(0, 10))

            for name, score in scores.items():
                ctk.CTkLabel(
                    score_frame,
                    text=f"{name.upper()}: {score:.0%}",
                    font=F_BODY_BOLD,
                    text_color=ACCENT if score >= 0.7 else WARNING
                ).pack(anchor="w", padx=12, pady=2)

        # Coaching messages
        coaching = result.get("coaching", [])
        if coaching:
            coach_frame = ctk.CTkFrame(self.coach_result, fg_color=CARD, corner_radius=8)
            coach_frame.pack(fill="x", padx=12, pady=(0, 10))

            ctk.CTkLabel(
                coach_frame,
                text="TAVSIYELER",
                font=F_H3,
                text_color=ACCENT
            ).pack(anchor="w", padx=12, pady=(10, 4))

            for msg in coaching:
                ctk.CTkLabel(
                    coach_frame,
                    text=f"-> {msg}",
                    text_color=TEXT,
                    wraplength=950,
                    justify="left"
                ).pack(anchor="w", padx=12, pady=2)

    def build_library_map_view(self):

        self.make_section_title(
            self.content,
            "Library DNA Map",
            "Kutuphanendeki parcalarin enerji/parlaklik dagilimini kesfet."
        )

        source = self.library or self.saved_tracks

        self.library_map = LibraryMap(self.content, width=850, height=480)
        self.library_map.pack(fill="both", expand=True, pady=(0, 10))
        self.library_map.set_tracks(source)

    def build_smart_set_view(self):

        self.make_section_title(
            self.content,
            "Smart Set Generator",
            "Mekan tipine gore enerji egrisi ile otomatik set olustur."
        )

        controls = ctk.CTkFrame(self.content, fg_color=CARD, corner_radius=8)
        controls.pack(fill="x", pady=(0, 10))

        self.smart_venue = StringVar(value="CLUB")
        self.smart_hours = StringVar(value="4")

        ctk.CTkComboBox(
            controls,
            variable=self.smart_venue,
            values=["CLUB", "WEDDING", "FESTIVAL", "LOUNGE"],
            width=140
        ).pack(side="left", padx=12, pady=12)

        ctk.CTkEntry(
            controls,
            textvariable=self.smart_hours,
            placeholder_text="Hours",
            width=80
        ).pack(side="left", padx=6, pady=12)

        ctk.CTkButton(
            controls,
            text="SMART SET OLUSTUR",
            command=self.generate_smart_set
        ).pack(side="left", padx=6, pady=12)

        ctk.CTkButton(
            controls,
            text="SET KAYDINI BASLAT",
            command=self.start_set_recording,
            fg_color="#00C896"
        ).pack(side="right", padx=6, pady=12)

        ctk.CTkButton(
            controls,
            text="KAYDI DURDUR",
            command=self.stop_set_recording,
            fg_color="#FF4D6D"
        ).pack(side="right", padx=6, pady=12)

        self.smart_result = ctk.CTkScrollableFrame(
            self.content, fg_color=PANEL, corner_radius=8
        )
        self.smart_result.pack(fill="both", expand=True, pady=(0, 10))

        ctk.CTkLabel(
            self.smart_result,
            text="Mekan tipi ve sure sec, SMART SET OLUSTUR'a bas.",
            text_color=MUTED
        ).pack(anchor="w", padx=12, pady=12)

    def generate_smart_set(self):

        source = self.library or self.saved_tracks
        venue = self.smart_venue.get()
        hours = float(self.smart_hours.get() or 4)

        result = self.smart_playlist.generate(source, venue, hours)

        for child in self.smart_result.winfo_children():
            child.destroy()

        # Stats
        stats = result.get("stats", {})
        ctk.CTkLabel(
            self.smart_result,
            text=f"{result['template']} | {result['total_tracks']} parca | "
                 f"Ort. enerji: {stats.get('avg_energy', 0)} | "
                 f"Ort. BPM: {stats.get('avg_bpm', 0)} | "
                 f"Tur cesitliligi: {stats.get('genre_diversity', 0)}",
            font=F_BODY_BOLD,
            text_color=ACCENT,
            wraplength=1000,
            justify="left"
        ).pack(anchor="w", padx=12, pady=(12, 8))

        # Phases
        for phase in result.get("phases", []):
            phase_frame = ctk.CTkFrame(self.smart_result, fg_color=CARD, corner_radius=8)
            phase_frame.pack(fill="x", padx=12, pady=4)

            ctk.CTkLabel(
                phase_frame,
                text=f"{phase['name']} ({phase['track_count']} parca) | Enerji: {phase['target_energy']}",
                font=F_BODY_BOLD,
                text_color=NEON_BLUE
            ).pack(anchor="w", padx=12, pady=(8, 2))

            ctk.CTkLabel(
                phase_frame,
                text=phase.get("instruction", ""),
                text_color=TEXT,
                wraplength=950,
                justify="left"
            ).pack(anchor="w", padx=12, pady=(0, 4))

            # Show first few tracks
            for track in phase.get("tracks", [])[:5]:
                ctk.CTkLabel(
                    phase_frame,
                    text=f"  - {track.get('name', '?')[:50]} | "
                         f"{track.get('bpm', '?')} BPM | E:{track.get('energy', 0):.2f} | "
                         f"{track.get('role', '?')}",
                    text_color=MUTED,
                    wraplength=950,
                    justify="left"
                ).pack(anchor="w", padx=18, pady=1)

            if phase["track_count"] > 5:
                ctk.CTkLabel(
                    phase_frame,
                    text=f"  ... +{phase['track_count'] - 5} parca daha",
                    text_color=MUTED
                ).pack(anchor="w", padx=18, pady=1)

        # Set as current
        all_tracks = []
        for phase in result.get("phases", []):
            all_tracks.extend(phase.get("tracks", []))
        self.current_set = all_tracks

    def start_set_recording(self):
        venue = self.smart_venue.get()
        style = "AFRO HOUSE"
        self.set_recorder.start_recording(venue=venue, style=style)
        self.set_status(f"SET KAYDI BASLADI: {venue}")

    def stop_set_recording(self):
        result = self.set_recorder.stop_recording()
        summary = self.set_recorder.get_session_summary()
        self.set_status(
            f"SET KAYDI DURDURULDU: {summary.get('tracks_played', 0)} parca, "
            f"{summary.get('duration_minutes', 0)} dakika"
        )

    def build_dj_profile_view(self):

        self.make_section_title(
            self.content,
            "DJ Profile / Style DNA",
            "Kutuphanenin ve setlerinin analiziyle DJ stil DNA'nı olustur."
        )

        controls = ctk.CTkFrame(self.content, fg_color=CARD, corner_radius=8)
        controls.pack(fill="x", pady=(0, 10))

        ctk.CTkButton(
            controls,
            text="PROFIL OLUSTUR",
            command=self.generate_dj_profile
        ).pack(side="left", padx=12, pady=12)

        ctk.CTkButton(
            controls,
            text="SECILI PARCA ICIN BENZERLER",
            command=self.show_track_similarity
        ).pack(side="left", padx=6, pady=12)

        ctk.CTkButton(
            controls,
            text="MFCC MODEL EGIT",
            command=self.train_mfcc_model
        ).pack(side="right", padx=6, pady=12)

        self.profile_result = ctk.CTkScrollableFrame(
            self.content, fg_color=PANEL, corner_radius=8
        )
        self.profile_result.pack(fill="both", expand=True, pady=(0, 10))

        self.generate_dj_profile()

    def generate_dj_profile(self):

        source = self.library or self.saved_tracks
        profile = self.dj_profile.build_profile(source)

        for child in self.profile_result.winfo_children():
            child.destroy()

        # DNA Display
        dna = profile.get("dna", "E00-B00-G00-P000")
        ctk.CTkLabel(
            self.profile_result,
            text=f"DJ DNA: {dna}",
            font=("Segoe UI", 28, "bold"),
            text_color=ACCENT
        ).pack(anchor="w", padx=12, pady=(12, 4))

        ctk.CTkLabel(
            self.profile_result,
            text=f"{profile.get('track_count', 0)} parca analiz edildi | "
                 f"{profile.get('genre_count', 0)} farkli tur",
            font=F_BODY_BOLD,
            text_color=TEXT
        ).pack(anchor="w", padx=12, pady=(0, 12))

        # Stats cards
        stats_frame = ctk.CTkFrame(self.profile_result, fg_color="transparent")
        stats_frame.pack(fill="x", padx=12, pady=(0, 8))

        for label, value in [
            ("ORT. ENERJI", f"{profile.get('avg_energy', 0):.2f}"),
            ("ORT. BPM", f"{profile.get('avg_bpm', 0):.0f}"),
            ("BPM ARALIGI", profile.get("bpm_range", "--")),
            ("ORT. AI EAR", f"{profile.get('avg_ear_score', 0):.2f}"),
        ]:
            card = ctk.CTkFrame(stats_frame, fg_color=CARD, corner_radius=8)
            card.pack(side="left", fill="x", expand=True, padx=4)
            ctk.CTkLabel(card, text=value, font=F_H2, text_color=ACCENT).pack(anchor="w", padx=10, pady=(8, 0))
            ctk.CTkLabel(card, text=label, font=F_META, text_color=MUTED).pack(anchor="w", padx=10, pady=(0, 8))

        # Energy distribution
        energy_dist = profile.get("energy_distribution", {})
        energy_frame = ctk.CTkFrame(self.profile_result, fg_color=CARD, corner_radius=8)
        energy_frame.pack(fill="x", padx=12, pady=(0, 8))

        ctk.CTkLabel(energy_frame, text="ENERJI DAGILIMI", font=F_BODY_BOLD, text_color=ACCENT).pack(anchor="w", padx=12, pady=(10, 4))

        for label, pct in [("DUSUK", energy_dist.get("low", 0)), ("ORTA", energy_dist.get("mid", 0)), ("YUKSEK", energy_dist.get("high", 0))]:
            bar_text = f"{label}: {'#' * int(pct * 30)}{'.' * (30 - int(pct * 30))} %{pct*100:.0f}"
            ctk.CTkLabel(energy_frame, text=bar_text, font=("Consolas", 10), text_color=TEXT).pack(anchor="w", padx=12, pady=1)

        # Top genres
        top_genres = profile.get("top_genres", [])
        if top_genres:
            genre_frame = ctk.CTkFrame(self.profile_result, fg_color=CARD, corner_radius=8)
            genre_frame.pack(fill="x", padx=12, pady=(0, 8))

            ctk.CTkLabel(genre_frame, text="EN COK KULLANILAN TURLER", font=F_BODY_BOLD, text_color=ACCENT).pack(anchor="w", padx=12, pady=(10, 4))

            for genre, count in top_genres[:5]:
                pct = count / max(1, profile.get("track_count", 1))
                ctk.CTkLabel(genre_frame, text=f"  {genre}: {count} parca (%{pct*100:.0f})", text_color=TEXT).pack(anchor="w", padx=12, pady=1)

        # Top keys
        top_keys = profile.get("top_keys", [])
        if top_keys:
            key_frame = ctk.CTkFrame(self.profile_result, fg_color=CARD, corner_radius=8)
            key_frame.pack(fill="x", padx=12, pady=(0, 8))

            ctk.CTkLabel(key_frame, text="EN COK KULLANILAN ANAHTARLAR", font=F_BODY_BOLD, text_color=NEON_PURPLE).pack(anchor="w", padx=12, pady=(10, 4))

            for key, count in top_keys:
                ctk.CTkLabel(key_frame, text=f"  {key}: {count} parca", text_color=TEXT).pack(anchor="w", padx=12, pady=1)

        # Insights
        insights = profile.get("insights", [])
        if insights:
            insight_frame = ctk.CTkFrame(self.profile_result, fg_color=CARD, corner_radius=8)
            insight_frame.pack(fill="x", padx=12, pady=(0, 8))

            ctk.CTkLabel(insight_frame, text="DJ TAVSIYELERI", font=F_BODY_BOLD, text_color=WARNING).pack(anchor="w", padx=12, pady=(10, 4))

            for insight in insights:
                ctk.CTkLabel(insight_frame, text=f"-> {insight}", text_color=TEXT, wraplength=950, justify="left").pack(anchor="w", padx=12, pady=2)

    def show_track_similarity(self):

        if not self.selected_track:
            self.set_status("Once bir parca sec.")
            return

        similar = self.similarity_engine.find_similar(
            self.selected_track, self.library or self.saved_tracks, limit=5
        )

        for child in self.profile_result.winfo_children():
            child.destroy()

        target_name = self.selected_track.get("name", "?")[:50]
        ctk.CTkLabel(
            self.profile_result,
            text=f"SIMILAR TO: {target_name}",
            font=F_H2,
            text_color=ACCENT
        ).pack(anchor="w", padx=12, pady=(12, 8))

        if not similar:
            ctk.CTkLabel(self.profile_result, text="Benzer parca bulunamadi.", text_color=MUTED).pack(anchor="w", padx=12)
            return

        for i, track in enumerate(similar, 1):
            card = ctk.CTkFrame(self.profile_result, fg_color=CARD, corner_radius=8)
            card.pack(fill="x", padx=12, pady=4)

            score = track.get("similarity_score", 0)
            reason = track.get("similarity_reason", "")

            ctk.CTkLabel(
                card,
                text=f"{i}. {track.get('name', '?')[:50]} | Benzerlik: {score:.0%}",
                font=F_BODY_BOLD,
                text_color=ACCENT if score > 0.7 else TEXT
            ).pack(anchor="w", padx=12, pady=(8, 2))

            ctk.CTkLabel(
                card,
                text=f"{track.get('bpm', '?')} BPM | {track.get('genre', '?')} | {reason}",
                text_color=MUTED,
                wraplength=900,
                justify="left"
            ).pack(anchor="w", padx=12, pady=(0, 8))

    def train_mfcc_model(self):

        self.set_status("MFCC model egitimi baslatildi... (arka plan)")

        def _train_worker():
            try:
                import subprocess
                result = subprocess.run(
                    [sys.executable, "scripts/train_genre_model.py"],
                    capture_output=True, text=True, timeout=300
                )
                output = result.stdout + result.stderr
                self.after(0, lambda: self.set_status(
                    f"MFCC EGITIM: {output[-200:] if output else 'tamamlandi'}"
                ))
            except Exception as e:
                self.after(0, lambda: self.set_status(f"MFCC EGITIM HATASI: {e}"))

        threading.Thread(target=_train_worker, daemon=True).start()

    def build_remix_lab_view(self):

        self.make_section_title(
            self.content,
            "Remix Atolyesi",
            "Secili parcadan remix fikri, vokal ayirma hazirligi ve DJ dostu akis plani uret."
        )

        controls = ctk.CTkFrame(self.content, fg_color=CARD, corner_radius=8)
        controls.pack(fill="x", pady=(0, 10))

        self.remix_style = StringVar(value="AFRO HOUSE")

        ctk.CTkLabel(
            controls,
            text="Hedef tarz",
            font=("Segoe UI", 13, "bold"),
            text_color=MUTED
        ).pack(side="left", padx=(12, 6), pady=12)

        ctk.CTkComboBox(
            controls,
            variable=self.remix_style,
            values=["AFRO HOUSE", "TECH HOUSE", "MELODIC HOUSE", "REGGAETON"],
            width=170
        ).pack(side="left", padx=12, pady=12)

        ctk.CTkButton(
            controls,
            text="REMIX PLANI HAZIRLA",
            command=self.plan_selected_remix
        ).pack(side="left", padx=6, pady=12)

        ctk.CTkButton(
            controls,
            text="HAZIRLIK KONTROLU",
            command=self.check_selected_remix_readiness
        ).pack(side="left", padx=6, pady=12)

        ctk.CTkButton(
            controls,
            text="PLANI DISA AKTAR",
            command=self.export_selected_remix_plan
        ).pack(side="left", padx=6, pady=12)

        ctk.CTkButton(
            controls,
            text="FL MASTERING PACK",
            command=self.export_fl_mastering_pack
        ).pack(side="left", padx=6, pady=12)

        ctk.CTkButton(
            controls,
            text="MIX MASTER DOKTORU",
            command=self.inspect_selected_mix_master
        ).pack(side="left", padx=6, pady=12)

        ctk.CTkButton(
            controls,
            text="WAV ANALIZ",
            command=self.analyze_selected_mix_master_audio
        ).pack(side="left", padx=6, pady=12)

        ctk.CTkButton(
            controls,
            text="AI REMIX WAV URET",
            command=self.render_selected_ai_remix_wav
        ).pack(side="left", padx=6, pady=12)

        ctk.CTkButton(
            controls,
            text="VOKALI AYIR",
            command=self.separate_selected_vocals
        ).pack(side="left", padx=6, pady=12)

        caps = self.remix_lab.capabilities()
        self.build_remix_status_panel(caps)

        self.remix_output = ctk.CTkScrollableFrame(
            self.content,
            fg_color=PANEL,
            corner_radius=8
        )
        self.remix_output.pack(fill="both", expand=True, pady=(0, 10))
        self.render_remix_empty_state(caps)

        source = self.library or self.saved_tracks
        self.build_filter_bar(self.content, source)

        table_frame = ctk.CTkFrame(self.content, fg_color=PANEL)
        table_frame.pack(fill="both", expand=True)
        self.table = TrackTable(
            table_frame,
            on_select=self.on_track_selected,
            on_double_click=self.on_track_double_click,
            on_right_click_action=self.on_track_right_click,
        )
        self.table.pack(fill="both", expand=True, padx=6, pady=6)
        self.populate_table(source)

    def build_astra_chat_view(self):
        from app.ui.astra_chat import AstraChatPanel
        panel = AstraChatPanel(self)
        panel.build(self.content)

    def build_astra_chat_view_old(self):
        """Legacy chat view (kept for reference)."""
        self.make_section_title(
            self.content,
            "Astra Chat",
            "Hologram asistanla konuş."
        )

        controls = ctk.CTkFrame(self.content, fg_color=CARD, corner_radius=8)
        controls.pack(fill="x", pady=(0, 10))

        self.jarvis_chat_input = StringVar(value="")

        ctk.CTkEntry(
            controls,
            textvariable=self.jarvis_chat_input,
            placeholder_text="Astra ile sohbet et...",
            width=640
        ).pack(side="left", padx=(12, 6), pady=12)

        ctk.CTkButton(
            controls,
            text="GONDER",
            width=110,
            command=self.send_jarvis_prompt
        ).pack(side="left", padx=6, pady=12)

        ctk.CTkButton(
            controls,
            text="KAMERA INCELE",
            width=130,
            command=self.inspect_camera_scene
        ).pack(side="left", padx=6, pady=12)

        ctk.CTkButton(
            controls,
            text="KAMERA ONIZLEME",
            width=150,
            command=self.toggle_camera_preview
        ).pack(side="left", padx=6, pady=12)

        body = ctk.CTkFrame(self.content, fg_color="transparent")
        body.pack(fill="both", expand=True)

        chat_frame = ctk.CTkFrame(body, fg_color=PANEL, corner_radius=8)
        chat_frame.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=6)

        ctk.CTkLabel(
            chat_frame,
            text="ASTRA SOHBET GECMİŞİ",
            font=("Segoe UI", 15, "bold"),
            text_color=ACCENT
        ).pack(anchor="w", padx=12, pady=(12, 6))

        self.jarvis_history_box = ctk.CTkTextbox(
            chat_frame,
            fg_color="#050B17",
            text_color=TEXT,
            wrap="word",
            width=1,
            height=18
        )
        self.jarvis_history_box.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.jarvis_history_box.configure(state="disabled")

        holo_frame = ctk.CTkFrame(body, fg_color=PANEL, corner_radius=8)
        holo_frame.pack(side="right", fill="both", expand=False, padx=(10, 0), pady=6, ipadx=6)
        holo_frame.configure(width=420)

        ctk.CTkLabel(
            holo_frame,
            text="ASTRA HOLOGRAM",
            font=("Segoe UI", 15, "bold"),
            text_color=ACCENT
        ).pack(anchor="w", padx=12, pady=(12, 6))

        self.jarvis_hologram_canvas = tk.Canvas(
            holo_frame,
            height=380,
            bg="#02060F",
            highlightthickness=0
        )
        self.jarvis_hologram_canvas.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self.jarvis_status_label = ctk.CTkLabel(
            holo_frame,
            text="Hologram senaryosu hazır. Kamerayı incele ya da sohbet et. Astra, seni işitiyor ve stüdyoda aktif.",
            font=("Segoe UI", 11),
            text_color=MUTED,
            wraplength=380,
            justify="left"
        )
        self.jarvis_status_label.pack(anchor="w", padx=12, pady=(0, 12))

        self.jarvis_holo_phase = 0
        self.jarvis_holo_running = True
        self.jarvis_speaking = False
        self.update_jarvis_hologram()

        self.render_jarvis_chat_message(
            "Astra",
            "Merhaba. DJ üretim asistanın Astra burada. Hologram bedenimle seninle üretim yapmaya hazırım."
        )

    def send_jarvis_prompt(self):

        text = str(self.jarvis_chat_input.get() or "").strip()

        if not text:
            self.set_status("Astra: Konuşma metni boş. Lütfen bir soru veya fikir yaz.")
            return

        self.jarvis_chat_input.set("")
        self.render_jarvis_chat_message("Sen", text)
        self.set_status("Astra: cevap hazırlanıyor...")

        threading.Thread(
            target=self.jarvis_chat_worker,
            args=(text,),
            daemon=True
        ).start()

    def jarvis_chat_worker(self, prompt):

        result = self.astra_assistant.chat(prompt)
        response = result.get("response", "Astra cevap üretirken bir sorun oldu.")

        self.after(0, lambda: self.render_jarvis_chat_message("Astra", response))
        self.after(0, lambda: self.set_status("Astra: cevap verdi."))

    def render_jarvis_chat_message(self, speaker, message):

        if not hasattr(self, "jarvis_history_box"):
            return

        self.jarvis_history_box.configure(state="normal")
        self.jarvis_history_box.insert("end", f"{speaker}: {message}\n\n")
        self.jarvis_history_box.see("end")
        self.jarvis_history_box.configure(state="disabled")

        if speaker == "Astra":
            self.jarvis_speaking = True
            self.after(900, lambda: setattr(self, "jarvis_speaking", False))

    def inspect_camera_scene(self):

        result = self.camera_assistant.inspect_scene()
        self.jarvis_status_label.configure(
            text=result.get("message", "Kamera incelemesi tamamlandı.")
        )
        self.set_status(f"Astra kamera inceleme: {result.get('message')}" )
        self.render_jarvis_chat_message("Astra", result.get("message", "Kamera sonucu alınamadı."))

    def toggle_camera_preview(self):

        if self.camera_preview_active:
            result = self.camera_assistant.stop_preview()
            self.camera_preview_active = False
            self.jarvis_status_label.configure(text=result.get("message"))
            self.set_status("Astra: kamera önizlemesi durduruldu.")
            return

        result = self.camera_assistant.start_preview()
        self.camera_preview_active = result.get("ok", False)
        self.jarvis_status_label.configure(text=result.get("message"))
        self.set_status("Astra: kamera önizlemesi başlatıldı." if result.get("ok") else result.get("message"))

        if not hasattr(self, "jarvis_hologram_canvas"):
            return

        if not self.jarvis_holo_running:
            return

        self.update_jarvis_hologram()

    def update_jarvis_hologram(self):

        if not hasattr(self, "jarvis_hologram_canvas"):
            return

        if not self.jarvis_holo_running:
            return

        canvas = self.jarvis_hologram_canvas
        width = max(canvas.winfo_width(), 1)
        height = max(canvas.winfo_height(), 1)
        canvas.delete("all")

        center_x = width // 2
        center_y = height // 2 + 20
        radius = min(width, height) // 6
        glow = 6 + (1 + math.sin(self.jarvis_holo_phase * 0.14)) * 3
        pulse = 4 + (1 + math.cos(self.jarvis_holo_phase * 0.09)) * 2

        # Hologram ripple ring
        for i in range(4):
            offset = i * 18
            canvas.create_oval(
                center_x - radius - offset,
                center_y - radius - offset,
                center_x + radius + offset,
                center_y + radius + offset,
                outline="#3B8BFF",
                width=1,
                stipple="gray50"
            )

        # Body glow and shape
        body_top = center_y - radius + 10
        body_bottom = center_y + radius + 28
        body_width = radius * 0.8

        canvas.create_oval(
            center_x - body_width,
            body_top - 30,
            center_x + body_width,
            body_top + 30,
            outline="#7DD1FF",
            width=3,
            fill="",
        )

        canvas.create_polygon(
            center_x - body_width * 0.75, body_top + 20,
            center_x + body_width * 0.75, body_top + 20,
            center_x + body_width * 0.45, body_bottom,
            center_x - body_width * 0.45, body_bottom,
            outline="#88CFFF",
            fill="",
            width=2
        )

        # Arms
        arm_y = body_top + 40
        canvas.create_line(
            center_x - body_width * 0.45,
            arm_y,
            center_x - body_width * 1.4,
            arm_y + 30,
            fill="#7DD1FF",
            width=3,
            dash=(3, 4)
        )
        canvas.create_line(
            center_x + body_width * 0.45,
            arm_y,
            center_x + body_width * 1.4,
            arm_y + 30,
            fill="#7DD1FF",
            width=3,
            dash=(3, 4)
        )

        # Core pulse reflects speaking or passive state
        if getattr(self, "jarvis_speaking", False):
            pulse_color = "#FFD36A"
            pulse_scale = pulse * 1.8
        elif getattr(self, "astra_passive", False):
            pulse_color = "#6EE8C7"
            pulse_scale = pulse * 0.6
        else:
            pulse_color = "#7EE8FF"
            pulse_scale = pulse

        canvas.create_oval(
            center_x - pulse_scale,
            center_y - pulse_scale,
            center_x + pulse_scale,
            center_y + pulse_scale,
            outline=pulse_color,
            width=2
        )

        # Hologram grid
        for i in range(8):
            x = center_x - radius * 1.1 + i * (radius * 2.2 / 7)
            canvas.create_line(x, body_top, x, body_bottom, fill="#1F3B5A", width=1)
        for i in range(6):
            y = body_top + i * ((body_bottom - body_top) / 5)
            canvas.create_line(center_x - radius * 1.05, y, center_x + radius * 1.05, y, fill="#1F3B5A", width=1)

        # Astra labels
        canvas.create_text(
            center_x,
            center_y - radius - 20,
            text="ASTRA",
            fill="#A3E7FF",
            font=("Segoe UI", 18, "bold")
        )

        canvas.create_text(
            center_x,
            center_y + radius + 18,
            text="DJ PRODÜKSİYON ASİSTANI",
            fill="#9CCBFF",
            font=("Segoe UI", 10),
        )

        self.jarvis_holo_phase += 1
        self.after(70, self.update_jarvis_hologram)

    def build_remix_status_panel(self, caps):

        status = ctk.CTkFrame(self.content, fg_color=PANEL, corner_radius=8)
        status.pack(fill="x", pady=(0, 10))

        demucs_text = "hazir" if caps["demucs_available"] else "kurulu degil"
        ffmpeg_text = "hazir" if caps["ffmpeg_available"] else "kurulu degil"
        warning_color = ACCENT if caps["demucs_available"] else WARNING

        ctk.CTkLabel(
            status,
            text=f"Vokal ayirma araci: Demucs {demucs_text}",
            font=("Segoe UI", 14, "bold"),
            text_color=warning_color
        ).pack(anchor="w", padx=12, pady=(12, 2))

        if caps.get("demucs_command"):
            ctk.CTkLabel(
                status,
                text=f"Demucs calisma yolu: {caps['demucs_command']}",
                text_color=MUTED,
                wraplength=1150,
                justify="left"
            ).pack(anchor="w", padx=12, pady=2)

        python_text = "hazir" if caps["python_available"] else "PATH'te gorunmuyor"
        ctk.CTkLabel(
            status,
            text=f"Python komutu: {python_text}",
            text_color=MUTED
        ).pack(anchor="w", padx=12, pady=2)

        ctk.CTkLabel(
            status,
            text=f"Ses donusturme araci: FFmpeg {ffmpeg_text}",
            text_color=MUTED
        ).pack(anchor="w", padx=12, pady=2)

        ctk.CTkLabel(
            status,
            text=f"Cikti klasoru: {caps['output_folder']}",
            text_color=MUTED
        ).pack(anchor="w", padx=12, pady=2)

        if (
            not caps["python_available"]
            or not caps["demucs_available"]
            or not caps["ffmpeg_available"]
        ):
            ctk.CTkLabel(
                status,
                text=f"Kurulum notu: {caps['install_hint']}",
                text_color=WARNING,
                wraplength=1150,
                justify="left"
            ).pack(anchor="w", padx=12, pady=(4, 12))

            for step in caps["install_steps"]:
                ctk.CTkLabel(
                    status,
                    text=step,
                    text_color=MUTED,
                    wraplength=1150,
                    justify="left"
                ).pack(anchor="w", padx=18, pady=1)

    def render_remix_empty_state(self, caps):

        steps = [
            "1. Alttaki tablodan remix yapmak istedigin parcayi sec.",
            "2. Hedef tarzi sec ve Remix Plani Hazirla butonuna bas.",
            "3. Vokali ayirmak icin Demucs ve FFmpeg hazir olduktan sonra Vokali Ayir butonunu kullan.",
        ]

        ctk.CTkLabel(
            self.remix_output,
            text="Baslangic Akisi",
            font=("Segoe UI", 16, "bold"),
            text_color=ACCENT
        ).pack(anchor="w", padx=12, pady=(12, 6))

        for step in steps:
            ctk.CTkLabel(
                self.remix_output,
                text=step,
                text_color=TEXT,
                wraplength=1100,
                justify="left"
            ).pack(anchor="w", padx=12, pady=2)

        if not caps["demucs_available"]:
            ctk.CTkLabel(
                self.remix_output,
                text="Not: Demucs kurulu olmadigi icin su an sadece remix plani hazirlanabilir.",
                text_color=WARNING,
                wraplength=1100,
                justify="left"
            ).pack(anchor="w", padx=12, pady=(10, 12))

    def plan_selected_remix(self):

        if not self.selected_track:
            self.set_status("REMIX LAB: Once bir parca sec.")
            return

        blueprint = self.remix_lab.build_remix_blueprint(
            self.selected_track,
            self.remix_style.get()
        )
        readiness = self.remix_lab.readiness_profile(
            self.selected_track,
            self.remix_style.get()
        )
        brief = self.remix_lab.creative_brief(
            self.selected_track,
            self.remix_style.get()
        )
        self.render_remix_blueprint(blueprint, readiness, brief)
        self.set_status(f"REMIX PLANI HAZIR: {blueprint['target_style']}")

    def check_selected_remix_readiness(self):

        if not self.selected_track:
            self.set_status("REMIX ATOLYESI: Hazirlik kontrolu icin parca sec.")
            return

        readiness = self.remix_lab.readiness_profile(
            self.selected_track,
            self.remix_style.get()
        )
        self.render_remix_readiness(readiness)
        self.set_status(
            f"REMIX HAZIRLIK: {readiness['score']}/100 | {readiness['verdict']}"
        )

    def export_selected_remix_plan(self):

        if not self.selected_track:
            self.set_status("REMIX ATOLYESI: Disa aktarmak icin parca sec.")
            return

        blueprint = self.remix_lab.build_remix_blueprint(
            self.selected_track,
            self.remix_style.get()
        )
        readiness = self.remix_lab.readiness_profile(
            self.selected_track,
            self.remix_style.get()
        )
        result = self.remix_lab.export_blueprint(blueprint, readiness)
        self.set_status(f"REMIX PLANI DISA AKTARILDI: {result['txt_path']}")
        self.log(f"Remix plan JSON: {result['json_path']}")

    def render_selected_ai_remix_wav(self):

        if not self.selected_track:
            self.set_status("AI REMIX: Once bir parca sec.")
            return

        self.resolve_track_audio_path(self.selected_track)
        result = self.remix_lab.render_remix_wav(
            self.selected_track,
            self.remix_style.get()
        )
        self.render_ai_remix_result(result)

        if result.get("ok"):
            self.set_status(
                "AI REMIX WAV HAZIR: "
                f"{result.get('wav_path')}"
            )
            return

        self.set_status(f"AI REMIX HATASI: {result.get('reason')}")

    def render_ai_remix_result(self, result):

        if not hasattr(self, "remix_output") or not self.remix_output.winfo_exists():
            self.set_view("remix_lab")

        for child in self.remix_output.winfo_children():
            child.destroy()

        ctk.CTkLabel(
            self.remix_output,
            text="AI REMIX WAV RENDER",
            font=("Segoe UI", 17, "bold"),
            text_color=ACCENT
        ).pack(anchor="w", padx=12, pady=(12, 6))

        if not result.get("ok"):
            ctk.CTkLabel(
                self.remix_output,
                text=result.get("message", result.get("reason", "Render hatasi")),
                text_color=WARNING,
                wraplength=1100,
                justify="left"
            ).pack(anchor="w", padx=12, pady=4)
            return

        lines = [
            f"Motor: {result.get('engine')}",
            f"Tarz: {result.get('target_style')}",
            f"BPM: {result.get('target_bpm')}",
            f"WAV: {result.get('wav_path')}",
            f"Manifest: {result.get('manifest_path')}",
            f"Kaynak WAV vokal dokusu: {'KULLANILDI' if result.get('vocal_texture_used') else 'YOK / GEREKMEDI'}",
            "Not: Bu ilk render motoru telifsiz procedural sample pack ile WAV uretir.",
        ]

        for line in lines:
            ctk.CTkLabel(
                self.remix_output,
                text=line,
                text_color=TEXT,
                wraplength=1100,
                justify="left"
            ).pack(anchor="w", padx=12, pady=2)

    def export_fl_mastering_pack(self):

        if not self.selected_track:
            self.set_status("FL MASTERING: Once bir parca sec.")
            return

        result = self.fl_studio_bridge.prepare_mastering_pack(
            self.selected_track,
            output_folder="DJ_REMIX_LAB"
        )
        self.set_status(f"FL MASTERING PACK HAZIR: {result['pack_folder']}")
        self.log(f"FL Studio mastering notes: {result['notes_path']}")

    def inspect_selected_mix_master(self):

        if not self.selected_track:
            self.set_status("MIX MASTER DOKTORU: Once bir parca sec.")
            return

        report = self.mix_master_doctor.diagnose(self.selected_track)
        self.render_mix_master_report(report)
        self.set_status(
            f"MIX MASTER DOKTORU: {report['score']}/100 | {report['verdict']}"
        )

    def analyze_selected_mix_master_audio(self):

        if not self.selected_track:
            self.set_status("WAV ANALIZ: Once bir parca sec.")
            return

        path = self.resolve_track_audio_path(self.selected_track)
        result = self.mix_master_engine.analyze_file(path)
        self.render_mix_master_audio_report(result)

        if result.get("ok"):
            score = result.get("doctor", {}).get("score", 0)
            waveform = result.get("waveform")
            phrase_points = result.get("phrase_points", [])
            self.apply_waveform_result_to_track(self.selected_track, result)

            if waveform:
                self.selected_track["waveform"] = waveform
                self.selected_track["phrase_points"] = phrase_points
                self.selected_track["duration"] = result.get(
                    "duration",
                    self.selected_track.get("duration", 0)
                )
                self.draw_track_waveform(self.selected_track)

            self.set_status(f"WAV ANALIZ HAZIR: Mix-master skor {score}/100")
        else:
            self.set_status(f"WAV ANALIZ HATASI: {result.get('reason')}")

    def render_mix_master_audio_report(self, result):

        if not hasattr(self, "remix_output") or not self.remix_output.winfo_exists():
            self.set_view("remix_lab")

        for child in self.remix_output.winfo_children():
            child.destroy()

        ctk.CTkLabel(
            self.remix_output,
            text="WAV / MIX MASTER ANALIZ",
            font=("Segoe UI", 17, "bold"),
            text_color=ACCENT
        ).pack(anchor="w", padx=12, pady=(12, 4))

        if not result.get("ok"):
            self.render_mix_master_list(
                "Analiz Hatasi",
                [result.get("reason", "Bilinmeyen hata")] + result.get("repair_plan", []),
                WARNING
            )
            return

        doctor = result.get("doctor", {})
        self.render_mix_master_list(
            "Master Karari",
            [
                f"Skor: {doctor.get('score')}/100",
                f"Karar: {doctor.get('verdict')}",
                f"Motor: {result.get('engine', 'UNKNOWN')}",
                f"Sure: {result.get('duration')} sn",
                f"Sample rate: {result.get('sample_rate')}",
                result.get("analysis_note", ""),
            ],
            TEXT
        )
        dynamics = result.get("dynamics", {})
        self.render_mix_master_list(
            "Dynamics",
            [
                f"Peak: {dynamics.get('peak_dbfs')} dBFS",
                f"RMS: {dynamics.get('rms_dbfs')} dBFS",
                f"LUFS proxy: {dynamics.get('lufs_proxy')}",
                f"Crest: {dynamics.get('crest_factor')}",
                f"Clipping: {dynamics.get('clipping_ratio')}",
            ],
            MUTED
        )
        studio = result.get("studio_verdict", {})
        targets = studio.get("reference_targets", {})
        self.render_mix_master_list(
            "Producer Studio Verdict",
            [
                f"Studio skor: {studio.get('score')}/100",
                f"Grade: {studio.get('grade')}",
                f"Club peak: {targets.get('club_peak')}",
                f"Club loudness: {targets.get('club_lufs')}",
                f"Streaming loudness: {targets.get('streaming_lufs')}",
                f"Low-end: {targets.get('sub_mono')}",
            ] + studio.get("producer_actions", []),
            ACCENT
        )
        spectrum = result.get("spectrum", {})
        self.render_mix_master_list(
            "Spektrum",
            [
                f"Brightness: {spectrum.get('brightness')}",
                f"Harshness: {spectrum.get('harshness')}",
                f"Mud risk: {spectrum.get('mud_risk')}",
                f"Bands: {spectrum.get('bands')}",
            ],
            MUTED
        )
        self.render_mix_master_list("Onarim Plani", result.get("repair_plan", []), WARNING)
        dna = result.get("recreation_dna", {})
        self.render_mix_master_list(
            "Yeniden Yaratim DNA",
            [f"{key}: {value}" for key, value in dna.items()],
            TEXT
        )

    def render_mix_master_report(self, report):

        if not hasattr(self, "remix_output") or not self.remix_output.winfo_exists():
            self.set_view("remix_lab")

        for child in self.remix_output.winfo_children():
            child.destroy()

        ctk.CTkLabel(
            self.remix_output,
            text=f"Mix Master Doctor | {report['track']}",
            font=("Segoe UI", 17, "bold"),
            text_color=ACCENT
        ).pack(anchor="w", padx=12, pady=(12, 4))

        score_color = ACCENT if report["score"] >= 80 else WARNING
        ctk.CTkLabel(
            self.remix_output,
            text=f"Profesyonel Skor: {report['score']} / 100 | {report['verdict']}",
            font=("Segoe UI", 15, "bold"),
            text_color=score_color
        ).pack(anchor="w", padx=12, pady=3)

        ctk.CTkLabel(
            self.remix_output,
            text=report["doctor_note"],
            text_color=TEXT,
            wraplength=1100,
            justify="left"
        ).pack(anchor="w", padx=12, pady=(0, 10))

        self.render_mix_master_list("Acil Mudahaleler", report["urgent_fixes"], WARNING)

        if report["issues"]:
            issue_lines = [
                f"{item['severity']} | {item['code']}: {item['message']} -> {item['repair']}"
                for item in report["issues"]
            ]
            self.render_mix_master_list("Tespit Edilen Sorunlar", issue_lines, TEXT)

        self.render_mix_master_list(
            "Suno / AI Cikti Kurtarma Zinciri",
            report["suno_rescue_chain"],
            TEXT
        )
        self.render_mix_master_list("Mix Zinciri", report["mix_chain"], MUTED)
        self.render_mix_master_list("Mastering Zinciri", report["mastering_chain"], MUTED)

        stem_lines = [
            f"{key}: {value}"
            for key, value in report["stem_strategy"].items()
        ]
        self.render_mix_master_list("Stem Stratejisi", stem_lines, TEXT)

    def render_mix_master_list(self, title, items, color):

        ctk.CTkLabel(
            self.remix_output,
            text=title,
            font=("Segoe UI", 14, "bold"),
            text_color=ACCENT_SOFT
        ).pack(anchor="w", padx=12, pady=(12, 4))

        for item in items:
            ctk.CTkLabel(
                self.remix_output,
                text=f"- {item}",
                text_color=color,
                wraplength=1100,
                justify="left"
            ).pack(anchor="w", padx=18, pady=2)

    def separate_selected_vocals(self):

        if not self.selected_track:
            self.set_status("REMIX LAB: Vocal ayirma icin parca sec.")
            return

        track = dict(self.selected_track)
        self.set_status("VOKAL AYIRMA: Demucs islemi baslatildi...")

        threading.Thread(
            target=self.separate_vocals_worker,
            args=(track,),
            daemon=True
        ).start()

    def separate_vocals_worker(self, track):

        result = self.remix_lab.separate_vocals(track)
        message = result.get("message", "")

        if len(message) > 220:
            message = message[-220:]

        self.after(
            0,
            lambda r=result, m=message: self.finish_vocal_separation(r, m)
        )

    def finish_vocal_separation(self, result, message):

        self.set_status(
            f"VOKAL AYIRMA: {self.remix_reason_text(result.get('reason'))} | {message}"
        )
        self.log(f"Demucs komutu: {result.get('command')}")

    def remix_reason_text(self, reason):

        labels = {
            "DONE": "tamamlandi",
            "DEMUCS_FAILED": "Demucs hata verdi",
            "DEMUCS_ERROR": "Demucs calistirilamadi",
            "DEMUCS_NOT_INSTALLED": "Demucs kurulu degil",
            "SOURCE_FILE_NOT_FOUND": "dosya bulunamadi",
        }

        return labels.get(reason, reason or "bilinmiyor")

    def render_remix_readiness(self, readiness):

        for child in self.remix_output.winfo_children():
            child.destroy()

        self.render_readiness_block(readiness)

    def render_readiness_block(self, readiness):

        ctk.CTkLabel(
            self.remix_output,
            text=f"Hazirlik Skoru: {readiness['score']} / 100",
            font=("Segoe UI", 16, "bold"),
            text_color=ACCENT if readiness["score"] >= 80 else WARNING
        ).pack(anchor="w", padx=12, pady=(12, 4))

        ctk.CTkLabel(
            self.remix_output,
            text=f"Durum: {readiness['verdict']}",
            text_color=TEXT
        ).pack(anchor="w", padx=12, pady=2)

        ctk.CTkLabel(
            self.remix_output,
            text=f"Tempo notu: {readiness['tempo_note']}",
            text_color=MUTED,
            wraplength=1100,
            justify="left"
        ).pack(anchor="w", padx=12, pady=2)

        ctk.CTkLabel(
            self.remix_output,
            text=f"Sonraki adim: {readiness['next_action']}",
            text_color=WARNING,
            wraplength=1100,
            justify="left"
        ).pack(anchor="w", padx=12, pady=(2, 8))

        for check in readiness["checks"]:
            marker = "OK" if check["ok"] else "EKSIK"
            ctk.CTkLabel(
                self.remix_output,
                text=f"{marker} | {check['label']}: {check['message']}",
                text_color=TEXT if check["ok"] else WARNING,
                wraplength=1100,
                justify="left"
            ).pack(anchor="w", padx=18, pady=1)

    def render_remix_blueprint(self, blueprint, readiness=None, brief=None):

        for child in self.remix_output.winfo_children():
            child.destroy()

        if readiness:
            self.render_readiness_block(readiness)

        ctk.CTkLabel(
            self.remix_output,
            text=(
                f"{blueprint['track']} -> {blueprint['target_style']} remixi | "
                f"{blueprint['source_bpm']} BPM -> {blueprint['target_bpm']} BPM "
                f"({blueprint['tempo_change_percent']:+.2f}%)"
            ),
            font=("Segoe UI", 15, "bold"),
            text_color=ACCENT
        ).pack(anchor="w", padx=12, pady=(14, 4))

        if brief:
            ctk.CTkLabel(
                self.remix_output,
                text=f"DJ hedefi: {brief['dj_goal']}",
                text_color=TEXT,
                wraplength=1100,
                justify="left"
            ).pack(anchor="w", padx=12, pady=3)

        labels = {
            "drum_feel": "Davul hissi",
            "bass": "Bass yaklasimi",
            "vocal_treatment": "Vokal kullanimi",
            "legal_note": "Telif notu",
        }

        for label in ("drum_feel", "bass", "vocal_treatment", "legal_note"):
            ctk.CTkLabel(
                self.remix_output,
                text=f"{labels[label]}: {blueprint[label]}",
                text_color=TEXT,
                wraplength=1100,
                justify="left"
            ).pack(anchor="w", padx=12, pady=3)

        ctk.CTkLabel(
            self.remix_output,
            text="Remix Akisi",
            font=("Segoe UI", 14, "bold"),
            text_color=WARNING
        ).pack(anchor="w", padx=12, pady=(12, 4))

        for section in blueprint["arrangement"]:
            ctk.CTkLabel(
                self.remix_output,
                text=(
                    f"{section['section']} | {section['bars']} bar | "
                    f"{section['instruction']}"
                ),
                text_color=MUTED,
                wraplength=1100,
                justify="left"
            ).pack(anchor="w", padx=18, pady=2)

        ctk.CTkLabel(
            self.remix_output,
            text="Stem Plani",
            font=("Segoe UI", 14, "bold"),
            text_color=WARNING
        ).pack(anchor="w", padx=12, pady=(12, 4))

        for item in blueprint["stem_plan"]:
            ctk.CTkLabel(
                self.remix_output,
                text=item,
                text_color=MUTED,
                wraplength=1100,
                justify="left"
            ).pack(anchor="w", padx=18, pady=2)

    def build_export_center_view(self):

        self.make_section_title(
            self.content,
            "Export Center",
            "Set, show ve Rekordbox hazirlik ciktilarini uret."
        )

        controls = ctk.CTkFrame(self.content, fg_color=CARD, corner_radius=8)
        controls.pack(fill="x", pady=(0, 10))

        ctk.CTkButton(
            controls,
            text="EXPORT CURRENT SET M3U",
            command=self.export_current_set_m3u
        ).pack(side="left", padx=8, pady=10)

        ctk.CTkButton(
            controls,
            text="EXPORT REKORDBOX XML STUB",
            command=self.export_rekordbox_stub
        ).pack(side="left", padx=8, pady=10)

        ctk.CTkButton(
            controls,
            text="REKORDBOX LIVE HAZIRLA",
            command=self.prepare_rekordbox_live_set
        ).pack(side="left", padx=8, pady=10)

        self.export_status = ctk.CTkLabel(
            self.content,
            text="Export icin Performance, Show Director veya Set Builder ile set olustur.",
            text_color=MUTED,
            anchor="w"
        )
        self.export_status.pack(fill="x", pady=(0, 10))

        source = self.current_set or self.library or self.saved_tracks
        self.build_filter_bar(self.content, source)

        table_frame = ctk.CTkFrame(self.content, fg_color=PANEL)
        table_frame.pack(fill="both", expand=True)
        self.table = TrackTable(
            table_frame,
            on_select=self.on_track_selected,
            on_double_click=self.on_track_double_click,
            on_right_click_action=self.on_track_right_click,
        )
        self.table.pack(fill="both", expand=True, padx=6, pady=6)
        self.populate_table(source)

    def build_cloud_export_view(self):

        self.make_section_title(
            self.content,
            "Cloud & Export",
            "Trend onerileri, DJ arsiv aboneligi ve Rekordbox/export isleri."
        )

        actions = ctk.CTkFrame(self.content, fg_color=CARD, corner_radius=8)
        actions.pack(fill="x", pady=(0, 10))

        ctk.CTkButton(
            actions,
            text="GLOBAL TRENDS",
            command=lambda: self.set_view("global_trends")
        ).pack(side="left", padx=12, pady=12)

        ctk.CTkButton(
            actions,
            text="EXPORT M3U",
            command=self.export_current_set_m3u
        ).pack(side="left", padx=6, pady=12)

        ctk.CTkButton(
            actions,
            text="REKORDBOX XML",
            command=self.export_rekordbox_stub
        ).pack(side="left", padx=6, pady=12)

        ctk.CTkButton(
            actions,
            text="REKORDBOX LIVE HAZIRLA",
            command=self.prepare_rekordbox_live_set
        ).pack(side="left", padx=6, pady=12)

        ctk.CTkButton(
            actions,
            text="SHOW MANIFEST",
            command=self.export_show_manifest
        ).pack(side="left", padx=6, pady=12)

        ctk.CTkButton(
            actions,
            text="GIG PACK HAZIRLA",
            command=self.prepare_gig_pack
        ).pack(side="left", padx=6, pady=12)

        ctk.CTkButton(
            actions,
            text="ACCOUNT / LICENSE",
            command=lambda: self.set_view("account")
        ).pack(side="left", padx=6, pady=12)

        source = self.current_set or self.library or self.saved_tracks
        plan = self.license.get_plan()
        access = self.cloud_archive.has_access(plan)

        stats = ctk.CTkFrame(self.content, fg_color="transparent")
        stats.pack(fill="x", pady=(0, 12))
        self.make_metric(stats, "EXPORT TRACKS", len(source))
        self.make_metric(stats, "PLAN", plan.get("plan", "DEMO"))
        self.make_metric(stats, "CLOUD ACCESS", "YES" if access else "NO")

        tabs = ctk.CTkTabview(self.content)
        tabs.pack(fill="both", expand=True)
        tabs.add("Trends")
        tabs.add("Archive Packs")
        tabs.add("Current Export")

        self._populate_trends_tab(tabs.tab("Trends"))
        self.populate_cloud_archive(tabs.tab("Archive Packs"), access)

        self.build_filter_bar(tabs.tab("Current Export"), source)
        table_frame = ctk.CTkFrame(tabs.tab("Current Export"), fg_color=PANEL)
        table_frame.pack(fill="both", expand=True)

        self.table = TrackTable(
            table_frame,
            on_select=self.on_track_selected,
            on_double_click=self.on_track_double_click,
            on_right_click_action=self.on_track_right_click,
        )
        self.table.pack(fill="both", expand=True, padx=6, pady=6)
        self.populate_table(source)

    def _populate_trends_tab(self, parent):
        """Populate trends tab."""
        ctk.CTkLabel(parent, text="Trends tab - implement populate_trends_tab", font=F_BODY).pack(padx=20, pady=20)

    def export_show_manifest(self):

        source = self.current_set or self.library or self.saved_tracks
        if not source:
            self.set_status("DISA AKTARMA: Once set olustur veya kutuphane yukle.")
            return

        import json
        os.makedirs("DJ_EXPORTS", exist_ok=True)
        manifest_path = os.path.join("DJ_EXPORTS", "show_manifest.json")

        manifest = {
            "version": "1.0",
            "generated_by": "DJ AI OS",
            "track_count": len(source),
            "tracks": [
                {
                    "name": t.get("name", ""),
                    "bpm": t.get("bpm", 0),
                    "key": t.get("camelot", t.get("key", "")),
                    "genre": t.get("genre", ""),
                    "energy": t.get("energy", 0),
                    "role": t.get("role", ""),
                    "version_type": t.get("version_type", ""),
                }
                for t in source
            ],
        }

        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        self.set_status(f"SHOW MANIFEST: {manifest_path}")

    def export_current_set_m3u(self):

        source = self.current_set or self.library or self.saved_tracks
        path = self.export_center.export_m3u(source, "dj_ai_current_set")
        self.export_status.configure(text=f"M3U exported: {path}")
        self.set_status(f"EXPORT READY: {path}")

    def export_rekordbox_stub(self):

        source = self.current_set or self.library or self.saved_tracks
        path = self.export_center.rekordbox_xml_stub(source, "dj_ai_rekordbox")
        self.export_status.configure(text=f"Rekordbox XML stub exported: {path}")
        self.set_status(f"REKORDBOX EXPORT READY: {path}")

    def prepare_rekordbox_live_set(self):

        source = self.current_set or self.library or self.saved_tracks

        if not source:
            self.set_status("REKORDBOX: Once library yukle veya set olustur.")
            return

        if not self.current_set:
            self.current_set = self.set_engine.build_set(source)
            source = self.current_set

        result = self.rekordbox_bridge.prepare_ai_performance(
            source,
            "dj_ai_live_set"
        )
        first_step = result["instructions"][0]
        status = (
            f"REKORDBOX LIVE HAZIR: XML {result['xml_path']} | "
            f"Manifest {result['manifest_path']} | {first_step}"
        )

        if hasattr(self, "export_status") and self.export_status.winfo_exists():
            self.export_status.configure(text=status)

        self.set_status(status)
        self.log("Rekordbox Bridge adimlari: " + " | ".join(result["instructions"]))

    def prepare_gig_pack(self):

        source = self.current_set or self.library or self.saved_tracks

        if not source:
            self.set_status("GIG PACK: Once library yukle veya set olustur.")
            return

        if not self.current_set:
            self.current_set = self.set_engine.build_set(source)
            source = self.current_set

        style = getattr(self, "performance_style", StringVar(value="AFRO HOUSE")).get()

        try:
            hours = float(
                getattr(self, "performance_hours", StringVar(value="4")).get()
            )
        except (TypeError, ValueError):
            hours = 4

        result = self.gig_pack_builder.build(
            source,
            style=style,
            hours=hours,
            name="dj_ai_gig_pack"
        )

        if not result.get("ok"):
            self.set_status(f"GIG PACK ERROR: {result.get('message')}")
            return

        text = (
            f"GIG PACK HAZIR: {result['headline']} | "
            f"Klasor: {result['pack_folder']}"
        )

        if hasattr(self, "performance_summary") and self.performance_summary.winfo_exists():
            self.performance_summary.configure(text=text)

        if hasattr(self, "export_status") and self.export_status.winfo_exists():
            self.export_status.configure(text=text)

        self.set_status(text)
        self.log(f"Gig Pack manifest: {result['manifest_path']}")

    def build_genre_review_view(self):

        GenreReviewView(self).build(self.content)

    def approve_selected_genre(self):

        if not self.selected_track:
            self.set_status("SELECT A TRACK FIRST")
            return

        record = self.genre_review.approve(
            self.selected_track,
            self.review_genre.get(),
            self.review_parent.get(),
            self.review_role.get()
        )
        self.selected_track.update(record)
        self.selected_track["discovery_status"] = "DJ_APPROVED"
        self.db.save_track(self.selected_track)
        self.set_status(f"GENRE APPROVED: {self.selected_track.get('name')}")

    def build_global_trends_view(self):

        self.make_section_title(
            self.content,
            "Global Trends",
            "DJ radar, cloud arsiv paketleri ve lisansli aylik guncellemeler."
        )

        plan = self.license.get_plan()
        access = self.cloud_archive.has_access(plan)

        status = ctk.CTkFrame(self.content, fg_color=CARD, corner_radius=8)
        status.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            status,
            text=(
                "DJ ARCHIVE ACCESS: ACTIVE"
                if access else
                "DJ ARCHIVE ACCESS: LICENSE REQUIRED"
            ),
            text_color=SUCCESS if access else WARNING,
            font=("Segoe UI", 14, "bold")
        ).pack(side="left", padx=12, pady=12)

        ctk.CTkLabel(
            status,
            text=(
                "Global kaynaklar resmi/izinli connector mantigi ile calisir; "
                "demo ekranda cloud seed verisi gosterilir."
            ),
            text_color=MUTED
        ).pack(side="left", padx=12)

        tabs = ctk.CTkTabview(self.content)
        tabs.pack(fill="both", expand=True)
        tabs.add("Trend Radar")
        tabs.add("Cloud Archive")
        tabs.add("My Library Fit")

        self.populate_trend_radar(tabs.tab("Trend Radar"))
        self.populate_cloud_archive(tabs.tab("Cloud Archive"), access)
        self.populate_library_fit(tabs.tab("My Library Fit"))

    def populate_trend_radar(self, parent):

        trends = self.trends.get_global_trends()
        self.render_trend_cards(parent, trends, show_reason=False)

    def populate_library_fit(self, parent):

        library = self.library or self.saved_tracks
        recommendations = self.trends.recommend_for_library(library)
        self.render_trend_cards(parent, recommendations, show_reason=True)

    def render_trend_cards(self, parent, trends, show_reason):

        area = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        area.pack(fill="both", expand=True, padx=8, pady=8)

        for item in trends:
            card = ctk.CTkFrame(area, fg_color=CARD, corner_radius=8)
            card.pack(fill="x", pady=5)

            title = f"{item.get('artist')} - {item.get('title')}"

            ctk.CTkLabel(
                card,
                text=title,
                font=("Segoe UI", 15, "bold"),
                text_color=TEXT
            ).pack(anchor="w", padx=12, pady=(10, 0))

            detail = (
                f"{item.get('genre')} | {item.get('role')} | "
                f"{item.get('bpm')} BPM | {item.get('key')} | "
                f"Trend {item.get('trend_score')} | "
                f"DJ Support {item.get('dj_support')}"
            )

            ctk.CTkLabel(
                card,
                text=detail,
                text_color=ACCENT_SOFT
            ).pack(anchor="w", padx=12, pady=(2, 0))

            if show_reason:
                ctk.CTkLabel(
                    card,
                    text=item.get("recommendation_reason", ""),
                    text_color=MUTED
                ).pack(anchor="w", padx=12, pady=(2, 10))
            else:
                ctk.CTkLabel(
                    card,
                    text=f"Source: {item.get('source')} | Updated: {item.get('updated_at')}",
                    text_color=MUTED
                ).pack(anchor="w", padx=12, pady=(2, 10))

    def populate_cloud_archive(self, parent, access):

        area = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        area.pack(fill="both", expand=True, padx=8, pady=8)

        for pack in self.cloud_archive.list_packs():
            card = ctk.CTkFrame(area, fg_color=CARD, corner_radius=8)
            card.pack(fill="x", pady=5)

            ctk.CTkLabel(
                card,
                text=pack.get("name", "Cloud Pack"),
                font=("Segoe UI", 15, "bold"),
                text_color=TEXT
            ).pack(anchor="w", padx=12, pady=(10, 0))

            detail = (
                f"{pack.get('month')} | {pack.get('genre')} | "
                f"{pack.get('tracks')} tracks | {pack.get('quality')}"
            )

            ctk.CTkLabel(
                card,
                text=detail,
                text_color=ACCENT_SOFT
            ).pack(anchor="w", padx=12, pady=(2, 0))

            ctk.CTkLabel(
                card,
                text=pack.get("description", ""),
                text_color=MUTED
            ).pack(anchor="w", padx=12, pady=(2, 8))

            ctk.CTkButton(
                card,
                text="DOWNLOAD ARCHIVE PACK" if access else "LICENSE REQUIRED",
                state="normal" if access else "disabled",
                command=lambda p=pack: self.download_cloud_pack(p)
            ).pack(anchor="w", padx=12, pady=(0, 12))

    def download_cloud_pack(self, pack):

        result = self.cloud_archive.download_pack(
            pack.get("id"),
            self.license.get_plan()
        )

        if result.get("ok"):
            self.set_status(f"CLOUD PACK READY: {result.get('path')}")
        else:
            self.set_status(f"CLOUD PACK BLOCKED: {result.get('reason')}")

    def build_crate_builder_view(self):

        self.make_section_title(
            self.content,
            "Crate Builder",
            "Genre ailelerine gore arsiv dagilimini kontrol et."
        )

        tracks = self.get_visible_tracks()
        counts = self.count_by_field(tracks, "parent_genre")

        grid = ctk.CTkScrollableFrame(self.content, fg_color="transparent")
        grid.pack(fill="both", expand=True)

        if not counts:
            ctk.CTkLabel(
                grid,
                text="Henuz crate olusturmak icin arsiv yok.",
                text_color=MUTED
            ).pack(anchor="w", padx=8, pady=8)
            return

        for family, count in sorted(counts.items(), key=lambda item: item[0]):
            row = ctk.CTkFrame(grid, fg_color=CARD, corner_radius=8)
            row.pack(fill="x", pady=4)

            ctk.CTkLabel(
                row,
                text=family or "UNKNOWN",
                font=("Segoe UI", 14, "bold"),
                text_color=TEXT
            ).pack(side="left", padx=12, pady=10)

            ctk.CTkLabel(
                row,
                text=f"{count} tracks",
                text_color=ACCENT
            ).pack(side="right", padx=12)

    def build_live_view(self):

        self.make_section_title(
            self.content,
            "Live DJ",
            "Hazir seti baslat, durdur ve siradaki parcaya gec."
        )

        deck = ctk.CTkFrame(self.content, fg_color=CARD, corner_radius=8)
        deck.pack(fill="x")

        ctk.CTkButton(deck, text="PLAY", command=self.play_set).pack(side="left", padx=12, pady=14)
        ctk.CTkButton(deck, text="STOP", command=self.stop_playback).pack(side="left", padx=6, pady=14)
        ctk.CTkButton(deck, text="NEXT", command=self.next_track).pack(side="left", padx=6, pady=14)
        ctk.CTkButton(
            deck,
            text="REKORDBOX LIVE HAZIRLA",
            command=self.prepare_rekordbox_live_set
        ).pack(side="left", padx=6, pady=14)

        current = self.current_set[0] if self.current_set else None
        now_text = current.get("name", "Set hazir degil") if current else "Set hazir degil"

        ctk.CTkLabel(
            self.content,
            text=now_text,
            font=("Segoe UI", 20, "bold"),
            text_color=TEXT
        ).pack(anchor="w", pady=18)

    def build_ai_memory_view(self):

        self.make_section_title(
            self.content,
            "AI Memory",
            "Son analiz, doktor ve arastirma mesajlari."
        )

        self.log_panel = AILogPanel(self.content)
        self.log_panel.pack(fill="both", expand=True)

        for message in self.ai_messages[-200:]:
            self.log_panel.log(message)

        controls = ctk.CTkFrame(self.content, fg_color=CARD, corner_radius=8)
        controls.pack(fill="x", pady=(10, 0))

        ctk.CTkButton(
            controls,
            text="FEEDBACK GOOD",
            command=lambda: self.record_feedback("GOOD")
        ).pack(side="left", padx=8, pady=10)

        ctk.CTkButton(
            controls,
            text="FEEDBACK BAD",
            command=lambda: self.record_feedback("BAD")
        ).pack(side="left", padx=8, pady=10)

        ctk.CTkButton(
            controls,
            text="NOT PEAK",
            command=lambda: self.record_feedback("NOT_PEAK")
        ).pack(side="left", padx=8, pady=10)

    def record_feedback(self, signal):

        if not self.selected_track:
            self.set_status("SELECT A TRACK FIRST")
            return

        event = self.feedback_learner.record(self.selected_track, signal)
        self.set_status(f"AI FEEDBACK SAVED: {event.get('signal')}")

    def build_account_view(self):

        AccountView(self).build(self.content)

    def create_checkout_intent(self, plan_name):

        path = self.commercial_api.write_checkout_intent(plan_name)
        self.set_status(f"CHECKOUT INTENT CREATED: {path}")

    def activate_license_from_ui(self):

        email = self.account_email.get()
        key = self.account_license_key.get()
        machine_id = self.license.machine.generate()
        result = self.commercial_api.activate_license(email, key, machine_id)

        if result.get("ok") and result.get("license"):
            self.plan = self.license.save_license(result["license"])
            self.set_status(f"LICENSE ACTIVATED: {self.plan.get('plan')}")
            self.set_view("account")
            return

        self.set_status(f"LICENSE ACTIVATION FAILED: {result.get('reason')}")

    def build_settings_view(self):

        SettingsView(self).build(self.content)

    def build_performance_dashboard(self):
        from app.ui.performance_dashboard import PerformanceDashboard
        dash = PerformanceDashboard(self)
        dash.build(self.content)

    def build_neural_synth_view(self):

        self.make_section_title(
            self.content,
            "NEURAL SYNTH",
            "Latent uzayda timbre morph — VAE ile ogrenilmis sesler, "
            "yeni gövde, yeni perde"
        )

        try:
            from app.ai.live_performance import LivePerformanceEngine
            from app.ui.neural_synth_panel import NeuralSynthPanel
            if not hasattr(self, "_neural_engine"):
                self._neural_engine = LivePerformanceEngine(bpm=128,
                                                            sample_rate=44100)
                self._neural_engine.load_genre("house")
            self.neural_panel = NeuralSynthPanel(
                self.content, engine=self._neural_engine, win=self)
            self.neural_panel.pack(fill="both", expand=True, pady=(0, 10))
        except Exception as exc:
            self.log(f"NEURAL SYNTH PANEL: {exc}")
            import traceback
            traceback.print_exc()

    def build_neural_bridge_view(self):

        self.make_section_title(
            self.content,
            "NEURAL BRIDGE",
            "Iki parcayi ayirmadan birlestir — A'nin tinsidan B'ye eriyen "
            "beat-senkron kopru"
        )

        try:
            from app.ui.neural_bridge_panel import NeuralBridgePanel
            self.neural_bridge_panel = NeuralBridgePanel(self.content, win=self)
            self.neural_bridge_panel.pack(fill="both", expand=True, pady=(0, 10))
        except Exception as exc:
            self.log(f"NEURAL BRIDGE PANEL: {exc}")
            import traceback
            traceback.print_exc()

    def build_pioneer_link_view(self):

        self.make_section_title(
            self.content,
            "PIONEER LINK",
            "Pioneer donanim + Rekordbox entegrasyonu — MIDI clock, "
            "transport, canli FX ve donanimdan ogrenme"
        )

        try:
            from app.ui.pioneer_link_panel import PioneerLinkPanel
            self.pioneer_panel = PioneerLinkPanel(self.content, win=self)
            self.pioneer_panel.pack(fill="both", expand=True, pady=(0, 10))
        except Exception as exc:
            self.log(f"PIONEER LINK PANEL: {exc}")
            import traceback
            traceback.print_exc()

    def build_beat_studio_view(self):

        self.make_section_title(
            self.content,
            "BEAT STUDIO",
            "AI ile beat uret, duzenle, disari aktar"
        )

        from app.ai.beat_studio import BeatStudio
        if not hasattr(self, '_beat_studio'):
            self._beat_studio = BeatStudio()

        # Command input
        cmd_frame = ctk.CTkFrame(self.content, fg_color=SURFACE, corner_radius=8, border_width=1, border_color=BORDER)
        cmd_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(cmd_frame, text="BEAT COMMAND", font=F_H3, text_color=RED).pack(anchor="w", padx=12, pady=(10, 4))

        input_row = ctk.CTkFrame(cmd_frame, fg_color="transparent")
        input_row.pack(fill="x", padx=12, pady=(0, 10))

        self.beat_command_entry = ctk.CTkEntry(
            input_row, placeholder_text="128 BPM tech house beat yap...",
            font=F_BODY, fg_color=BG, border_color=BORDER
        )
        self.beat_command_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.beat_command_entry.bind("<Return>", lambda e: self._run_beat_command())

        ctk.CTkButton(input_row, text="GENERATE", fg_color=RED, hover_color=RED_HOVER,
                       text_color="#FFF", font=F_BODY_BOLD, width=100,
                       command=self._run_beat_command).pack(side="left")

        # Quick buttons
        quick_frame = ctk.CTkFrame(cmd_frame, fg_color="transparent")
        quick_frame.pack(fill="x", padx=12, pady=(0, 10))

        for label, cmd in [("House 128", "128 BPM house beat"), ("Techno 135", "135 BPM techno beat"),
                           ("DnB 172", "172 BPM dnb beat"), ("Trap 140", "140 BPM trap beat"),
                           ("Afro 122", "122 BPM afro house beat"), ("MARS 130", "130 BPM mars beat")]:
            ctk.CTkButton(quick_frame, text=label, fg_color=SURFACE_RAISED, hover_color=BORDER,
                          text_color=TEXT_SECONDARY, font=F_META, width=90,
                          command=lambda c=cmd: (self.beat_command_entry.delete(0, "end"),
                                                  self.beat_command_entry.insert(0, c),
                                                  self._run_beat_command())).pack(side="left", padx=3)

        # Result area (compact — DAW gets the expand)
        self.beat_result_frame = ctk.CTkFrame(self.content, fg_color=SURFACE, corner_radius=8, border_width=1, border_color=BORDER)
        self.beat_result_frame.pack(fill="x", pady=(0, 8))

        # FULL DAW — pattern sequencer + piano roll + arrangement + mixer
        try:
            from app.ui.beat_studio_daw import DAWPanel
            self.daw_panel = DAWPanel(self.content, win=self)
            self.daw_panel.pack(fill="both", expand=True, pady=(0, 10))
            self._beat_studio = getattr(self, "_beat_studio", None)
            if self._beat_studio and hasattr(self._beat_studio, "last_project"):
                try:
                    self.daw_panel.project = self._beat_studio.last_project
                    self.daw_panel.engine.project = self._beat_studio.last_project
                    self.daw_panel.engine.mark_dirty()
                    self.daw_panel._refresh_all()
                except Exception:
                    pass
        except Exception as exc:
            self.log(f"DAW PANEL: {exc}")
            import traceback
            traceback.print_exc()

        self.beat_result_label = ctk.CTkLabel(
            self.beat_result_frame, text="Beat komutu bekleniyor...",
            font=F_META, text_color=TEXT_DIM, wraplength=800, justify="left"
        )
        self.beat_result_label.pack(anchor="w", padx=12, pady=10)

        # Export buttons
        export_frame = ctk.CTkFrame(self.content, fg_color=SURFACE, corner_radius=8, border_width=1, border_color=BORDER)
        export_frame.pack(fill="x")

        ctk.CTkButton(export_frame, text="EXPORT MIX WAV", fg_color=RED, text_color="#FFF",
                       command=lambda: self._export_beat("mix")).pack(side="left", padx=8, pady=8)
        ctk.CTkButton(export_frame, text="EXPORT STEMS", fg_color=SURFACE_RAISED, text_color=TEXT_PRIMARY,
                       command=lambda: self._export_beat("stems")).pack(side="left", padx=8, pady=8)
        ctk.CTkButton(export_frame, text="EXPORT PRO 24-bit", fg_color=SURFACE_RAISED, text_color=TEXT_PRIMARY,
                       command=lambda: self._export_beat("pro")).pack(side="left", padx=8, pady=8)

    def _run_beat_command(self):
        cmd = self.beat_command_entry.get()
        if not cmd:
            return
        from app.ai.beat_studio import BeatStudio
        if not hasattr(self, '_beat_studio'):
            self._beat_studio = BeatStudio()
        result = self._beat_studio.generate(cmd)
        self.beat_result_label.configure(
            text=f"Genre: {result['genre'].replace('_', ' ').title()} | BPM: {result['bpm']} | "
                 f"Bars: {result['bars']} | Duration: {result['duration']:.1f}s | "
                 f"Instruments: {', '.join(result['stems'].keys())}"
        )
        # Push into the DAW panel so the user can edit the pattern/piano roll
        if hasattr(self, "daw_panel"):
            try:
                self.daw_panel.from_beat_result(result)
            except Exception as exc:
                self.log(f"DAW sync: {exc}")
        # Preview the beat so the user actually hears it
        played = self._beat_studio.preview(result)
        if played:
            self.set_status(f"BEAT GENERATED + PREVIEW: {result['genre']} @ {result['bpm']} BPM")
        else:
            self.set_status(f"BEAT GENERATED: {result['genre']} @ {result['bpm']} BPM")

    def _export_beat(self, mode):
        if not hasattr(self, '_beat_studio') or not self._beat_studio.last_result:
            self.set_status("Once bir beat olustur.")
            return
        import os
        os.makedirs("DJ_EXPORTS", exist_ok=True)
        result = self._beat_studio.last_result
        if mode == "stems":
            path = self._beat_studio.export_stems(result, "DJ_EXPORTS/stems")
            self.set_status(f"STEMS EXPORTED: {list(path.keys())}")
        elif mode == "pro":
            path = self._beat_studio.export_pro_wav(result, f"DJ_EXPORTS/{result['genre']}_{result['bpm']}bpm_pro.wav", bit_depth=24)
            self.set_status(f"PRO WAV EXPORTED: {path}")
        else:
            path = self._beat_studio.export_mix(result, f"DJ_EXPORTS/{result['genre']}_{result['bpm']}bpm_mix.wav")
            self.set_status(f"MIX EXPORTED: {path}")

    def _update_stats_bar(self):
        """Update the bottom stats bar with current library info."""
        if not hasattr(self, "stats_bar") or not self.stats_bar.winfo_exists():
            return

        source = self.library or self.saved_tracks
        genres = len(set(t.get("parent_genre", t.get("genre", "")) for t in source))
        dupes = self.count_value(source, "duplicate_status", "POSSIBLE_DUPLICATE")
        health = self.archive_auditor.audit(self.archive_output_folder).get("health_score", 0)

        # DNA
        if source:
            profile = self.dj_profile.build_profile(source[:200])
            dna = profile.get("dna", "---")
        else:
            dna = "---"

        self.stats_bar.update_stats(
            tracks=len(source),
            genres=genres,
            duplicates=dupes,
            health=health,
            dna=dna,
        )

    def get_visible_tracks(self):

        return self.library or self.saved_tracks

    def refresh_library_from_db(self):

        self.saved_tracks = self.db.load_all()
        relinked = self.archive_brain.apply_playable_paths(self.saved_tracks)
        self.archived_ids = {
            t.get("id")
            for t in self.saved_tracks
            if t.get("id")
        }
        self.processed_source_index = self.build_processed_source_index(
            self.saved_tracks
        )
        self.total_archived = len(self.archived_ids)
        self.doctor.build_index(self.saved_tracks)
        self.set_status(
            f"ARCHIVE REFRESHED | relinked={relinked} | {self.get_ready_status()}"
        )
        self.set_view("library")

    def run_archive_health_check(self):

        tracks = self.library or self.saved_tracks

        if not tracks:
            self.set_status("ARSIV SAGLIK: Kontrol edilecek kayit yok.")
            return

        report = self.archive_brain.health_report(tracks)
        relinked = self.archive_brain.apply_playable_paths(tracks)

        for track in tracks:
            if track.get("path_status") != "MISSING_FILE":
                self.db.save_track(track)

        missing_preview = report["missing_tracks"][:5]

        self.log(
            "ARSIV SAGLIK RAPORU: "
            f"toplam={report['total']} ok={report['ok']} "
            f"archive_copy={report['archive_copy']} "
            f"kayip={report['missing']} relinked={relinked}"
        )

        for track in missing_preview:
            self.log(
                "ARSIV KAYIP: "
                f"{track.get('name')} | eski path={track.get('path')}"
            )

        self.set_status(
            "ARSIV SAGLIK: "
            f"ok={report['ok']} kayip={report['missing']} relinked={relinked}"
        )

        if hasattr(self, "archive_cockpit") and self.archive_cockpit.winfo_exists():
            self.archive_cockpit.update_stats(
                tracks=report["total"],
                issues=self.count_problem_tracks(tracks),
                locked=True,
                mode="HEALTH LOCK",
                missing=report["missing"],
                relinked=relinked
            )

        if hasattr(self, "table") and self.table.winfo_exists():
            self.populate_table(tracks)

    def populate_table(self, tracks):

        if not hasattr(self, "table") or not self.table.winfo_exists():
            return

        self.active_table_source = list(tracks)
        self.table.set_tracks(self.filtered_tracks(self.active_table_source))

    def count_by_field(self, tracks, field):

        counts = {}

        for track in tracks:
            value = track.get(field) or "UNKNOWN"
            counts[value] = counts.get(value, 0) + 1

        return counts

    def count_value(self, tracks, field, expected):

        return sum(1 for track in tracks if track.get(field) == expected)

    def count_problem_tracks(self, tracks):

        problem_filters = (
            "NEEDS_RESEARCH",
            "DUPLICATES",
            "LOW_BITRATE",
            "ANALYSIS_FALLBACK",
            "LOW_AI_EAR",
            "VOCAL_RISK"
        )

        return sum(
            1
            for track in tracks
            if any(self.matches_issue_filter(track, issue) for issue in problem_filters)
        )

    def average_number(self, tracks, field):

        values = []

        for track in tracks:
            try:
                value = float(track.get(field, 0) or 0)
            except (TypeError, ValueError):
                continue

            if value > 0:
                values.append(value)

        if not values:
            return 0

        return round(sum(values) / len(values), 2)

    # =====================================================
    # LOAD LIBRARY
    # =====================================================
    def load_library(self):

        if self.is_scanning_library:
            self.set_status("SCAN ZATEN CALISIYOR: Durdurmak icin TARAMAYI DURDUR.")
            return

        folder = filedialog.askdirectory()
        if not folder:
            return

        if self.scanner.is_excluded_path(folder):
            self.set_status("SCAN ENGELLENDI: Programin uretilmis arsiv klasoru tekrar taranmaz.")
            return

        self.scan_cancel_event.clear()
        self.is_scanning_library = True
        self.set_status("SCANNING + AI ANALYSIS...")

        self.scan_thread = threading.Thread(
            target=self.scan_worker,
            args=(folder,),
            daemon=True
        )
        self.scan_thread.start()

    def cancel_library_scan(self):

        if not self.is_scanning_library:
            self.set_status("SCAN: Aktif tarama yok.")
            return

        self.scan_cancel_event.set()
        self.set_status("SCAN DURDURULUYOR: Mevcut parca tamamlaninca duracak.")

    # =====================================================
    # SCAN WORKER
    # =====================================================
    def scan_worker(self, folder):

        try:
            raw = self.scan_folder_cancellable(folder)

            if self.scan_cancel_event.is_set():
                self.after(
                    0,
                    lambda: self.set_status(
                        f"SCAN IPTAL EDILDI | bulunan={len(raw)} | arsive yeni kopya zorlanmadi"
                    )
                )
                return

            cleaned = self.music_ai.clean_tracks(raw)

            self.library = self.get_allowed_tracks(cleaned)

            if not self.library:
                self.after(
                    0,
                    lambda: self.set_status(
                        "ARSIV IMPORT: Yeni islenecek ses dosyasi bulunamadi."
                    )
                )
                return

            self.after(0, self.reset_table)

            total = max(len(self.library), 1)

            skipped = 0
            analyzed = 0

            for i, track in enumerate(self.library):

                if self.scan_cancel_event.is_set():
                    self.after(
                        0,
                        lambda a=analyzed, s=skipped: self.set_status(
                            "SCAN IPTAL EDILDI | "
                            f"new={a}, already_done={s}"
                        )
                    )
                    return

                try:
                    if self.scan_cancel_event.is_set():
                        break

                    existing = self.existing_processed_track(track)

                    if existing:
                        track.update(existing)
                        skipped += 1
                        self.log(
                            "Arsiv kaydi zaten var, tekrar analiz/kopya yok: "
                            f"{track.get('name')}"
                        )
                    else:
                        if self.scan_cancel_event.is_set():
                            break

                        self.enrich_track(track)
                        analyzed += 1

                except Exception as e:
                    self.log(f"AI ERROR: {e}")

                # DB SAVE (CRITICAL)
                self.db.save_track(track)
                self.remember_processed_track(track)

                track_id = track.get("id")

                if track_id and track_id not in self.archived_ids:
                    self.archived_ids.add(track_id)
                    self.total_archived += 1

                self.queue.push(track)

                self.after(
                    0,
                    lambda v=(i + 1) / total: self.update_progress(v)
                )

            self.after(
                0,
                lambda: self.set_status(
                    "AI ARCHIVE COMPLETE | "
                    f"new={analyzed}, already_done={skipped} | "
                    f"{self.get_ready_status()}"
                )
            )

            self.after(
                0,
                lambda: show_toast(
                    f"Tarama tamamlandi: {analyzed} yeni, {skipped} mevcut",
                    "success"
                )
            )

            # Update stats bar
            self.after(
                0,
                lambda: self._update_stats_bar()
            )

        except Exception as e:
            self.log(f"SCAN ERROR: {e}")
        finally:
            self.is_scanning_library = False
            self.scan_cancel_event.clear()
            self.scan_thread = None

    def scan_folder_cancellable(self, folder):

        tracks = []

        for path in self.archive_brain.collect_audio_files(folder):
            if self.scan_cancel_event.is_set():
                break

            track = self.scanner.process_file(path) or self.build_basic_track(path)

            if track:
                tracks.append(track)

            count = len(tracks)

            if count and count % 25 == 0:
                self.after(
                    0,
                    lambda c=count: self.set_status(
                        f"SCAN: {c} ses dosyasi bulundu, analiz hazirlaniyor..."
                    )
                )

        return tracks

    def enrich_track(self, track, archive=True, show_duplicate=True):

        audio = self.analyzer.analyze(track.get("path", track.get("id")))
        self.merge_audio_analysis(track, audio)
        self.apply_tempo_intelligence(track)

        ai = self.music_ai.analyze(
            track.get("id"),
            track
        )

        track.update({
            "genre": ai.get("genre", track.get("genre", "unknown")),
            "parent_genre": ai.get("parent_genre", ""),
            "subgenre": ai.get("subgenre", ""),
            "discovery_status": ai.get("discovery_status", ""),
            "matched_signals": ai.get("matched_signals", []),
            "assistant_message": ai.get("assistant_message", ""),
            "mood": ai.get("mood", track.get("mood", "unknown")),
            "role": ai.get("role", track.get("role", "")),
            "quality": ai.get("quality", track.get("quality", "")),
            "confidence": float(ai.get("confidence", 0) or 0),
            "energy": float(ai.get("energy", track.get("energy", 0)) or 0),
            "bpm": float(ai.get("bpm", track.get("bpm", 0)) or 0),
            "bpm_original": ai.get(
                "bpm_original",
                track.get("bpm_original", track.get("bpm", 0))
            ),
            "bpm_correction": ai.get(
                "bpm_correction",
                track.get("bpm_correction", "")
            ),
            "tempo_confidence": ai.get(
                "tempo_confidence",
                track.get("tempo_confidence", 0)
            ),
            "tempo_warning": ai.get(
                "tempo_warning",
                track.get("tempo_warning", "")
            ),
            "brightness": float(
                ai.get("brightness", track.get("brightness", 0)) or 0
            ),
            "key": ai.get("key", track.get("key", "")),
            "camelot": ai.get(
                "camelot",
                track.get("camelot", "")
            ),
            "version_type": detect_version(track.get("name", "")),
        })

        # Track DNA
        track["track_dna"] = dna_to_string(generate_dna(track))

        if track.get("assistant_message"):
            self.log(track["assistant_message"])

        if track.get("tempo_warning"):
            self.log(f"Tempo Intelligence: {track['tempo_warning']}")

        ear = self.ai_ear.analyze(track)
        track.update(ear)
        heart = self.dj_heart.analyze_track(track)
        track.update(heart)
        self.apply_professional_role_guard(track)

        if track.get("ai_ear_summary"):
            self.log(f"AI Ear: {track['ai_ear_summary']}")

        if track.get("heart_advice"):
            self.log(
                "DJ Heart: "
                f"{track.get('emotional_color')} / "
                f"{track.get('crowd_moment')} | "
                f"{track.get('heart_advice')}"
            )

        doctor = self.doctor.inspect(track)
        track.update(doctor)

        if track.get("doctor_message"):
            self.log(track["doctor_message"])

        research = self.research.prepare_research(track)
        track.update(research)

        if track.get("research_message"):
            self.log(track["research_message"])

        if show_duplicate and track.get("duplicate_status") == "POSSIBLE_DUPLICATE":
            self.duplicate_reviews.append(track)
            self.after(
                0,
                lambda t=track: self.show_duplicate_review(t)
            )

        if archive:
            self.archive_track_file(track)
        else:
            track["archived_path"] = ""
            self.log(
                "DROP PREVIEW: analiz tamam, arsive otomatik kopya yazilmadi."
            )

    def apply_professional_role_guard(self, track):

        confidence = float(track.get("confidence", 0) or 0)
        energy = float(track.get("energy", 0) or 0)
        bpm = float(track.get("bpm", 0) or 0)
        ear = float(track.get("ai_ear_score", 0) or 0)
        discovery = track.get("discovery_status")

        if track.get("role") != "PEAK TIME":
            return

        if discovery == "DISCOVERED" or confidence < 0.55:
            track["role"] = "GROOVE" if energy >= 0.62 else "WARMUP"
            track["quality"] = "NEEDS_DJ_REVIEW"
            return

        if energy < 0.84 or bpm < 124 or ear < 0.68:
            track["role"] = "GROOVE"

            if track.get("quality") == "PEAK_TIME_TRACK":
                track["quality"] = "STRONG_TRACK"

    def archive_track_file(self, track):

        source = track.get("path") or track.get("id")

        if not source or not os.path.exists(source):
            track["archived_path"] = ""
            return

        existing = self.existing_processed_track(track)

        if existing and existing.get("archived_path"):
            track["archived_path"] = existing.get("archived_path", "")
            fingerprint = self.organizer.file_fingerprint(track["archived_path"])
            track["content_fingerprint"] = fingerprint
            track["archive_status"] = "LINKED_EXISTING"
            self.log(
                "Arsiv baglantisi mevcut, yeni kopya yazilmadi: "
                f"{track['archived_path']}"
            )
            return

        try:
            archived_path = self.organizer.safe_copy(
                source,
                track,
                track.get("suggested_filename")
            )
            track["archived_path"] = os.path.abspath(archived_path)
            fingerprint = self.organizer.file_fingerprint(track["archived_path"])
            track["content_fingerprint"] = fingerprint
            track["archive_status"] = (
                "ARCHIVED"
                if os.path.abspath(source) != track["archived_path"]
                else "LINKED_EXISTING"
            )

            if os.path.abspath(source) == track["archived_path"]:
                self.log(f"Arsiv zaten mevcut: {track['archived_path']}")
            else:
                self.log(f"Arsiv baglandi/kopyalandi: {track['archived_path']}")
        except Exception as e:
            track["archived_path"] = ""
            track["content_fingerprint"] = ""
            track["archive_status"] = "ARCHIVE_ERROR"
            self.log(f"ARSIV KOPYA HATASI: {e}")

    def build_processed_source_index(self, tracks):

        index = {}

        for track in tracks:
            for field in ("id", "path"):
                key = self.normalized_path_key(track.get(field))

                if key:
                    index.setdefault(key, track)

        return index

    def existing_processed_track(self, track):

        if not hasattr(self, "processed_source_index"):
            self.processed_source_index = {}

        for field in ("id", "path"):
            key = self.normalized_path_key(track.get(field))

            if key and key in self.processed_source_index:
                return self.processed_source_index[key]

        return None

    def remember_processed_track(self, track):

        if not hasattr(self, "processed_source_index"):
            self.processed_source_index = {}

        for field in ("id", "path"):
            key = self.normalized_path_key(track.get(field))

            if key:
                self.processed_source_index[key] = track

    def normalized_path_key(self, value):

        if not value:
            return ""

        try:
            return os.path.normcase(os.path.abspath(value))
        except (TypeError, ValueError):
            return ""

    def show_duplicate_review(self, track):

        from app.ui.ai_duplicate_dialog import AIDuplicateDialog

        group = {
            "best": track.get("duplicate_match", {}),
            "duplicate": track,
            "recommendation": track.get("recommended_duplicate_action", "")
        }

        AIDuplicateDialog(
            self,
            group,
            self.on_duplicate_decision
        )

    def on_duplicate_decision(self, choice, group):

        duplicate = group.get("duplicate", {})
        match = group.get("best", {})

        self.log(
            "Duplicate karari kaydedildi: "
            f"{choice} | yeni: {duplicate.get('name')} | "
            f"mevcut: {match.get('name')}"
        )

    def merge_audio_analysis(self, track, audio):

        track["analysis_status"] = audio.get("analysis_status", "FALLBACK")
        track["analysis_error"] = audio.get("analysis_error", "")

        numeric_fields = [
            "bpm",
            "energy",
            "brightness",
            "roughness",
            "danceability",
            "drop_strength"
        ]

        for field in numeric_fields:
            value = audio.get(field)

            if value not in (None, "", 0):
                track[field] = value

        for field in ("key", "camelot", "mood_vector", "waveform"):
            value = audio.get(field)

            if value not in (None, "", [], "Unknown"):
                track[field] = value

        value = audio.get("phrase_points")

        if value not in (None, "", []):
            track["phrase_points"] = value

    def apply_tempo_intelligence(self, track):

        tempo = self.club_intelligence.normalize_track_tempo(track)
        track.update(tempo)

    def get_allowed_tracks(self, tracks):

        max_tracks = self.plan["max_tracks"]

        if self.plan["licensed"] and max_tracks <= 0:
            return tracks

        remaining = max_tracks - self.total_archived

        allowed = []
        new_slots = max(0, remaining)

        for track in tracks:
            track_id = track.get("id")

            if track_id in self.archived_ids:
                allowed.append(track)
                continue

            if new_slots <= 0:
                continue

            allowed.append(track)
            new_slots -= 1

        return allowed

    # =====================================================
    # SET ENGINE
    # =====================================================
    def generate_set(self):

        source = self.library or self.saved_tracks

        if not source:
            show_toast("Once kutuphane yukle!", "warning")
            return

        self.current_set = self.set_engine.build_set(source)

        if hasattr(self, "table") and self.table.winfo_exists():
            self.active_table_source = list(self.current_set)
            self.table.set_tracks(self.filtered_tracks(self.active_table_source))

        self.set_status("SET READY")
        show_toast(f"Set hazir: {len(self.current_set)} parca", "success")

    # =====================================================
    # PLAYBACK
    # =====================================================
    def play_set(self):

        # Use visible tracks (library or saved_tracks from DB)
        if not self.current_set:
            self.current_set = self.get_visible_tracks()

        if not self.current_set:
            show_toast("Oynatilacak parca yok", "warning")
            return

        for track in self.current_set:
            self.resolve_track_audio_path(track)

        self.is_playing = True

        self.set_status("PLAYING")
        self.mini_player.set_playing(True)
        if self.current_set:
            self.mini_player.update_track(self.current_set[0])

        self.playback.play(self.current_set)
        show_toast("Cal basladi", "success")

    def stop_playback(self):

        self.playback.stop()
        self.is_playing = False
        self.set_status("STOPPED")
        self.mini_player.set_playing(False)

    def next_track(self):
        self.playback.next_track()

    # =====================================================
    # CALLBACK
    # =====================================================
    def on_now_playing(self, track):

        self.after(0, lambda: self.set_status(
            f"NOW PLAYING: {track.get('name','UNKNOWN')}"
        ))
        self.after(0, lambda t=track: self.update_booth_panel(t))

    # =====================================================
    # QUEUE UI
    # =====================================================
    def ui_consumer(self):

        t0 = time.perf_counter()

        track = self.queue.get()

        if track:
            self.after(0, lambda t=track: self.add_track_to_ui(t))

        # throttled live refresh for the DJ booth (every ~500ms)
        self._ui_consumer_tick = getattr(self, "_ui_consumer_tick", 0) + 1
        if self._ui_consumer_tick % 10 == 0:
            if (
                self.current_view == "dj_booth"
                and hasattr(self, "dj_booth")
                and getattr(self.dj_booth, "refresh", None)
            ):
                try:
                    self.dj_booth.refresh()
                except Exception:
                    pass

        self._frame_ms = (time.perf_counter() - t0) * 1000.0
        self.after(50, self.ui_consumer)

    def add_track_to_ui(self, track):

        if not hasattr(self, "table") or not self.table.winfo_exists():
            return

        if track not in self.active_table_source:
            self.active_table_source.append(track)

        if track in self.filtered_tracks([track]):
            self.table.add_track(track)

        if hasattr(self, "ai_dashboard") and self.ai_dashboard.winfo_exists():
            self.ai_dashboard.update_track(track)

        self.draw_track_waveform(track)

        if not track.get("waveform"):
            self.request_waveform_analysis(track)

        self.update_booth_panel(track)

    def on_track_selected(self, track):

        self.selected_track = track
        self.resolve_track_audio_path(track)

        if hasattr(self, "ai_dashboard") and self.ai_dashboard.winfo_exists():
            self.ai_dashboard.update_track(track)

        self.draw_track_waveform(track)

        if not track.get("waveform"):
            self.request_waveform_analysis(track)

        self.update_booth_panel(track)

        if hasattr(self, "transition_box") and self.transition_box.winfo_exists():
            advice = track.get("transition_advice") or "Bu parca icin mix onerisi yok."
            ear = track.get("ai_ear_summary", "")
            heart = track.get("heart_advice", "")
            text = advice if not ear else f"{advice} | AI Ear: {ear}"

            if heart:
                text = f"{text} | DJ Heart: {heart}"

            self.transition_box.configure(text=text)

    def on_track_double_click(self, track):
        """Double-click on a track: play from this track in the current context (Rekordbox style)."""
        self.selected_track = track
        self.resolve_track_audio_path(track)

        # Determine the playable list: current_set > filtered visible tracks > library
        playable_list = []
        if self.current_set:
            playable_list = self.current_set
        elif hasattr(self, "table") and self.table.winfo_exists():
            # Use currently filtered/visible tracks
            playable_list = self.filtered_tracks(self.active_table_source) if self.active_table_source else []
        if not playable_list:
            playable_list = self.library or self.saved_tracks or []

        # Find index of clicked track in playable list
        start_index = 0
        for i, t in enumerate(playable_list):
            if t.get("id") == track.get("id") or t.get("path") == track.get("path"):
                start_index = i
                break

        # Play from this track onward
        self.current_set = playable_list[start_index:]
        self.is_playing = True
        self.mini_player.set_playing(True)
        self.mini_player.update_track(track)
        self.playback.play(self.current_set)
        self.set_status(f"CALIYOR: {track.get('name', '?')}")
        show_toast(f"CALIYOR: {track.get('name', '?')[:40]}", "info")

    def on_track_right_click(self, action, track):
        """Handle right-click context menu actions."""
        self.selected_track = track

        if action == "play":
            self.on_track_double_click(track)

        elif action == "load_a":
            self.deck_engine.load("A", track)
            self.set_status(f"DECK A: {track.get('name', '?')[:40]}")
            show_toast(f"Deck A'ya yuklendi: {track.get('name', '?')[:30]}", "info")
            if hasattr(self, "deck_status_label") and self.deck_status_label:
                self.update_deck_status()

        elif action == "load_b":
            self.deck_engine.load("B", track)
            self.set_status(f"DECK B: {track.get('name', '?')[:40]}")
            show_toast(f"Deck B'ye yuklendi: {track.get('name', '?')[:30]}", "info")
            if hasattr(self, "deck_status_label") and self.deck_status_label:
                self.update_deck_status()

        elif action == "add_set":
            self.current_set.append(track)
            self.set_status(f"SET'E EKLENDI: {track.get('name', '?')[:40]} ({len(self.current_set)} parca)")
            show_toast(f"Sete eklendi: {len(self.current_set)} parca", "success")

        elif action == "info":
            # Show track info in status
            info = (
                f"{track.get('name', '?')} | "
                f"BPM: {track.get('bpm', '?')} | "
                f"KEY: {track.get('camelot', track.get('key', '?'))} | "
                f"ENERGY: {track.get('energy', 0):.2f} | "
                f"GENRE: {track.get('genre', '?')} | "
                f"VERSION: {track.get('version_type', '?')}"
            )
            self.set_status(info)

    def request_waveform_analysis(self, track):

        path = self.resolve_track_audio_path(track)
        key = self.normalized_path_key(path)

        if not key or key in self.waveform_analysis_pending:
            return

        if not self.is_supported_audio_path(path):
            return

        self.waveform_analysis_pending.add(key)
        self.set_status(f"WAVEFORM: {track.get('name', 'parca')} analiz ediliyor...")

        threading.Thread(
            target=self.waveform_analysis_worker,
            args=(track, key),
            daemon=True
        ).start()

    def waveform_analysis_worker(self, track, key):

        try:
            ok = self.ensure_waveform_analysis(track, force=True, log_errors=True)

            if ok:
                self.after(0, lambda t=track: self.refresh_waveform_after_analysis(t))
            else:
                self.after(
                    0,
                    lambda t=track: self.set_status(
                        "WAVEFORM: Grafik uretilemedi. "
                        f"{t.get('waveform_error', 'Analiz paketi gerekli.')}"
                    )
                )
        finally:
            self.waveform_analysis_pending.discard(key)

    def refresh_waveform_after_analysis(self, track):

        if self.selected_track is track:
            self.draw_track_waveform(track)

        if hasattr(self, "ai_dashboard") and self.ai_dashboard.winfo_exists():
            self.ai_dashboard.update_track(track)

        self.update_booth_panel(track)
        self.log_hot_cues(track)
        self.set_status(
            "WAVEFORM HAZIR: "
            f"{track.get('name', 'parca')} | {track.get('waveform_engine', 'engine')}"
        )

    def log_hot_cues(self, track):

        cues = track.get("hot_cues") or []

        if not cues:
            return

        text = " | ".join(
            f"{cue.get('label')} {cue.get('seconds')}s"
            for cue in cues
        )
        self.log(f"AI HOT CUES: {track.get('name', 'parca')} | {text}")

    def update_booth_panel(self, track):

        if hasattr(self, "neon_booth") and self.neon_booth.winfo_exists():
            self.neon_booth.update_track(track)

    def draw_track_waveform(self, track):

        for widget_name in ("primary_waveform", "waveform"):
            widget = getattr(self, widget_name, None)

            if widget and widget.winfo_exists():
                widget.draw_waveform(
                    track.get("waveform", []),
                    track.get("phrase_points", []),
                    track.get("bpm", 0),
                    track.get("duration", 0)
                )

    # =====================================================
    # RESET TABLE
    # =====================================================
    def reset_table(self):

        if hasattr(self, "table") and self.table.winfo_exists():
            self.table.clear()

    def update_progress(self, value):

        if hasattr(self, "progress") and self.progress.winfo_exists():
            self.progress.set(value)
