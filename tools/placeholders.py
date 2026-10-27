"""Placeholder loops for Gilvry, so the app has something to play before real stems arrive.

Every loop is 16 bars of 4/4 at 160 bpm in D, on one shared chord progression, rendered so
anything ringing past the end wraps around to the start (seamless). Mostly plucks, blips and
arpeggios: short sounds that make rhythm, rather than melodies. Writes FLAC into stems/.
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


def bloop(freq, dur, decay=7, drop=0.6):
    """A round blip: a sine that lands on its pitch from a little above, and dies away."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = freq * (1 + drop * np.exp(-t * 70))
    ph = 2 * np.pi * np.cumsum(f) / SR
    return (np.sin(ph) + 0.15 * np.sin(2 * ph)) * np.exp(-t * decay) * np.minimum(1, t / 0.002)


def bleep(freq, dur, decay=14, bright=0.6):
    """A short hollow beep: odd harmonics only, like a square wave with the edges rounded off."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for k in (1, 3, 5, 7):
        out += (1 / k) * bright ** ((k - 1) / 2) * np.sin(2 * np.pi * freq * k * t)
    return out * np.exp(-t * decay) * np.minimum(1, t / 0.002)


def fm(freq, dur, ratio=3.5, index=2.5, decay=4, index_decay=9):
    """A struck, slightly metallic tone (kalimba, marimba), by frequency modulation."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    mod = index * np.exp(-t * index_decay) * np.sin(2 * np.pi * freq * ratio * t)
    return np.sin(2 * np.pi * freq * t + mod) * np.exp(-t * decay) * np.minimum(1, t / 0.002)


def euclid(hits, steps, rotate=0):
    """hits spread as evenly as they'll go over steps (the rhythms behind a lot of world music)."""
    return [((i * hits) // steps != ((i + 1) * hits) // steps) for i in range(-rotate, steps - rotate)][::-1]


def chord_at(beat):
    return TONES[CHORDS[int(beat // 4) % BARS]]


PENTATONIC = [62, 64, 66, 69, 71]  # D E F# A B: sits well over every chord here


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

    # Up-arpeggio of round bloops in eighths, with gaps, soft and low
    lp = Loop()
    rest = np.random.default_rng(6)
    for i in range(BARS * 8):
        beat = i / 2
        chord = chord_at(beat)
        notes = [chord[0] - 12, chord[1] - 12, chord[2] - 12, chord[0]]
        if rest.random() < 0.8:
            lp.add(bloop(hz(notes[i % 4]), 0.5, decay=6), at(beat))
    finish(lp, 'arp_e1_misty_01')

    # Sequencer: up-and-down sixteenths of bleeps, accents on the beat
    lp = Loop()
    for i in range(BARS * 16):
        beat = i / 4
        chord = chord_at(beat)
        notes = [chord[0], chord[1], chord[2], chord[0] + 12, chord[2], chord[1]]
        lp.add(bleep(hz(notes[i % 6] + 12), 0.18, decay=22) * (1 if i % 4 == 0 else 0.55), at(beat))
    finish(lp, 'seq_e3_bright_01')

    # Kalimba: seven hits spread over sixteen steps, on the pentatonic, drifting up and down
    lp = Loop()
    pattern = euclid(7, 16)
    walk = 2
    krng = np.random.default_rng(7)
    for bar in range(BARS):
        for step, hit in enumerate(pattern):
            if hit:
                walk = int(np.clip(walk + krng.integers(-2, 3), 0, 9))
                m = PENTATONIC[walk % 5] + 12 * (walk // 5)
                lp.add(fm(hz(m), 1.2, ratio=5.6, index=1.6, decay=3.5), at(bar * 4 + step / 4))
    finish(lp, 'kalimba_e2_warm_01')

    # Marimba: the tresillo (3 + 3 + 2 eighths) on root and fifth, a chord tone on top
    lp = Loop()
    for bar in range(BARS):
        chord = TONES[CHORDS[bar]]
        for beat, m in ((0, chord[0] - 12), (1.5, chord[2] - 12), (3, chord[0]), (3.5, chord[1])):
            lp.add(fm(hz(m), 1.0, ratio=4, index=1.2, decay=5, index_decay=14), at(bar * 4 + beat))
    finish(lp, 'marimba_e2_calm_01')

    # Low bloops, few and far between, off the beat
    lp = Loop()
    brng = np.random.default_rng(8)
    for bar in range(BARS):
        root = TONES[CHORDS[bar]][0] % 12 + 38
        for beat in (0.5, 1.75, 2.5, 3.25):
            if brng.random() < 0.45:
                lp.add(bloop(hz(root + int(brng.choice([0, 7, 12]))), 0.9, decay=4, drop=1.2), at(bar * 4 + beat))
    finish(lp, 'blip_e1_dusky_01')

    # High bleeps: five over eight, octaves leaping
    lp = Loop()
    pattern = euclid(5, 8, rotate=1)
    for bar in range(BARS):
        chord = TONES[CHORDS[bar]]
        for step, hit in enumerate(pattern):
            if hit:
                m = chord[step % 3] + (24 if step % 2 else 12)
                lp.add(bleep(hz(m), 0.25, decay=16, bright=0.4), at(bar * 4 + step / 2))
    finish(lp, 'bleep_e3_warm_01')

    # Pulse: one note repeating in eighths, the root or its fifth, some notes louder
    lp = Loop()
    accents = [1, 0.4, 0.6, 0.4, 0.9, 0.4, 0.6, 0.7]
    for bar in range(BARS):
        root = TONES[CHORDS[bar]][0] % 12 + 50
        for i in range(8):
            m = root + (7 if bar % 4 == 3 and i >= 4 else 0)
            lp.add(fm(hz(m), 0.3, ratio=2, index=0.8, decay=11) * accents[i], at(bar * 4 + i / 2))
    finish(lp, 'pulse_e2_misty_01')

    # Three against four: a three-note figure in dotted eighths, so it lands somewhere new each beat
    lp = Loop()
    i = 0
    beat = 0.0
    while beat < BARS * 4:
        chord = chord_at(beat)
        lp.add(pluck(hz([chord[0], chord[2], chord[1] + 12][i % 3]), 0.9, bright=0.8, decay=4, rng=rng), at(beat))
        beat += 0.75
        i += 1
    finish(lp, 'triplet_e2_bright_01')

    # Drips: now and then a high clear note, from the pentatonic
    lp = Loop()
    drng = np.random.default_rng(9)
    for step in range(BARS * 8):
        if drng.random() < 0.18:
            m = int(drng.choice(PENTATONIC)) + 24
            lp.add(bloop(hz(m), 1.4, decay=3, drop=0.08) * 0.6, at(step / 2))
    finish(lp, 'drip_e1_calm_01')

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
