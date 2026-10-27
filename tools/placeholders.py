"""Placeholder loops for Gilvry, so the app has something to play before real stems arrive.

Every loop is 16 bars of 4/4 at 160 bpm in D, on one shared chord progression, rendered so
anything ringing past the end wraps around to the start (seamless). Writes FLAC into stems/.
Run from the repo root: python3 tools/placeholders.py  (needs numpy and ffmpeg)
"""
import subprocess
import numpy as np

SR = 44100
BPM = 160
BARS = 16
BEAT = 60 / BPM
L = int(round(BARS * 4 * BEAT * SR))

# One chord per bar, shared by every stem
CHORDS = ['D', 'D', 'G', 'D', 'D', 'D', 'A', 'A', 'D', 'D', 'G', 'D', 'G', 'A', 'D', 'D']
TONES = {'D': [62, 66, 69], 'G': [67, 71, 62], 'A': [69, 73, 64], 'Bm': [71, 62, 66]}
SCALE = [62, 64, 66, 67, 69, 71, 73]  # D major


def hz(midi):
    return 440 * 2 ** ((midi - 69) / 12)


def at(beat):
    return int(round(beat * BEAT * SR))


class Loop:
    def __init__(self):
        self.y = np.zeros(L)

    def add(self, signal, start):
        idx = (start + np.arange(len(signal))) % L
        np.add.at(self.y, idx, signal)


def env(n, attack, release, sustain_level=1.0):
    t = np.arange(n) / SR
    e = np.minimum(1, t / max(attack, 1e-4))
    tail = int(release * SR)
    if tail and tail < n:
        e[-tail:] *= np.linspace(1, 0, tail) ** 2
    return e * sustain_level


def pluck(freq, dur, bright=1.0, decay=1.6, harmonics=14, rng=None):
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for k in range(1, harmonics + 1):
        f = freq * k * (1 + 0.0004 * k * k)
        if f > SR / 2.2:
            break
        amp = (1 / k ** (1.6 - 0.5 * bright)) * (0.5 + 0.5 * np.sin(k * 1.7))
        out += amp * np.sin(2 * np.pi * f * t + (rng.random() * 6.28 if rng is not None else 0)) * np.exp(-t * decay * (1 + 0.35 * k))
    out *= np.minimum(1, t / 0.003)
    out[-200:] *= np.linspace(1, 0, 200)
    return out


def bowed(freq, dur, bright=1.0, vibrato=5.2, depth=0.006, attack=0.12, release=0.2, harmonics=22):
    n = int(dur * SR)
    t = np.arange(n) / SR
    vib = 1 + depth * np.sin(2 * np.pi * vibrato * t) * np.minimum(1, t / 0.4)
    phase = 2 * np.pi * np.cumsum(freq * vib) / SR
    out = np.zeros(n)
    for k in range(1, harmonics + 1):
        if freq * k > SR / 2.2:
            break
        # A saw, rolled off; bright lets more upper harmonics through, with a body resonance near 3k
        amp = (1 / k) * np.exp(-k / (5 + 9 * bright)) * (1 + 0.6 * np.exp(-((freq * k - 2900) / 900) ** 2))
        out += amp * np.sin(k * phase)
    noise = np.random.default_rng(int(freq)).standard_normal(n)
    noise = np.diff(np.concatenate([[0], noise])) * 0.012 * bright
    return (out + noise) * env(n, attack, release)


def pad(freqs, dur, bright=0.5, attack=1.2, release=1.4):
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for f0 in freqs:
        for detune in (-0.0035, 0, 0.004):
            f = f0 * (1 + detune)
            for k in range(1, 10):
                out += (1 / k) * np.exp(-k / (1.5 + 4 * bright)) * np.sin(2 * np.pi * f * k * t + k * detune * 900)
    return out * env(n, attack, release)


def bell(freq, dur, decay=1.2):
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for ratio, amp, d in ((1, 1, 1), (2.76, 0.45, 1.8), (5.4, 0.25, 2.6), (8.93, 0.12, 3.5)):
        out += amp * np.sin(2 * np.pi * freq * ratio * t) * np.exp(-t * decay * d)
    return out * np.minimum(1, t / 0.002)


def noise_burst(dur, decay, rng, highpass=True):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = rng.standard_normal(n)
    if highpass:
        x = np.diff(np.concatenate([[0], x]))
    return x * np.exp(-t * decay)


def kick(dur=0.45):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 48 + 70 * np.exp(-t * 28)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)


def melody(rng, notes_per_bar, register, leap=2, chord_pull=0.6):
    """A wandering line: steps through the scale, leaning on chord tones at each bar."""
    scale = sorted(set(s + 12 * o for s in SCALE for o in (-1, 0, 1, 2)))
    pos = min(range(len(scale)), key=lambda i: abs(scale[i] - register))
    line = []
    for bar in range(BARS):
        chord = [c % 12 for c in TONES[CHORDS[bar]]]
        for i in range(notes_per_bar):
            if i == 0 and rng.random() < chord_pull:
                near = [j for j in range(len(scale)) if scale[j] % 12 in chord and abs(j - pos) <= 3]
                if near:
                    pos = near[rng.integers(len(near))]
            else:
                pos += int(rng.integers(-leap, leap + 1))
            pos = int(np.clip(pos, 0, len(scale) - 1))
            if abs(scale[pos] - register) > 9:
                pos += -1 if scale[pos] > register else 1
            line.append((bar * 4 + i * 4 / notes_per_bar, scale[pos]))
    return line


def finish(loop, name, target_rms=0.08):
    y = loop.y
    y = y - y.mean()
    rms = np.sqrt(np.mean(y ** 2)) or 1
    y = y * target_rms / rms
    peak = np.max(np.abs(y))
    if peak > 0.95:
        y = np.tanh(y / peak * 1.2) / np.tanh(1.2) * 0.95
    pcm = (np.clip(y, -1, 1) * 32767).astype('<i2').tobytes()
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 's16le', '-ar', str(SR), '-ac', '1', '-i', '-',
                    f'stems/{name}.flac'], input=pcm, check=True)
    print(name)


def main():
    rng = np.random.default_rng(160)

    # Drone: low D and A, slowly breathing, dark
    lp = Loop()
    t = np.arange(L) / SR
    swell = 0.75 + 0.25 * np.sin(2 * np.pi * t * 2 / (L / SR))
    loop_seconds = L / SR
    for f, a in ((hz(38), 1), (hz(45), 0.6), (hz(50), 0.35)):
        f = round(f * loop_seconds) / loop_seconds  # whole cycles per loop, so the end meets the start
        for k in range(1, 8):
            wobble = 0.6 * np.sin(2 * np.pi * t * 3 / loop_seconds)
            lp.y += a * swell * (1 / k ** 1.4) * np.sin(2 * np.pi * f * k * t + k * wobble)
    finish(lp, 'drone_e1_dusky_01')

    # Pads follow the chords, a new chord each time it changes
    for name, bright, octave in (('pad_e1_calm_01', 0.35, 0), ('pad_e2_bright_01', 0.9, 12)):
        lp = Loop()
        bar = 0
        while bar < BARS:
            run = 1
            while bar + run < BARS and CHORDS[bar + run] == CHORDS[bar]:
                run += 1
            freqs = [hz(m - 12 + octave) for m in TONES[CHORDS[bar]]]
            lp.add(pad(freqs, run * 4 * BEAT + 1.4, bright), at(bar * 4))
            bar += run
        finish(lp, name)

    # Bass
    lp = Loop()
    for bar in range(BARS):
        root = TONES[CHORDS[bar]][0] % 12 + 36
        for beat in (0, 2):
            lp.add(pluck(hz(root), 1.4, bright=0.2, decay=2.2, harmonics=6), at(bar * 4 + beat))
    finish(lp, 'bass_e2_calm_01')
    lp = Loop()
    for bar in range(BARS):
        root = TONES[CHORDS[bar]][0] % 12 + 36
        for beat, step in ((0, 0), (1, 7), (2, 0), (3, 7)):
            lp.add(pluck(hz(root + step), 0.6, bright=0.4, decay=4, harmonics=8), at(bar * 4 + beat))
    finish(lp, 'bass_e3_bright_01')

    # Percussion
    lp = Loop()
    for bar in range(BARS):
        for beat in (0, 2):
            lp.add(kick() * 0.9, at(bar * 4 + beat))
        for eighth in range(8):
            lp.add(noise_burst(0.08, 60, rng) * (0.25 if eighth % 2 else 0.12), at(bar * 4 + eighth / 2))
    finish(lp, 'perc_e2_calm_01', 0.06)
    lp = Loop()
    for bar in range(BARS):
        for beat in range(4):
            lp.add(kick(), at(bar * 4 + beat))
        for beat in (1, 3):
            lp.add(noise_burst(0.18, 22, rng) * 0.5 + pluck(hz(55), 0.18, decay=20, harmonics=3) * 0.3, at(bar * 4 + beat))
        for six in range(16):
            lp.add(noise_burst(0.05, 90, rng) * (0.3 if six % 2 else 0.14), at(bar * 4 + six / 4))
    finish(lp, 'perc_e3_bright_01', 0.07)

    # Guitar: strums on 1, 2-and, 4
    lp = Loop()
    for bar in range(BARS):
        chord = TONES[CHORDS[bar]]
        voicing = sorted([chord[0] - 12, chord[1] - 12, chord[2] - 12, chord[0], chord[1]])
        for beat, down in ((0, True), (1.5, False), (3, True)):
            for i, m in enumerate(voicing if down else voicing[::-1][:3]):
                lp.add(pluck(hz(m), 1.6, bright=0.6, decay=1.8, rng=rng) * (0.8 if down else 0.5), at(bar * 4 + beat) + i * 260)
    finish(lp, 'guitar_e2_calm_01')

    # Banjo: rolling eighths, high and bright
    lp = Loop()
    for bar in range(BARS):
        chord = TONES[CHORDS[bar]]
        roll = [chord[0] + 12, chord[1], chord[2], chord[0] + 12, chord[1] + 12, chord[2], chord[0] + 12, chord[1]]
        for i, m in enumerate(roll):
            lp.add(pluck(hz(m), 0.7, bright=1.0, decay=5, rng=rng) * (1 if i % 3 == 0 else 0.7), at(bar * 4 + i / 2))
    finish(lp, 'banjo_e3_bright_01')

    # Low harp-like plucks, sparse and dark
    lp = Loop()
    for bar in range(BARS):
        chord = TONES[CHORDS[bar]]
        for beat, m in ((0, chord[0] - 12), (1.5, chord[2] - 12), (3, chord[1] - 12)):
            if rng.random() < 0.8:
                lp.add(pluck(hz(m), 3.0, bright=0.15, decay=0.9, rng=rng), at(bar * 4 + beat))
    finish(lp, 'pluck_e1_dusky_01')

    # Fiddles
    lp = Loop()
    for beat, m in melody(np.random.default_rng(1), 1, 57, leap=1):
        lp.add(bowed(hz(m), 4 * BEAT + 0.25, bright=0.35, attack=0.35, release=0.35, depth=0.004), at(beat))
    finish(lp, 'fiddle_e1_dusky_01')
    lp = Loop()
    for beat, m in melody(np.random.default_rng(2), 2, 69, leap=2):
        lp.add(bowed(hz(m), 2 * BEAT + 0.12, bright=0.6, attack=0.15, release=0.2), at(beat))
    finish(lp, 'fiddle_e2_calm_01')
    lp = Loop()
    for beat, m in melody(np.random.default_rng(3), 8, 74, leap=2, chord_pull=0.8):
        lp.add(bowed(hz(m), BEAT / 2 + 0.03, bright=1.0, attack=0.02, release=0.04, depth=0.002), at(beat))
    finish(lp, 'fiddle_e3_bright_01')

    # Whistle: airy sine with a little breath
    lp = Loop()
    for beat, m in melody(np.random.default_rng(4), 2, 81, leap=2):
        n = int((2 * BEAT + 0.08) * SR)
        tt = np.arange(n) / SR
        f = hz(m) * (1 + 0.004 * np.sin(2 * np.pi * 5.5 * tt) * np.minimum(1, tt / 0.3))
        ph = 2 * np.pi * np.cumsum(f) / SR
        tone = np.sin(ph) + 0.08 * np.sin(2 * ph) + 0.03 * noise_burst(n / SR, 0, rng)
        lp.add(tone * env(n, 0.05, 0.1), at(beat))
    finish(lp, 'whistle_e2_bright_01')

    # Bells: a few chimes, long rings that wrap past the loop end
    lp = Loop()
    brng = np.random.default_rng(5)
    for bar in range(0, BARS, 2):
        chord = TONES[CHORDS[bar]]
        for _ in range(2):
            m = chord[brng.integers(3)] + 12
            lp.add(bell(hz(m), 6.0, decay=0.7) * 0.6, at(bar * 4 + int(brng.integers(0, 8)) / 2))
    finish(lp, 'bells_e1_calm_01')


if __name__ == '__main__':
    main()
