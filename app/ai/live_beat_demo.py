#!/usr/bin/env python
"""
DJ AI OS — Live Beat Studio Demo

Real-time beat generation with live parameter control.
Shows integration of BeatStudio streaming + Realtime AI Ear.
"""

import sys
import os
import time
import threading
import signal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.ai.beat_studio import BeatStudio
from app.ai.ai_ear_realtime import RealtimeAIEar, create_realtime_ear

try:
    import sounddevice as sd
    HAS_AUDIO = True
except Exception:
    HAS_AUDIO = False
    print("sounddevice not available - running in offline mode")


class LiveBeatSession:
    """
    Live beat generation session with real-time analysis.
    """

    def __init__(self, sample_rate=44100, chunk_size=1024):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size

        # Initialize components
        self.beat_studio = BeatStudio()
        self.ai_ear = RealtimeAIEar(sample_rate=sample_rate, chunk_size=chunk_size)

        # Audio stream
        self.stream = None
        self.running = False

        # Setup callbacks
        self.ai_ear.on_beat = self._on_beat
        self.ai_ear.on_analysis = self._on_analysis

        # Stream generator
        self._stream_gen = None

    def _on_beat(self, bpm):
        """Called when a beat is detected."""
        print(f"🎵 BEAT @ {bpm:.1f} BPM")

    def _on_analysis(self, analysis):
        """Called on each analysis frame."""
        # Print periodic status
        if analysis.frame_count % 20 == 0:
            print(f"\r📊 {analysis.bpm:.1f}BPM | "
                  f"Centroid:{analysis.spectral_centroid:.0f}Hz | "
                  f"Energy:{analysis.rms_energy:.3f} | "
                  f"Vocal:{'🎤' if analysis.vocal_present else '—'} | "
                  f"Key:{analysis.key} | "
                  f"DR:{analysis.dynamic_range:.1f}dB", end="", flush=True)

            # Show mix suggestions
            if analysis.suggested_eq:
                print(f" | EQ:{analysis.suggested_eq}", end="")
            if analysis.suggested_compression:
                print(f" | Comp:{analysis.suggested_compression}", end="")

    def start(self, initial_command: str = "128 BPM tech house beat"):
        """Start the live session."""
        print(f"\n🎛 Starting Live Beat Session")
        print(f"   Initial: {initial_command}")
        print(f"   Sample Rate: {self.sample_rate}Hz")
        print(f"   Chunk Size: {self.chunk_size}")
        print("-" * 60)

        # Start AI Ear
        self.ai_ear.start()

        # Start beat stream generator
        self._stream_gen = self.beat_studio.generate_stream(initial_command, self.chunk_size)

        # Start audio output
        if HAS_AUDIO:
            self.stream = sd.OutputStream(
                samplerate=self.sample_rate,
                blocksize=self.chunk_size,
                channels=1,
                dtype='float32',
                callback=self._audio_callback
            )
            self.stream.start()
        else:
            # Offline mode - just generate chunks
            self._offline_loop()

        self.running = True

        # Start interactive control thread
        self._control_thread = threading.Thread(target=self._control_loop, daemon=True)
        self._control_thread.start()

    def _audio_callback(self, outdata, frames, time_info, status):
        """Audio output callback - called from sounddevice thread."""
        if status:
            print(f"Audio status: {status}")

        try:
            chunk = next(self._stream_gen)
            outdata[:, 0] = chunk[:frames]
        except StopIteration:
            outdata.fill(0)
        except Exception as e:
            print(f"Stream error: {e}")
            outdata.fill(0)

    def _offline_loop(self):
        """Run without audio output (for testing)."""
        def loop():
            for i, chunk in enumerate(self._stream_gen):
                if not self.running:
                    break
                # Feed to AI Ear for analysis
                self.ai_ear.process_chunk(chunk)
                time.sleep(self.chunk_size / self.sample_rate)

        self._offline_thread = threading.Thread(target=loop, daemon=True)
        self._offline_thread.start()

    def _control_loop(self):
        """Interactive command loop."""
        print("\n🎮 LIVE CONTROLS:")
        print("  l <level>        - Master volume (0-2)")
        print("  m <ch> <0/1>     - Mute channel")
        print("  s <ch> <0/1>     - Solo channel")
        print("  f <ch> <freq>    - Filter cutoff (20-20000)")
        print("  p <ch> <ratio>   - Pitch (0.5-2.0)")
        print("  d <ch> <mult>    - Decay (0.1-5.0)")
        print("  bpm <value>      - Change BPM")
        print("  swing <value>    - Swing (0-0.5)")
        print("  gf <freq>        - Global filter")
        print("  new <command>    - New beat pattern")
        print("  q                - Quit")
        print("-" * 60)

        while self.running:
            try:
                cmd = input("> ").strip().split()
                if not cmd:
                    continue

                action = cmd[0].lower()

                if action == 'q':
                    self.stop()
                    break

                elif action == 'l' and len(cmd) == 2:
                    self.beat_studio.set_master_volume(float(cmd[1]))
                    print(f"Master volume: {float(cmd[1]):.2f}")

                elif action == 'm' and len(cmd) == 3:
                    self.beat_studio.set_channel_mute(cmd[1], cmd[2] == '1')
                    print(f"Channel {cmd[1]} muted: {cmd[2] == '1'}")

                elif action == 's' and len(cmd) == 3:
                    self.beat_studio.set_channel_solo(cmd[1], cmd[2] == '1')
                    print(f"Channel {cmd[1]} solo: {cmd[2] == '1'}")

                elif action == 'f' and len(cmd) == 3:
                    self.beat_studio.set_channel_filter(cmd[1], float(cmd[2]))
                    print(f"Channel {cmd[1]} filter: {float(cmd[2]):.0f}Hz")

                elif action == 'p' and len(cmd) == 3:
                    self.beat_studio.set_channel_pitch(cmd[1], float(cmd[2]))
                    print(f"Channel {cmd[1]} pitch: {float(cmd[2]):.2f}x")

                elif action == 'd' and len(cmd) == 3:
                    self.beat_studio.set_channel_decay(cmd[1], float(cmd[2]))
                    print(f"Channel {cmd[1]} decay: {float(cmd[2]):.2f}x")

                elif action == 'bpm' and len(cmd) == 2:
                    self.beat_studio.set_bpm(int(cmd[1]))
                    print(f"BPM: {cmd[1]}")

                elif action == 'swing' and len(cmd) == 2:
                    self.beat_studio.set_swing(float(cmd[1]))
                    print(f"Swing: {float(cmd[1]):.2f}")

                elif action == 'gf' and len(cmd) == 2:
                    self.beat_studio.set_global_filter(float(cmd[1]))
                    print(f"Global filter: {float(cmd[1]):.0f}Hz")

                elif action == 'new' and len(cmd) > 1:
                    new_cmd = ' '.join(cmd[1:])
                    print(f"Switching to: {new_cmd}")
                    self._stream_gen = self.beat_studio.generate_stream(new_cmd, self.chunk_size)

                elif action == 'help':
                    print("Commands: l, m, s, f, p, d, bpm, swing, gf, new, q")

                else:
                    print("Unknown command. Type 'help' for list.")

            except (EOFError, KeyboardInterrupt):
                self.stop()
                break
            except Exception as e:
                print(f"Error: {e}")

    def stop(self):
        """Stop the session."""
        print("\n🛑 Stopping...")
        self.running = False
        self.beat_studio.stop_stream()
        self.ai_ear.stop()

        if self.stream:
            self.stream.stop()
            self.stream.close()

        print("✅ Stopped")


def signal_handler(sig, frame):
    print("\n🛑 Interrupted")
    sys.exit(0)


def main():
    signal.signal(signal.SIGINT, signal_handler)

    print("=" * 60)
    print("🎛 DJ AI OS — LIVE BEAT STUDIO")
    print("=" * 60)
    print("\nAvailable genres:", list(BeatStudio().get_pattern_library().keys()))

    # Get initial command
    cmd = input("\nEnter beat command (or press Enter for default): ").strip()
    if not cmd:
        cmd = "128 BPM tech house beat with heavy kick"

    session = LiveBeatSession()
    try:
        session.start(cmd)
        # Keep main thread alive
        while session.running:
            time.sleep(0.5)
    except KeyboardInterrupt:
        session.stop()


if __name__ == "__main__":
    main()