import os

class Scanner:
    def __init__(self):
        self.supported = (".mp3", ".wav")

    def scan(self, folder):
        files = []

        for root, _, fs in os.walk(folder):
            for f in fs:
                if f.lower().endswith(self.supported):
                    files.append(os.path.join(root, f))

        return files
