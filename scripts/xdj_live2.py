"""
Persistent live XDJ-RR capture with immediate logging.
Sends Pioneer MIDI init to the device then logs everything.
"""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join("DJ_EXPORTS", "xdj_live2.log")
os.makedirs("DJ_EXPORTS", exist_ok=True)

with open(OUT, "w", encoding="utf-8") as fh:
    def log(s):
        fh.write(f"[{time.time():.1f}] {s}\n")
        fh.flush()

    try:
        import mido
        midi_in = mido.open_input("Pioneer DJ XDJ-RR MIDI 1")
        # send init to output port (some controllers need a poke)
        try:
            midi_out = mido.open_output("Pioneer DJ XDJ-RR MIDI 2")
            for cc in (1, 2, 3, 4, 5):
                midi_out.send(mido.Message("control_change", channel=0,
                                           control=cc, value=0))
            midi_out.send(mido.Message("program_change", channel=0, program=0))
            log("MIDI init sent to device")
            midi_out.close()
        except Exception as e:
            log(f"MIDI out fail: {e}")
        log("LISTENING... move jog/buttons/pads/faders NOW (run until stopped)")
        while True:
            for msg in midi_in.iter_pending():
                if msg.type == "control_change":
                    log(f"CC ch{msg.channel} ctrl={msg.control} val={msg.value}")
                elif msg.type == "note_on":
                    log(f"NOTE_ON ch{msg.channel} note={msg.note} vel={msg.velocity}")
                elif msg.type == "note_off":
                    log(f"NOTE_OFF ch{msg.channel} note={msg.note}")
                elif msg.type == "pitchwheel":
                    log(f"PITCHWHEEL ch{msg.channel} pitch={msg.pitch}")
                else:
                    log(f"OTHER {msg}")
            time.sleep(0.01)
    except Exception as e:
        log(f"FATAL: {e}")
