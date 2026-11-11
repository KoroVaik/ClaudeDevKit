#!/usr/bin/env node
// Full-resolution evidence screenshots from a headless Edge or Chrome, over the DevTools protocol.
// No dependencies (Node 22+: built-in WebSocket and fetch). Read-only by design: it loads pages,
// fills fields and clicks only what the spec lists, and always stops the browser it started.
//
// Why it exists: the in-app browser's screenshot tool returns at most about 800 px wide, however big
// the viewport is, and `zoom` only crops that small image. A 3840x2160 page therefore comes out
// unreadable. This script renders the same page at its real size and saves a PNG of one section.
//
// Usage: web-kit-shot --spec <spec.json> --out <folder>
//
// Spec (JSON):
//   {
//     "size": "3840x2160",                  viewport; default 1920x1080
//     "scale": 1,                           device scale factor: the screen's OS display scaling (1.75 for 175%); default 1
//     "setup": [ ...steps ],                run once, before the shots (sign in here)
//     "shots": [
//       { "name": "dishes-list",            file name without extension
//         "steps": [ ...steps ],            run before the capture; the first is usually {"goto": "<url>"}
//         "selector": "main .dish-list",    capture only this element; omit for the whole viewport
//         "margin": 24,                     with a selector: CSS px of the page around the element, all sides
//         "fullPage": false }               true: the whole page height instead of the viewport
//     ]
//   }
// Steps (one key each):
//   {"goto": "http://localhost:5174/"}      open a URL and wait for the load
//   {"fill": ["css selector", "text"]}      type text; "@C:/path/file.txt" types that file's first line
//                                           (use it for a password, so it never appears in a spec)
//   {"click": "css selector"}               click an element
//   {"press": "Enter"}                      press a key
//   {"waitFor": "css selector"}             wait up to 15 s for an element
//   {"wait": 1000}                          wait milliseconds (animations, fades)
//
// The result is printed as one line per file: "<absolute path> <width>x<height>".

import { spawn, execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';

const args = Object.fromEntries(
  process.argv.slice(2).reduce((acc, a, i, all) => (a.startsWith('--') ? [...acc, [a.slice(2), all[i + 1]]] : acc), []),
);
if (!args.spec || !args.out) {
  console.error('Usage: web-kit-shot --spec <spec.json> --out <folder>');
  process.exit(2);
}
const spec = JSON.parse(readFileSync(args.spec, 'utf8').replace(/^﻿/, ''));
const outDir = resolve(args.out);
mkdirSync(outDir, { recursive: true });
const [vw, vh] = (spec.size || '1920x1080').split('x').map(Number);
const dsf = spec.scale || 1;

function findBrowser() {
  const candidates = [
    process.env.WEB_KIT_BROWSER,
    'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
    'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
    'C:/Program Files/Google/Chrome/Application/chrome.exe',
    '/usr/bin/microsoft-edge',
    '/usr/bin/google-chrome',
    '/usr/bin/chromium',
    '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  ];
  const found = candidates.find((p) => p && existsSync(p));
  if (!found) throw new Error('No Edge or Chrome found; set WEB_KIT_BROWSER to its executable.');
  return found;
}

const profile = mkdtempSync(join(tmpdir(), 'web-kit-shot-'));
const browser = spawn(
  findBrowser(),
  [
    '--headless=new',
    '--remote-debugging-port=0',
    `--user-data-dir=${profile}`,
    '--no-first-run',
    '--no-default-browser-check',
    '--disable-extensions',
    '--hide-scrollbars',
    `--window-size=${vw},${vh}`,
    'about:blank',
  ],
  { stdio: 'ignore' },
);

function stopBrowser() {
  try {
    if (process.platform === 'win32') {
      // Edge hands its work to child processes the PID does not cover: stop everything that uses our profile.
      const ps = `Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*${profile.replace(/'/g, "''")}*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }`;
      execFileSync('powershell', ['-NoProfile', '-Command', ps], { stdio: 'ignore' });
    } else browser.kill('SIGKILL');
  } catch { /* already gone */ }
  try { rmSync(profile, { recursive: true, force: true, maxRetries: 10, retryDelay: 300 }); } catch { /* best effort */ }
}
process.on('exit', stopBrowser);

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function debuggerPort() {
  const file = join(profile, 'DevToolsActivePort');
  for (let i = 0; i < 100; i++) {
    if (existsSync(file)) return readFileSync(file, 'utf8').split('\n')[0].trim();
    await sleep(100);
  }
  throw new Error('The browser did not open its debugging port.');
}

async function connect(port) {
  const targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json();
  const page = targets.find((t) => t.type === 'page');
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = () => rej(new Error('DevTools socket failed')); });
  let id = 0;
  const pending = new Map();
  const waiters = [];
  ws.onmessage = (m) => {
    const msg = JSON.parse(m.data);
    if (msg.id && pending.has(msg.id)) {
      const { res, rej } = pending.get(msg.id);
      pending.delete(msg.id);
      msg.error ? rej(new Error(msg.error.message)) : res(msg.result);
    } else if (msg.method) {
      waiters.filter((w) => w.method === msg.method).forEach((w) => w.res(msg.params));
    }
  };
  const send = (method, params = {}) => new Promise((res, rej) => {
    const myId = ++id;
    pending.set(myId, { res, rej });
    ws.send(JSON.stringify({ id: myId, method, params }));
  });
  const once = (method, ms = 30000) => new Promise((res, rej) => {
    const t = setTimeout(() => rej(new Error(`Timed out waiting for ${method}`)), ms);
    waiters.push({ method, res: (p) => { clearTimeout(t); res(p); } });
  });
  return { send, once, close: () => ws.close() };
}

async function main() {
  const cdp = await connect(await debuggerPort());
  const { send, once } = cdp;
  await send('Page.enable');
  await send('Runtime.enable');
  await send('Emulation.setDeviceMetricsOverride', { width: vw, height: vh, deviceScaleFactor: dsf, mobile: false });

  const evalJs = async (expression) => {
    const r = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
    if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || 'script failed');
    return r.result.value;
  };
  const waitFor = async (selector, ms = 15000) => {
    const end = Date.now() + ms;
    while (Date.now() < end) {
      if (await evalJs(`!!document.querySelector(${JSON.stringify(selector)})`)) return;
      await sleep(150);
    }
    throw new Error(`Element not found: ${selector}`);
  };
  const valueOf = (v) => (typeof v === 'string' && v.startsWith('@') ? readFileSync(v.slice(1), 'utf8').split(/\r?\n/)[0] : v);

  async function run(step) {
    if (step.goto) {
      const loaded = once('Page.loadEventFired');
      await send('Page.navigate', { url: step.goto });
      await loaded;
      await sleep(500); // let the app render after the load event
    } else if (step.fill) {
      const [selector, value] = step.fill;
      await waitFor(selector);
      await evalJs(`document.querySelector(${JSON.stringify(selector)}).focus()`);
      await send('Input.insertText', { text: valueOf(value) });
    } else if (step.click) {
      await waitFor(step.click);
      await evalJs(`document.querySelector(${JSON.stringify(step.click)}).click()`);
      await sleep(500);
    } else if (step.press) {
      await send('Input.dispatchKeyEvent', { type: 'keyDown', key: step.press, code: step.press, text: step.press === 'Enter' ? '\r' : undefined });
      await send('Input.dispatchKeyEvent', { type: 'keyUp', key: step.press, code: step.press });
      await sleep(500);
    } else if (step.waitFor) {
      await waitFor(step.waitFor);
    } else if (step.wait) {
      await sleep(step.wait);
    } else {
      throw new Error(`Unknown step: ${JSON.stringify(step).replace(/"@[^"]*"/g, '"@..."')}`);
    }
  }

  for (const step of spec.setup || []) await run(step);

  for (const shot of spec.shots || []) {
    for (const step of shot.steps || []) await run(step);
    await sleep(300);
    const params = { format: 'png', captureBeyondViewport: true };
    if (shot.selector) {
      await waitFor(shot.selector);
      const r = await evalJs(`(() => { const e = document.querySelector(${JSON.stringify(shot.selector)});
        e.scrollIntoView({block:'start'}); const b = e.getBoundingClientRect();
        return {x: b.left + scrollX, y: b.top + scrollY, width: b.width, height: b.height}; })()`);
      const m = Math.max(0, Number(shot.margin) || 0);
      const x = Math.max(0, r.x - m), y = Math.max(0, r.y - m);
      params.clip = { x, y, width: r.x + r.width + m - x, height: r.y + r.height + m - y, scale: 1 };
    } else if (shot.fullPage) {
      const r = await evalJs('({width: document.documentElement.scrollWidth, height: document.documentElement.scrollHeight})');
      params.clip = { x: 0, y: 0, width: r.width, height: r.height, scale: 1 };
    }
    const { data } = await send('Page.captureScreenshot', params);
    const buf = Buffer.from(data, 'base64');
    const file = join(outDir, `${shot.name}.png`);
    writeFileSync(file, buf);
    console.log(`${file} ${buf.readUInt32BE(16)}x${buf.readUInt32BE(20)}`);
  }
  cdp.close();
}

main().then(() => process.exit(0), (e) => { console.error(`web-kit-shot failed: ${e.message}`); process.exit(1); });
