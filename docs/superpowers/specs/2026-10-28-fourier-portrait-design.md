# Fourier Portrait: design

Date: 2026-10-28
Status: approved in chat 2026-10-28

## Intent

Replace the static profile photo in the home page heading with an animation:
a chain of spinning circles (Fourier epicycles) whose tip traces a one-line
sketch of the portrait live in the browser. When the sketch is complete it
holds briefly, then crossfades into the real photo, which remains as the
final state.

It is a signature piece for the landing page, not a reusable widget. One
portrait, one page.

## Goals

- On page load the visitor watches the portrait being drawn by epicycles,
  with the circles and the pen tip visible, and ends up looking at the
  normal photo.
- The sketch is recognisably the person in the photo.
- No layout shift relative to today: the heading keeps the same size and
  placement on desktop and mobile.
- Visitors without JavaScript, search engines, and people with "reduce
  motion" enabled see exactly what they see today: the photo.
- No new runtime dependencies. Everything expensive happens offline.

## Non-goals

- Replaying the animation without a page reload. The owner explicitly does
  not want a click-to-replay. A reload is the only way to see it again.
- Running the photo-to-line conversion in the browser.
- Looping or kinetic "forever" mode.
- Generalising to arbitrary images at runtime.

## Anti-goals (what would make it a failure even if it works)

- The circles overwhelm the drawing, so the visitor sees a blur of rings
  and never a face.
- The sketch reconstructs as mush: too few Fourier terms for the path, or a
  path full of long jumps across the background.
- The page jumps when the canvas appears or when the photo fades in.
- The photo is missing or delayed for no-JS or reduced-motion visitors.
- Shipping p5, Svelte, or any other runtime library for this. The owner
  asked for plain TypeScript.

## Constraints and existing context

- Site: Astro 5 with MDX pages. The heading lives in
  `src/components/Heading.astro`; the home page `src/pages/index.mdx`
  passes `<Img filename="alex.png" alt="Alex Gulko" width="400"
  loading="eager" class="padding" scales slot="left"/>` into its `left`
  slot.
- `Img.astro` wraps Astro's `<Image>` with `max-width: 100%; height: auto`.
  The `scales` attribute is passed through as an HTML attribute; nothing in
  the component reads it. The builder should check for a global stylesheet
  rule on `[scales]` or `.padding` in `public/styles` before relying on
  either.
- The left column is `50vw` on desktop and `100%` under 800px.
- Source photo: the owner supplied `C:/Users/alexg/Downloads/DSC04521_1.JPG`
  (1440x1080 landscape JPEG, golden-hour portrait, head slightly left of
  centre, busy background of sky, mountains, plants, and people). The
  build crops it to a square around the head and shoulders, saves the crop
  into `src/assets/` under a new name (the existing `alex.png` is left in
  place), and both the sketch and the final crossfade use that crop. The
  crop rectangle is the builder's call, chosen by eye so the face sits
  roughly where it does in today's photo.
- Offline tooling: Python 3 with numpy, scipy, and Pillow are installed.
  OpenCV and scikit-image are not. The offline script must not require
  them unless the builder installs them explicitly and notes it.
- Owner decisions: plain TypeScript inside an Astro component, no Svelte;
  circles and tip visible during the trace; finished sketch fades into the
  photo; no replay control.

## Behaviour

Timeline on page load (durations are my call; owner said the timing
"sounds good"):

1. Script starts. It hides the real image (opacity 0) and shows the canvas.
   Hiding happens from JavaScript, not in CSS, so no-JS visitors keep the
   photo.
2. Trace: about 8 seconds. The epicycle chain spins through one full period
   and the tip lays down the line. Elapsed real time drives the phase, not
   frame count, so slow devices draw a shorter-looking animation rather
   than a slower one. Easing: linear, so that circle speed reads as
   constant.
3. Hold: about 1 second on the completed sketch with the circles removed
   and only the line showing.
4. Crossfade: about 1.5 seconds, canvas opacity 1 to 0 and image opacity
   0 to 1 together, via CSS transitions. The canvas is then removed from
   the layout.
5. Final state: the photo, exactly as today.

If `prefers-reduced-motion: reduce` matches, the script does nothing. The
image is never hidden and the loop never starts.

Nothing is interactive. No click, hover, or scroll affects it.

## Visual treatment

- Circles: thin strokes in the page foreground colour at low opacity
  (around 0.15). Each circle is drawn at the current position of its
  arrow's base.
- Arrows: the radius vectors, drawn as thin lines in the foreground colour
  at moderate opacity (around 0.5). No arrowheads; a small dot at the tip.
- Trace: the line drawn so far, in the foreground colour at full opacity,
  slightly thicker than the arrows, round joins and caps.
- Colour: the site has no theme variables for text colour and no dark
  theme; `<main>` sets `color: black` inline. The script reads
  `getComputedStyle(wrapper).color` so it follows whatever the page uses.
- Background: transparent canvas over the heading background.

## Data pipeline (offline, committed output)

A Python script at `scripts/fourier_portrait.py` takes an image path and
writes `src/data/fourier-portrait.json`. Steps:

1. Subject mask. The source has a busy background, so a mask step must
   exist; edges in the background are the biggest quality risk. The script
   accepts an optional mask image (white = keep). Builder's call on how
   that mask is produced: a hand-built geometric mask, or a one-off run of
   a background-removal tool such as `rembg` installed locally for the
   purpose (offline only, never shipped). Either way the mask image is
   committed next to the script so the result is reproducible.
2. Edge extraction with numpy/scipy only: grayscale, Gaussian blur, Sobel
   or similar gradient, threshold with hysteresis or a single tuned
   threshold, then thinning to one-pixel-wide strokes.
3. Chaining: walk edge pixels into strokes, order strokes greedily by
   nearest endpoint, join with straight segments, and close the loop back
   to the start. The result is one continuous closed path.
4. Light smoothing and resampling to a fixed number of evenly spaced
   points, M in the 2000 to 3000 range.
5. Normalise in image-frame coordinates, not path-bounding-box
   coordinates: x = px / width - 0.5, y = py / height - 0.5. The sketch
   must land exactly where the face is in the photo so that the crossfade
   does not jump or rescale. (My call, follows from the intent.)
6. Discrete Fourier transform of the complex path x + iy. Keep K terms
   (target 200 to 500) with frequencies from -K/2 to K/2, sorted by
   amplitude descending so the large slow circles come first in the chain.
7. Write JSON: `{ "k": K, "m": M, "coeffs": [[freq, re, im], ...] }`.
   Expected size: single-digit kilobytes.
8. Also write preview PNGs of the reconstruction at K = 100, 200, and 400
   to a scratch folder so the path can be tuned by eye before any browser
   work. This is a validate-first step: do not integrate a path that
   reconstructs badly.

## Component

`src/components/FourierPortrait.astro`:

- Props: the same props the current `<Img>` takes (`filename`, `alt`,
  `width`, `loading`, `class`, `scales`) so the home page swaps one tag for
  another and the rendered `<img>` is unchanged.
- Markup: a `position: relative` wrapper containing the `<Img>` and an
  absolutely positioned `<canvas>` covering it.
- Script: a hoisted `<script>` block in TypeScript, importing the JSON
  coefficients. No external libraries.
- Sizing: read the image's `clientWidth` and `clientHeight` after layout,
  observe changes with `ResizeObserver`, set canvas pixel size to that
  times `devicePixelRatio`, and map the unit box onto the canvas so that
  (-0.5, -0.5) is the image's top-left corner and (0.5, 0.5) its
  bottom-right. No margin: the sketch is registered to the photo. The
  canvas is sized to the image, never the other way around, so the image
  continues to govern layout.
- Render loop: `requestAnimationFrame`. Each frame computes every epicycle
  position for the current phase, draws circles and arrows, appends the
  tip to the trace array, and redraws the whole trace. Redrawing a few
  thousand points per frame is cheap.
- Lifecycle: trace, hold, crossfade, then remove the canvas and the
  observer.
- If the image has not laid out yet (zero size), wait for the `load` event
  or the first non-zero resize before starting.

Integration: in `src/pages/index.mdx` replace the `<Img ... slot="left"/>`
line with `<FourierPortrait ... slot="left"/>` carrying the same
attributes.

## Left to the builder

- Exact edge thresholds, blur radius, thinning method, and mask shape for
  `alex.png`, tuned by eye using the preview PNGs.
- Final K and M after looking at previews.
- Whether to drop the smallest circles from drawing (not from the maths)
  when their radius falls under about one device pixel, to reduce clutter.
- How the script is invoked (arguments, defaults) and where the previews
  go.
- Whether the preview images live in the scratch folder only or also in
  `docs/`.

- Base: the working tree has uncommitted edits to `Heading.astro` (a
  `subtitle` slot) and `index.mdx` (subtitle text). Those are the owner's
  in-progress work. Build on top of the working tree, leave the subtitle
  edits untouched, and do not commit them as part of this feature. (My
  call.)
- The JSON file lives at `src/data/fourier-portrait.json`; `src/data/` is
  new. (My call.)

## Owner questions outstanding

None. The owner supplied the photo on 2026-10-28.

## Chosen parameters (2026-10-30: new photo, one line, face from landmarks)

Photo: on 2026-10-30 the owner replaced the sunset portrait with a frontal,
evenly lit campus photo (`PXL_20260823_213326383.MP(2).jpg`, 628x837, their
own crop of the full frame). It is cropped to `src/assets/alex-campus.jpg`
with `python scripts/crop_square.py <photo> src/assets/alex-campus.jpg --left 30
--top 170 --size 560 --resize 1000`. `alex-sunset.jpg`, its mask and its
landmarks stay in the repo for the record.

Mask: `rembg` (bria-rmbg model), alpha thresholded at 128, committed as
`scripts/fourier_portrait/mask-campus.png`. Face landmarks: mediapipe
FaceLandmarker (offline, one-off) via `scripts/fourier_portrait/landmarks.py`,
committed as `scripts/fourier_portrait/landmarks-campus.json`. Regenerate with:

```
python -m scripts.fourier_portrait.landmarks src/assets/alex-campus.jpg --model <scratch>/face_landmarker.task --out scripts/fourier_portrait/landmarks-campus.json
python -m scripts.fourier_portrait src/assets/alex-campus.jpg --mask scripts/fourier_portrait/mask-campus.png --landmarks scripts/fourier_portrait/landmarks-campus.json --out src/data/fourier-portrait.json --k 700 --m 20000 --sigma 1.5 --low 0.05 --high 0.12 --min-len 12 --max-strokes 320 --focus 0.5,0.4,0.3 --smooth 3 --prune 6 --neck-drop 0.35 --face-cut 1.15 --color "#a3512b"
```

The first command needs `pip install mediapipe` and the model file from
https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
(3.8 MB, kept outside the repo). Only the JSON it writes is used afterwards;
the main pipeline stays numpy/scipy/Pillow.

Owner requests on 2026-10-30, in order: "return to only one path and make it
meaningful", "the face looks uncanny", "come up with a color for the trace",
then the new photo ("do this instead"), then "the face look super uncanny"
and "remove the face from the trace", then (after a blank head outline still read
as uncanny) a choice of "hair and shirt only" with the pen lifted on jumps, and
"reduce the resolution of fourier transform", then "increase the complexity
and length of the curve".

- The silhouette and all edge strokes fold into one closed tour.
- `--focus FX,FY,R` ranks edge strokes by length times a Gaussian of their
  centroid's distance from the face centre (0.5, 0.4, radius 0.3), so hair
  and collar win over background-free clutter. The silhouette is always kept.
- Uncanny, and the face removed: a face's luminance edges are shadow
  terminators and skin folds, not features (on the sunset photo no blur or
  threshold separated them; on the campus photo edges-only still drew the
  neck and cheek shading). Drawing the face from landmarks (brows, eye
  almonds, iris circles, nose, lips, jaw, Chaikin-smoothed) read as a mask;
  an empty head outline read as a hollow face. The shipped drawing is hair,
  ears, collar and shoulders only: the landmarks are used just to clear the
  region (edge strokes with their centroid inside the oval scaled by
  `--face-shrink 0.9`, or inside that oval shifted down by `--neck-drop
  0.35` of its height, are dropped) and `--face-cut 1.15` cuts the
  silhouette and any remaining stroke where it enters the oval scaled by
  1.15, keeping the outside pieces. The photo supplies the face on the fade.
  Omit `--landmarks` for the edges-only drawing. The landmark feature-stroke
  code was removed in the cleanup; it lives in the pre-squash history.
- Pen lifts: every jump between strokes (and the closing jump) is recorded
  as a `[t0, t1]` phase interval in the path's `lifts` array. The
  browser still runs one chain and one tip, but while the phase is inside a
  lift the tip moves without drawing and the trail starts a new subpath when
  the pen comes down. So the connecting lines that crossed the face are gone;
  about 28% of the tour is pen-up travel.
- Colour: `--color "#a3512b"`, a burnt sienna (luma about 0.40 on white),
  picked for the sunset photo and kept for the campus one, where it echoes
  the hair and the brick roofs against the white tee. Circles, arms, tip and
  trail all use it.
- K=700 on M=20000 with 320 edge strokes (lower thresholds 0.05/0.12 and
  min-len 12 to find them): the owner first asked to reduce the Fourier
  resolution (K 1000 to 250 with 110 strokes) and then to increase the
  complexity and length of the curve. The extra strokes are hair strands,
  the collar seam and the shirt folds; the path is about 21000 px long
  before normalisation. 220/500 and 344/900 were previewed as the
  neighbours.

Circles larger than 12% of the canvas width, the static freq-0 term, and
sub-pixel circles are not drawn (their arms still are), per the owner's
earlier request to remove the biggest circles. Trails are kept as
incrementally built Path2D objects.

Earlier settings for the record: K/M were raised 300/2500, 600/5000,
1000/8000, 2400/16000 on 2026-10-28, the last with 8 coloured paths drawn
by simultaneous chains. That multi-path mode, the colour sampling and a
histogram-equalisation option were removed in the 2026-10-30 cleanup (see
the next section); the JSON format and the component still accept several
paths.

## Multiple coloured strokes (2026-10-28, removed 2026-10-30)

For a day the edge strokes were split into spatial clusters (k-means on
stroke centroids), each its own closed path and Fourier series coloured from
the photo, all chains drawing at once. The owner then asked for one path,
and the clustering, colour sampling and K-sharing code went in the cleanup;
it is in the `fourier-portrait-pre-squash` history. What stayed: the JSON
shape `{ "m", "k", "paths": [{ "color": "#rrggbb" | "ink", "coeffs": [[freq, re, im], ...], "lifts": [[t0, t1], ...] }] }`
and the component's one-chain-per-path drawing, so several paths still work.

Also fixed after the whole-branch review: the silhouette no longer traces
the photo's bottom edge (erosion border value), the 2-opt pass no longer
reverses the whole tour each round, the animation clock starts on the first
painted frame (so a tab opened in the background still plays from the start
when shown), chain arms are always drawn to the tip, resizing during the
fade no longer wipes the sketch, and the trail starts at the phase-0 point.

Tests: `python -m pytest scripts/tests -q` (30) and `node --test tests/epicycles.test.ts` (14)
(Node 22.18 or later, for built-in type stripping).
