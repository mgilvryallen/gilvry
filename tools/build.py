"""Turn the stems/ folder into what Gilvry plays: loops/*.mp3 and loops/index.json.

Takes WAV, AIFF, FLAC, MP3, M4A/AAC, OGG/Opus or CAF, any sample rate or bit depth, mono or
stereo. Each stem is checked against the others' length, measured for loudness (so they can be
evened out in the app), and saved as MP3 with a little of its own end before it and its own
start after it. MP3s carry a sliver of silence at the start that differs by browser; with the
loop wrapped around itself, the app can cut out an exact, seamless loop whatever that sliver is.

Names: instrument_e1_mood_01.wav (energy 1 to 3, take number optional), for example
fiddle_e3_bright_01.wav. Settings are in gilvry.json.

python3 tools/build.py [out_dir]   (default: loops; needs ffmpeg)
"""
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

SR = 44100
PAD = 8192  # samples of wrap-around on each side
AUDIO = {'.wav', '.wave', '.aif', '.aiff', '.flac', '.mp3', '.m4a', '.aac', '.ogg', '.oga', '.opus', '.caf'}
NAME = re.compile(r'^([a-z0-9-]+)_e([123])_([a-z0-9-]+)(?:_(\d+))?$', re.I)
BUILD_VERSION = '1'  # bump to re-encode everything


def decode(path):
    probe = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'a:0', '-show_entries', 'stream=channels',
                            '-of', 'csv=p=0', str(path)], capture_output=True, text=True, check=True)
    channels = min(2, int(probe.stdout.strip() or 1))
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-f', 'f32le', '-ac', str(channels),
                          '-ar', str(SR), '-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype='<f4').reshape(-1, channels)


def loudness(audio):
    """Integrated loudness (LUFS), measured on the loop played twice so its start isn't a cold start."""
    twice = np.concatenate([audio, audio]).astype('<f4').tobytes()
    out = subprocess.run(['ffmpeg', '-v', 'info', '-nostats', '-f', 'f32le', '-ar', str(SR), '-ac', str(audio.shape[1]),
                          '-i', '-', '-af', 'ebur128', '-f', 'null', '-'], input=twice, capture_output=True).stderr.decode()
    found = re.findall(r'I:\s+(-?[\d.]+|-inf) LUFS', out)
    return float(found[-1]) if found and found[-1] != '-inf' else None


def encode(audio, dest):
    wrapped = np.concatenate([audio[-PAD:], audio, audio[:PAD]])
    peak = float(np.max(np.abs(wrapped))) or 1
    if peak > 0.99:
        wrapped = wrapped * (0.99 / peak)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', str(audio.shape[1]), '-i', '-',
                    '-c:a', 'libmp3lame', '-q:a', '2', str(dest)], input=wrapped.astype('<f4').tobytes(), check=True)


def main():
    root = Path(__file__).resolve().parent.parent
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else root / 'loops'
    out.mkdir(parents=True, exist_ok=True)
    config = json.loads((root / 'gilvry.json').read_text())
    warnings = []

    found = []
    for path in sorted((root / 'stems').iterdir()):
        if path.name.startswith('.') or path.suffix.lower() not in AUDIO:
            if path.is_file() and not path.name.startswith('.') and path.name.lower() != 'readme.md':
                warnings.append(f'{path.name}: not an audio file Gilvry knows, skipped.')
            continue
        match = NAME.match(path.stem)
        if not match:
            warnings.append(f'{path.name}: name should look like fiddle_e2_bright_01, skipped.')
            continue
        found.append((path, match))

    stems = []
    decoded = {}
    for path, match in found:
        try:
            decoded[path] = decode(path)
        except subprocess.CalledProcessError:
            warnings.append(f'{path.name}: could not be read, skipped.')
    if not decoded:
        sys.exit('No stems to build.')

    # The loop length is whatever most stems agree on; a few samples either way gets trimmed or filled
    lengths = sorted(len(a) for a in decoded.values())
    frames = lengths[len(lengths) // 2]
    tolerance = int(0.05 * SR)

    names = set()
    for path, match in found:
        if path not in decoded:
            continue
        audio = decoded[path]
        if abs(len(audio) - frames) > tolerance:
            warnings.append(f'{path.name}: {len(audio) / SR:.3f}s long, but the loops are {frames / SR:.3f}s. Skipped.')
            continue
        if len(audio) != frames:
            audio = audio[:frames] if len(audio) > frames else np.concatenate([audio, np.zeros((frames - len(audio), audio.shape[1]), '<f4')])
        instrument, energy, mood, take = match.group(1).lower(), int(match.group(2)), match.group(3).lower(), match.group(4) or '01'
        name = f'{instrument}_e{energy}_{mood}_{take}'
        if name in names:
            warnings.append(f'{path.name}: another file already has the name {name}, skipped.')
            continue
        names.add(name)
        if mood not in config['moods']:
            warnings.append(f'{path.name}: the mood "{mood}" isn\'t in gilvry.json\'s moods list, so it sits in the middle.')

        digest = hashlib.sha1(BUILD_VERSION.encode() + path.read_bytes()).hexdigest()[:10]
        lufs = loudness(audio)
        gain = 0.0 if lufs is None else max(-24.0, min(12.0, config.get('targetLufs', -20) - lufs))
        file = f'{name}.{digest}.mp3'
        if not (out / file).exists():
            encode(audio, out / file)
        role = 'bed' if instrument in config['beds'] else 'rhythm' if instrument in config['rhythm'] else 'tune'
        stems.append({'file': file, 'name': name, 'instrument': instrument, 'energy': energy, 'mood': mood,
                      'role': role, 'gain': round(gain, 2), 'lufs': None if lufs is None else round(lufs, 1)})
        print(f'{name}: {"" if lufs is None else f"{lufs:.1f} LUFS, "}gain {gain:+.1f} dB')

    # Clear out encodings of stems that changed or went away
    keep = {s['file'] for s in stems} | {'index.json'}
    for old in out.glob('*.mp3'):
        if old.name not in keep:
            old.unlink()

    bpm = config['bars'] * config['beatsPerBar'] * 60 * SR / frames
    index = {'bpm': round(bpm, 3), 'bars': config['bars'], 'beatsPerBar': config['beatsPerBar'],
             'tempoRange': config['tempoRange'], 'moods': config['moods'], 'sampleRate': SR, 'frames': frames,
             'pad': PAD, 'stems': stems, 'warnings': warnings}
    (out / 'index.json').write_text(json.dumps(index, indent=1))
    print(f'{len(stems)} stems, {frames / SR:.3f}s loops, {bpm:.2f} bpm')
    for w in warnings:
        print('Warning:', w)

    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary, 'a') as f:
            f.write(f'### Gilvry: {len(stems)} stems, {bpm:.1f} bpm\n\n')
            f.write('\n'.join(f'- {s["name"]} ({s["role"]}, {s["lufs"]} LUFS)' for s in stems) + '\n')
            if warnings:
                f.write('\n**Warnings**\n\n' + '\n'.join(f'- {w}' for w in warnings) + '\n')


if __name__ == '__main__':
    main()
