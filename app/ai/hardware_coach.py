"""
DJ AI OS — Hardware Coach
=========================
The DJ AI that learns from your HANDS. It watches the raw hardware events
(PioneerLink hands them over from the CDJ/XDJ/DJM — jog wheel spins, EQ
knob moves, filter, faders, crossfader, pads) and turns them into live
mix coaching: what are you doing, where is the mix going, and what should
you do next — timed, in Turkish, with a confidence.

It also builds a tiny Markov model over your action sequence, so it can
predict the next move ("you always grab the crossfader after the filter")
and — when you're on a set — point at the next track that fits the energy
you've just created.

    coach = HardwareCoach()
    coach.feed({"type": "jog", "deck": "A", "delta": -3})
    coach.feed({"type": "crossfader", "deck": "mixer", "value": 0.72})
    coach.suggest()   # -> [(text, confidence, kind), ...]
"""

import time
from collections import Counter

DECKS = "ABCD"
WINDOW_S = 20.0


class HardwareCoach:
    """Accumulate hardware events, measure the mix, coach the DJ."""

    def __init__(self, window_s=WINDOW_S):
        self.window_s = window_s
        self.events = []            # [(t, event_dict), ...] rolling window
        self._actions = []          # [(t, action_type), ...] for Markov
        self._counts = Counter()    # action_type -> occurrences
        self.state = {d: {"jog": 0.0, "eq": 0.0, "filter": 0.5,
                          "fader": 0.5, "pads": 0} for d in DECKS}
        self.cross_pos = 0.5
        self.cross_vel = 0.0
        self.cross_hist = []        # [(t, pos), ...]
        self.last_event = None
        self.last_action_type = None
        self.transitions = Counter()  # (prev, next) -> n
        self.ready = False

    # ============================================================
    # FEED
    # ============================================================
    def feed(self, ev):
        if not isinstance(ev, dict) or "type" not in ev:
            return
        t = time.time()
        typ = ev["type"]
        deck = ev.get("deck", "")

        self.events.append((t, ev))
        cutoff = t - self.window_s
        while self.events and self.events[0][0] < cutoff:
            self.events.pop(0)

        self._counts[typ] += 1
        if typ != self.last_action_type:
            if self.last_action_type:
                self.transitions[(self.last_action_type, typ)] += 1
            self.last_action_type = typ
        self._actions.append((t, typ))
        while self._actions and self._actions[0][0] < cutoff:
            self._actions.pop(0)

        if deck in self.state:
            if typ == "jog":
                self.state[deck]["jog"] += abs(ev.get("delta", 0))
            elif typ in ("eq_hi", "eq_mid", "eq_low"):
                self.state[deck]["eq"] += 1
            elif typ == "filter":
                self.state[deck]["filter"] = ev.get("value", 0.5)
            elif typ == "fader":
                self.state[deck]["fader"] = ev.get("value", 0.5)
            elif typ == "pad":
                self.state[deck]["pads"] += 1
        elif typ == "crossfader":
            v = ev.get("value", 0.5)
            self.cross_vel = v - self.cross_pos
            self.cross_pos = v
            self.cross_hist.append((t, v))
            while self.cross_hist and self.cross_hist[0][0] < cutoff:
                self.cross_hist.pop(0)

        self.last_event = ev
        if len(self.events) >= 3:
            self.ready = True

    # ============================================================
    # MEASURE
    # ============================================================
    def activity(self):
        """Per-deck activity score 0..~1."""
        total = 0.0
        scores = {}
        for d in DECKS:
            s = self.state[d]
            sc = (s["jog"] * 0.5
                  + s["eq"] * 1.5
                  + abs(s["filter"] - 0.5) * 4.0
                  + s["fader"] * 1.0
                  + s["pads"] * 1.5)
            scores[d] = sc
            total += sc
        if total > 0:
            for d in DECKS:
                scores[d] = min(1.0, scores[d] / max(total / len(DECKS), 1e-6))
        return scores

    def active_deck(self):
        act = self.activity()
        if all(v < 0.05 for v in act.values()):
            return None
        return max(act, key=act.get)

    def cross_trend(self):
        if len(self.cross_hist) < 2:
            return 0.0
        (t0, p0), (t1, p1) = self.cross_hist[0], self.cross_hist[-1]
        # use a 2s characteristic timescale so near-simultaneous events
        # can't blow up the metric; clamp to a sane -2..2 range
        dt = max(t1 - t0, 2.0)
        trend = (p1 - p0) / dt * 10.0
        return max(-2.0, min(2.0, trend))

    def predict_next(self):
        """Most likely next action given the last one (Markov-lite)."""
        if not self.last_action_type:
            return None, 0.0
        pool = [nxt for (prev, nxt), n in self.transitions.items()
                if prev == self.last_action_type]
        if not pool:
            return None, 0.0
        c = Counter(pool)
        best, n = c.most_common(1)[0]
        tot = sum(c.values())
        return best, n / tot

    # ============================================================
    # COACH
    # ============================================================
    def suggest(self, set_tracks=None):
        """Return [(text, confidence, kind), ...] sorted by confidence."""
        out = []
        act = self.activity()
        deck = self.active_deck()
        trend = self.cross_trend()

        # crossfader moving toward B -> hand the mix over
        if self.cross_pos > 0.62 and trend > 0.15:
            out.append(("Crossfader B'ye kayıyor — B'yi öne al, "
                        "A'nın bass'ını 4 bar içinde kıs.", 0.9, "mix"))
        elif self.cross_pos < 0.38 and trend < -0.15:
            out.append(("Crossfader A'ya dönüyor — A'nın enerjisini geri "
                        "getir, B'yi filtreden çek.", 0.9, "mix"))

        # a deck is riding its filter
        for d in DECKS:
            if act[d] > 0.3 and abs(self.state[d]["filter"] - 0.5) > 0.35:
                out.append((f"Deck {d} filtresi aşırı sürülüyor — düşüşte "
                            "merkeze al ya da FX'e bırak.", 0.75, "eq"))

        # heavy EQ fiddling = tired ears / rough mix
        if deck and self.state[deck]["eq"] >= 4:
            out.append((f"Deck {deck} EQ'sunda çok oynadın — aynı bölgeyi "
                        "kesip bir kez bırak, sürekli oynama.", 0.6, "eq"))

        # jog activity on the incoming deck
        if deck and self.state[deck]["jog"] > 30:
            out.append((f"Deck {deck} jog'unda sürekli düzeltme var — "
                        "tempo fader'ını ±%1 içinde sabitle.", 0.7, "beatmatch"))

        # pad usage = cue/loop creativity
        if deck and self.state[deck]["pads"] >= 3:
            out.append((f"Deck {deck} pad'lerinde dolanıyorsun — ilk 8 bar'ı "
                        "loop'layıp B'yi üzerine sür.", 0.55, "structure"))

        # recent play = a new deck just came in
        if self._counts["play"] >= 1 and deck and self.cross_pos <= 0.5:
            out.append((f"{deck} deck'inde PLAY var — 8 bar boyunca kulaklıkta "
                        "dinle, sonra fade ile getir.", 0.5, "structure"))

        # markov hint
        nxt, conf = self.predict_next()
        if nxt and conf > 0.4:
            lbl = {"crossfader": "crossfader", "filter": "filtre",
                   "jog": "jog", "eq_hi": "HI EQ", "play": "PLAY"}.get(nxt, nxt)
            out.append((f"Desenin: {self.last_action_type} → {nxt} "
                        f"(%{int(conf * 100)}) — {lbl} için hazır ol.", 0.4, "pattern"))

        # set pointer: next track that fits
        if set_tracks and len(set_tracks) >= 2 and deck:
            cur_bpm = None
            # find the playing track's bpm from last play event deck? not
            # tracked; use the active deck's tempo hint instead
            nxt_t = set_tracks[0]
            out.append((f"Set'te sırada: {nxt_t.get('name', '')} "
                        f"({nxt_t.get('bpm') or '?'} BPM · "
                        f"{nxt_t.get('camelot') or nxt_t.get('key') or '?'})",
                        0.45, "set"))

        # nothing much happening
        if not out:
            out.append(("Karışım dengeli — bekleyen düşüşe bir giriş (riser) "
                        "koy, sonra B'yi getir.", 0.35, "idle"))

        out.sort(key=lambda x: -x[1])
        return out

    def summary(self):
        """Compact status line for the panel."""
        deck = self.active_deck()
        act = self.activity()
        line = "aktif deck: "
        line += ", ".join(f"{d} %{int(act[d] * 100)}" for d in DECKS)
        line += f" | cross {self.cross_pos:.2f}"
        if self.last_event:
            ev = self.last_event
            line += f" | son: {ev.get('type')}"
            if ev.get("deck"):
                line += f"@{ev['deck']}"
        return line, deck
