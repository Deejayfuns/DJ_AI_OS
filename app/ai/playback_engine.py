import pygame
import time
import threading


class PlaybackEngine:

    def __init__(self, callback=None):

        pygame.mixer.init()

        self.callback = callback
        self.tracks = []
        self.index = 0
        self.playing = False

    def play(self, tracks):

        if not tracks:
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

                if self.callback:
                    self.callback(track)

                while pygame.mixer.music.get_busy():
                    if not self.playing:
                        return
                    time.sleep(0.2)

            except Exception as e:
                print("PLAYBACK ERROR:", e)

            self.index += 1

    def stop(self):

        self.playing = False
        pygame.mixer.music.stop()

    def next_track(self):

        pygame.mixer.music.stop()
        self.index += 1
