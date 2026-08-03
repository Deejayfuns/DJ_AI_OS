from queue import Queue
from datetime import datetime


class TrackQueue:

    def __init__(self, memory_engine=None):

        self.queue = Queue()

        self.last_track = None
        self.transitions = []
        self.events = []

        # 🧠 NEW: memory hook
        self.memory = memory_engine

    def push(self, track):

        if self.last_track:

            transition = {
                "from": self.last_track["id"],
                "to": track["id"],
                "timestamp": str(datetime.now())
            }

            self.transitions.append(transition)

        self.last_track = track
        self.queue.put(track)

    def get(self):

        if self.queue.empty():
            return None

        track = self.queue.get()

        self.events.append({
            "type": "play",
            "track": track["id"],
            "timestamp": str(datetime.now())
        })

        return track

    # -------------------------
    # FEEDBACK SIGNALS
    # -------------------------

    def skip(self, track):

        self.events.append({
            "type": "skip",
            "track": track["id"],
            "timestamp": str(datetime.now())
        })

        # 🔥 negative learning
        if self.memory:
            self.memory.log_session({
                "tracks": [track],
                "transitions": [],
                "feedback": -1
            })

    def replay(self, track):

        self.events.append({
            "type": "replay",
            "track": track["id"],
            "timestamp": str(datetime.now())
        })

        # 🔥 positive learning
        if self.memory:
            self.memory.log_session({
                "tracks": [track],
                "transitions": [],
                "feedback": +1
            })

    def size(self):

        return self.queue.qsize()
