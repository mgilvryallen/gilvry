"""Placeholder loops for Little Guy, so the app has something to play before real stems arrive.

Every loop is 16 bars of 4/4 at 90 bpm in D, on one shared chord progression, rendered so
anything ringing past the end wraps around to the start (seamless). Blips, plucks, arpeggios,
sub bass and drums, all on a swung, slightly loose grid: offbeats land late, snares lean back,
and no two hits are quite the same loudness. Writes FLAC into stems/.
Run from the repo root: python3 tools/placeholders.py  (needs numpy and ffmpeg)
"""
import subprocess
import numpy as np

SR = 44100
BPM = 90
BARS = 16
BEAT = 60 / BPM
L = int(round(BARS * 4 * BEAT * SR))

# One chord per bar, shared by every stem
CHORDS = ['D', 'D', 'G', 'D', 'D', 'D', 'A', 'A', 'D', 'D', 'G', 'D', 'G', 'A', 'D', 'D']
TONES = {'D': [62, 66, 69], 'G': [67, 71, 62], 'A': [69, 73, 64], 'Bm': [71, 62, 66]}

# The groove. Swing is how late the offbeats land (0.5 is straight, 0.55 is about as far as it
# goes here); each layer gets its own, so they don't quite agree. Hits also wander a little off
# the grid, the snare sits a touch behind the beat, and offbeats are played softer (lean).
SWING = 0.53
LOOSE = 0.006
LAY_BACK = 0.025
groove = np.random.default_rng(90)


def feel(swing):
    """Set the swing for the layer about to be made."""
    global SWING
    SWING = swing


def sixteenth(i):
    """Where sixteenth number i lands, in beats, swung and a touch loose."""
    swing = 0.5 * (2 * SWING - 1) * 0.5 if i % 2 else 0
    return i * 0.25 + swing + groove.normal(0, LOOSE)


def eighth(i):
    swing = 0.5 * (2 * SWING - 1) if i % 2 else 0
    return i * 0.5 + swing + groove.normal(0, LOOSE)


def lean(i, per_beat):
    """How hard the ith note of a grid is played: full on the beat, softer on the and,
    softest on the sixteenths in between."""
    if per_beat == 4:
        return (1.0, 0.55, 0.78, 0.55)[i % 4]
    return (1.0, 0.68)[i % 2]


def velocity(base, spread=0.25):
    """No two hits the same: base loudness, give or take."""
    return max(0.05, base * (1 - spread / 2 + spread * groove.random()))


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


def kick808(dur=0.9, tune=46, punch=95, decay=5.5):
    """A round, low kick: a sine dropping fast onto its note, a short click at the front."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = tune + punch * np.exp(-t * 32)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * decay)
    click = groove.standard_normal(n) * np.exp(-t * 400) * 0.25
    return body + click


def snare(dur=0.35, rng=None, tone=185):
    n = int(dur * SR)
    t = np.arange(n) / SR
    rng = rng or groove
    noise = np.diff(np.concatenate([[0], rng.standard_normal(n)])) * np.exp(-t * 16) * 0.6
    body = np.sin(2 * np.pi * tone * t) * np.exp(-t * 28) * 0.7
    return noise + body


def hat(open_=False, rng=None):
    """Metallic hiss: noise with the lows taken out twice over, short (or long, if open)."""
    dur = 0.45 if open_ else 0.07
    n = int(dur * SR)
    t = np.arange(n) / SR
    rng = rng or groove
    x = rng.standard_normal(n)
    x = np.diff(np.diff(np.concatenate([[0, 0], x])))
    metal = sum(np.sign(np.sin(2 * np.pi * f * t)) for f in (3140, 4320, 5530, 6210)) * 0.08
    return (x * 0.35 + metal) * np.exp(-t * (9 if open_ else 70))


def sub(freq, dur, glide_from=None, glide=0.06, decay=1.2, release=0.08):
    """Sub bass: a sine with a little second and third harmonic, so phones can hint at it."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = np.full(n, freq)
    if glide_from:
        f = freq + (glide_from - freq) * np.exp(-t / glide)
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sin(ph) + 0.18 * np.sin(2 * ph) + 0.06 * np.sin(3 * ph)
    return y * np.exp(-t * decay) * env(n, 0.006, release)


def root_at(beat, octave=36):
    return TONES[CHORDS[int(beat // 4) % BARS]][0] % 12 + octave


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

    # ---- Beds ----
    for name, bright, octave, chords in (('pad_e1_calm_01', 0.35, 0, None), ('pad_e2_bright_01', 0.9, 12, None),
                                         ('pad_e1_dusky_01', 0.15, -12, {'D': [62, 69, 64], 'G': [67, 62, 69], 'A': [69, 64, 71]})):
        lp = Loop()
        bar = 0
        while bar < BARS:
            run = 1
            while bar + run < BARS and CHORDS[bar + run] == CHORDS[bar]:
                run += 1
            tones = (chords or TONES)[CHORDS[bar]]
            lp.add(pad([hz(m - 12 + octave) for m in tones], run * 4 * BEAT + 1.4, bright), at(bar * 4))
            bar += run
        finish(lp, name)

    # ---- Low end ----
    # Long sub notes, sliding into each new chord
    lp = Loop()
    prev = None
    for bar in range(BARS):
        root = root_at(bar * 4, 26)
        if bar == 0 or CHORDS[bar] != CHORDS[bar - 1]:
            lp.add(sub(hz(root), 4 * BEAT * 0.98, glide_from=hz(prev) if prev else None, glide=0.12, decay=0.25, release=0.3), at(bar * 4))
        else:
            lp.add(sub(hz(root), 3 * BEAT, decay=0.5, release=0.3) * 0.8, at(bar * 4 + 0.02))
        prev = root
    finish(lp, 'sub_e1_dusky_01', 0.1)

    # 808-style: a syncopated figure, the same shape as the kick, notes ringing into each other
    feel(0.54)
    lp = Loop()
    for bar in range(BARS):
        root = root_at(bar * 4, 38)
        steps = [(0, 0, 1.0, 1.6), (7, 0, 0.8, 0.7), (10, 12 if bar % 2 else 0, 0.85, 1.0)]
        if bar % 4 == 3:
            steps.append((14, 7, 0.7, 0.5))
        for step, up, vel, length in steps:
            lp.add(sub(hz(root + up), length, glide_from=hz(root + up + 5), glide=0.03, decay=1.0) * velocity(vel, 0.15) * (0.5 + 0.5 * lean(step, 4)), at(bar * 4 + sixteenth(step)))
    finish(lp, 'sub_e2_warm_01', 0.1)

    # Bouncing octaves, swung sixteenths
    feel(0.52)
    lp = Loop()
    for bar in range(BARS):
        root = root_at(bar * 4, 38)
        for step, up, vel in ((0, 0, 1), (3, 12, 0.9), (6, 0, 1), (8, 0, 0.9), (11, 12, 0.9), (14, 7, 1)):
            lp.add(sub(hz(root + up), 0.5, decay=4) * velocity(vel, 0.2) * lean(step, 4), at(bar * 4 + sixteenth(step)))
    finish(lp, 'sub_e3_bright_01', 0.1)

    # A plucked bass with a sub under it, on the one and the and-of-three
    feel(0.53)
    lp = Loop()
    for bar in range(BARS):
        root = root_at(bar * 4, 38)
        for beat, vel in ((0, 1), (2.5, 0.75)):
            b = bar * 4 + beat + groove.normal(0, LOOSE)
            lp.add((pluck(hz(root), 1.3, bright=0.2, decay=2.2, harmonics=6) + 0.6 * sub(hz(root - 12), 1.3, decay=2)) * velocity(vel), at(b))
    finish(lp, 'bass_e2_calm_01', 0.1)

    # ---- Drums: kick and snare ----
    def drum_loop(name, kick_steps, swing, ghost=0.0, rim=False, clap=False, fills=True, target=0.08):
        feel(swing)
        lp = Loop()
        drng = np.random.default_rng(sum(map(ord, name)))
        for bar in range(BARS):
            steps = list(kick_steps)
            if fills and bar % 4 == 3:
                steps = steps + [14]
            for step in steps:
                lp.add(kick808() * velocity(1.0 if step == 0 else 0.85, 0.15) * (0.6 + 0.4 * lean(step, 4)), at(bar * 4 + sixteenth(step)))
            for beat in (1, 3):
                hit = snare(rng=drng, tone=320 if rim else 185) * (0.45 if rim else 0.9)
                if clap:
                    # A clap: three quick bursts of noise, a hair apart
                    for k in range(3):
                        burst = snare(0.12, drng, 1200) * 0.3
                        start = int(k * 0.011 * SR)
                        hit[start:start + len(burst)] += burst[:len(hit) - start]
                lp.add(hit * velocity(1, 0.2), at(bar * 4 + beat + LAY_BACK + groove.normal(0, LOOSE)))
            for step in range(16):
                if ghost and step % 4 in (2, 3) and drng.random() < ghost:
                    lp.add(snare(0.12, drng) * velocity(0.18, 0.5), at(bar * 4 + sixteenth(step) + LAY_BACK))
        finish(lp, name, target)

    drum_loop('drums_e1_calm_01', [0, 10], 0.53, rim=True, fills=False, target=0.07)
    drum_loop('drums_e2_warm_01', [0, 7, 10], 0.55, ghost=0.25)
    drum_loop('drums_e3_bright_01', [0, 3, 6, 10, 13], 0.52, ghost=0.35, clap=True)

    # ---- Hats ----
    def hats_loop(name, grid, swing, accents, open_every=0, skip=0.0, shaker=False, target=0.05):
        feel(swing)
        lp = Loop()
        hrng = np.random.default_rng(sum(map(ord, name)))
        for bar in range(BARS):
            count = 16 if grid == 16 else 8
            for i in range(count):
                if hrng.random() < skip:
                    continue
                beat = bar * 4 + (sixteenth(i) if grid == 16 else eighth(i))
                opened = open_every and i == count - 2 and bar % open_every == open_every - 1
                sound = hat(opened, hrng)
                if shaker:
                    sound = np.convolve(sound, np.ones(30) / 30, mode='same') * 2.5
                lp.add(sound * velocity(accents[i % len(accents)], 0.3) * lean(i, grid // 4), at(beat))
        finish(lp, name, target)

    hats_loop('hats_e1_misty_01', 8, 0.55, [0.9, 1.0], skip=0.1, shaker=True)
    hats_loop('hats_e2_warm_01', 16, 0.54, [1.0, 0.7, 0.9, 0.75], open_every=2, skip=0.06)
    hats_loop('hats_e3_bright_01', 16, 0.52, [0.95, 0.8, 1.0, 0.85], open_every=1)

    # ---- Plucks, blips and arpeggios ----
    # Up-arpeggio of round bloops in swung eighths, with gaps
    feel(0.55)
    lp = Loop()
    for i in range(BARS * 8):
        beat = eighth(i)
        chord = chord_at(i / 2)
        notes = [chord[0] - 12, chord[1] - 12, chord[2] - 12, chord[0]]
        if rng.random() < 0.8:
            lp.add(bloop(hz(notes[i % 4]), 0.6, decay=5) * velocity([1, 0.8, 0.9, 0.85][i % 4], 0.35) * lean(i, 2), at(bar_wrap(beat)))
    finish(lp, 'arp_e1_misty_01')

    # Kalimba: seven hits spread over sixteen steps, on the pentatonic, drifting
    feel(0.54)
    lp = Loop()
    pattern = euclid(7, 16)
    walk = 2
    for bar in range(BARS):
        for step, hit in enumerate(pattern):
            if hit:
                walk = int(np.clip(walk + rng.integers(-2, 3), 0, 9))
                m = PENTATONIC[walk % 5] + 12 * (walk // 5)
                lp.add(fm(hz(m), 1.4, ratio=5.6, index=1.6, decay=3) * velocity(0.85, 0.4) * lean(step, 4), at(bar_wrap(bar * 4 + sixteenth(step))))
    finish(lp, 'kalimba_e2_warm_01')

    # High bleeps: five over eight, octaves leaping
    feel(0.51)
    lp = Loop()
    pattern = euclid(5, 8, rotate=1)
    for bar in range(BARS):
        chord = TONES[CHORDS[bar]]
        for step, hit in enumerate(pattern):
            if hit:
                m = chord[step % 3] + (24 if step % 2 else 12)
                lp.add(bleep(hz(m), 0.3, decay=13, bright=0.4) * velocity(0.85, 0.4) * lean(step, 2), at(bar_wrap(bar * 4 + eighth(step))))
    finish(lp, 'bleep_e3_warm_01')

    # Drips: now and then a high clear note
    feel(0.55)
    lp = Loop()
    for step in range(BARS * 8):
        if rng.random() < 0.18:
            lp.add(bloop(hz(int(rng.choice(PENTATONIC)) + 24), 1.6, decay=2.5, drop=0.08) * velocity(0.6, 0.5) * lean(step, 2), at(bar_wrap(eighth(step))))
    finish(lp, 'drip_e1_calm_01')

    # Low harp-like plucks, sparse and dark
    feel(0.52)
    lp = Loop()
    for bar in range(BARS):
        chord = TONES[CHORDS[bar]]
        for step, m in ((0, chord[0] - 12), (6, chord[2] - 12), (12, chord[1] - 12)):
            if rng.random() < 0.8:
                lp.add(pluck(hz(m), 3.0, bright=0.15, decay=0.9, rng=rng) * velocity(0.8, 0.4), at(bar_wrap(bar * 4 + sixteenth(step))))
    finish(lp, 'pluck_e1_dusky_01')

    # Bells: a few chimes, long rings that wrap past the loop end
    feel(0.54)
    lp = Loop()
    for bar in range(0, BARS, 2):
        chord = TONES[CHORDS[bar]]
        for _ in range(2):
            m = chord[rng.integers(3)] + 12
            lp.add(bell(hz(m), 7.0, decay=0.6) * velocity(0.6, 0.5), at(bar_wrap(bar * 4 + eighth(int(rng.integers(0, 8))))))
    finish(lp, 'bells_e1_calm_01')


def bar_wrap(beat):
    return beat % (BARS * 4)


if __name__ == '__main__':
    main()
