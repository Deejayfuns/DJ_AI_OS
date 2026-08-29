"""
DJ AI OS — Song Vault (Premium Module)

High-quality music acquisition engine for the top package tier.

Give it a single track name or a .txt playlist (one track per line,
`#` for comments) and it researches the web, resolves the best available
audio source, and downloads it losslessly or near-losslessly:

  - MP3 320 kbps  (best quality lossy — club standard)
  - WAV 16-bit    (lossless master)

Built on yt-dlp + ffmpeg. Designed for content you have the right to
use (your own productions, live sets, edits, Creative Commons, royalty-
free material). Always respect the copyright of the sources it searches.

API:
    vault = SongVault(out_dir="DJ_SONG_VAULT", fmt="mp3_320")
    vault.set_format("wav")
    queries = vault.parse_playlist("tracks.txt")     # -> ["artist - title", ...]
    result = vault.search_and_download("artist - title", progress=cb)
    results = vault.download_batch(queries, progress=cb)
"""

import os
import threading

from app.core.paths import get_song_vault_dir

try:
    import yt_dlp
    HAS_YTDLP = True
except Exception:
    HAS_YTDLP = False


# (preferredcodec, preferredquality, final_extension)
FORMAT_SPECS = {
    "mp3_320": {"codec": "mp3", "quality": "320", "ext": "mp3", "label": "MP3 320 kbps"},
    "wav":     {"codec": "wav", "quality": "0",   "ext": "wav", "label": "WAV (lossless)"},
}


class SongVault:
    """Search + download engine backed by yt-dlp."""

    def __init__(self, out_dir=None, fmt="mp3_320"):
        self.out_dir = out_dir or str(get_song_vault_dir())
        self.fmt = fmt if fmt in FORMAT_SPECS else "mp3_320"
        self.history = []
        self._lock = threading.Lock()
        try:
            os.makedirs(self.out_dir, exist_ok=True)
        except Exception:
            pass

    # ----------------------------------------------------------
    # CONFIG
    # ----------------------------------------------------------
    def set_output_dir(self, path):
        path = os.path.abspath(path)
        try:
            os.makedirs(path, exist_ok=True)
        except Exception:
            pass
        self.out_dir = path

    def set_format(self, fmt):
        if fmt in FORMAT_SPECS:
            self.fmt = fmt

    def spec(self):
        return FORMAT_SPECS[self.fmt]

    # ----------------------------------------------------------
    # PLAYLIST PARSING
    # ----------------------------------------------------------
    @staticmethod
    def parse_playlist(txt_path):
        """Parse a txt playlist: one track per line, '#' comments ignored."""
        queries = []
        with open(txt_path, encoding="utf-8", errors="replace") as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                queries.append(line)
        return queries

    # ----------------------------------------------------------
    # YT-DLP OPTIONS
    # ----------------------------------------------------------
    def _build_opts(self, progress_hook=None, skip_download=False):
        spec = self.spec()
        opts = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(self.out_dir, "%(title).120s [%(id)s].%(ext)s"),
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "overwrites": False,
            "no_color": True,
            "noprogress": True,
            "ignoreerrors": False,
            "concurrent_fragment_downloads": 4,
            "extractor_args": {"youtube": {"player_client": ["android"], "skip": ["webpage"]}},
        }
        if not skip_download:
            post = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": spec["codec"],
                "preferredquality": spec["quality"],
            }]
            opts["postprocessors"] = post
            if progress_hook:
                opts["progress_hooks"] = [progress_hook]
        return opts

    # ----------------------------------------------------------
    # RESOLVE / PRE-CHECK
    # ----------------------------------------------------------
    def _resolve(self, query):
        """Return the first search-hit video info dict (no download)."""
        if not HAS_YTDLP:
            return None
        opts = self._build_opts(skip_download=True)
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info("ytsearch1:%s" % query, download=False)
        entries = info.get("entries") or [info]
        if not entries:
            return None
        # Skip playlist objects with no actual video entries
        first = entries[0]
        if first.get("_type") == "playlist" and not first.get("entries"):
            return None
        return first

    @staticmethod
    def _final_path(ydl, video, ext):
        """Predict the post-processed audio path for a resolved video."""
        base = ydl.prepare_filename(video)
        return os.path.splitext(base)[0] + "." + ext

    # ----------------------------------------------------------
    # SINGLE TRACK
    # ----------------------------------------------------------
    def search_and_download(self, query, progress=None):
        """Search + download + convert one track.

        progress(dict): {"stage": "searching"|"downloading"|"converting",
                         "query", "percent" (str, downloading only),
                         "speed" (str, downloading only)}
        Returns dict with keys: ok, query, title, path, size, duration,
        skipped (bool), error (str, when not ok).
        """
        query = (query or "").strip()
        if not query:
            return {"ok": False, "query": query, "error": "Empty query"}

        if not HAS_YTDLP:
            return {"ok": False, "query": query,
                    "error": "yt-dlp not installed — run: pip install yt-dlp"}

        spec = self.spec()
        status = {"stage": "searching", "query": query}
        if progress:
            progress(dict(status))

        try:
            with yt_dlp.YoutubeDL(self._build_opts(skip_download=True)) as probe:
                resolved = self._resolve(query)
                if not resolved:
                    return {"ok": False, "query": query,
                            "error": "No result found for: %s" % query}

                final = self._final_path(probe, resolved, spec["ext"])
                title = resolved.get("title") or query

                # already downloaded?
                if os.path.exists(final) and os.path.getsize(final) > 0:
                    result = {"ok": True, "query": query, "title": title,
                              "path": final, "size": os.path.getsize(final),
                              "duration": resolved.get("duration"), "skipped": True}
                    self._record(result)
                    return result

            # download + convert
            def hook(d):
                if d.get("status") == "downloading":
                    status["stage"] = "downloading"
                    status["percent"] = (d.get("_percent_str") or "").strip()
                    status["speed"] = (d.get("_speed_str") or "").strip()
                elif d.get("status") == "finished":
                    status["stage"] = "converting"
                if progress:
                    progress(dict(status))

            with yt_dlp.YoutubeDL(self._build_opts(hook)) as ydl:
                info = ydl.extract_info("ytsearch1:%s" % query, download=True)
                entries = info.get("entries") or [info]
                video = entries[0]
                final = self._final_path(ydl, video, spec["ext"])
                if not os.path.exists(final):
                    # fallback: scan dir for most recent audio file
                    final = self._newest_in_dir()

            size = os.path.getsize(final) if os.path.exists(final) else 0
            result = {"ok": True, "query": query,
                      "title": video.get("title") if video else query,
                      "path": final, "size": size,
                      "duration": video.get("duration") if video else None,
                      "skipped": False}
            self._record(result)
            return result

        except Exception as exc:
            return {"ok": False, "query": query, "error": str(exc)}

    def _newest_in_dir(self):
        try:
            files = [os.path.join(self.out_dir, f)
                     for f in os.listdir(self.out_dir)
                     if os.path.isfile(os.path.join(self.out_dir, f))]
            return max(files, key=os.path.getmtime) if files else None
        except Exception:
            return None

    def _record(self, result):
        with self._lock:
            self.history.append(result)

    # ----------------------------------------------------------
    # BATCH
    # ----------------------------------------------------------
    def download_batch(self, queries, progress=None):
        """Sequentially download a list of queries. progress called with
        {"stage": "batch", "index", "total", "query", "result"} per item."""
        results = []
        total = len(queries)
        for i, q in enumerate(queries):
            def p(d):
                if progress:
                    progress({"stage": "batch", "index": i, "total": total,
                              "query": q, "status": d})
            r = self.search_and_download(q, progress=p)
            results.append(r)
            if progress:
                progress({"stage": "batch", "index": i, "total": total,
                          "query": q, "done": True, "result": r})
        return results


# Convenience for CLI-style use: python app/ai/song_vault.py tracks.txt [mp3_320|wav]
if __name__ == "__main__":
    import sys
    src = sys.argv[1] if len(sys.argv) > 1 else ""
    fmt = sys.argv[2] if len(sys.argv) > 2 else "mp3_320"
    vault = SongVault(fmt=fmt)
    queries = vault.parse_playlist(src) if src.endswith(".txt") else [src]
    if not queries:
        print("Usage: song_vault.py tracks.txt [mp3_320|wav]   | one track per line")
        sys.exit(1)

    def report(d):
        st = d.get("status")
        if st and st.get("stage") == "downloading":
            print("  %-12s %s  %s" % (d.get("query", "")[:24],
                                      st.get("percent", ""),
                                      st.get("speed", "")), end="\r")
        elif st and st.get("stage") == "converting":
            print("  %-12s converting..." % d.get("query", "")[:24])

    for r in vault.download_batch(queries, progress=report):
        tag = "SKIP" if r.get("skipped") else ("OK  " if r.get("ok") else "FAIL")
        size_mb = r.get("size", 0) / (1024 * 1024)
        print("%s %-40s %6.2f MB  %s" % (
            tag, r.get("title", r.get("query", ""))[:40], size_mb,
            r.get("path", r.get("error", ""))))
