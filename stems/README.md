# Stems

Drop loops here. Each push rebuilds the app with whatever is in this folder (see the Actions tab
for a summary and any warnings).

**Names:** `instrument_e2_mood_01.wav`

- **instrument:** anything, lowercase, e.g. `fiddle`, `banjo`, `bodhran`. Only one loop per
  instrument plays at a time. `drone` and `pad` are beds (one is always under everything);
  `perc`, `drums`, `shaker`, `bodhran`, `bones` and `spoons` are rhythm (they come in as
  Kindling rises). Both lists are in `gilvry.json`.
- **e1, e2 or e3:** energy, 1 is quietest.
- **mood:** one of `dusky`, `misty`, `calm`, `warm`, `bright` (dusk to dawn, also in
  `gilvry.json`, where you can add your own).
- **01:** take number, so you can have more than one of a kind.

**Files:** WAV, AIFF, FLAC, MP3, M4A/AAC, OGG/Opus or CAF. Any sample rate and bit depth,
mono or stereo. Lossless (WAV, AIFF, FLAC) is best, since the app makes its own MP3s. GitHub's
upload page takes files up to 25 MB.

**Loops:** all the same length (16 bars), cut exactly on the bar line, with nothing faded at the
ends. Anything ringing past the end should be folded back onto the start, so it loops without a
seam. Loudness gets evened out for you.

The placeholder loops (made by `tools/placeholders.py`) can be deleted once real ones are in.
