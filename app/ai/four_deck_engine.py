"""
DJ AI OS — Four-Deck Engine (HID-driven)

Extends the 2-deck AudioEngine to 4 logical decks (A, B, C, D) where the
physical Pioneer XDJ-RR/RX2 Layer button maps the channel faders/EQ:

    Layer 1  -> decks A, B (fader A -> deck A, fader B -> deck B)
    Layer 2  -> decks C, D (fader A -> deck C, fader B -> deck D)

HID events from HIDDeckController are translated into deck operations.

This engine is the bridge between:
    HIDDeckController (hardware)  <->  FourDeckEngine (logic)
                                <->  DeckStudio UI (display/control)

Each deck wraps an AudioEngine-style VLC player. When VLC is unavailable,
decks fall back to a simulated position clock so the UI still works.
"""

import threading
import time

try:
    import vlc
    VLC_AVAILABLE = True
except Exception:
    VLC_AVAILABLE = False


class Deck:
    """One logical deck: transport state + track + position clock."""

    def __init__(self, deck_id, engine, vlc_player=None):
        self.id = deck_id                 # 'A'|'B'|'C'|'D'
        self.engine = engine              # parent FourDeckEngine
        self.player = vlc_player
        self.track = None
        self.playing = False
        self.paused = False
        self.loaded = False
        self.volume = 1.0
        self.tempo = 1.0
        self.position = 0.0               # seconds (simulated if no VLC)
        self.length = 0.0
        self.cue = 0.0
        self.hot_cues = {}                # pad# -> seconds
        self.eq = {"hi": 0.0, "mid": 0.0, "low": 0.0}
        self.filter = 0.0
        self._clock = None
        self._clock_on = False

    # ---- transport ----
    def load(self, track):
        self.track = track
        self.length = float(track.get("length") or 0.0)
        self.position = 0.0
        self.cue = 0.0
        self.loaded = True
        self.playing = False

        # --- Beatgrid sync from Rekordbox import ---
        bg = track.get("beatgrid")
        if bg and isinstance(bg, dict):
            bpm = bg.get("bpm")
            first_beat = bg.get("first_beat", 0.0)
            if bpm and bpm > 0:
                # set deck tempo to track's native BPM (so pitch=0.0 means original speed)
                self.tempo = 1.0  # pitch slider at center
                # VLC rate will be adjusted by pitch slider relative to this native BPM
                # Store native BPM for display and sync calculations
                self._native_bpm = float(bpm)
                # Cue at first beat marker if present
                if first_beat and first_beat > 0:
                    self.cue = float(first_beat)
                    self.position = self.cue
        else:
            self._native_bpm = float(track.get("bpm") or 0.0)

        if self.player:
            path = track.get("path")
            if path:
                try:
                    self.player.set_media(
                        self.engine._vlc_instance.media_new(path))
                    self.length = self.player.get_length() / 1000.0 or self.length
                    # Seek to cue point (first beat)
                    if self.cue > 0:
                        self.player.set_time(int(self.cue * 1000))
                except Exception:
                    pass

    def play(self):
        if self.player:
            try:
                self.player.play()
                self.playing = True
                self.paused = False
            except Exception:
                self.playing = False
        else:
            self.playing = True
            self.paused = False
            self._start_clock()
        self._emit({"type": "state", "deck": self.id,
                    "playing": self.playing, "paused": self.paused})

    def pause(self):
        if self.player:
            try:
                self.player.pause()
            except Exception:
                pass
        self.paused = not self.paused
        self.playing = not self.paused
        self._emit({"type": "state", "deck": self.id,
                    "playing": self.playing, "paused": self.paused})

    def stop(self):
        if self.player:
            try:
                self.player.stop()
            except Exception:
                pass
        self.playing = False
        self.paused = False
        self.position = 0.0
        self._stop_clock()
        self._emit({"type": "state", "deck": self.id,
                    "playing": False, "paused": False})

    def seek(self, seconds):
        self.position = max(0.0, min(self.length or 1e9, seconds))
        if self.player:
            try:
                self.player.set_time(int(self.position * 1000))
            except Exception:
                pass

    def set_cue(self):
        self.cue = self.position

    def back_to_cue(self):
        self.seek(self.cue)

    def set_hot_cue(self, pad):
        self.hot_cues[pad] = self.position

    def trigger_hot_cue(self, pad):
        if pad in self.hot_cues:
            self.seek(self.hot_cues[pad])

    def set_tempo(self, t):
        self.tempo = max(0.25, min(4.0, t))
        if self.player:
            try:
                self.player.set_rate(self.tempo)
            except Exception:
                pass
        self._emit({"type": "tempo", "deck": self.id, "tempo": self.tempo})

    def set_volume(self, v):
        self.volume = max(0.0, min(1.0, v))
        if self.player:
            try:
                self.player.audio_set_volume(int(self.volume * 100))
            except Exception:
                pass
        self._emit({"type": "volume", "deck": self.id, "volume": self.volume})

    # ---- simulated position clock ----
    def _start_clock(self):
        if self._clock_on:
            return
        self._clock_on = True
        self._clock = threading.Thread(target=self._clock_loop, daemon=True)
        self._clock.start()

    def _stop_clock(self):
        self._clock_on = False

    def _clock_loop(self):
        last = time.time()
        while self._clock_on and self.playing:
            now = time.time()
            dt = now - last
            last = now
            self.position += dt * self.tempo
            if self.length and self.position >= self.length:
                self.position = 0.0
            self._emit({"type": "position", "deck": self.id,
                        "position": self.position, "length": self.length})
            time.sleep(0.05)

    def _emit(self, evt):
        if self.engine and self.engine.callback:
            try:
                self.engine.callback(evt)
            except Exception:
                pass

    def state(self):
        return {
            "deck": self.id, "playing": self.playing, "paused": self.paused,
            "loaded": self.loaded, "track": self.track,
            "position": self.position, "length": self.length,
            "volume": self.volume, "tempo": self.tempo,
            "cue": self.cue, "hot_cues": dict(self.hot_cues),
            "eq": dict(self.eq), "filter": self.filter,
        }


class FourDeckEngine:
    """
    4-deck playback with Layer mapping for Pioneer XDJ-RR/RX2.
    """

    def __init__(self, callback=None, use_vlc=None):
        self.callback = callback
        self.use_vlc = VLC_AVAILABLE if use_vlc is None else use_vlc
        self.layer = 1                       # 1 -> A/B, 2 -> C/D
        self.crossfader = 0.5
        self.master_volume = 1.0
        self._vlc_instance = None

        if self.use_vlc:
            try:
                self._vlc_instance = vlc.Instance("--no-video")
            except Exception:
                self._vlc_instance = None
                self.use_vlc = False

        self.decks = {}
        for did in ("A", "B", "C", "D"):
            player = None
            if self.use_vlc and self._vlc_instance:
                try:
                    player = self._vlc_instance.media_player_new()
                except Exception:
                    player = None
            self.decks[did] = Deck(did, self, vlc_player=player)

        self.active_pair = ("A", "B")        # physical faders control this pair
        self._update_active_pair()

    # ---- layer ----
    def _update_active_pair(self):
        self.active_pair = ("A", "B") if self.layer == 1 else ("C", "D")

    def toggle_layer(self):
        self.layer = 2 if self.layer == 1 else 1
        self._update_active_pair()
        self._emit({"type": "layer", "layer": self.layer,
                    "decks": list(self.active_pair)})
        return self.layer

    def set_layer(self, n):
        self.layer = 1 if n == 1 else 2
        self._update_active_pair()

    # ---- physical control routing ----
    def physical_deck(self, side):
        """Map fader A/B -> active deck pair."""
        a, b = self.active_pair
        return a if side == "A" else b

    def fader(self, side, value):
        deck = self.physical_deck(side)
        self.decks[deck].set_volume(value)

    def crossfade(self, value):
        self.crossfader = max(0.0, min(1.0, value))
        a, b = self.active_pair
        # simple equal-power-ish taper
        left = max(0.0, 1.0 - self.crossfader * 2)
        right = max(0.0, self.crossfader * 2 - 1.0)
        self.decks[a].set_volume(max(0.0, min(1.0, left * 2)))
        self.decks[b].set_volume(max(0.0, min(1.0, right * 2)))
        self._emit({"type": "crossfader", "value": value})

    def eq(self, side, band, value):
        deck = self.physical_deck(side)
        self.decks[deck].eq[band] = max(-1.0, min(1.0, value))

    def filter(self, side, value):
        deck = self.physical_deck(side)
        self.decks[deck].filter = max(0.0, min(1.0, value))

    # ---- HID event dispatch ----
    def handle_hid_event(self, evt):
        """Translate a HIDDeckController event into deck operations."""
        t = evt.get("type")
        if t == "jog":
            deck = self.decks[evt["deck"]]
            # 200 steps/rev of a jog ~ 1/4 turn; nudge position a few ms/step
            deck.seek(deck.position + evt["delta"] * 0.0005)
        elif t == "tempo":
            deck = self.decks[evt["deck"]]
            # 0..1 fader -> tempo 0.5..1.5 (center ~1.0)
            v = evt["value"]
            deck.set_tempo(0.5 + v * 1.0)
        elif t == "fader":
            self.fader(evt["deck"], evt["value"])
        elif t == "crossfader":
            self.crossfade(evt["value"])
        elif t == "button":
            deck = self.decks[evt["deck"]]
            if evt["control"] == "play":
                if deck.playing:
                    deck.pause()
                else:
                    deck.play()
            elif evt["control"] == "cue":
                if evt.get("pressed"):
                    deck.back_to_cue()
            elif evt["control"] == "sync":
                self._sync_deck(deck)
        elif t == "pad":
            deck = self.decks[evt["deck"]]
            if evt.get("pressed"):
                if evt["pad"] in deck.hot_cues:
                    deck.trigger_hot_cue(evt["pad"])
                else:
                    deck.set_hot_cue(evt["pad"])
        elif t == "layer":
            self.toggle_layer()

    def _sync_deck(self, deck):
        """Match deck BPM to the master using Rekordbox beatgrid BPM if available."""
        master = None
        for d in self.decks.values():
            if d.playing:
                master = d
                break
        if master is None:
            for d in self.decks.values():
                if getattr(d, "_native_bpm", 0) > 0:
                    master = d
                    break
        # Use native BPM from beatgrid for accurate sync
        mbpm = getattr(master, "_native_bpm", 0) or (master.track.get("bpm") if master and master.track else 0)
        dbpm = getattr(deck, "_native_bpm", 0) or (deck.track.get("bpm") if deck.track else 0)
        if master and master is not deck and mbpm and dbpm:
            deck.set_tempo(mbpm / dbpm)

    # ---- master ----
    def set_master_volume(self, v):
        self.master_volume = max(0.0, min(1.0, v))

    # ---- state snapshot ----
    def snapshot(self):
        return {
            "layer": self.layer,
            "active_pair": list(self.active_pair),
            "crossfader": self.crossfader,
            "master_volume": self.master_volume,
            "decks": {did: self.decks[did].state() for did in ("A", "B", "C", "D")},
        }

    # ---- lifecycle ----
    def stop_all(self):
        for d in self.decks.values():
            d.stop()

    def _emit(self, evt):
        if self.callback:
            try:
                self.callback(evt)
            except Exception:
                pass
