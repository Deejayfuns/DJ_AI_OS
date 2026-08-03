from app.core.audio_scanner import AudioScanner

from app.ai.set_builder import SetBuilder
from app.ai.harmonic_engine import HarmonicEngine
from app.ai.dj_memory import DJMemory


# ------------------------------------------------
# INIT SYSTEM
# ------------------------------------------------

scanner = AudioScanner()

harmonic = HarmonicEngine()

memory = DJMemory()

builder = SetBuilder(harmonic)


# ------------------------------------------------
# SCAN REAL FOLDER
# ------------------------------------------------

FOLDER = r"C:\Users\X\Music\DJ_LIBRARY"

tracks = scanner.scan_folder(FOLDER)

print(f"\n🎧 Found tracks: {len(tracks)}\n")


# ------------------------------------------------
# BUILD AI SET
# ------------------------------------------------

dj_set = builder.build(tracks)


# ------------------------------------------------
# OUTPUT DJ SET
# ------------------------------------------------

print("\n🔥 AI DJ SET\n")

for i, t in enumerate(dj_set):

    print(
        f"{i+1}. "
        f"{t['name']} | "
        f"{t['bpm']} BPM | "
        f"{t['genre']} | "
        f"KEY:{t.get('camelot')} | "
        f"E:{t['energy']} | "
        f"Q:{t['quality']} | "
        f"S:{t['quality_score']} | "
        f"TAGS:{','.join(t['tags'])}"
    )

    # ------------------------------------------------
    # SAVE MEMORY
    # ------------------------------------------------

    memory.log_play(t, i)


# ------------------------------------------------
# DJ PROFILE
# ------------------------------------------------

print("\n🧠 DJ STYLE PROFILE\n")

profile = memory.analyze_style()

for genre, data in profile.items():

    print(
        f"{genre} -> "
        f"Avg Position: {data['avg_position']}"
    )


# ------------------------------------------------
# ENERGY CURVE
# ------------------------------------------------

print("\n📈 ENERGY CURVE\n")

curve = memory.energy_curve()

for point in curve:

    print(
        f"Position {point['position']} "
        f"→ Energy {point['avg_energy']}"
    )
