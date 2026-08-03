from collections import defaultdict


class DJCrateBuilder:

    def __init__(self, audio_brain):

        self.brain = audio_brain

    # =====================================================
    # MAIN ENTRY
    # =====================================================

    def build_crates(self, tracks):

        crates = defaultdict(list)

        for track in tracks:

            # 🧠 ANALYZE TRACK
            analyzed = self.brain.analyze(track)

            genre = analyzed.get("genre_cluster", "unknown")
            mood = analyzed.get("mood", "unknown")
            energy = analyzed.get("energy", track.get("energy", 0))

            # =================================================
            # 1. GENRE CRATES (your original logic)
            # =================================================
            crates[genre].append(analyzed)

            # =================================================
            # 2. MOOD CRATES (DJ FLOW LOGIC)
            # =================================================
            crates[f"mood_{mood}"].append(analyzed)

            # =================================================
            # 3. ENERGY CRATES (SET STRUCTURE)
            # =================================================

            if energy < 0.35:
                crates["warmup"].append(analyzed)

            elif energy < 0.6:
                crates["groove"].append(analyzed)

            elif energy < 0.8:
                crates["drive"].append(analyzed)

            else:
                crates["peak"].append(analyzed)

            # =================================================
            # 4. DJ UTILITY CRATES
            # =================================================

            if energy > 0.85:
                crates["high_energy_weapons"].append(analyzed)

            if energy < 0.3:
                crates["safe_tracks"].append(analyzed)

            # =================================================
            # 5. UNKNOWN LEARNING FEED
            # =================================================

            if genre == "unknown":
                crates["learning_pool"].append(analyzed)

        # =====================================================
        # SORT EVERY CRATE BY DJ SCORE
        # =====================================================

        for k in crates:

            crates[k] = sorted(
                crates[k],
                key=lambda x: x.get("dj_score", 0),
                reverse=True
            )

        return dict(crates)
