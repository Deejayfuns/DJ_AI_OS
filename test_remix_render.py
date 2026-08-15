from app.ai.remix_lab import RemixLab
import os

lab = RemixLab()
track = {
    'name': 'Hadis - Ara Beni',
    'path': '',
    'bpm': 128,
    'camelot': '8A',
    'key': 'A minor'
}

print('Rendering MELODIC HOUSE remix (16 sec preview)...')
result = lab.render_remix_wav(track, target_style='MELODIC HOUSE', output_folder='DJ_REMIX_LAB', duration_seconds=16)
print('OK:', result['ok'])
print('WAV:', result['wav_path'])
print('Manifest:', result['manifest_path'])
print('Engine:', result['engine'])
print('Target BPM:', result['target_bpm'])
print('Vocal texture used:', result['vocal_texture_used'])
print()
print('File exists:', os.path.exists(result['wav_path']))
print('Size:', os.path.getsize(result['wav_path']) if os.path.exists(result['wav_path']) else 0, 'bytes')
