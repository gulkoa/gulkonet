import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  parseCoeffs, chainPoints, tracePoints, timeline, toCanvas, canvasSize, shouldAnimate,
  TRACE_MS, HOLD_MS, FADE_MS,
} from '../src/lib/epicycles.ts';

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

test('parsePaths maps colours and coefficient triples per path', async () => {
  const { parsePaths } = await import('../src/lib/epicycles.ts');
  const raw = { m: 10, k: 2, paths: [{ color: '#112233', coeffs: [[1, 0.5, -0.25]] }, { color: '#445566', coeffs: [[-1, 0, 1]] }] };
  assert.deepEqual(parsePaths(raw), [
    { color: '#112233', coeffs: [{ freq: 1, re: 0.5, im: -0.25 }], lifts: [] },
    { color: '#445566', coeffs: [{ freq: -1, re: 0, im: 1 }], lifts: [] },
  ]);
});

test('circleVisible hides the static term, sub-pixel circles and the largest circles', async () => {
  const { circleVisible, MAX_CIRCLE_FRACTION } = await import('../src/lib/epicycles.ts');
  const width = 400;
  assert.equal(circleVisible({ freq: 0, re: 0.3, im: 0 }, width), false);          // constant offset, never spins
  assert.equal(circleVisible({ freq: 1, re: 0.001, im: 0 }, width), false);        // under one CSS pixel
  assert.equal(circleVisible({ freq: 1, re: 0.05, im: 0 }, width), true);          // 20 px: drawn
  assert.equal(circleVisible({ freq: 1, re: MAX_CIRCLE_FRACTION + 0.01, im: 0 }, width), false); // too big
});

test('tipPoint equals the last joint of chainPoints', async () => {
  const { tipPoint } = await import('../src/lib/epicycles.ts');
  const c = [{ freq: 0, re: 0.1, im: 0.2 }, { freq: 2, re: 0.3, im: -0.1 }, { freq: -3, re: 0.05, im: 0.07 }];
  for (const phase of [0, 0.13, 0.5, 0.99]) {
    const last = chainPoints(c, phase).at(-1)!;
    const tip = tipPoint(c, phase);
    near(tip.x, last.x); near(tip.y, last.y);
  }
});

test('penDown is false inside a lift interval and true elsewhere', async () => {
  const { penDown } = await import('../src/lib/epicycles.ts');
  const lifts = [{ from: 0.2, to: 0.3 }, { from: 0.9, to: 1 }];
  assert.equal(penDown(lifts, 0.1), true);
  assert.equal(penDown(lifts, 0.25), false);
  assert.equal(penDown(lifts, 0.3), true);
  assert.equal(penDown(lifts, 0.95), false);
  assert.equal(penDown([], 0.5), true);
});

test('tracePhases lists the phases tracePoints samples', async () => {
  const { tracePhases } = await import('../src/lib/epicycles.ts');
  const ph = tracePhases(0.1, 0.35, 0.1);
  assert.equal(ph.length, 3);
  near(ph[0], 0.2); near(ph[1], 0.3); near(ph[2], 0.35);
  assert.deepEqual(tracePhases(0.5, 0.5, 0.1), []);
  near(tracePhases(0.95, 1.4, 0.1).at(-1)!, 1);
});

test('parsePaths reads optional lifts', async () => {
  const { parsePaths } = await import('../src/lib/epicycles.ts');
  const specs = parsePaths({ paths: [
    { color: '#abc', coeffs: [[1, 0.5, 0]], lifts: [[0.1, 0.2]] },
    { color: 'ink', coeffs: [[1, 0.5, 0]] },
  ] });
  assert.deepEqual(specs[0].lifts, [{ from: 0.1, to: 0.2 }]);
  assert.deepEqual(specs[1].lifts, []);
});
