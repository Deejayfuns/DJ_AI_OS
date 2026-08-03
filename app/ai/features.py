from mutagen.mp3 import MP3
from mutagen.easyid3 import EasyID3

def extract_features(path):
    bpm = None
    genre = None
    artist = None
    title = None

    try:
        audio = MP3(path, ID3=EasyID3)

        if "bpm" in audio:
            bpm = int(float(audio["bpm"][0]))

        genre = audio.get("genre", ["unknown"])[0]
        artist = audio.get("artist", ["unknown"])[0]
        title = audio.get("title", ["unknown"])[0]

    except:
        pass

    return {
        "path": path,
        "bpm": bpm,
        "genre": genre,
        "artist": artist,
        "title": title
    }
