"""
Long capture of XDJ-RR MIDI + HID. Run, then move controls for 60s.
Logs unique message signatures so we can map the protocol.
"""
import sys, os, time, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join("DJ_EXPORTS", "xdj_live.log")

def log(s, fh):
    fh.write(f"[{time.time():.1f}] {s}\n")
    fh.flush()

os.makedirs("DJ_EXPORTS", exist_ok=True)
with open(OUT, "w", encoding="utf-8") as fh:
    # HID
    hid_ok = False
    try:
        import hid
        dev = hid.device()
        dev.open(0x2B73, 0x0027)
        dev.set_nonblocking(1)
        dev.write(bytes([0x01]) + b"\x00" * 63)
        time.sleep(0.3)
        hid_ok = True
        log("HID open + handshake OK", fh)
    except Exception as e:
        log(f"HID fail: {e}", fh)

    # MIDI
    midi_ok = False
    try:
        import mido
        midi_in = mido.open_input("Pioneer DJ XDJ-RR MIDI 1")
        midi_ok = True
        log("MIDI IN open OK", fh)
    except Exception as e:
        log(f"MIDI fail: {e}", fh)

    log("NOW MOVE CONTROLS FOR 60s...", fh)
    start = time.time()
    midi_seen = {}
    hid_seen = {}
    while time.time() - start < 60:
        if midi_ok:
            for msg in midi_in.iter_pending():
                if msg.type == "control_change":
                    k = ("cc", msg.channel, msg.control, msg.value)
                elif msg.type in ("note_on", "note_off"):
                    k = ("note", msg.channel, msg.note, msg.velocity if msg.type == "note_on" else "off")
                elif msg.type == "pitchwheel":
                    k = ("pw", msg.channel, msg.pitch)
                else:
                    k = (msg.type, str(msg))
                midi_seen[k] = midi_seen.get(k, 0) + 1
        if hid_ok:
            raw = dev.read(64)
            while raw:
                key = (raw[0], tuple(raw[1:8]))
                hid_seen[key] = hid_seen.get(key, 0) + 1
                raw = dev.read(64)
        time.sleep(0.01)

    log("--- MIDI unique ---", fh)
    for k, n in sorted(midi_seen.items(), key=lambda x: -x[1]):
        log(f"  {n:4d}x {k}", fh)
    log("--- HID unique ---", fh)
    for k, n in sorted(hid_seen.items(), key=lambda x: -x[1]):
        log(f"  {n:4d}x r{k[0]} bytes{k[1]}", fh)
    log(f"TOTAL midi={sum(midi_seen.values())} hid={sum(hid_seen.values())}", fh)

    if hid_ok: dev.close()
    if midi_ok: midi_in.close()
print("done")
