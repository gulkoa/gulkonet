# Fourier Portrait Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the home page profile photo with a canvas animation in which spinning Fourier epicycles trace a one-line sketch of the portrait, hold, then crossfade into the photo.

**Architecture:** An offline Python package (`scripts/fourier_portrait/`) turns a square crop of the supplied photo into one closed path and writes its Fourier coefficients to `src/data/fourier-portrait.json`. A pure TypeScript module (`src/lib/epicycles.ts`) evaluates the epicycle chain and the animation timeline, unit-tested with Node's built-in runner. An Astro component (`src/components/FourierPortrait.astro`) wraps the existing `Img` with a canvas and drives the animation from a hoisted TS script.

**Tech Stack:** Astro 5, TypeScript (no Svelte, no p5), HTML canvas; Python 3.12 with numpy, scipy, Pillow, pytest for the offline step.

**Spec:** `docs/superpowers/specs/2026-10-28-fourier-portrait-design.md`

## Global Constraints

- No new runtime dependencies. `package.json` is not modified.
- Component is plain TypeScript in an Astro `<script>`; no Svelte, no p5.
- Offline script imports only numpy, scipy, Pillow and the standard library. A background-removal tool (`rembg`) may be run once locally to produce the committed mask, and is never imported by the script.
- Timing: trace 8000 ms, hold 1000 ms, crossfade 1500 ms. Linear phase, driven by elapsed real time.
- No replay control of any kind. Reduced motion: script does nothing and the image stays visible.
- The image is hidden from JavaScript, never from CSS.
- Sketch coordinates are image-frame: x = px / width - 0.5, y = py / height - 0.5. The canvas maps (-0.5, -0.5) to the image's top-left and (0.5, 0.5) to bottom-right, no margin.
- JSON shape: `{ "k": K, "m": M, "coeffs": [[freq, re, im], ...] }`, coefficients sorted by amplitude descending. K in 200 to 500, M in 2000 to 3000.
- `src/assets/alex.png` is left untouched; the crop is saved under a new name.
- The uncommitted edits in `src/components/Heading.astro` and `src/pages/index.mdx` (subtitle slot and text) are the owner's; keep them, and do not include them in any commit of this feature. Commit `index.mdx` only with `git add -p` limited to the `<FourierPortrait>` hunk.

## Review Focus

1. Tab backgrounded mid-trace: `requestAnimationFrame` pauses, elapsed time jumps, and the trace must still be a complete line, not a gap. Test pinned in Task 5 (`tracePoints` fills every intermediate phase step between frames).
2. Image not yet laid out when the script runs (`clientWidth` 0): the animation must wait for the first non-zero size rather than drawing on a 0x0 canvas. Test pinned in Task 5 (`canvasSize` returns null for zero input) and manual check in Task 7.
3. Window resized or phone rotated mid-trace: the trace is stored in unit coordinates and the canvas re-mapped, so the drawn line stays on the face. Test pinned in Task 5 (`toCanvas` mapping) and manual check in Task 7.
4. Strokes chained in a bad order produce long jumps across the face, which a truncated Fourier series renders as ringing. Test pinned in Task 2 (`order_strokes` picks the nearest endpoint and reverses a stroke when that is closer).
5. Reduced-motion visitor must never see the image hidden, even briefly. Test pinned in Task 5 (`shouldAnimate(false)`) and manual check in Task 7.

---

### Task 1: Square crop of the supplied photo

**Files:**
- Create: `scripts/crop_square.py`
- Create: `src/assets/alex-sunset.jpg`

**Interfaces:**
- Produces: `src/assets/alex-sunset.jpg`, square, 1000x1000, used by Task 3 as the sketch source and by Task 7 as the displayed image.

- [ ] **Step 1: Write `scripts/crop_square.py`**

CLI: `python scripts/crop_square.py <in> <out> --left L --top T --size S --resize 1000`. Crops the box `(L, T, L+S, T+S)` with Pillow, resizes to `--resize` with Lanczos, saves JPEG quality 90.

- [ ] **Step 2: Run it against the supplied photo and look at the result**

Run (starting values; adjust by eye so the head and shoulders fill the frame like today's `alex.png`, with the chin roughly two thirds down):

```bash
python scripts/crop_square.py "C:/Users/alexg/Downloads/DSC04521_1.JPG" src/assets/alex-sunset.jpg --left 230 --top 60 --size 1000 --resize 1000
```

Expected: a 1000x1000 JPEG. View it with the Read tool. Iterate on `--left/--top/--size` until the face sits roughly where it does in `alex.png`. Record the final values in the commit message.

- [ ] **Step 3: Commit**

```bash
git add scripts/crop_square.py src/assets/alex-sunset.jpg
git commit -m "feat(portrait): add square crop of new profile photo"
```

---

### Task 2: Edge extraction and path chaining (Python)

**Files:**
- Create: `scripts/fourier_portrait/__init__.py` (empty)
- Create: `scripts/fourier_portrait/edges.py`
- Create: `scripts/fourier_portrait/path.py`
- Create: `scripts/tests/__init__.py` (empty)
- Create: `scripts/tests/test_edges.py`
- Create: `scripts/tests/test_path.py`
- Create: `scripts/conftest.py` (adds repo root to `sys.path` so `import scripts.fourier_portrait` works under pytest)

**Interfaces:**
- Produces (`edges.py`):
  - `load_gray(path: str) -> np.ndarray` float32 HxW in 0..1.
  - `load_mask(path: str, shape: tuple[int, int]) -> np.ndarray` bool HxW, white = True, resized to `shape` if needed.
  - `edge_map(gray: np.ndarray, sigma: float, low: float, high: float, mask: np.ndarray | None) -> np.ndarray` bool HxW. Gaussian blur, Sobel gradient magnitude, hysteresis threshold (pixels above `high` seed, grow into pixels above `low` via `scipy.ndimage.label`), then AND with mask when given.
  - `thin(edges: np.ndarray) -> np.ndarray` bool HxW, one-pixel-wide (Zhang-Suen, pure numpy).
- Produces (`path.py`):
  - `chain_strokes(edges: np.ndarray, min_len: int = 8) -> list[np.ndarray]` each stroke an (n, 2) float array of (x, y) pixel coords, walked from endpoints first; strokes shorter than `min_len` dropped.
  - `order_strokes(strokes: list[np.ndarray]) -> np.ndarray` one (N, 2) array: greedy nearest-endpoint order starting from the longest stroke, reversing a stroke when its far end is nearer, concatenated, closed by appending the first point.
  - `resample(path: np.ndarray, m: int) -> np.ndarray` (m, 2) evenly spaced by arc length along the closed path.
  - `smooth(path: np.ndarray, window: int) -> np.ndarray` circular moving average, same shape.

- [ ] **Step 1: Write failing tests in `scripts/tests/test_edges.py`**

```python
import numpy as np
from scripts.fourier_portrait.edges import edge_map, thin

def ring_image(size=64, r_in=18, r_out=22):
    yy, xx = np.mgrid[:size, :size]
    d = np.hypot(xx - size / 2, yy - size / 2)
    return ((d > r_in) & (d < r_out)).astype(np.float32)

def test_edge_map_finds_ring_edges_only():
    e = edge_map(ring_image(), sigma=1.0, low=0.05, high=0.2, mask=None)
    yy, xx = np.nonzero(e)
    d = np.hypot(xx - 32, yy - 32)
    assert len(d) > 50
    assert np.all((d > 14) & (d < 26))

def test_edge_map_respects_mask():
    mask = np.zeros((64, 64), bool); mask[:, :32] = True
    e = edge_map(ring_image(), sigma=1.0, low=0.05, high=0.2, mask=mask)
    assert e[:, 32:].sum() == 0 and e[:, :32].sum() > 0

def test_thin_makes_one_pixel_lines():
    e = edge_map(ring_image(), sigma=1.0, low=0.05, high=0.2, mask=None)
    t = thin(e)
    assert 0 < t.sum() < e.sum()
    # no 2x2 fully-set block remains
    blocks = t[:-1, :-1] & t[1:, :-1] & t[:-1, 1:] & t[1:, 1:]
    assert blocks.sum() == 0
```

- [ ] **Step 2: Write failing tests in `scripts/tests/test_path.py`**

```python
import numpy as np
from scripts.fourier_portrait.path import chain_strokes, order_strokes, resample, smooth

def test_chain_strokes_walks_a_line_into_one_stroke():
    e = np.zeros((20, 20), bool); e[10, 2:18] = True
    strokes = chain_strokes(e, min_len=4)
    assert len(strokes) == 1 and len(strokes[0]) == 16
    assert strokes[0][0].tolist() in ([2, 10], [17, 10])

def test_chain_strokes_drops_short_strokes():
    e = np.zeros((20, 20), bool); e[10, 2:18] = True; e[3, 3:5] = True
    assert len(chain_strokes(e, min_len=4)) == 1

def test_order_strokes_reverses_to_nearest_endpoint():
    a = np.array([[0, 0], [10, 0]], float)      # longest, starts chain
    b = np.array([[30, 0], [12, 0]], float)     # its far end is nearer to (10,0)
    p = order_strokes([a, b])
    assert p[:4].tolist() == [[0, 0], [10, 0], [12, 0], [30, 0]]
    assert p[-1].tolist() == [0, 0]            # closed

def test_resample_is_even_and_closed():
    sq = np.array([[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]], float)
    r = resample(sq, 40)
    assert r.shape == (40, 2)
    seg = np.linalg.norm(np.diff(np.vstack([r, r[:1]]), axis=0), axis=1)
    assert np.allclose(seg, 1.0, atol=1e-6)

def test_smooth_preserves_shape_and_mean():
    p = np.random.default_rng(0).random((50, 2))
    s = smooth(p, 5)
    assert s.shape == p.shape and np.allclose(s.mean(0), p.mean(0))
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest scripts/tests -q`
Expected: ImportError / ModuleNotFoundError for `scripts.fourier_portrait.edges`.

- [ ] **Step 4: Implement `edges.py` and `path.py` to the interfaces above**

`chain_strokes`: 8-connected walk; start from pixels with exactly one neighbour (endpoints), then from any remaining pixel for loops; mark visited.
`resample`: cumulative arc length with `np.interp` on x and y separately over `np.linspace(0, total, m, endpoint=False)`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest scripts/tests -q`
Expected: 8 passed.

- [ ] **Step 6: Commit**

```bash
git add scripts/fourier_portrait scripts/tests scripts/conftest.py
git commit -m "feat(portrait): edge extraction and single-path chaining"
```

---

### Task 3: Fourier coefficients, JSON, previews, CLI (Python)

**Files:**
- Create: `scripts/fourier_portrait/fourier.py`
- Create: `scripts/fourier_portrait/preview.py`
- Create: `scripts/fourier_portrait/__main__.py`
- Create: `scripts/tests/test_fourier.py`

**Interfaces:**
- Consumes: Task 2 functions.
- Produces (`fourier.py`):
  - `normalize(path: np.ndarray, width: int, height: int) -> np.ndarray` applies x/width - 0.5, y/height - 0.5.
  - `coefficients(path: np.ndarray, k: int) -> list[tuple[int, float, float]]` `(freq, re, im)` for freqs `-k//2 .. k//2` (k odd gives symmetric range; use `range(-(k // 2), k - k // 2)`), computed from `np.fft.fft(x + 1j*y) / m`, sorted by amplitude descending.
  - `reconstruct(coeffs, m: int) -> np.ndarray` (m, 2) sum of `c * exp(2πi f t)` for t in `linspace(0, 1, m, endpoint=False)`.
  - `write_json(coeffs, k: int, m: int, out_path: str) -> None` exact shape from Global Constraints, floats rounded to 6 decimals.
- Produces (`preview.py`): `render(path: np.ndarray, size: int, out_path: str) -> None` draws a unit-box path onto a white `size`x`size` PNG with a 2 px black line.
- Produces (`__main__.py`): `python -m scripts.fourier_portrait <image> --mask <png> --out src/data/fourier-portrait.json --k 300 --m 2500 --sigma 1.5 --low 0.04 --high 0.12 --min-len 12 --smooth 3 --previews <dir>`. Writes the JSON and, under `--previews`, `path.png` plus `recon-100.png`, `recon-200.png`, `recon-400.png`.

- [ ] **Step 1: Write failing tests in `scripts/tests/test_fourier.py`**

```python
import json, numpy as np
from scripts.fourier_portrait.fourier import normalize, coefficients, reconstruct, write_json

def unit_circle(m=256):
    t = np.linspace(0, 2 * np.pi, m, endpoint=False)
    return np.stack([np.cos(t), np.sin(t)], 1) * 0.4

def test_normalize_maps_image_frame_to_unit_box():
    p = normalize(np.array([[0, 0], [100, 50]], float), 100, 50)
    assert p.tolist() == [[-0.5, -0.5], [0.5, 0.5]]

def test_circle_has_single_dominant_coefficient_at_freq_1():
    c = coefficients(unit_circle(), k=21)
    assert len(c) == 21
    f, re, im = c[0]
    assert f == 1 and abs(re - 0.4) < 1e-6 and abs(im) < 1e-6
    assert abs(c[1][1]) < 1e-6 and abs(c[1][2]) < 1e-6

def test_reconstruct_round_trips_circle():
    p = unit_circle()
    r = reconstruct(coefficients(p, k=21), 256)
    assert np.allclose(r, p, atol=1e-6)

def test_write_json_shape(tmp_path):
    out = tmp_path / "c.json"
    write_json(coefficients(unit_circle(), k=5), 5, 256, str(out))
    d = json.loads(out.read_text())
    assert d["k"] == 5 and d["m"] == 256 and len(d["coeffs"]) == 5
    assert all(len(c) == 3 and isinstance(c[0], int) for c in d["coeffs"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest scripts/tests/test_fourier.py -q`
Expected: ModuleNotFoundError.

- [ ] **Step 3: Implement `fourier.py`, `preview.py`, `__main__.py`**

- [ ] **Step 4: Run all tests**

Run: `python -m pytest scripts/tests -q`
Expected: 12 passed.

- [ ] **Step 5: Smoke the CLI on a synthetic ring**

Write a 200x200 ring PNG to the scratchpad with Pillow, run the CLI on it with `--previews` into the scratchpad, and view `recon-100.png` with the Read tool.
Expected: a clean circle, and a JSON with `k` coefficients.

- [ ] **Step 6: Commit**

```bash
git add scripts/fourier_portrait scripts/tests
git commit -m "feat(portrait): Fourier coefficients, previews and CLI"
```

---

### Task 4: Subject mask and the real coefficient file

**Files:**
- Create: `scripts/fourier_portrait/mask.png` (1000x1000, white = keep)
- Create: `src/data/fourier-portrait.json`
- Modify: `docs/superpowers/specs/2026-10-28-fourier-portrait-design.md` (record final parameters in a short "Chosen parameters" line at the end)

**Interfaces:**
- Consumes: Task 1 crop, Task 3 CLI.
- Produces: `src/data/fourier-portrait.json` imported by Task 6.

- [ ] **Step 1: Produce the mask**

Preferred: `pip install rembg onnxruntime` in a throwaway venv, run `rembg i src/assets/alex-sunset.jpg <scratch>/cutout.png`, then threshold its alpha at 128 and save as `scripts/fourier_portrait/mask.png` with Pillow. Fallback if that fails: build the mask as a filled polygon traced by hand over the crop (list the vertices in a tiny `scripts/make_mask.py`). Either way view the mask with the Read tool: the face, hair, neck and shirt should be white, everything else black.

- [ ] **Step 2: Run the pipeline with previews**

```bash
python -m scripts.fourier_portrait src/assets/alex-sunset.jpg --mask scripts/fourier_portrait/mask.png --out src/data/fourier-portrait.json --k 300 --m 2500 --previews <scratchpad>/previews
```

View `path.png`, then `recon-100.png`, `recon-200.png`, `recon-400.png`. Tune `--sigma`, `--low`, `--high`, `--min-len`, `--smooth` until `path.png` reads as a recognisable face with few long jumps, and pick the smallest K whose reconstruction still shows eyes, nose, mouth and hairline. Set that K. Do not integrate a path that reconstructs as mush.

- [ ] **Step 3: Check the JSON**

Run: `python -c "import json;d=json.load(open('src/data/fourier-portrait.json'));print(d['k'],d['m'],len(d['coeffs']))"` and check file size is under 20 KB.
Expected: `k` matches, `len(coeffs) == k`.

- [ ] **Step 4: Commit**

```bash
git add scripts/fourier_portrait/mask.png src/data/fourier-portrait.json docs/superpowers/specs/2026-10-28-fourier-portrait-design.md
git commit -m "feat(portrait): subject mask and generated Fourier coefficients"
```

---

### Task 5: Epicycle maths and timeline (TypeScript, pure)

**Files:**
- Create: `src/lib/epicycles.ts`
- Create: `tests/epicycles.test.ts` (outside `src/` so `astro check`, whose tsconfig includes only `src/**`, does not reject the `.ts` import extension Node needs)

**Interfaces:**
- Produces:
  - `export type Coeff = { freq: number; re: number; im: number }`
  - `export type Point = { x: number; y: number }`
  - `export function parseCoeffs(raw: { coeffs: number[][] }): Coeff[]`
  - `export function chainPoints(coeffs: Coeff[], phase: number): Point[]` returns `coeffs.length + 1` joints starting at `{x:0,y:0}`; joint i+1 = joint i + c_i rotated by `2π · freq · phase`. The last joint is the pen tip. `phase` in 0..1.
  - `export function tracePoints(coeffs: Coeff[], fromPhase: number, toPhase: number, step: number): Point[]` tips at `fromPhase + step`, `fromPhase + 2·step`, ... while strictly less than `end = min(toPhase, 1)`, then `end` itself as the last point (use a 1e-9 epsilon on the comparison). Returns `[]` when `end <= fromPhase`. A frame gap of any size therefore yields a continuous trail that lands exactly on `end`.
  - `export const TRACE_MS = 8000, HOLD_MS = 1000, FADE_MS = 1500`
  - `export type Stage = 'trace' | 'hold' | 'fade' | 'done'`
  - `export function timeline(elapsedMs: number): { stage: Stage; phase: number }` phase = min(elapsed / TRACE_MS, 1).
  - `export function toCanvas(p: Point, width: number, height: number): Point` maps unit box to pixels: `x = (p.x + 0.5) * width`.
  - `export function canvasSize(clientW: number, clientH: number, dpr: number): { w: number; h: number } | null` null when either dimension is 0.
  - `export function shouldAnimate(reducedMotion: boolean): boolean`

- [ ] **Step 1: Write failing tests in `src/lib/epicycles.test.ts`**

```ts
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parseCoeffs, chainPoints, tracePoints, timeline, toCanvas, canvasSize, shouldAnimate, TRACE_MS, HOLD_MS, FADE_MS } from '../src/lib/epicycles.ts';

const near = (a: number, b: number) => assert.ok(Math.abs(a - b) < 1e-9, `${a} !~ ${b}`);

test('parseCoeffs maps triples', () => {
  assert.deepEqual(parseCoeffs({ coeffs: [[1, 0.5, -0.25]] }), [{ freq: 1, re: 0.5, im: -0.25 }]);
});

test('chainPoints rotates a single unit vector', () => {
  const c = [{ freq: 1, re: 1, im: 0 }];
  const p0 = chainPoints(c, 0); near(p0[1].x, 1); near(p0[1].y, 0);
  const p1 = chainPoints(c, 0.25); near(p1[1].x, 0); near(p1[1].y, 1);
  assert.equal(p0.length, 2);
});

test('chainPoints sums joints tip to tail', () => {
  const c = [{ freq: 0, re: 0.1, im: 0.2 }, { freq: 2, re: 0.3, im: 0 }];
  const p = chainPoints(c, 0.5);
  near(p[1].x, 0.1); near(p[1].y, 0.2); near(p[2].x, 0.4); near(p[2].y, 0.2);
});

test('tracePoints fills every step in a gap and clamps to 1', () => {
  const c = [{ freq: 1, re: 1, im: 0 }];
  const pts = tracePoints(c, 0.1, 0.5, 0.1);
  assert.equal(pts.length, 4);
  near(pts[pts.length - 1].x, Math.cos(2 * Math.PI * 0.5));
  assert.equal(tracePoints(c, 0.95, 1.4, 0.1).length, 1);
  assert.equal(tracePoints(c, 0.5, 0.5, 0.1).length, 0);
});

test('timeline stages at the spec boundaries', () => {
  assert.deepEqual(timeline(0), { stage: 'trace', phase: 0 });
  assert.deepEqual(timeline(TRACE_MS / 2), { stage: 'trace', phase: 0.5 });
  assert.equal(timeline(TRACE_MS).stage, 'hold');
  assert.equal(timeline(TRACE_MS + HOLD_MS).stage, 'fade');
  assert.equal(timeline(TRACE_MS + HOLD_MS + FADE_MS).stage, 'done');
  assert.equal(timeline(TRACE_MS + 1).phase, 1);
});

test('toCanvas maps the unit box onto pixels', () => {
  assert.deepEqual(toCanvas({ x: -0.5, y: -0.5 }, 400, 400), { x: 0, y: 0 });
  assert.deepEqual(toCanvas({ x: 0.5, y: 0 }, 400, 200), { x: 400, y: 100 });
});

test('canvasSize is null before layout and scales by dpr', () => {
  assert.equal(canvasSize(0, 400, 2), null);
  assert.deepEqual(canvasSize(400, 300, 2), { w: 800, h: 600 });
});

test('shouldAnimate is false under reduced motion', () => {
  assert.equal(shouldAnimate(true), false);
  assert.equal(shouldAnimate(false), true);
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `node --test tests/epicycles.test.ts`
Expected: fails to import `../src/lib/epicycles.ts`.

- [ ] **Step 3: Implement `src/lib/epicycles.ts`**

Note `freq` 0 contributes a constant offset. No DOM access in this file.

- [ ] **Step 4: Run tests to verify they pass**

Run: `node --test tests/epicycles.test.ts`
Expected: 8 pass, 0 fail.

- [ ] **Step 5: Commit**

```bash
git add src/lib/epicycles.ts tests/epicycles.test.ts
git commit -m "feat(portrait): epicycle chain maths and animation timeline"
```

---

### Task 6: The Astro component

**Files:**
- Create: `src/components/FourierPortrait.astro`

**Interfaces:**
- Consumes: `src/lib/epicycles.ts` (Task 5), `src/data/fourier-portrait.json` (Task 4), `src/components/Img.astro`.
- Produces: `<FourierPortrait filename alt width loading class scales />` accepting exactly the props the home page currently gives `<Img>`, forwarding all of them to `<Img>`.

- [ ] **Step 1: Write the markup and styles**

```astro
---
import Img from './Img.astro';
const props = Astro.props;
---
<div class="fourier-portrait" data-fourier-portrait>
  <Img {...props} />
  <canvas class="fourier-canvas" aria-hidden="true"></canvas>
</div>
```

Styles: wrapper `position: relative; display: inline-block; line-height: 0`; canvas `position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; opacity: 0; transition: opacity 1500ms ease`. Image gets `transition: opacity 1500ms ease` through a `:global(.fourier-portrait img)` rule, since `Img.astro` renders the `<img>` with its own scoped styles. No CSS hides the image.

- [ ] **Step 2: Write the hoisted script**

`<script>` (TS) that, for each `[data-fourier-portrait]`:

1. `if (!shouldAnimate(matchMedia('(prefers-reduced-motion: reduce)').matches)) return;`
2. Parse coefficients from the imported JSON once. Read `getComputedStyle(wrapper).color` as the ink colour.
3. Wait for a non-zero `canvasSize(img.clientWidth, img.clientHeight, devicePixelRatio)`; if null, listen for `img` `load` and a `ResizeObserver` on the wrapper and retry.
4. On start: set `img.style.opacity = '0'`, canvas opacity 1, record `performance.now()`.
5. `ResizeObserver` keeps canvas pixel size in sync and triggers a full redraw of the stored trail (unit coords) via `toCanvas`.
6. Frame loop: `timeline(now - start)`; in `trace`, append `tracePoints(coeffs, lastPhase, phase, 1 / m)` to the trail; draw trail (full opacity, line width 2 css px, round joins/caps), then circles (alpha 0.15, width 1) and radii (alpha 0.5, width 1) from `chainPoints`, skipping circles with radius under 1 css px, and a 3 px dot at the tip. In `hold`, draw the trail only. In `fade`, set canvas opacity 0 and img opacity 1 once, keep drawing nothing. In `done`, cancel the loop, disconnect the observer, remove the canvas.
7. Draw with `ctx.setTransform(dpr, 0, 0, dpr, 0, 0)` so all sizes are in CSS pixels.

- [ ] **Step 3: Type-check**

Run: `npx astro check`
Expected: 0 errors (warnings about pre-existing files are fine).

- [ ] **Step 4: Commit**

```bash
git add src/components/FourierPortrait.astro
git commit -m "feat(portrait): FourierPortrait component"
```

---

### Task 7: Wire into the home page and verify in a browser

**Files:**
- Modify: `src/pages/index.mdx:9,17` (import and the `slot="left"` tag only)

**Interfaces:**
- Consumes: Task 6 component.

- [ ] **Step 1: Swap the tag**

Add `import FourierPortrait from '../components/FourierPortrait.astro';` and replace the `<Img ... slot="left"/>` line with:

```mdx
<FourierPortrait filename="alex-sunset.jpg" alt="Alex Gulko" width="400" loading="eager" class="padding" scales slot="left"/>
```

Leave the subtitle lines exactly as they are.

- [ ] **Step 2: Run the dev server and watch it**

Run: `npm run dev` in the background, open the home page with the browser tools, and record a GIF named `fourier_portrait.gif` of the full 10.5 seconds. Check: circles and tip visible, line lands on the face, hold, crossfade, photo at the end with no layout shift (compare heading height before and after). Read the console for errors.

- [ ] **Step 3: Manual checks for Review Focus**

- Narrow the window under 800px mid-trace: line stays on the face.
- Emulate `prefers-reduced-motion: reduce` (DevTools rendering panel) and reload: photo shown immediately, no canvas.
- Switch tabs for 3 seconds mid-trace and return: trail has no gap.

- [ ] **Step 4: Build**

Run: `npm run build`
Expected: `astro check` and `astro build` succeed.

- [ ] **Step 5: Commit the hunk only**

```bash
git add -p src/pages/index.mdx   # accept only the import and the FourierPortrait hunks
git commit -m "feat(portrait): replace home page photo with Fourier portrait"
```

Verify with `git diff --cached` before committing that no subtitle lines are staged, and with `git status` after that `Heading.astro` and the subtitle hunk are still unstaged.
