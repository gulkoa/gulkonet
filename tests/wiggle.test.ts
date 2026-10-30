import { test } from 'node:test';
import assert from 'node:assert/strict';
import { WiggleDetector, sampleTrail, type WigglePoint } from '../src/scripts/wiggle.ts';

const STEP = 16; // ms between pointer samples, roughly one per frame

// Triangle wave: a back-and-forth shake of the given frequency and amplitude. Returns the end time.
function shake(d: WiggleDetector, hz: number, amplitude: number, ms: number, t0 = 0) {
  const half = 1000 / hz / 2;
  let t = t0;
  for (; t <= t0 + ms; t += STEP) {
    const phase = ((t - t0) % (2 * half)) / half; // 0..2
    const x = 400 + amplitude * (phase < 1 ? phase * 2 - 1 : 3 - phase * 2);
    d.move(x, 300, t);
  }
  return t;
}

// A slow drift of 1 px per sample (about 60 px/s). Returns the lowest intensity seen and the end time.
function drift(d: WiggleDetector, ms: number, t0: number) {
  let low = Infinity;
  let t = t0;
  for (let i = 0; t <= t0 + ms; i++, t += STEP) {
    d.move(400 + i, 300, t);
    low = Math.min(low, d.intensity(t));
  }
  return { low, t };
}

test('a straight sweep across the page never lights up', () => {
  const d = new WiggleDetector();
  let peak = 0;
  for (let t = 0; t <= 600; t += STEP) {
    d.move(t * 2, 300 + t * 0.2, t); // ~2 px per ms, slightly diagonal
    peak = Math.max(peak, d.intensity(t));
  }
  assert.equal(peak, 0);
});

test('a rapid back-and-forth shake lights up fully', () => {
  const d = new WiggleDetector();
  const t = shake(d, 9, 50, 800);
  assert.equal(d.intensity(t), 1);
  assert.ok(d.isLatched());
});

test('a slow drift on its own never lights up', () => {
  const d = new WiggleDetector();
  assert.equal(drift(d, 2000, 0).low, 0);
});

test('once triggered, the trail keeps following slow movement', () => {
  const d = new WiggleDetector();
  const t = shake(d, 9, 50, 800);
  assert.equal(drift(d, 3000, t).low, 1);
});

test('once triggered, the trail survives a short pause and fades after a long one', () => {
  const d = new WiggleDetector();
  const t = shake(d, 9, 50, 800);
  assert.equal(d.intensity(t + 1000), 1, 'still on after a 1 s pause');
  assert.equal(d.intensity(t + 2500), 0, 'gone after 2.5 s without movement');
  assert.ok(!d.isLatched());
});

test('after the trail has gone, slow movement does not bring it back', () => {
  const d = new WiggleDetector();
  const t = shake(d, 9, 50, 800);
  assert.equal(d.intensity(t + 2500), 0);
  assert.equal(drift(d, 1000, t + 2500).low, 0);
});

test('sub-pixel jitter in place does not count as shaking', () => {
  const d = new WiggleDetector();
  let peak = 0;
  for (let i = 0, t = 0; t <= 800; i++, t += STEP) {
    d.move(400 + (i % 2), 300, t); // alternates 400, 401, 400, 401...
    peak = Math.max(peak, d.intensity(t));
  }
  assert.equal(peak, 0);
});

test('sampleTrail places ghosts by arc length from the newest point backward', () => {
  const points: WigglePoint[] = [];
  for (let i = 0; i <= 10; i++) points.push({ x: i * 10, y: 0, t: i * 16 }); // 0..100 px, oldest first
  const ghosts = sampleTrail(points, 25, 10);
  assert.deepEqual(ghosts.map((g) => Math.round(g.x)), [100, 75, 50, 25, 0]);
  assert.ok(ghosts.every((g) => g.y === 0));
  assert.equal(Math.round(ghosts[1].t), 120); // interpolated: x=75 is at t=120
});

test('sampleTrail caps the number of ghosts', () => {
  const points: WigglePoint[] = [];
  for (let i = 0; i <= 100; i++) points.push({ x: i * 5, y: i * 5, t: i });
  assert.equal(sampleTrail(points, 10, 7).length, 7);
});

test('sampleTrail returns nothing for an empty path', () => {
  assert.deepEqual(sampleTrail([], 10, 10), []);
});
