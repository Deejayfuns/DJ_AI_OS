"""
Capture XDJ-RR MIDI + HID activity to a log file.
Run this, then move controls on the XDJ-RR for ~20 seconds.
"""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

OUT = os.path.join("DJ_EXPORTS", "xdj_capture.log")
os.makedirs("DJ_EXPORTS", exist_ok=True)

lines = []
def log(s):
    lines.append(f"[{time.time():.2f}] {s}")

# 1) HID handshake + read
try:
    import hid
    vid, pid = 0x2B73, 0x0027
    dev = hid.device()
    dev.open(vid, pid)
    dev.set_nonblocking(1)
    dev.write(bytes([0x01]) + b"\x00" * 63)
    log("HID opened + handshake sent")
    hid_ok = True
except Exception as e:
    log(f"HID open fail: {e}")
    hid_ok = False

# 2) MIDI listen
try:
    import mido
    port = mido.open_input("Pioneer DJ XDJ-RR MIDI 1")
    log("MIDI port open")
    midi_ok = True
except Exception as e:
    log(f"MIDI open fail: {e}")
    midi_ok = False

log("CAPTURING 20s — MOVE CONTROLS NOW")
start = time.time()
while time.time() - start < 20:
    if hid_ok:
        raw = dev.read(64)
        while raw:
            log(f"HID r{raw[0]}: {list(raw[:16])}")
            raw = dev.read(64)
    if midi_ok:
        for msg in port.iter_pending():
            log(f"MIDI {msg}")
    time.sleep(0.01)

if hid_ok:
    dev.close()
if midi_ok:
    port.close()

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print(f"done — {len(lines)} lines -> {OUT}")
