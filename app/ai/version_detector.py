"""Detect track version type from filename.

Version intelligence helps the duplicate system distinguish between:
- Same song, different encode (EXACT_DUPLICATE → quarantine one)
- Same song, different version (VERSION_DUPLICATE → keep both)
- Creative rework (REMIK → always keep separately)
"""

import re


VERSION_PATTERNS = {
    "EXTENDED": [
        "extended", "ext mix", "extended mix", "extended version",
    ],
    "RADIO_EDIT": [
        "radio edit", "radio mix", "single edit", "single version",
    ],
    "CLUB_MIX": [
        "club mix", "club edit", "club version",
    ],
    "REMIK": [
        "remix", "rmx", "rework", "reconstructed", "flip",
    ],
    "ACAPELLA": [
        "acapella", "acappella", "vocal", "vocals only",
    ],
    "INSTRUMENTAL": [
        "instrumental", "inst", "dub", "dub mix",
    ],
    "LIVE": [
        "live", "recorded live", "live at", "live mix",
    ],
    "Piano_VER": [
        "piano version", "piano mix",
    ],
}

# Same song family — these are the same track in different versions,
# not creative reworks. Keep both, don't quarantine.
SAME_SONG_FAMILIES = {
    frozenset({"ORIGINAL", "EXTENDED", "RADIO_EDIT", "CLUB_MIX", "Piano_VER"}),
}

# Creative reworks — always keep separately.
CREATIVE_WORKS = {"REMIK", "ACAPELLA", "INSTRUMENTAL", "LIVE"}


def detect_version(filename):
    """Detect version type from a track filename.

    Returns a string like "EXTENDED", "REMIK", "ACAPELLA", or "ORIGINAL"
    (if no specific version pattern matches).
    """
    if not filename:
        return "ORIGINAL"

    name = _clean_text(filename)

    for version_type, patterns in VERSION_PATTERNS.items():
        for pattern in patterns:
            if pattern in name:
                return version_type

    return "ORIGINAL"


def are_same_song_version(type_a, type_b):
    """Return True if two version types represent the same song.

    Original + Extended + Radio Edit + Club Mix = same song.
    Remix / Acapella / Instrumental = different creative work.
    """
    if type_a == type_b:
        return True

    if type_a in CREATIVE_WORKS or type_b in CREATIVE_WORKS:
        return False

    for family in SAME_SONG_FAMILIES:
        if type_a in family and type_b in family:
            return True

    return False


def _clean_text(text):
    """Normalize filename for pattern matching."""
    text = text.lower()
    text = re.sub(r"[_\-\(\)\[\]]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
