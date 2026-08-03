import os
import sys
import tempfile
import math
import struct
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.ai.music_ai import MusicAI
from app.ai.audio_analyzer import AudioAnalyzer
from app.ai.ai_ear import AIEar
from app.ai.club_intelligence import ClubIntelligence
from app.ai.deck_engine import DeckEngine
from app.ai.dj_heart import DJHeart
from app.ai.feedback_learner import FeedbackLearner
from app.ai.genre_review import GenreReviewStudio
from app.ai.genre_knowledge_base import GenreKnowledgeBase
from app.ai.mix_master_doctor import MixMasterDoctor
from app.ai.mix_master_engine import MixMasterEngine
from app.ai.music_research_assistant import MusicResearchAssistant
from app.ai.performance_planner import PerformancePlanner
from app.ai.remix_lab import RemixLab
from app.ai.set_engine import SetEngine
from app.ai.show_director import ShowDirector
from app.ai.voice_assistant import VoiceAssistant
from app.ai.voice_command_router import VoiceCommandRouter
from app.ai.voice_runtime import VoiceRuntime
from app.cloud.trend_recommender import TrendRecommender
from app.cloud.dj_archive_cloud import DJArchiveCloud
from app.cloud.commercial_api import CommercialAPIClient
from app.core.archive_auditor import ArchiveAuditor
from app.core.archive_brain import ArchiveBrain
from app.core.archive_reconciler import ArchiveReconciler
from app.core.export_center import ExportCenter
from app.core.organizer import Organizer
from app.core.library_doctor import LibraryDoctor
from app.core.rekordbox_bridge import RekordboxBridge
from app.core.gig_pack_builder import GigPackBuilder
from app.core.fl_studio_bridge import FLStudioBridge
from app.license.entitlements import EntitlementManager
from app.license.license_manager import LicenseManager
from app.server.billing_service import BillingService
from app.server.cloud_service import CloudService
from app.server.license_service import LicenseService
from data.db.ai_library_db import AILibraryDB


def test_music_ai_classifies_track():
    ai = MusicAI()
    base = {
        "id": "C:/Music/deep_house_124.mp3",
        "path": "C:/Music/deep_house_124.mp3",
        "name": "deep_house_124.mp3",
        "bpm": 124,
        "genre": "UNKNOWN",
        "energy": 0.78,
        "duration": 360,
        "camelot": "8A",
    }

    result = ai.analyze(base["path"], base)

    assert result["genre"] == "DEEP HOUSE"
    assert result["parent_genre"] == "HOUSE"
    assert result["role"] == "GROOVE"
    assert result["quality"] == "STRONG_TRACK"
    assert result["assistant_message"]


def test_music_ai_classifies_wedding_archive_tracks():
    ai = MusicAI()
    base = {
        "id": "C:/Wedding/Kina Gecesi Oyun Havasi.mp3",
        "path": "C:/Wedding/Kina Gecesi Oyun Havasi.mp3",
        "name": "Kina Gecesi Oyun Havasi.mp3",
        "bpm": 112,
        "genre": "",
        "energy": 0.68,
        "duration": 240,
    }

    result = ai.analyze(base["path"], base)

    assert result["parent_genre"] == "WEDDING & EVENT"
    assert result["genre"] == "KINA GECESI"
    assert result["role"] == "KINA_RITUAL"
    assert result["quality"] == "EVENT_DANCEFLOOR_TRACK"


def test_unknown_styles_do_not_become_peak_time_archive_folders():
    ai = MusicAI()
    result = ai.analyze(
        "C:/Music/strange_future_ritual_126.mp3",
        {
            "id": "C:/Music/strange_future_ritual_126.mp3",
            "path": "C:/Music/strange_future_ritual_126.mp3",
            "name": "strange_future_ritual_126.mp3",
            "bpm": 126,
            "energy": 0.86,
            "duration": 300,
            "genre": "",
        }
    )
    folder = Organizer("OUT").build_path(result)

    assert result["discovery_status"] == "DISCOVERED"
    assert result["role"] != "PEAK TIME"
    assert "DISCOVERED_STYLE" not in folder
    assert "NEEDS_REVIEW" in folder


def test_set_engine_builds_ordered_set():
    tracks = [
        {
            "id": "1",
            "bpm": 122,
            "energy": 0.55,
            "key": "8A",
            "mood_vector": [0.1, 0.2],
            "drop_strength": 0.1,
        },
        {
            "id": "2",
            "bpm": 124,
            "research_status": "NEEDS_REVIEW",
            "research_query": "DJ Track 1 house",
            "research_links": {"beatport": "https://example.com"},
            "research_message": "Online arastirma oneriyorum.",
            "artwork_status": "MISSING",
            "album_art_url": "",
            "album_art_path": "",
            "hit_status": "CLUB_READY_CANDIDATE",
            "release_year": "",
            "label": "",
            "external_metadata": {"source": "test"},
            "energy": 0.7,
            "key": "8A",
            "mood_vector": [0.1, 0.22],
            "drop_strength": 0.12,
        },
        {
            "id": "3",
            "bpm": 128,
            "energy": 0.9,
            "key": "9A",
            "mood_vector": [0.2, 0.3],
            "drop_strength": 0.2,
        },
    ]

    result = SetEngine(None).build_set(tracks)

    assert [track["id"] for track in result] == ["1", "2", "3"]
    assert result[0]["mix_strategy"] == "OPENING"
    assert result[1]["transition_score"] > 0
    assert result[1]["transition_advice"]


def test_library_db_persists_archive_fields():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    try:
        db = AILibraryDB(path)
        db.save_track({
            "id": "t1",
            "name": "Track 1",
            "path": "C:/music/t1.mp3",
            "artist": "DJ",
            "duration": 300,
            "bpm": 124,
            "key": "8A",
            "camelot": "8A",
            "genre": "house",
            "parent_genre": "HOUSE",
            "subgenre": "TECH HOUSE",
            "mood": "driving",
            "role": "GROOVE",
            "quality": "STRONG_TRACK",
            "confidence": 0.8,
            "discovery_status": "KNOWN",
            "matched_signals": ["house", "bpm"],
            "research_status": "NEEDS_REVIEW",
            "research_query": "DJ Track 1 house",
            "research_links": {"beatport": "https://example.com"},
            "research_message": "Online arastirma oneriyorum.",
            "artwork_status": "MISSING",
            "album_art_url": "",
            "album_art_path": "",
            "hit_status": "CLUB_READY_CANDIDATE",
            "release_year": "",
            "label": "",
            "external_metadata": {"source": "test"},
            "archived_path": "C:/DJ_LIBRARY_OUTPUT/HOUSE/Track 1.mp3",
            "assistant_message": "TECH HOUSE olarak sınıflandırdım.",
            "energy": 0.7,
            "brightness": 0.5,
            "roughness": 0.1,
            "danceability": 0.9,
            "drop_strength": 0.2,
            "waveform": [0, 0.25, -0.25, 1],
            "analysis_status": "FULL",
            "analysis_error": "",
            "bitrate": 320,
            "file_size": 123456,
            "ai_ear_score": 0.82,
            "rhythmic_density": 0.7,
            "vocal_risk": 0.2,
            "intro_outro_mixability": 0.8,
            "arrangement_score": 0.75,
            "crowd_energy_role": "DRIVE_BUILDER",
            "ai_ear_summary": "PRO_READY",
            "bpm_original": 63,
            "bpm_correction": "DOUBLE_TIME_CORRECTED",
            "tempo_confidence": 0.91,
            "tempo_warning": "BPM 63 -> 126 duzeltildi.",
            "heart_score": 0.74,
            "emotional_color": "TRIBAL_LIFT",
            "crowd_moment": "LOCK_IN",
            "heart_advice": "Groove kilitlenince yukselis ver.",
        })

        rows = db.load_all()
        db.close()

        assert len(rows) == 1
        assert rows[0]["role"] == "GROOVE"
        assert rows[0]["quality"] == "STRONG_TRACK"
        assert rows[0]["camelot"] == "8A"
        assert rows[0]["parent_genre"] == "HOUSE"
        assert rows[0]["matched_signals"] == ["house", "bpm"]
        assert rows[0]["research_status"] == "NEEDS_REVIEW"
        assert rows[0]["research_links"] == {"beatport": "https://example.com"}
        assert rows[0]["external_metadata"] == {"source": "test"}
        assert rows[0]["archived_path"].endswith("Track 1.mp3")
        assert rows[0]["file_size"] == 123456
        assert rows[0]["ai_ear_score"] == 0.82
        assert rows[0]["crowd_energy_role"] == "DRIVE_BUILDER"
        assert rows[0]["bpm_original"] == 63
        assert rows[0]["bpm_correction"] == "DOUBLE_TIME_CORRECTED"
        assert rows[0]["tempo_confidence"] == 0.91
        assert rows[0]["heart_score"] == 0.74
        assert rows[0]["emotional_color"] == "TRIBAL_LIFT"
        assert rows[0]["crowd_moment"] == "LOCK_IN"
        assert rows[0]["waveform"] == [0, 0.25, -0.25, 1]
        assert rows[0]["analysis_status"] == "FULL"
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_demo_license_limit():
    manager = LicenseManager()

    assert manager.check_limit(0) is True
    assert manager.get_plan()["plan"] == "OWNER_DEV"
    assert manager.get_plan()["max_tracks"] == 0
    assert manager.check_limit(manager.trial_limit) is True


def test_audio_analyzer_fallback_is_safe():
    result = AudioAnalyzer().analyze("missing-file.mp3")

    assert result["analysis_status"] == "FALLBACK"
    assert result["waveform"] == []


def test_audio_scanner_skips_generated_archive_folders():
    from app.core.audio_scanner import AudioScanner

    folder = tempfile.mkdtemp()
    generated = os.path.join(folder, "DJ_LIBRARY_OUTPUT", "AFRO HOUSE")
    os.makedirs(generated, exist_ok=True)

    path = os.path.join(generated, "Generated Archive Copy.mp3")

    with open(path, "wb") as handle:
        handle.write(b"not a real mp3")

    try:
        tracks = AudioScanner().scan_folder(folder)

        assert tracks == []
    finally:
        for root, dirs, files in os.walk(folder, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(folder)


def test_audio_scanner_rejects_archive_root_selection():
    from app.core.audio_scanner import AudioScanner

    folder = tempfile.mkdtemp()
    archive_root = os.path.join(folder, "DJ_LIBRARY_OUTPUT")
    genre = os.path.join(archive_root, "RNB", "GROOVE")
    os.makedirs(genre, exist_ok=True)

    path = os.path.join(genre, "Already Archived.mp3")

    with open(path, "wb") as handle:
        handle.write(b"not a real mp3")

    try:
        tracks = AudioScanner().scan_folder(archive_root)

        assert tracks == []
    finally:
        for root, dirs, files in os.walk(folder, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(folder)


def test_ai_ear_scores_professional_mixability():
    result = AIEar().analyze({
        "name": "Deep Tool Instrumental Mix.mp3",
        "genre": "DEEP HOUSE",
        "bpm": 124,
        "energy": 0.72,
        "brightness": 0.5,
        "roughness": 0.04,
        "danceability": 0.85,
        "drop_strength": 0.35,
        "duration": 360,
        "waveform": [0.1, 0.15, 0.2, 0.18] * 40,
    })

    assert result["ai_ear_score"] >= 0.6
    assert result["vocal_risk"] < 0.3
    assert result["intro_outro_mixability"] >= 0.6
    assert result["ai_ear_summary"]


def test_club_intelligence_corrects_half_and_double_tempo():
    engine = ClubIntelligence()

    half = engine.normalize_track_tempo({
        "name": "Afro House Tool (63 BPM).mp3",
        "genre": "AFRO HOUSE",
        "bpm": 63,
    })
    double = engine.normalize_track_tempo({
        "name": "Peak House Weapon (129 BPM).mp3",
        "genre": "AFRO HOUSE",
        "bpm": 198,
    })

    assert half["bpm"] == 126
    assert half["bpm_correction"] == "DOUBLE_TIME_CORRECTED"
    assert double["bpm"] == 129
    assert double["bpm_correction"] == "HALF_TIME_CORRECTED"


def test_dj_heart_builds_emotional_pulse_map():
    heart = DJHeart()
    tracks = [
        {
            "id": "warm",
            "name": "Organic Warm Tool.mp3",
            "genre": "ORGANIC HOUSE",
            "role": "WARMUP",
            "energy": 0.48,
            "brightness": 0.42,
            "vocal_risk": 0.15,
            "intro_outro_mixability": 0.82,
            "ai_ear_score": 0.78,
        },
        {
            "id": "peak",
            "name": "Afro Peak Chant.mp3",
            "genre": "AFRO HOUSE",
            "role": "PEAK TIME",
            "energy": 0.88,
            "brightness": 0.62,
            "vocal_risk": 0.35,
            "intro_outro_mixability": 0.7,
            "ai_ear_score": 0.84,
        },
    ]

    result = heart.analyze_track(tracks[0])
    heart_map = heart.build_heart_map(tracks)

    assert result["heart_score"] > 0.5
    assert result["emotional_color"] == "EARTHY_WARMTH"
    assert heart_map["pulse"] > 0
    assert heart_map["moments"]
    assert heart_map["advice"]


def test_voice_command_router_understands_dj_commands():
    router = VoiceCommandRouter()

    assert router.interpret("set olustur")["intent"] == "GENERATE_SET"
    assert router.interpret("kalp ekranini ac")["intent"] == "OPEN_HEART"
    assert router.interpret("arsivi kontrol et")["intent"] == "AUDIT_ARCHIVE"
    assert router.interpret("sonraki parcaya gec")["intent"] == "NEXT"
    assert router.interpret("bu parca nasil")["intent"] == "COACH_SELECTED_TRACK"
    assert router.interpret("set nasil")["intent"] == "COACH_CURRENT_SET"
    assert router.interpret("nasil mixleyeyim")["intent"] == "AUTO_MIX_COACH"
    assert router.interpret("anlamadigim bir sey")["intent"] == "UNKNOWN"


def test_voice_runtime_reports_capabilities_without_microphone():
    runtime = VoiceRuntime()
    status = runtime.status()
    assistant = VoiceAssistant()
    result = assistant.interpret_command("deckleri ac")

    assert "tts_available" in status
    assert "stt_available" in status
    assert result["intent"] == "OPEN_DECKS"
    assert assistant.capability_summary()["mode"] == "VOICE_RUNTIME_READY"


def test_remix_lab_builds_blueprint_and_demucs_command():
    lab = RemixLab()
    track = {
        "id": "missing.mp3",
        "path": "missing.mp3",
        "name": "Vocal Song.mp3",
        "bpm": 96,
        "camelot": "8A",
    }

    blueprint = lab.build_remix_blueprint(track, "AFRO HOUSE")
    result = lab.separate_vocals(track)

    assert blueprint["target_style"] == "AFRO HOUSE"
    assert blueprint["target_bpm"] == 122
    assert blueprint["arrangement"]
    assert result["ok"] is False
    assert result["reason"] == "SOURCE_FILE_NOT_FOUND"


def test_remix_lab_readiness_brief_and_export():
    folder = tempfile.mkdtemp()
    source = os.path.join(folder, "Vocal Song.mp3")

    with open(source, "wb") as handle:
        handle.write(b"test")

    lab = RemixLab()
    track = {
        "id": source,
        "path": source,
        "name": "Vocal Song.mp3",
        "bpm": 96,
        "camelot": "8A",
    }

    try:
        blueprint = lab.build_remix_blueprint(track, "TECH HOUSE")
        readiness = lab.readiness_profile(track, "TECH HOUSE")
        brief = lab.creative_brief(track, "TECH HOUSE")
        exported = lab.export_blueprint(blueprint, readiness, output_folder=folder)

        assert readiness["score"] >= 30
        assert readiness["checks"]
        assert readiness["next_action"]
        assert brief["title"]
        assert brief["production_focus"]
        assert os.path.exists(exported["json_path"])
        assert os.path.exists(exported["txt_path"])
    finally:
        for name in os.listdir(folder):
            os.remove(os.path.join(folder, name))
        os.rmdir(folder)


def test_performance_planner_picks_afro_opening_track():
    tracks = [
        {
            "id": "peak",
            "name": "Peak Vocal Anthem.mp3",
            "genre": "AFRO HOUSE",
            "parent_genre": "HOUSE",
            "role": "PEAK TIME",
            "bpm": 126,
            "energy": 0.9,
            "vocal_risk": 0.75,
            "intro_outro_mixability": 0.4,
            "ai_ear_score": 0.6,
        },
        {
            "id": "open",
            "name": "Organic Afro Tool Intro.mp3",
            "genre": "ORGANIC HOUSE",
            "parent_genre": "HOUSE",
            "role": "WARMUP",
            "bpm": 121,
            "energy": 0.5,
            "vocal_risk": 0.1,
            "intro_outro_mixability": 0.82,
            "ai_ear_score": 0.78,
        },
    ]

    result = PerformancePlanner().recommend_openers(
        tracks,
        "AFRO HOUSE",
        limit=1
    )

    assert result[0]["id"] == "open"
    assert "vokal riski dusuk" in result[0]["opening_reason"]


def test_deck_engine_builds_auto_mix_plan():
    plan = DeckEngine().auto_mix_plan(
        {
            "name": "Track A",
            "bpm": 122,
            "energy": 0.5,
        },
        {
            "name": "Track B",
            "bpm": 124,
            "energy": 0.65,
            "phrase_points": [
                {"label": "START", "position": 0.02},
                {"label": "BUILD", "position": 0.24},
            ],
        }
    )

    assert plan["mode"] in {"LONG_BLEND", "ENERGY_LIFT"}
    assert plan["bars"] >= 16
    assert plan["crossfade_curve"]


def test_show_director_builds_segmented_show_and_rescue_crate():
    tracks = [
        {
            "id": f"t{i}",
            "name": f"Afro Track {i}.mp3",
            "genre": "AFRO HOUSE" if i % 2 == 0 else "ORGANIC HOUSE",
            "parent_genre": "HOUSE",
            "bpm": 120 + (i % 6),
            "energy": 0.3 + (i % 7) * 0.09,
            "ai_ear_score": 0.65 + (i % 3) * 0.08,
            "intro_outro_mixability": 0.62 + (i % 4) * 0.06,
            "vocal_risk": 0.15 + (i % 3) * 0.1,
            "crowd_energy_role": "DRIVE_BUILDER",
            "phrase_points": [
                {"label": "START", "position": 0.02},
                {"label": "BUILD", "position": 0.22},
            ],
        }
        for i in range(24)
    ]

    show = ShowDirector().build_show(tracks, "AFRO HOUSE", 4)

    assert show["segments"]
    assert show["segments"][0]["instruction"]
    assert show["rescue_tracks"]
    assert show["director_note"]


def test_library_doctor_suggests_names_and_duplicates():
    doctor = LibraryDoctor()
    existing = {
        "id": "old",
        "name": "Artist - Track Name Extended Mix.mp3",
        "artist": "Artist",
        "path": "C:/Music/Artist - Track Name Extended Mix.mp3",
        "bitrate": 192,
        "file_size": 1000,
        "bpm": 124,
        "camelot": "8A",
        "genre": "DEEP HOUSE",
        "role": "GROOVE",
    }

    doctor.build_index([existing])

    new_track = {
        "id": "new",
        "name": "Artist Track Name 320kbps.mp3",
        "artist": "Artist",
        "path": "C:/Music/Artist Track Name 320kbps.mp3",
        "bitrate": 320,
        "file_size": 2000,
        "bpm": 124,
        "camelot": "8A",
        "genre": "DEEP HOUSE",
        "role": "GROOVE",
    }

    result = doctor.inspect(new_track)

    assert result["suggested_filename"].endswith(".mp3")
    assert result["duplicate_status"] == "POSSIBLE_DUPLICATE"
    assert result["recommended_duplicate_action"] == "KEEP_NEW_HIGHER_QUALITY"


def test_archive_auditor_reports_legacy_and_zero_byte_files():
    folder = tempfile.mkdtemp()
    legacy = os.path.join(folder, "DISCOVERED_STYLE_1", "PEAK TIME")
    os.makedirs(legacy, exist_ok=True)
    zero_path = os.path.join(legacy, "Track (63Bpm).mp3")

    with open(zero_path, "wb"):
        pass

    try:
        auditor = ArchiveAuditor()
        report = auditor.audit(folder)
        report_path = auditor.write_report(report, output_folder=folder)

        assert report["total_audio_files"] == 1
        assert report["zero_byte_files"]
        assert report["legacy_discovered_folders"]
        assert report["tempo_anomalies"]
        assert report["health_score"] < 100
        assert os.path.exists(report_path)
    finally:
        report_path = os.path.join(folder, "archive_audit_latest.json")
        if os.path.exists(report_path):
            os.remove(report_path)
        if os.path.exists(zero_path):
            os.remove(zero_path)
        if os.path.exists(legacy):
            os.rmdir(legacy)
        parent = os.path.join(folder, "DISCOVERED_STYLE_1")
        if os.path.exists(parent):
            os.rmdir(parent)
        if os.path.exists(folder):
            os.rmdir(folder)


def test_remix_lab_renders_ai_remix_wav():
    folder = tempfile.mkdtemp()
    lab = RemixLab()
    track = {
        "id": "synthetic-source",
        "path": "",
        "name": "Original Song.wav",
        "bpm": 118,
        "camelot": "9A",
    }

    try:
        result = lab.render_remix_wav(
            track,
            "AFRO HOUSE",
            output_folder=folder,
            duration_seconds=4
        )

        assert result["ok"] is True
        assert os.path.exists(result["wav_path"])
        assert os.path.exists(result["manifest_path"])

        with wave.open(result["wav_path"], "rb") as handle:
            assert handle.getnchannels() == 2
            assert handle.getframerate() == 44100
            assert handle.getnframes() > 0
    finally:
        for root, dirs, files in os.walk(folder, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))

        if os.path.exists(folder):
            os.rmdir(folder)


def test_organizer_does_not_duplicate_same_audio_content():
    folder = tempfile.mkdtemp()
    source_folder = tempfile.mkdtemp()
    source = os.path.join(source_folder, "Track.mp3")

    with open(source, "wb") as handle:
        handle.write(b"same audio content")

    organizer = Organizer(folder)
    track = {
        "genre": "AFRO HOUSE",
        "parent_genre": "HOUSE",
        "role": "GROOVE",
    }

    try:
        first = organizer.safe_copy(source, track, "Artist - Track.mp3")
        second = organizer.safe_copy(source, track, "Artist - Track.mp3")
        audio_files = []

        for current, _dirs, files in os.walk(folder):
            for filename in files:
                if filename.endswith(".mp3"):
                    audio_files.append(os.path.join(current, filename))

        assert first == second
        assert len(audio_files) == 1
    finally:
        for root, dirs, files in os.walk(folder, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        for root, dirs, files in os.walk(source_folder, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(folder)
        os.rmdir(source_folder)


def test_organizer_blocks_filename_collision_without_suffix_copy():
    folder = tempfile.mkdtemp()
    source_folder = tempfile.mkdtemp()
    first = os.path.join(source_folder, "First.mp3")
    second = os.path.join(source_folder, "Second.mp3")

    with open(first, "wb") as handle:
        handle.write(b"first audio")

    with open(second, "wb") as handle:
        handle.write(b"second audio")

    organizer = Organizer(folder)
    track = {
        "genre": "AFRO HOUSE",
        "parent_genre": "HOUSE",
        "role": "GROOVE",
    }

    try:
        organizer.safe_copy(first, track, "Artist - Same Name.mp3")

        try:
            organizer.safe_copy(second, track, "Artist - Same Name.mp3")
            raised = False
        except FileExistsError:
            raised = True

        audio_files = []

        for current, _dirs, files in os.walk(folder):
            for filename in files:
                if filename.endswith(".mp3"):
                    audio_files.append(os.path.join(current, filename))

        assert raised is True
        assert len(audio_files) == 1
        assert not any(path.endswith("_1.mp3") for path in audio_files)
    finally:
        for root, dirs, files in os.walk(folder, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        for root, dirs, files in os.walk(source_folder, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(folder)
        os.rmdir(source_folder)


def test_archive_auditor_reports_renamed_duplicate_groups():
    folder = tempfile.mkdtemp()

    try:
        for name in ("Song.mp3", "Song_1.mp3", "Song_2.mp3"):
            with open(os.path.join(folder, name), "wb") as handle:
                handle.write(b"audio")

        report = ArchiveAuditor().audit(folder)

        assert report["duplicate_name_groups"]
        assert report["duplicate_name_groups"][0]["count"] == 3
        assert report["health_score"] < 100
    finally:
        for name in os.listdir(folder):
            os.remove(os.path.join(folder, name))
        os.rmdir(folder)


def test_archive_reconciler_builds_exact_duplicate_cleanup_plan():
    folder = tempfile.mkdtemp()
    target = os.path.join(folder, "AFRO HOUSE", "GROOVE")
    os.makedirs(target, exist_ok=True)

    keep = os.path.join(target, "Song.mp3")
    duplicate = os.path.join(target, "Song_1.mp3")
    unique = os.path.join(target, "Other.mp3")

    with open(keep, "wb") as handle:
        handle.write(b"same audio")

    with open(duplicate, "wb") as handle:
        handle.write(b"same audio")

    with open(unique, "wb") as handle:
        handle.write(b"different audio")

    try:
        reconciler = ArchiveReconciler(folder)
        plan = reconciler.build_cleanup_plan()
        path = reconciler.write_plan(plan, output_folder=folder)
        quarantine = reconciler.quarantine_manifest(plan)
        quarantine_path = reconciler.write_quarantine_manifest(
            plan,
            output_folder=folder,
            quarantine_folder=os.path.join(folder, "QUARANTINE")
        )

        assert plan["duplicate_file_count"] == 1
        assert plan["duplicate_groups"][0]["keep"].endswith("Song.mp3")
        assert plan["duplicate_groups"][0]["duplicates"][0].endswith("Song_1.mp3")
        assert plan["reclaimable_bytes"] > 0
        assert quarantine["operation_count"] == 1
        assert os.path.exists(path)
        assert os.path.exists(quarantine_path)
    finally:
        for root, dirs, files in os.walk(folder, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(folder)


def test_music_research_assistant_prepares_safe_links():
    assistant = MusicResearchAssistant()
    result = assistant.prepare_research({
        "name": "Unknown Track 124.mp3",
        "artist": "UNKNOWN",
        "genre": "DISCOVERED_STYLE_1",
        "confidence": 0.2,
        "role": "PEAK TIME",
        "energy": 0.8,
    })

    assert result["research_status"] == "NEEDS_REVIEW"
    assert "beatport" in result["research_links"]
    assert "soundcloud" in result["research_links"]
    assert result["artwork_status"] == "MISSING"
    assert result["research_message"]


def test_music_research_assistant_marks_event_tracks():
    assistant = MusicResearchAssistant()
    result = assistant.prepare_research({
        "name": "Kina Gecesi Oyun Havasi.mp3",
        "artist": "UNKNOWN",
        "genre": "KINA GECESI",
        "parent_genre": "WEDDING & EVENT",
        "confidence": 0.9,
        "role": "KINA_RITUAL",
        "energy": 0.7,
    })

    assert result["hit_status"] == "EVENT_FLOOR_ESSENTIAL"
    assert "dugun/kina/event" in result["research_message"]


def test_genre_knowledge_discovers_unknown_styles():
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)

    try:
        os.remove(path)
        kb = GenreKnowledgeBase(discovery_file=path)
        result = kb.classify({
            "name": "strange_future_ritual_117.wav",
            "genre": "",
            "bpm": 117,
            "energy": 0.42,
        })

        assert result["discovery_status"] == "DISCOVERED"
        assert result["genre"].startswith("DISCOVERED_STYLE_")
        assert os.path.exists(path)
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_trend_recommender_ranks_and_fits_library():
    recommender = TrendRecommender()
    library = [
        {
            "genre": "TECH HOUSE",
            "role": "PEAK TIME",
        }
    ]

    trends = recommender.get_global_trends()
    fitted = recommender.recommend_for_library(library)

    assert trends
    assert trends[0]["trend_score"] >= trends[-1]["trend_score"]
    assert fitted[0]["library_fit_score"] >= fitted[-1]["library_fit_score"]
    assert fitted[0]["recommendation_reason"]


def test_cloud_archive_requires_license_and_writes_manifest():
    folder = tempfile.mkdtemp()
    cloud = DJArchiveCloud(download_folder=folder)

    blocked = cloud.download_pack(
        "monthly_tech_house_essentials",
        {"licensed": False, "plan": "DEMO"}
    )

    allowed = cloud.download_pack(
        "monthly_tech_house_essentials",
        {"licensed": True, "plan": "DJ_ARCHIVE"}
    )

    try:
        assert blocked["ok"] is False
        assert blocked["reason"] == "DJ_ARCHIVE_LICENSE_REQUIRED"
        assert allowed["ok"] is True
        assert os.path.exists(allowed["path"])
    finally:
        if os.path.exists(allowed.get("path", "")):
            os.remove(allowed["path"])
        if os.path.exists(folder):
            os.rmdir(folder)


def test_entitlements_gate_commercial_features():
    manager = EntitlementManager()

    demo = manager.entitlements_for({
        "licensed": False,
        "plan": "DEMO",
        "max_tracks": 1000,
    })
    archive = manager.entitlements_for({
        "licensed": True,
        "plan": "DJ_ARCHIVE",
        "max_tracks": 100000,
        "updates_until": "2099-01-01",
    })

    assert demo["dj_archive_downloads"] is False
    assert archive["dj_archive_downloads"] is True
    assert archive["updates_active"] is True


def test_commercial_api_writes_checkout_intent():
    folder = tempfile.mkdtemp()
    api = CommercialAPIClient()

    path = api.write_checkout_intent("DJ_ARCHIVE", output_folder=folder)

    try:
        assert os.path.exists(path)
    finally:
        if os.path.exists(path):
            os.remove(path)
        if os.path.exists(folder):
            os.rmdir(folder)


def test_export_center_writes_m3u_and_rekordbox_stub():
    folder = tempfile.mkdtemp()
    exporter = ExportCenter(output_folder=folder)
    tracks = [
        {
            "id": "1",
            "name": "Track 1",
            "path": "C:/Music/Track 1.mp3",
            "duration": 300,
            "bpm": 124,
            "camelot": "8A",
        }
    ]
    m3u = exporter.export_m3u(tracks, "test_set")
    xml = exporter.rekordbox_xml_stub(tracks, "test_rekordbox")

    try:
        assert os.path.exists(m3u)
        assert os.path.exists(xml)
    finally:
        for path in (m3u, xml):
            if os.path.exists(path):
                os.remove(path)
        if os.path.exists(folder):
            os.rmdir(folder)


def test_rekordbox_bridge_prepares_live_export_bundle():
    folder = tempfile.mkdtemp()
    bridge = RekordboxBridge(output_folder=folder)
    tracks = [
        {
            "id": "1",
            "name": "Track 1",
            "path": "C:/Music/Track 1.mp3",
            "duration": 300,
            "bpm": 124,
            "camelot": "8A",
            "role": "GROOVE",
        },
        {
            "id": "2",
            "name": "Track 2",
            "path": "C:/Music/Track 2.mp3",
            "duration": 280,
            "bpm": 126,
            "camelot": "9A",
            "role": "PEAK TIME",
        },
    ]

    result = bridge.prepare_ai_performance(tracks, "test_live")
    status = bridge.status()

    try:
        assert result["ok"] is True
        assert os.path.exists(result["xml_path"])
        assert os.path.exists(result["m3u_path"])
        assert os.path.exists(result["manifest_path"])
        assert result["instructions"]
        assert status["mode"] == "XML_BRIDGE"
        assert status["direct_control"] is False
    finally:
        for name in os.listdir(folder):
            os.remove(os.path.join(folder, name))
        os.rmdir(folder)


def test_gig_pack_builder_creates_professional_show_bundle():
    folder = tempfile.mkdtemp()
    tracks = [
        {
            "id": f"t{i}",
            "name": f"Track {i}.mp3",
            "path": f"C:/Music/Track {i}.mp3",
            "duration": 300,
            "genre": "AFRO HOUSE",
            "parent_genre": "HOUSE",
            "bpm": 120 + i,
            "camelot": "8A",
            "energy": 0.45 + (i % 5) * 0.08,
            "ai_ear_score": 0.7,
            "intro_outro_mixability": 0.72,
            "vocal_risk": 0.2,
        }
        for i in range(10)
    ]

    result = GigPackBuilder(output_folder=folder).build(
        tracks,
        style="AFRO HOUSE",
        hours=2,
        name="test_gig"
    )

    try:
        assert result["ok"] is True
        assert os.path.exists(result["manifest_path"])
        assert os.path.exists(result["briefing"])
        assert os.path.exists(result["rekordbox_xml"])
        assert os.path.exists(result["rescue_crate_m3u"])
        assert result["headline"]
    finally:
        for root, dirs, files in os.walk(folder, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(folder)


def test_fl_studio_bridge_creates_mastering_pack():
    folder = tempfile.mkdtemp()
    bridge = FLStudioBridge(output_folder=folder)
    track = {
        "name": "Master Candidate.mp3",
        "genre": "AFRO HOUSE",
        "role": "PEAK TIME",
        "energy": 0.88,
        "brightness": 0.75,
        "roughness": 0.2,
        "danceability": 0.86,
    }

    result = bridge.prepare_mastering_pack(track)
    status = bridge.status()

    try:
        assert result["ok"] is True
        assert os.path.exists(result["report_path"])
        assert os.path.exists(result["notes_path"])
        assert "LUFS" in result["headline"]
        assert "club translation" in result["headline"]
        assert "mix-master doktor" in result["headline"]
        assert status["mode"] == "MASTERING_HANDOFF"
    finally:
        for root, dirs, files in os.walk(folder, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(folder)


def test_mix_master_doctor_flags_suno_quality_repairs():
    report = MixMasterDoctor().diagnose({
        "name": "Suno Afro House Demo.mp3",
        "genre": "AFRO HOUSE",
        "role": "PEAK TIME",
        "energy": 0.88,
        "brightness": 0.84,
        "roughness": 0.42,
        "danceability": 0.72,
        "drop_strength": 0.08,
        "vocal_risk": 0.7,
        "intro_outro_mixability": 0.42,
    })

    codes = {issue["code"] for issue in report["issues"]}

    assert report["score"] < 75
    assert "AI_SOURCE_ARTIFACTS" in codes
    assert "KICK_PUNCH_BLURRED" in codes
    assert report["suno_rescue_chain"]
    assert report["urgent_fixes"]


def test_mix_master_engine_fallback_is_safe():
    result = MixMasterEngine().analyze_file("missing.wav")

    assert result["ok"] is False
    assert result["repair_plan"]


def test_mix_master_engine_analyzes_wav_without_librosa():
    folder = tempfile.mkdtemp()
    path = os.path.join(folder, "test_master.wav")
    sr = 44100

    with wave.open(path, "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(sr)
        frames = []

        for index in range(sr // 4):
            sample = int(math.sin(2 * math.pi * 440 * index / sr) * 12000)
            frames.append(struct.pack("<hh", sample, sample))

        handle.writeframes(b"".join(frames))

    try:
        engine = MixMasterEngine()
        original_librosa = __import__("app.ai.mix_master_engine", fromlist=["librosa"])
        saved_librosa = original_librosa.librosa
        saved_np = original_librosa.np
        original_librosa.librosa = None
        original_librosa.np = None

        try:
            result = engine.analyze_file(path)
        finally:
            original_librosa.librosa = saved_librosa
            original_librosa.np = saved_np

        assert result["ok"] is True
        assert result["engine"] == "WAV_STDLIB_FALLBACK"
        assert result["dynamics"]["peak_dbfs"] < 0
        assert result["waveform"]
        assert result["phrase_points"]
    finally:
        if os.path.exists(path):
            os.remove(path)
        os.rmdir(folder)


def test_archive_brain_relinks_to_archive_copy_when_source_moves():
    folder = tempfile.mkdtemp()
    archive = os.path.join(folder, "DJ_LIBRARY_OUTPUT", "HOUSE", "GROOVE")
    os.makedirs(archive)
    archived_path = os.path.join(archive, "Track.wav")

    with open(archived_path, "wb") as handle:
        handle.write(b"RIFF")

    track = {
        "id": os.path.join(folder, "old", "Track.wav"),
        "path": os.path.join(folder, "old", "Track.wav"),
        "archived_path": archived_path,
    }

    try:
        brain = ArchiveBrain()
        report = brain.health_report([track])
        relinked = brain.apply_playable_paths([track])

        assert report["missing"] == 0
        assert relinked == 1
        assert track["path"] == os.path.abspath(archived_path)
        assert track["path_status"] == "OK_SOURCE"
    finally:
        if os.path.exists(archived_path):
            os.remove(archived_path)

        for root, dirs, files in os.walk(folder, topdown=False):
            for name in dirs:
                os.rmdir(os.path.join(root, name))

        if os.path.exists(folder):
            os.rmdir(folder)


def test_feedback_learner_records_weights():
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    os.remove(path)
    learner = FeedbackLearner(path=path)
    track = {
        "id": "t1",
        "name": "Track 1",
        "genre": "AFRO HOUSE",
        "role": "GROOVE",
    }

    try:
        learner.record(track, "GOOD")
        learner.apply_to_track(track)
        assert track["dj_feedback_score"] > 0
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_genre_review_approves_discovered_track():
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    os.remove(path)
    review = GenreReviewStudio(mapping_path=path)
    track = {
        "id": "x",
        "name": "Unknown Tune.mp3",
        "genre": "DISCOVERED_STYLE_1",
        "parent_genre": "UNKNOWN",
        "discovery_status": "DISCOVERED",
    }

    try:
        assert review.needs_review([track])
        review.approve(track, "AFRO HOUSE", "HOUSE", "WARMUP")
        updated = review.apply(track)
        assert updated["genre"] == "AFRO HOUSE"
        assert updated["discovery_status"] == "DJ_APPROVED"
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_commercial_api_local_activation_fallback():
    client = CommercialAPIClient(base_url="http://127.0.0.1:9")
    result = client.activate_license(
        "dj@example.com",
        "ARCHIVE-12345678",
        "machine-1"
    )

    assert result["ok"] is True
    assert result["license"]["plan"] == "DJ_ARCHIVE"


def test_server_license_activation_and_entitlements():
    service = LicenseService(secret="test-secret")

    activated = service.activate(
        "dj@example.com",
        "ARCHIVE-12345678",
        "machine-1"
    )
    checked = service.entitlements_for_license(activated["license"])

    assert activated["ok"] is True
    assert activated["license"]["plan"] == "DJ_ARCHIVE"
    assert checked["ok"] is True
    assert checked["entitlements"]["dj_archive_downloads"] is True


def test_server_billing_checkout_and_webhook_contract():
    billing = BillingService()
    checkout = billing.create_checkout(
        "PRO",
        "dj@example.com",
        "https://success",
        "https://cancel"
    )
    webhook = billing.handle_webhook({
        "type": "subscription_created",
        "payload": {
            "email": "dj@example.com",
            "plan": "PRO",
        },
    })

    assert checkout["ok"] is True
    assert checkout["checkout"]["status"] == "PENDING_PROVIDER"
    assert webhook["action"] == "ISSUE_LICENSE"


def test_server_cloud_download_requires_entitlement():
    cloud = CloudService()
    blocked = cloud.download_pack(
        "monthly_tech_house_essentials",
        {
            "licensed": False,
            "plan": "DEMO",
            "entitlements": {
                "dj_archive_downloads": False,
            },
        }
    )
    allowed = cloud.download_pack(
        "monthly_tech_house_essentials",
        {
            "licensed": True,
            "plan": "DJ_ARCHIVE",
            "entitlements": {
                "dj_archive_downloads": True,
            },
        }
    )

    assert blocked["ok"] is False
    assert allowed["ok"] is True
    assert allowed["download"]["signed_url"]


# ============================================================
# NEW MODULE TESTS
# ============================================================

def test_version_detector_basic():
    from app.ai.version_detector import detect_version
    assert detect_version("Song (Extended Mix).mp3") == "EXTENDED"
    assert detect_version("Track (Radio Edit).mp3") == "RADIO_EDIT"
    assert detect_version("Vocal Rework.flac") == "REMIK"
    assert detect_version("Original Mix.wav") == "ORIGINAL"
    assert detect_version("Acapella Version.mp3") == "ACAPELLA"


def test_version_detector_same_song_family():
    from app.ai.version_detector import are_same_song_version
    assert are_same_song_version("ORIGINAL", "EXTENDED") is True
    assert are_same_song_version("ORIGINAL", "RADIO_EDIT") is True
    assert are_same_song_version("ORIGINAL", "REMIK") is False
    assert are_same_song_version("REMIK", "ACAPELLA") is False


def test_emergency_crate_finds_rescue_tracks():
    from app.ai.emergency_crate import EmergencyCrate
    crate = EmergencyCrate()
    library = [
        {"id": "1", "name": "Peak Track", "genre": "AFRO HOUSE", "role": "PEAK TIME", "energy": 0.9, "camelot": "8A"},
        {"id": "2", "name": "Warm Track", "genre": "HOUSE", "role": "WARMUP", "energy": 0.3, "camelot": "8A"},
        {"id": "3", "name": "Groove Track", "genre": "TECH HOUSE", "role": "GROOVE", "energy": 0.65, "camelot": "9A"},
    ]
    current = {"id": "2", "energy": 0.3, "camelot": "8A"}
    rescue = crate.find_rescue_tracks(library, current, limit=3)
    assert len(rescue) > 0
    assert rescue[0].get("rescue_score", 0) > 0


def test_emergency_crate_assesses_set_health():
    from app.ai.emergency_crate import EmergencyCrate
    crate = EmergencyCrate()
    tracks = [
        {"bpm": 124, "energy": 0.5, "camelot": "8A"},
        {"bpm": 124, "energy": 0.5, "camelot": "8A"},
        {"bpm": 124, "energy": 0.5, "camelot": "8A"},
        {"bpm": 124, "energy": 0.5, "camelot": "8A"},
        {"bpm": 124, "energy": 0.5, "camelot": "8A"},
    ]
    result = crate.assess_set_health(tracks)
    assert "health_score" in result
    assert result["health_score"] >= 0


def test_dj_coach_analyzes_set():
    from app.ai.dj_coach import DJCoach
    coach = DJCoach()
    tracks = [
        {"bpm": 120, "energy": 0.4, "role": "WARMUP", "camelot": "8A", "genre": "HOUSE"},
        {"bpm": 124, "energy": 0.6, "role": "GROOVE", "camelot": "8A", "genre": "HOUSE"},
        {"bpm": 126, "energy": 0.8, "role": "PEAK TIME", "camelot": "9A", "genre": "HOUSE"},
        {"bpm": 128, "energy": 0.9, "role": "PEAK TIME", "camelot": "9A", "genre": "TECH HOUSE"},
        {"bpm": 124, "energy": 0.5, "role": "WARMUP", "camelot": "8A", "genre": "HOUSE"},
    ]
    result = coach.analyze_set(tracks, "CLUB")
    assert result["grade"] in ("S", "A", "B", "C", "D")
    assert "scores" in result
    assert "coaching" in result


def test_track_dna_generates_barcode():
    from app.ai.track_dna import generate_dna, dna_to_string
    track = {"energy": 0.8, "brightness": 0.6, "danceability": 0.7, "vocal_risk": 0.2, "drop_strength": 0.4, "heart_score": 0.7, "roughness": 0.3}
    dna = generate_dna(track)
    assert len(dna) > 0
    dna_str = dna_to_string(dna)
    assert "|" in dna_str


def test_track_similarity_finds_similar():
    from app.ai.track_similarity import TrackSimilarityEngine
    engine = TrackSimilarityEngine()
    target = {"id": "1", "name": "Track A", "bpm": 124, "energy": 0.7, "brightness": 0.5, "genre": "HOUSE", "camelot": "8A", "role": "GROOVE"}
    library = [
        {"id": "2", "name": "Track B", "bpm": 126, "energy": 0.72, "brightness": 0.48, "genre": "HOUSE", "camelot": "8A", "role": "GROOVE"},
        {"id": "3", "name": "Track C", "bpm": 140, "energy": 0.95, "brightness": 0.8, "genre": "TECHNO", "camelot": "12B", "role": "PEAK TIME"},
    ]
    similar = engine.find_similar(target, library, limit=2)
    assert len(similar) > 0
    assert similar[0]["similarity_score"] > 0


def test_dj_profile_builds_from_tracks():
    from app.ai.dj_profile import DJProfile
    profile = DJProfile()
    tracks = [
        {"genre": "HOUSE", "energy": 0.7, "bpm": 124, "camelot": "8A", "role": "GROOVE", "ai_ear_score": 0.8},
        {"genre": "TECHNO", "energy": 0.9, "bpm": 135, "camelot": "12B", "role": "PEAK TIME", "ai_ear_score": 0.7},
        {"genre": "HOUSE", "energy": 0.5, "bpm": 120, "camelot": "8A", "role": "WARMUP", "ai_ear_score": 0.6},
    ]
    result = profile.build_profile(tracks)
    assert result["track_count"] == 3
    assert "dna" in result
    assert "insights" in result
    assert len(result["top_genres"]) > 0


def test_smart_playlist_generates_wedding():
    from app.ai.smart_playlist import SmartPlaylistGenerator
    gen = SmartPlaylistGenerator()
    library = [
        {"id": str(i), "genre": "HOUSE", "parent_genre": "HOUSE", "energy": 0.3 + i * 0.08, "bpm": 120 + i, "role": ["OPENING", "WARMUP", "GROOVE", "PEAK TIME"][i % 4], "ai_ear_score": 0.7}
        for i in range(20)
    ]
    result = gen.generate(library, "WEDDING", hours=2)
    assert result["venue"] == "WEDDING"
    assert result["total_tracks"] > 0
    assert len(result["phases"]) > 0


def test_smart_playlist_generates_club():
    from app.ai.smart_playlist import SmartPlaylistGenerator
    gen = SmartPlaylistGenerator()
    library = [
        {"id": str(i), "genre": "TECH HOUSE", "parent_genre": "HOUSE", "energy": 0.4 + i * 0.05, "bpm": 124 + i, "role": ["WARMUP", "GROOVE", "PEAK TIME"][i % 3], "ai_ear_score": 0.7}
        for i in range(30)
    ]
    result = gen.generate(library, "CLUB", hours=3)
    assert result["venue"] == "CLUB"
    assert result["total_tracks"] > 0


def test_set_recorder_records_session():
    from app.ai.set_recorder import SetRecorder
    recorder = SetRecorder()
    recorder.start_recording("CLUB")
    assert recorder.recording is True
    recorder.record_track_start({"id": "1", "name": "Track 1", "bpm": 124, "energy": 0.7})
    recorder.record_track_end()
    recorder.record_skip({"id": "2", "name": "Track 2"}, reason="wrong genre")
    summary = recorder.get_session_summary()
    assert summary["tracks_played"] == 1
    assert summary["tracks_skipped"] == 1
    result = recorder.stop_recording()
    assert result["total_tracks"] == 1


def test_mfcc_classifier_fallback():
    from app.ai.mfcc_classifier import MFCCClassifier
    clf = MFCCClassifier()
    assert clf.is_available() is False  # No model trained yet
    result = clf.predict({"energy": 0.7, "brightness": 0.5, "mfcc": [0.1] * 13})
    assert result is None  # Returns None when no model


def test_deck_engine_bpm_match_report():
    from app.ai.deck_engine import DeckEngine
    engine = DeckEngine()
    engine.load("A", {"bpm": 124, "energy": 0.7, "camelot": "8A"})
    engine.load("B", {"bpm": 126, "energy": 0.65, "camelot": "8A"})
    report = engine.bpm_match_report()
    assert report["matched"] is True
    assert report["diff"] == 2.0
    assert report["harmonic_match"] is True


if __name__ == "__main__":
    test_music_ai_classifies_track()
    test_music_ai_classifies_wedding_archive_tracks()
    test_unknown_styles_do_not_become_peak_time_archive_folders()
    test_set_engine_builds_ordered_set()
    test_library_db_persists_archive_fields()
    test_demo_license_limit()
    test_audio_analyzer_fallback_is_safe()
    test_audio_scanner_skips_generated_archive_folders()
    test_audio_scanner_rejects_archive_root_selection()
    test_ai_ear_scores_professional_mixability()
    test_club_intelligence_corrects_half_and_double_tempo()
    test_dj_heart_builds_emotional_pulse_map()
    test_voice_command_router_understands_dj_commands()
    test_voice_runtime_reports_capabilities_without_microphone()
    test_remix_lab_builds_blueprint_and_demucs_command()
    test_remix_lab_readiness_brief_and_export()
    test_remix_lab_renders_ai_remix_wav()
    test_performance_planner_picks_afro_opening_track()
    test_deck_engine_builds_auto_mix_plan()
    test_show_director_builds_segmented_show_and_rescue_crate()
    test_library_doctor_suggests_names_and_duplicates()
    test_archive_auditor_reports_legacy_and_zero_byte_files()
    test_organizer_does_not_duplicate_same_audio_content()
    test_organizer_blocks_filename_collision_without_suffix_copy()
    test_archive_auditor_reports_renamed_duplicate_groups()
    test_archive_reconciler_builds_exact_duplicate_cleanup_plan()
    test_music_research_assistant_prepares_safe_links()
    test_music_research_assistant_marks_event_tracks()
    test_genre_knowledge_discovers_unknown_styles()
    test_trend_recommender_ranks_and_fits_library()
    test_cloud_archive_requires_license_and_writes_manifest()
    test_entitlements_gate_commercial_features()
    test_commercial_api_writes_checkout_intent()
    test_export_center_writes_m3u_and_rekordbox_stub()
    test_rekordbox_bridge_prepares_live_export_bundle()
    test_gig_pack_builder_creates_professional_show_bundle()
    test_fl_studio_bridge_creates_mastering_pack()
    test_mix_master_doctor_flags_suno_quality_repairs()
    test_mix_master_engine_fallback_is_safe()
    test_mix_master_engine_analyzes_wav_without_librosa()
    test_archive_brain_relinks_to_archive_copy_when_source_moves()
    test_feedback_learner_records_weights()
    test_genre_review_approves_discovered_track()
    test_commercial_api_local_activation_fallback()
    test_server_license_activation_and_entitlements()
    test_server_billing_checkout_and_webhook_contract()
    test_server_cloud_download_requires_entitlement()
    test_version_detector_basic()
    test_version_detector_same_song_family()
    test_emergency_crate_finds_rescue_tracks()
    test_emergency_crate_assesses_set_health()
    test_dj_coach_analyzes_set()
    test_track_dna_generates_barcode()
    test_track_similarity_finds_similar()
    test_dj_profile_builds_from_tracks()
    test_smart_playlist_generates_wedding()
    test_smart_playlist_generates_club()
    test_set_recorder_records_session()
    test_mfcc_classifier_fallback()
    test_deck_engine_bpm_match_report()
    print("smoke tests passed")


