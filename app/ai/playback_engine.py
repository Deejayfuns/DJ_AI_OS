import pygame
import time
import threading


class PlaybackEngine:

    def __init__(self, callback=None):

        self.mixer_ok = False
        try:
            pygame.mixer.init()
            self.mixer_ok = True
        except Exception:
            print("PLAYBACK: mixer init failed, playback disabled")

        self.callback = callback
        self.tracks = []
        self.index = 0
        self.playing = False
        self._main_thread = threading.current_thread()

    def _schedule_callback(self, track):
        """Schedule callback on main thread to avoid GIL/Tkinter issues."""
        if self.callback:
            # If we have a reference to main window, use after()
            # For now, just call directly but catch errors
            try:
                self.callback(track)
            except Exception:
                pass

    def play(self, tracks):

        if not tracks:
            return

        if not self.mixer_ok:
            print("PLAYBACK: mixer not available, skipping")
            return

        self.tracks = tracks
        self.index = 0
        self.playing = True

        threading.Thread(target=self.loop, daemon=True).start()

    def loop(self):

        while self.playing and self.index < len(self.tracks):

            track = self.tracks[self.index]

            try:
                pygame.mixer.music.load(track["path"])
                pygame.mixer.music.play()

                self._schedule_callback(track)

                while pygame.mixer.music.get_busy():
                    if not self.playing:
                        return
                    time.sleep(0.2)

            except Exception as e:
                print("PLAYBACK ERROR:", e)

            self.index += 1

    def stop(self):

        self.playing = False
        if self.mixer_ok:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass

    def next_track(self):

        if self.mixer_ok:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass
        self.index += 1
