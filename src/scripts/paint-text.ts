// While the cursor trail is latched, the characters the pointer passes over turn rainbow:
// each touched character is wrapped in a span with its own hue.

/** Elements whose text is left alone. */
const SKIP = 'script, style, textarea, input, select, button, svg, canvas, [contenteditable], .katex, .project-card-letters, #command-dialog, .rainbow-char';

interface Caret { node: Node; offset: number }

function caretAt(x: number, y: number): Caret | null {
  const doc = document as any;
  if (typeof doc.caretPositionFromPoint === 'function') {
    const p = doc.caretPositionFromPoint(x, y);
    return p ? { node: p.offsetNode, offset: p.offset } : null;
  }
  if (typeof doc.caretRangeFromPoint === 'function') {
    const r = doc.caretRangeFromPoint(x, y);
    return r ? { node: r.startContainer, offset: r.startOffset } : null;
  }
  return null;
}

function rectOf(node: Text, start: number, end: number): DOMRect | null {
  const range = document.createRange();
  range.setStart(node, start);
  range.setEnd(node, end);
  const rects = range.getClientRects();
  return rects.length ? rects[0] : null;
}

function wrap(node: Text, start: number, end: number, hue: number): void {
  const range = document.createRange();
  range.setStart(node, start);
  range.setEnd(node, end);
  const span = document.createElement('span');
  span.className = 'rainbow-char';
  span.style.color = `hsl(${hue} 100% 50%)`;
  range.surroundContents(span);
}

/** Paints the character under (x, y), if there is one. Returns true when something was painted. */
export function paintTextAt(x: number, y: number, nextHue: () => number): boolean {
  const caret = caretAt(x, y);
  if (!caret || caret.node.nodeType !== Node.TEXT_NODE) return false;
  const node = caret.node as Text;
  const parent = node.parentElement;
  if (!parent || parent.closest(SKIP)) return false;
  const text = node.data;
  // The caret lands between characters; the touched glyph is on one side of it.
  for (const i of [caret.offset, caret.offset - 1]) {
    if (i < 0 || i >= text.length) continue;
    let start = i;
    let end = i + 1;
    const code = text.charCodeAt(i);
    if (code >= 0xdc00 && code <= 0xdfff) start = i - 1; // low surrogate: keep the pair together
    else if (code >= 0xd800 && code <= 0xdbff) end = i + 2; // high surrogate
    if (start < 0 || end > text.length) continue;
    if (/^\s+$/.test(text.slice(start, end))) continue;
    const rect = rectOf(node, start, end);
    if (!rect || x < rect.left || x > rect.right || y < rect.top || y > rect.bottom) continue;
    wrap(node, start, end, nextHue());
    return true;
  }
  return false;
}

/** Paints every character along the straight line from (x0, y0) to (x1, y1). */
export function paintTextAlong(x0: number, y0: number, x1: number, y1: number, nextHue: () => number, step = 4): void {
  const n = Math.max(1, Math.ceil(Math.hypot(x1 - x0, y1 - y0) / step));
  for (let s = 0; s <= n; s++) {
    paintTextAt(x0 + ((x1 - x0) * s) / n, y0 + ((y1 - y0) * s) / n, nextHue);
  }
}
