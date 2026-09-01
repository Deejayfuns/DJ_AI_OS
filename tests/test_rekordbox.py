"""
Headless tests for Rekordbox XML import.
"""

import os
import tempfile

from app.core.rekordbox_import import (
    RekordboxImporter, file_url_to_path, parse_cue_points, parse_beatgrid,
)

SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<DJ_PLAYLISTS Version="1.0.0">
  <PRODUCT Name="rekordbox" Version="6.8.5"/>
  <COLLECTION Entries="3">
    <TRACK>
      <Location>file:///C:/Users/X/Music/afro_house/Baobab.mp3</Location>
      <Name>Baobab</Name><Artist>Gianluca Colletti</Artist>
      <Genre>Afro House</Genre><Bpm>122.0</Bpm><Tonality>8A</Tonality>
      <Length>360000</Length>
      <CuePoints Count="2">1 0 0 0 0
2 60000 0 0 0</CuePoints>
      <BeatGrid>0 122.000000</BeatGrid>
    </TRACK>
    <TRACK>
      <Location>file:///C:/Users/X/Music/afro_house/Yama.mp3</Location>
      <Name>Yama By Night</Name><Artist>Hugel</Artist>
      <Bpm>122.0</Bpm><Tonality>7A</Tonality><Length>300000</Length>
    </TRACK>
    <TRACK>
      <Location>file:///C:/Users/X/Music/house/Deep.mp3</Location>
      <Name>Deep House</Name><Artist>Test</Artist>
      <Bpm>124.0</Bpm><Tonality>6A</Tonality><Length>280000</Length>
    </TRACK>
  </COLLECTION>
  <PLAYLISTS>
    <NODE Type="ROOT" Name="ROOT">
      <NODE Type="FOLDER" Name="Afro">
        <NODE Type="PLAYLIST" Name="Top 100">
          <TRACK Index="0"/><TRACK Index="1"/>
        </NODE>
      </NODE>
    </NODE>
  </PLAYLISTS>
</DJ_PLAYLISTS>
"""


def _parse():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "rb.xml")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(SAMPLE_XML)
        return RekordboxImporter().parse(path)


def test_file_url_conversion():
    # On any platform, Windows drive-letter paths return backslashes
    assert file_url_to_path("file:///C:/Users/X/Music/x.mp3") == "C:\\Users\\X\\Music\\x.mp3"
    assert file_url_to_path("file:///C:/Music/song%20name.mp3") == "C:\\Music\\song name.mp3"
    # Non-file URLs or paths without drive letters pass through (normalized)
    assert file_url_to_path("/plain/path.mp3") == "/plain/path.mp3"


def test_parse_collection():
    tracks, _ = _parse()
    assert len(tracks) == 3
    t = tracks[0]
    assert t["title"] == "Baobab"
    assert t["artist"] == "Gianluca Colletti"
    assert t["bpm"] == 122.0
    assert t["key"] == "8A"
    assert t["source"] == "rekordbox"


def test_parse_cues_and_grid():
    cues = parse_cue_points("1 0 0 0 0\n2 60000 0 0 0")
    assert cues[0]["time"] == 0.0
    assert cues[1]["time"] == 60.0
    grid = parse_beatgrid("0 122.000000")
    assert grid["bpm"] == 122.0
    assert grid["first_beat"] == 0.0


def test_parse_playlists():
    _, playlists = _parse()
    assert len(playlists) == 1
    assert playlists[0]["name"] == "ROOT/Afro/Top 100"
    assert playlists[0]["track_indexes"] == [0, 1]


def test_playlist_resolution():
    tracks, playlists = _parse()
    imp = RekordboxImporter()
    pl_tracks = imp.playlist_tracks(playlists, 0, tracks)
    assert [t["title"] for t in pl_tracks] == ["Baobab", "Yama By Night"]
