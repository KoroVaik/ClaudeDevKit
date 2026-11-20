#!/usr/bin/env node
// One owner-facing picture of one state: the mockup and the built screen side by side, at equal height,
// with a very short title line on top that says what the frame shows. No dependencies: it lays the two
// PNGs out in a throwaway page and shoots it with capture.mjs (headless Edge or Chrome).
//
// Why it exists: the owner reads pictures on a phone. A contact sheet of many screens is unreadable there,
// and a mockup and its result sent apart are hard to compare (owner, Zhratva, 2026-11-20). Agents used to
// write one-off image scripts for this.
//
// Usage: web-kit-pair --left <mockup.png> --right <app.png> --title "<short text>" --out <file.png>
//
// Both halves keep their whole frame (each is one full phone window, never cropped); the shorter one is
// scaled up to the taller one's height. The title is at most 60 characters: the essence of the state in
// the owner's words, not "mockup" / "built". Prints one line: "<absolute path> <width>x<height>".

import { spawnSync } from 'node:child_process';
import { existsSync, mkdtempSync, openSync, readSync, closeSync, copyFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const TITLE_MAX = 60;
const args = Object.fromEntries(
  process.argv.slice(2).reduce((acc, a, i, all) => (a.startsWith('--') ? [...acc, [a.slice(2), all[i + 1]]] : acc), []),
);
const fail = (msg, code = 1) => { console.error(`web-kit-pair failed: ${msg}`); process.exit(code); };

if (!args.left || !args.right || !args.title || !args.out || !/\.png$/i.test(args.out)) {
  console.error('Usage: web-kit-pair --left <mockup.png> --right <app.png> --title "<short text>" --out <file.png>');
  process.exit(2);
}
const title = args.title.trim();
if (!title) fail('the title is empty.', 2);
if (title.length > TITLE_MAX) fail(`the title has ${title.length} characters; keep it to ${TITLE_MAX} (a very short line).`, 2);

// Width and height from the PNG header (IHDR follows the 8-byte signature).
function pngSize(path) {
  if (!existsSync(path)) fail(`not found: ${path}`);
  const buf = Buffer.alloc(24);
  const fd = openSync(path, 'r');
  try { readSync(fd, buf, 0, 24, 0); } finally { closeSync(fd); }
  if (buf.readUInt32BE(0) !== 0x89504e47 || buf.toString('ascii', 12, 16) !== 'IHDR') fail(`not a PNG: ${path}`);
  return { w: buf.readUInt32BE(16), h: buf.readUInt32BE(20) };
}

const left = pngSize(resolve(args.left));
const right = pngSize(resolve(args.right));
const height = Math.max(left.h, right.h);
const leftW = Math.round((left.w * height) / left.h);
const rightW = Math.round((right.w * height) / right.h);
const gap = Math.max(8, Math.round(height / 60));
const titleH = Math.max(32, Math.round(height / 16));
const width = leftW + gap + rightW + 2 * gap;
const total = titleH + height + gap;

const esc = (s) => s.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
const html = `<!doctype html><meta charset="utf-8"><style>
html,body{margin:0;background:#fff;overflow:hidden}
#p{display:inline-block;width:${width}px;background:#fff}
.t{height:${titleH}px;display:flex;align-items:center;justify-content:center;font:600 ${Math.round(titleH * 0.5)}px system-ui,sans-serif;color:#111;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;padding:0 ${gap}px}
.r{display:flex;gap:${gap}px;padding:0 ${gap}px ${gap}px}
img{display:block;height:${height}px}
</style><div id="p"><div class="t">${esc(title)}</div><div class="r"><img style="width:${leftW}px" src="${pathToFileURL(resolve(args.left)).href}"><img style="width:${rightW}px" src="${pathToFileURL(resolve(args.right)).href}"></div></div>`;

const work = mkdtempSync(join(tmpdir(), 'web-kit-pair-'));
try {
  const page = join(work, 'pair.html');
  writeFileSync(page, html);
  const spec = join(work, 'spec.json');
  // Board-sized window, so capture.mjs never emulates a phone for a narrow pair.
  writeFileSync(spec, JSON.stringify({
    size: `${Math.max(width, 768)}x${total}`,
    scale: 1,
    shots: [{ name: 'pair', steps: [{ goto: pathToFileURL(page).href }], selector: '#p', fitHeight: false }],
  }));
  const capture = join(dirname(fileURLToPath(import.meta.url)), 'capture.mjs');
  const r = spawnSync(process.execPath, [capture, '--spec', spec, '--out', work], { encoding: 'utf8' });
  if (r.status !== 0) fail((r.stderr || r.stdout || 'capture.mjs failed').trim());
  const out = resolve(args.out);
  rmSync(out, { force: true });
  copyFileSync(join(work, 'pair.png'), out);
  const size = pngSize(out);
  console.log(`${out} ${size.w}x${size.h}`);
} finally {
  rmSync(work, { recursive: true, force: true });
}
