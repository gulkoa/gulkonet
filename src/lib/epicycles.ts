// Pure maths for the Fourier portrait: no DOM access in this file.

export type Coeff = { freq: number; re: number; im: number };
export type Point = { x: number; y: number };
export type Stage = 'trace' | 'hold' | 'fade' | 'done';

export const TRACE_MS = 8000;
export const HOLD_MS = 1000;
export const FADE_MS = 1500;

const EPS = 1e-9;

export function parseCoeffs(raw: { coeffs: number[][] }): Coeff[] {
  return raw.coeffs.map(([freq, re, im]) => ({ freq, re, im }));
}

/** Joints of the epicycle chain at `phase` (0..1): origin first, pen tip last. */
export function chainPoints(coeffs: Coeff[], phase: number): Point[] {
  const joints: Point[] = [{ x: 0, y: 0 }];
  let x = 0;
  let y = 0;
  for (const c of coeffs) {
    const angle = 2 * Math.PI * c.freq * phase;
    const cos = Math.cos(angle);
    const sin = Math.sin(angle);
    x += c.re * cos - c.im * sin;
    y += c.re * sin + c.im * cos;
    joints.push({ x, y });
  }
  return joints;
}

/** The pen tip at `phase` without building the joint array. */
export function tipPoint(coeffs: Coeff[], phase: number): Point {
  let x = 0;
  let y = 0;
  for (const c of coeffs) {
    const angle = 2 * Math.PI * c.freq * phase;
    const cos = Math.cos(angle);
    const sin = Math.sin(angle);
    x += c.re * cos - c.im * sin;
    y += c.re * sin + c.im * cos;
  }
  return { x, y };
}

const tip = tipPoint;

/**
 * The phases fromPhase+step, fromPhase+2*step, ... while strictly below
 * end = min(toPhase, 1), then end itself. Empty when end <= fromPhase.
 */
export function tracePhases(fromPhase: number, toPhase: number, step: number): number[] {
  const end = Math.min(toPhase, 1);
  if (end <= fromPhase + EPS) return [];
  const out: number[] = [];
  for (let p = fromPhase + step; p < end - EPS; p += step) out.push(p);
  out.push(end);
  return out;
}

/** Pen tips at each of tracePhases(fromPhase, toPhase, step). */
export function tracePoints(coeffs: Coeff[], fromPhase: number, toPhase: number, step: number): Point[] {
  return tracePhases(fromPhase, toPhase, step).map((p) => tip(coeffs, p));
}

/** A phase interval [from, to) during which the pen is lifted (a jump between strokes). */
export type Lift = { from: number; to: number };

/** Whether the pen is down (drawing) at `phase`. */
export function penDown(lifts: Lift[], phase: number): boolean {
  for (const l of lifts) if (phase >= l.from && phase < l.to) return false;
  return true;
}

export function timeline(elapsedMs: number): { stage: Stage; phase: number } {
  const phase = Math.min(elapsedMs / TRACE_MS, 1);
  if (elapsedMs < TRACE_MS) return { stage: 'trace', phase };
  if (elapsedMs < TRACE_MS + HOLD_MS) return { stage: 'hold', phase };
  if (elapsedMs < TRACE_MS + HOLD_MS + FADE_MS) return { stage: 'fade', phase };
  return { stage: 'done', phase };
}

/** Unit box (-0.5..0.5) to CSS pixels: (-0.5,-0.5) is the image's top-left. */
export function toCanvas(p: Point, width: number, height: number): Point {
  return { x: (p.x + 0.5) * width, y: (p.y + 0.5) * height };
}

export function canvasSize(clientW: number, clientH: number, dpr: number): { w: number; h: number } | null {
  if (clientW <= 0 || clientH <= 0) return null;
  return { w: Math.round(clientW * dpr), h: Math.round(clientH * dpr) };
}

export function shouldAnimate(reducedMotion: boolean): boolean {
  return !reducedMotion;
}

export type PathSpec = { color: string; coeffs: Coeff[]; lifts: Lift[] };

export function parsePaths(raw: { paths: { color: string; coeffs: number[][]; lifts?: number[][] }[] }): PathSpec[] {
  return raw.paths.map((p) => ({
    color: p.color,
    coeffs: parseCoeffs(p),
    lifts: (p.lifts ?? []).map(([from, to]) => ({ from, to })),
  }));
}

/** Circles larger than this fraction of the canvas width are not drawn (their arms still are). */
export const MAX_CIRCLE_FRACTION = 0.12;

/** Whether a coefficient's circle is worth drawing: it spins, is at least a pixel, and is not huge. */
export function circleVisible(c: Coeff, width: number): boolean {
  if (c.freq === 0) return false;
  const r = Math.hypot(c.re, c.im);
  return r * width >= 1 && r <= MAX_CIRCLE_FRACTION;
}
