// Shake detection for the cursor-trail easter egg. Pure logic, no DOM, so it can be unit tested.

export interface WigglePoint { x: number; y: number; t: number }

export interface WiggleOptions {
  /** Pointer deltas shorter than this many px are treated as jitter and ignored. */
  minDelta?: number;
  /** Time constant (ms) of the energy decay while the trail is still charging up. */
  decayMs?: number;
  /** Energy at which the effect starts to show. */
  onEnergy?: number;
  /** Energy at which the effect is fully on and latches. */
  fullEnergy?: number;
  /** Once latched, how long (ms) the trail survives without any pointer movement. */
  holdMs?: number;
  /** How long (ms) the trail takes to fade after the hold runs out. */
  fadeMs?: number;
}

const DEFAULTS: Required<WiggleOptions> = {
  minDelta: 3,
  decayMs: 350,
  onEnergy: 2.5,
  fullEnergy: 4.5,
  holdMs: 1500,
  fadeMs: 500,
};

function smoothstep(k: number): number {
  if (k <= 0) return 0;
  if (k >= 1) return 1;
  return k * k * (3 - 2 * k);
}

/**
 * Counts direction reversals of the pointer. Each reversal adds one unit of energy; energy decays
 * exponentially with time, so speed alone never counts: a fast sweep across the page stays dark
 * while a back-and-forth shake charges up. Once the energy reaches `fullEnergy` the detector
 * latches: the trail then follows the pointer at any speed and only lets go after the pointer
 * has been still for `holdMs`.
 */
export class WiggleDetector {
  private readonly options: Required<WiggleOptions>;
  private energy = 0;
  private energyT = 0;
  private anchorX = NaN;
  private anchorY = NaN;
  private prevDx = 0;
  private prevDy = 0;
  private latched = false;
  private lastMoveT = -Infinity;

  constructor(options: WiggleOptions = {}) {
    this.options = { ...DEFAULTS, ...options };
  }

  /** Feed every pointer position, with its timestamp in ms. */
  move(x: number, y: number, t: number): void {
    this.decay(t);
    if (Number.isNaN(this.anchorX)) {
      this.anchorX = x;
      this.anchorY = y;
      return;
    }
    const dx = x - this.anchorX;
    const dy = y - this.anchorY;
    if (Math.hypot(dx, dy) < this.options.minDelta) return; // jitter: wait until the pointer really moved
    this.lastMoveT = t;
    if (dx * this.prevDx + dy * this.prevDy < 0) {
      this.energy += 1; // direction reversed
      if (this.energy >= this.options.fullEnergy) this.latched = true;
    }
    this.prevDx = dx;
    this.prevDy = dy;
    this.anchorX = x;
    this.anchorY = y;
  }

  /** 0 when calm, 1 when shaking hard or latched, smooth in between. */
  intensity(t: number): number {
    this.decay(t);
    if (this.latched) {
      const idle = t - this.lastMoveT;
      if (idle <= this.options.holdMs) return 1;
      if (idle < this.options.holdMs + this.options.fadeMs) {
        return smoothstep(1 - (idle - this.options.holdMs) / this.options.fadeMs);
      }
      this.latched = false; // let go: the next shake has to charge up again
      this.energy = 0;
    }
    return smoothstep((this.energy - this.options.onEnergy) / (this.options.fullEnergy - this.options.onEnergy));
  }

  /** True while the trail is following the pointer regardless of speed. */
  isLatched(): boolean {
    return this.latched;
  }

  reset(): void {
    this.energy = 0;
    this.anchorX = NaN;
    this.anchorY = NaN;
    this.prevDx = 0;
    this.prevDy = 0;
    this.latched = false;
    this.lastMoveT = -Infinity;
  }

  private decay(t: number): void {
    if (t > this.energyT) this.energy *= Math.exp(-(t - this.energyT) / this.options.decayMs);
    this.energyT = Math.max(this.energyT, t);
  }
}

/**
 * Walks the path from its newest point backward and returns one ghost position every `spacing` px
 * of arc length, newest first, at most `maxGhosts` of them. Timestamps are interpolated.
 */
export function sampleTrail(points: WigglePoint[], spacing: number, maxGhosts: number): WigglePoint[] {
  const ghosts: WigglePoint[] = [];
  if (points.length === 0 || maxGhosts <= 0) return ghosts;
  const head = points[points.length - 1];
  ghosts.push({ x: head.x, y: head.y, t: head.t });
  if (!(spacing > 0)) return ghosts;
  let remaining = spacing;
  for (let i = points.length - 1; i > 0 && ghosts.length < maxGhosts; i--) {
    let ax = points[i].x;
    let ay = points[i].y;
    let at = points[i].t;
    const b = points[i - 1];
    let segLen = Math.hypot(b.x - ax, b.y - ay);
    while (segLen >= remaining && ghosts.length < maxGhosts) {
      const f = remaining / segLen;
      ax += (b.x - ax) * f;
      ay += (b.y - ay) * f;
      at += (b.t - at) * f;
      ghosts.push({ x: ax, y: ay, t: at });
      segLen -= remaining;
      remaining = spacing;
    }
    remaining -= segLen;
  }
  return ghosts;
}
