class BPMEngine:

    def detect_role(self, bpm):

        if bpm is None:
            return "UNKNOWN", 0.3

        if bpm < 115:
            return "WARMUP", 0.4

        elif bpm < 123:
            return "GROOVE", 0.7

        elif bpm < 128:
            return "PEAK", 0.9

        else:
            return "HIGH ENERGY", 1.0
