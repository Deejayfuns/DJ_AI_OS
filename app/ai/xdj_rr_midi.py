"""
DJ AI OS — Pioneer XDJ-RR MIDI mapping (calibrated from the live unit)

Channel layout (confirmed by live capture):
    ch0 = Deck A   ch2 = Deck C   (physical deck 1, layer toggle)
    ch1 = Deck B   ch3 = Deck D   (physical deck 2, layer toggle)
    ch4 = Mixer (EQ, faders, crossfader)
    ch5 = Utility buttons

Controls (confirmed):
    Jog wheel   : CC 16 (relative ticks) + CC 34 (high-res fine)
                  absolute position: CC 0 (coarse) + CC 32 (fine, 14-bit)
    Jog touch   : CC 100 / CC 102
    Transport   : NOTE messages (vel 127 press / 0 release)
                  PLAY = note 0, CUE = note 32 (per deck channel)
                  (sync/pads/tempo/EQ/crossfader still calibrating)

A translated event looks like:
    {"type": "play", "deck": "A"}
    {"type": "cue",  "deck": "A"}
    {"type": "jog",  "deck": "A", "delta": int}
"""

# MIDI channel -> logical deck (physical layer 1)
CHANNEL_TO_DECK = {0: "A", 1: "B", 2: "C", 3: "D"}

# NOTE -> action (per deck channel). Calibrated so far:
NOTE_MAP = {
    0: "play",
    1: "shift",   # utility / shift (tentative)
    31: "unknown", # appears twice, need to identify
    32: "cue",    # confirmed: CUE button on all decks
    81: "sync",   # confirmed: SYNC button on all decks
}

# Pad channels (utility channels)
PAD_CHANNEL_LOW = 5   # pads 1-4 (notes 0-3)
PAD_CHANNEL_HIGH = 6  # pads 5-8 (notes 0-3)

# CC -> action for mixer/deck controls (per channel or ch4)
CC_MAP = {
    # Deck-level (ch0-ch3) - 14-bit faders use coarse+fine pairs
    33: "tempo",      # tempo fader coarse (ch0-ch3)
    48: "tempo_fine", # tempo fader fine   (ch0-ch3)
    # EQ (ch0-ch3) - Pioneer standard
    9: "eq_hi",       # HI EQ
    10: "eq_mid",     # MID EQ
    11: "eq_low",     # LOW EQ (but ch4 ctrl=11 is crossfader)
    # Filter (ch0-ch3)
    12: "filter",     # Filter knob
    # Channel fader (ch0-ch3) - standard MIDI volume
    7: "fader",       # Channel fader (deck level)
    # Mixer (ch4)
    11: "crossfader", # Crossfader (ch4)
    # Channel faders on mixer (ch4) - Pioneer often uses 41/42/43/44
    41: "fader_ch1",  # Mixer ch1 fader
    42: "fader_ch2",  # Mixer ch2 fader
    43: "fader_ch3",  # Mixer ch3 fader
    44: "fader_ch4",  # Mixer ch4 fader
}

# CC jog: 16 = relative delta, 34 = high-res fine delta
JOG_DELTA_CC = 16
JOG_FINE_CC = 34

# Jog touch indicators
JOG_TOUCH_CC = 100
JOG_VEL_CC = 102


# ============================================================
# CALIBRATION HELPER
# ============================================================
# Run this in a REPL while the capture script is running:
#   from app.ai.xdj_rr_midi import Calibrator, translate
#   cal = Calibrator()
#   # ... when a MIDI msg arrives ...
#   cal.learn(msg, "cue")  # or "sync", "pad1", "pad2", "tempo", "eq_hi", "eq_mid", "eq_low", "filter", "crossfader", "fader_ch1", "shift"
#   cal.save()  # writes to this file

class Calibrator:
    """Helper to learn MIDI mappings from live capture."""

    NOTE_LABELS = {"play", "cue", "sync", "pad1", "pad2", "pad3", "pad4",
                   "pad5", "pad6", "pad7", "pad8", "shift"}
    CC_LABELS = {"tempo", "eq_hi", "eq_mid", "eq_low", "filter",
                 "crossfader", "fader_ch1", "fader_ch2", "shift"}

    def __init__(self):
        self.learned_notes = {}
        self.learned_ccs = {}

    def learn(self, msg, label):
        """Learn a mapping from a mido Message and a label."""
        if label not in self.NOTE_LABELS and label not in self.CC_LABELS:
            print(f"Unknown label: {label}. Valid: {self.NOTE_LABELS | self.CC_LABELS}")
            return

        ch = getattr(msg, "channel", None)
        deck = CHANNEL_TO_DECK.get(ch)

        if msg.type == "note_on":
            note = msg.note
            self.learned_notes[label] = {"note": note, "channel": ch, "deck": deck}
            print(f"Learned NOTE: {label} -> note={note} ch={ch} deck={deck}")
        elif msg.type == "control_change":
            cc = msg.control
            self.learned_ccs[label] = {"cc": cc, "channel": ch, "deck": deck}
            print(f"Learned CC: {label} -> cc={cc} ch={ch} deck={deck}")
        else:
            print(f"Unsupported msg type for learning: {msg.type}")

    def save(self):
        """Print Python code to paste into this module."""
        print("\n# === PASTE INTO NOTE_MAP ===")
        for label, info in self.learned_notes.items():
            note = info["note"]
            print(f"    {note}: \"{label}\",")

        print("\n# === PASTE INTO CC_MAP ===")
        for label, info in self.learned_ccs.items():
            cc = info["cc"]
            deck_note = f" (deck {info['deck']})" if info["deck"] else " (mixer ch4)"
            print(f"    {cc}: \"{label}\",  # {deck_note}")

        # Also return dicts for programmatic use
        return self.learned_notes, self.learned_ccs


def translate(msg, layer=1):
    """Translate a mido Message from the XDJ-RR into an event dict (or None).

    Args:
        msg: mido Message
        layer: current layer (1 = decks A/B, 2 = decks C/D)
    """
    ch = getattr(msg, "channel", None)
    deck = CHANNEL_TO_DECK.get(ch)
    if msg.type == "control_change":
        cc, val = msg.control, msg.value
        if cc == JOG_DELTA_CC and deck and val != 64:
            # relative tick: 64 = center (no movement), +/- = direction
            delta = val - 64
            return {"type": "jog", "deck": deck, "delta": delta}
        # 14-bit tempo fader (coarse CC33 + fine CC48)
        if cc == 33 and deck:
            # Store coarse value, will combine with fine when it arrives
            return {"type": "tempo_coarse", "deck": deck, "value": val}
        if cc == 48 and deck:
            # Combine coarse + fine into 14-bit value (0-16383)
            return {"type": "tempo_fine", "deck": deck, "value": val}
        # CC mapping for mixer/deck controls
        action = CC_MAP.get(cc)
        if action and deck:
            return {"type": action, "deck": deck, "value": val / 127.0}
        if action and ch == 4:  # mixer channel
            return {"type": action, "deck": "mixer", "value": val / 127.0}
        return None
    if msg.type == "note_on" and msg.velocity == 127:
        # Pad channels (ch5/ch6) - map to active layer decks
        if ch in (PAD_CHANNEL_LOW, PAD_CHANNEL_HIGH):
            return _pad_event(msg, layer)
        # Deck channels (ch0-ch3)
        if deck:
            action = NOTE_MAP.get(msg.note)
            if action == "play":
                return {"type": "play", "deck": deck}
            if action == "cue":
                return {"type": "cue", "deck": deck}
            if action == "sync":
                return {"type": "sync", "deck": deck}
            if action and action.startswith("pad"):
                pad = int(action[3:])
                return {"type": "pad", "deck": deck, "pad": pad}
            if action == "shift":
                return {"type": "shift", "deck": deck, "pressed": True}
    if msg.type == "note_off" and deck:
        action = NOTE_MAP.get(msg.note)
        if action == "shift":
            return {"type": "shift", "deck": deck, "pressed": False}
    return None


def _pad_event(msg, layer):
    """Translate pad note from ch5/ch6 to deck+pad number."""
    note = msg.note
    if msg.channel == PAD_CHANNEL_LOW:       # pads 1-4
        pad_num = note + 1                    # note 0->pad1, 1->pad2, 2->pad3, 3->pad4
    elif msg.channel == PAD_CHANNEL_HIGH:    # pads 5-8
        pad_num = note + 5                    # note 0->pad5, 1->pad6, 2->pad7, 3->pad8
    else:
        return None
    # Map to current layer's decks
    if layer == 1:
        deck_left, deck_right = "A", "B"
    else:
        deck_left, deck_right = "C", "D"
    # Pads 1-4 -> left deck, 5-8 -> right deck
    deck = deck_left if pad_num <= 4 else deck_right
    return {"type": "pad", "deck": deck, "pad": pad_num}