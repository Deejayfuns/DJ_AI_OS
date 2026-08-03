"""Track DNA — unique visual fingerprint for each track.

Every track gets a unique color barcode based on its audio DNA:
- Energy → hue position
- Brightness → saturation
- Danceability → bar width
- Vocal risk → stripe pattern
- Drop strength → accent marks
- Heart score → warmth

The DNA is a compact visual identifier — like a genetic code for music.
Used in the track table as a colorful mini-barcode and in the Library Map.
"""


def generate_dna(track):
    """Generate a DNA barcode from track audio features.

    Returns a list of (color_hex, width_pct) tuples representing
    the track's unique visual DNA pattern.
    """
    energy = float(track.get("energy", 0.5) or 0.5)
    brightness = float(track.get("brightness", 0.5) or 0.5)
    danceability = float(track.get("danceability", 0.5) or 0.5)
    vocal_risk = float(track.get("vocal_risk", 0.2) or 0.2)
    drop = float(track.get("drop_strength", 0.3) or 0.3)
    heart = float(track.get("heart_score", 0.5) or 0.5)
    roughness = float(track.get("roughness", 0.3) or 0.3)

    bars = []

    # Bar 1: Energy band (large)
    hue = energy_to_hue(energy)
    bars.append((hue, 3))

    # Bar 2: Brightness
    sat = brightness_to_color(brightness)
    bars.append((sat, 2))

    # Bar 3: Danceability pattern
    d_color = "#00FFA3" if danceability > 0.7 else "#22D3FF" if danceability > 0.4 else "#6F7C8A"
    bars.append((d_color, 2 if danceability > 0.6 else 1))

    # Bar 4: Vocal risk indicator
    if vocal_risk > 0.5:
        bars.append(("#FF3DF2", 1))  # High vocal = magenta
    elif vocal_risk > 0.3:
        bars.append(("#FFB020", 1))  # Medium = yellow
    else:
        bars.append(("#00C896", 1))  # Low = green

    # Bar 5: Drop strength
    drop_color = "#FF4D6D" if drop > 0.6 else "#9B5CFF" if drop > 0.3 else "#3A1D78"
    bars.append((drop_color, 2 if drop > 0.5 else 1))

    # Bar 6: Heart warmth
    heart_color = "#FF3DF2" if heart > 0.7 else "#FFB020" if heart > 0.4 else "#2979FF"
    bars.append((heart_color, 1))

    # Bar 7: Roughness texture
    rough_color = "#EAF2FF" if roughness > 0.6 else "#6F7C8A"
    bars.append((rough_color, 1))

    # Bar 8: Energy band 2 (mirrors energy for visual symmetry)
    bars.append((hue, 2))

    return bars


def energy_to_hue(energy):
    """Map energy (0-1) to a color hue."""
    if energy > 0.8:
        return "#FF3DF2"  # Magenta — peak energy
    if energy > 0.6:
        return "#9B5CFF"  # Purple — high energy
    if energy > 0.4:
        return "#00FFA3"  # Mint — medium energy
    if energy > 0.2:
        return "#22D3FF"  # Cyan — low energy
    return "#6F7C8A"  # Gray — very low


def brightness_to_color(brightness):
    """Map brightness (0-1) to a color."""
    if brightness > 0.7:
        return "#EAF2FF"  # Bright white
    if brightness > 0.5:
        return "#22D3FF"  # Blue
    if brightness > 0.3:
        return "#9B5CFF"  # Purple
    return "#0D1020"  # Dark


def dna_to_string(dna):
    """Convert DNA to a compact string representation."""
    return "|".join(f"{color}:{width}" for color, width in dna)


def dna_similarity(dna_a, dna_b):
    """Calculate similarity between two DNA barcodes (0-1)."""
    if not dna_a or not dna_b:
        return 0.0

    min_len = min(len(dna_a), len(dna_b))
    matches = 0
    total = 0

    for i in range(min_len):
        c_a, w_a = dna_a[i]
        c_b, w_b = dna_b[i]
        total += 1
        if c_a == c_b and w_a == w_b:
            matches += 1

    return matches / max(1, total)
