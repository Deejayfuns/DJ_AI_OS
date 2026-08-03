"""
Live performance test utilities.
- `LivePerformanceTester` can run a simple MIDI loopback latency test if `mido` is available.
- Falls back to a Python scheduling latency probe otherwise.
"""
import time
import logging

try:
    import mido
except Exception:
    mido = None

logger = logging.getLogger("live_mode")


class LivePerformanceTester:
    def __init__(self, midi_port_name=None):
        self.midi_port_name = midi_port_name
        self.outport = None
        self.inport = None
        if mido:
            try:
                if midi_port_name:
                    self.outport = mido.open_output(midi_port_name)
                    self.inport = mido.open_input(midi_port_name)
                else:
                    names = mido.get_output_names()
                    if names:
                        self.outport = mido.open_output(names[0])
                    inames = mido.get_input_names()
                    if inames:
                        self.inport = mido.open_input(inames[0])
            except Exception:
                logger.exception("Failed to open MIDI ports for live tester")

    def midi_loopback_latency(self, messages=20, delay=0.05):
        """Send timestamped note_on messages and wait for the same on input to measure roundtrip.
        Returns list of latencies in seconds.
        """
        if not mido or not self.outport or not self.inport:
            raise RuntimeError("MIDI ports not available for loopback test")

        latencies = []
        received = {}

        def on_msg(msg):
            try:
                if hasattr(msg, 'time'):
                    # ignore timing-only messages
                    pass
                key = (msg.type, getattr(msg, 'note', None))
                if key in sent_map:
                    sent_ts = sent_map.pop(key)
                    received[key] = time.time() - sent_ts
            except Exception:
                logger.exception("on_msg fail")

        # attach temporary iterator
        iterator = self.inport.iter_pending

        sent_map = {}
        for i in range(messages):
            note = 60 + (i % 12)
            key = ("note_on", note)
            sent_map[key] = time.time()
            self.outport.send(mido.Message('note_on', note=note, velocity=100))
            # poll for replies for a short window
            start = time.time()
            while time.time() - start < 0.5:
                for msg in iterator():
                    on_msg(msg)
                if key not in sent_map:
                    break
                time.sleep(0.002)
            if key in sent_map:
                # missed
                latencies.append(None)
                sent_map.pop(key, None)
            else:
                latencies.append(received.get(key))
            time.sleep(delay)

        return latencies

    def scheduling_latency_probe(self, iterations=1000):
        """Measure Python scheduling jitter by sleeping for a fixed interval and recording drift."""
        interval = 0.01
        deltas = []
        next_time = time.time() + interval
        for i in range(iterations):
            now = time.time()
            sleep_time = max(0, next_time - now)
            time.sleep(sleep_time)
            actual = time.time()
            deltas.append(actual - next_time)
            next_time += interval
        return deltas


if __name__ == '__main__':
    t = LivePerformanceTester()
    try:
        print('Scheduling probe sample:', t.scheduling_latency_probe(100)[:5])
    except Exception as e:
        print('Probe failed:', e)
