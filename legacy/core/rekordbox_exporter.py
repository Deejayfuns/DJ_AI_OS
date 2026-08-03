"""
Basic Rekordbox XML exporter skeleton.
Generates a minimal Rekordbox collection XML and playlists compatible with Rekordbox imports.
"""
import xml.etree.ElementTree as ET
from xml.dom import minidom
import os


def prettify_xml(elem):
    rough = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough)
    return reparsed.toprettyxml(indent="  ")


def export_collection(tracks, out_path):
    """tracks: list of dicts with keys id, location, title, artist, bpm, length"""
    root = ET.Element('DJ_PLAYLISTS', version='1.0')
    collection = ET.SubElement(root, 'COLLECTION')

    for t in tracks:
        entry = ET.SubElement(collection, 'TRACK', {
            'TrackID': str(t.get('id', '')),
            'Location': str(t.get('location', '')),
            'Title': str(t.get('title', '')),
            'Artist': str(t.get('artist', '')),
            'BPM': str(t.get('bpm', '0')),
            'Duration': str(t.get('length', '0')),
        })
        # optional cues/hotcues
        cues = t.get('cues') or []
        if cues:
            cues_el = ET.SubElement(entry, 'CUES')
            for c in cues:
                # c: dict with position (seconds), type ('HOT'|'CUE'), index
                attrs = {
                    'Position': str(c.get('position', 0)),
                    'Type': str(c.get('type', 'CUE')),
                    'Index': str(c.get('index', '0')),
                }
                ET.SubElement(cues_el, 'CUE', attrs)

    xml = prettify_xml(root)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(xml)

    return out_path


def export_playlist(name, tracks, out_path):
    root = ET.Element('DJ_PLAYLISTS', version='1.0')
    playlist = ET.SubElement(root, 'PLAYLIST', {'Name': name})
    for t in tracks:
        ET.SubElement(playlist, 'TRACKREF', {'TrackID': str(t.get('id', ''))})

    xml = prettify_xml(root)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(xml)

    return out_path


if __name__ == '__main__':
    # quick demo
    demo_tracks = [
        {'id': 1, 'location': '/music/track1.mp3', 'title': 'Track 1', 'artist': 'Artist A', 'bpm': 124, 'length': 180},
        {'id': 2, 'location': '/music/track2.mp3', 'title': 'Track 2', 'artist': 'Artist B', 'bpm': 126, 'length': 200},
    ]
    os.makedirs('exports', exist_ok=True)
    print(export_collection(demo_tracks, 'exports/rekordbox_collection.xml'))
    print(export_playlist('Top 2', demo_tracks, 'exports/top2_playlist.xml'))
