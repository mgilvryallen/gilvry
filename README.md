# Little Guy

Loops and a drone that layer and wander on their own. Press play and it builds: the hum of a
shruti box underneath, a sub, a groove, little plucks and blips coming and going over it. Four
sliders steer it, loosely.

**Use it:** https://mgilvryallen.github.io/littleguy/

- **Kindling** (embers to bonfire): how much is going on. More layers, livelier ones, drums
  and then hats as it rises, and it changes its mind more often.
- **Hour** (dusk to dawn): which moods it reaches for, and how dark or open the sound is.
- **Gait** (amble to scurry): tempo, 60 to 120 bpm, without changing the pitch.
- **Hum** (hush to front porch): the drone, which is [Drone](https://github.com/mgilvryallen/drone)'s
  own engine playing Front Porch. It adds voices as it rises: root, fifth, low root, octave,
  ninth, tenth. Past halfway, the drone takes over as the bed and the pads step aside. It's
  never still: its voices swell and sink, and any but the root may drop out for a while and
  ease back in.

Every loop runs in time with the rest; layers come and go on bar lines, sway a little on their
own, and now and then step back for a bar or two. The picture is the music: each layer is a
blot of color, the hum is rings in the middle, the low end glows along the bottom.

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

The tempo comes from the loops themselves: 16 bars of 4/4 in however long they last. Loops made
in the middle of the range (around 85 to 90 bpm) stretch best both ways. `littleguy.json` has the
bar count, tempo range, moods, which instruments count as beds, lows and rhythm, and the key
the drone plays in.

## Make your own copy

Click **Use this template** on GitHub, then **Settings → Pages**, source **GitHub Actions**.
Everything the app does is in `index.html`; the loop preparation is `tools/build.py`.

Made by [M'Gilvry Allen](https://mgilvryallen.com).
