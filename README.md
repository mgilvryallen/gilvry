# Gilvry

Folk loops that layer and wander on their own. Press play and it builds: a bed underneath, tunes
drifting in and out over it, a rhythm when things heat up. Four sliders steer it, loosely.

**Use it:** https://mgilvryallen.github.io/gilvry/

- **Kindling** (embers to bonfire): how many layers play, and how lively they are.
- **Hour** (dusk to dawn): which moods it reaches for, and how open the sound is.
- **Gait** (amble to scurry): tempo, 150 to 175 bpm, without changing the pitch.
- **Wander** (linger to roam): how often it changes its mind.

Every loop runs in time with the rest; layers only come and go on bar lines, fading slowly. The
picture is the music: each layer is a blot of color, the rhythm pulses on the beat.

## Put it on your phone

- **iPhone:** open the link in Safari, tap Share, then **Add to Home Screen**.
- **Android:** open it in Chrome, tap the menu, then **Install app**.

Once it's played once, it works offline. The screen stays on while it plays.

## Adding loops

Upload them into the `stems/` folder on GitHub (**Add file → Upload files**). Naming and format
notes are in [stems/README.md](stems/README.md). Each upload runs **Build and publish** (in the
Actions tab): it checks the loops all match in length, evens out their loudness, makes small
MP3s, and publishes the app. A minute or two later the new loops are live. If a file has a
problem, it's skipped and named in that run's summary.

The tempo comes from the loops themselves: 16 bars of 4/4 in however long they last. Change
`bars` or `beatsPerBar` in `gilvry.json` if yours are different, and the tempo range and moods
live there too.

## Make your own copy

Click **Use this template** on GitHub, then **Settings → Pages**, source **GitHub Actions**.
Everything the app does is in `index.html`; the loop preparation is `tools/build.py`.

Made by [M'Gilvry Allen](https://mgilvryallen.com).
