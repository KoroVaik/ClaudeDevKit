// Builds the mockup pages (*.html) from the JSON specs in <mockups folder>/src/.
// Usage: node build-mockups.mjs [--dir <mockups folder>]            write the HTML files
//        node build-mockups.mjs [--dir <mockups folder>] --check    validate specs, fail if generated files are stale
// The mockups folder defaults to docs/mockups under the git root of the current directory and must exist.
// A spec with "frame": "desktop" draws wide admin-style screens instead of phones (one mockups folder per frame kind).
// Optional <mockups folder>/mockups.config.json: { "title", "pageNote", "indexNote", "indexIntro", "filterPlaceholder", "screenCount", "userLetters", "stepTitle" }. Every page embeds the folder's mockups.css; a mockups.css missing from the folder is written from default-mockups.css
// (next to this script); an existing one is the project's and is never touched.
// Optional <mockups folder>/parts/<name>.json: a JSON array of blocks that specs reuse with { "type": "part", "name": "<name>" }. The spec format is in skills/draw-mockup/spec-format.md. No dependencies.
import { spawnSync } from 'node:child_process';
import { existsSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { dirname, join, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const args = process.argv.slice(2);
const dirFlag = args.indexOf('--dir');
const dirName = dirFlag >= 0 ? args[dirFlag + 1] : undefined;
if (dirFlag >= 0 && !dirName) {
  console.error('--dir needs a folder');
  process.exit(1);
}

function projectRoot() {
  const result = spawnSync('git', ['rev-parse', '--show-toplevel'], { encoding: 'utf8' });
  if (result.status !== 0) {
    console.error('Not inside a git repository, so the project root is unknown: pass --dir <mockups folder>.');
    process.exit(1);
  }
  return result.stdout.trim();
}

const mockupsDir = dirName ? resolve(process.cwd(), dirName) : join(projectRoot(), 'docs', 'mockups');
const srcDir = join(mockupsDir, 'src');
const partsDir = join(mockupsDir, 'parts');
const checkOnly = args.includes('--check');
const shownDir = relative(process.cwd(), mockupsDir).split(sep).join('/') || '.';
const RUN_HINT = `web-kit-mockups${dirName ? ` --dir ${dirName}` : ''}`;

// Optional project texts; a missing file or key falls back to a neutral default.
const config = existsSync(join(mockupsDir, 'mockups.config.json'))
  ? JSON.parse(readFileSync(join(mockupsDir, 'mockups.config.json'), 'utf8'))
  : {};
const INDEX_TITLE = config.title ?? 'Mockups';
const USER_LETTERS = { A: 'A', B: 'B', ...(config.userLetters ?? {}) };
const STEP_TITLE = config.stepTitle ?? 'Step {current} of {total}';
const PAGE_NOTE = config.pageNote ?? 'Low-fidelity wireframe. Not an accepted UI.';
// Index texts: {count} is replaced by a number. Without them the index uses the English defaults below.
const INDEX_INTRO = config.indexIntro;
const FILTER_PLACEHOLDER = config.filterPlaceholder ?? 'Filter by title or group';
const SCREEN_COUNT = config.screenCount;

const NAME_RE = /^[a-z0-9]+(-[a-z0-9]+)*$/;
const TONES = ['ok', 'warn'];
const BUTTON_KINDS = ['plain', 'save', 'approve'];
const CHIP_SIZES = ['s', 'm', 'l'];
const CHIP_TONES = ['warn', 'danger'];
const USERS = USER_LETTERS;
const DAY_TONES = ['choice', 'chosen', 'cooking', 'done'];
const FRAMES = ['phone', 'desktop'];
const CARD_TONES = ['ok', 'warn', 'danger'];
const SCREEN_W_MIN = 240;
const SCREEN_W_MAX = 1440;
const NOTE_MAX = 160;
const MAP_THUMB_SCALE = 0.075;

// A board draws its screens as phone frames (default) or as wide desktop screens (spec "frame": "desktop").
// The screens map is "phones" for a phone board; "screens" is accepted as the same map for a desktop board.
const frameOf = (spec) => spec.frame ?? 'phone';
const screensOf = (spec) => spec.phones ?? spec.screens;

const esc = (s) =>
  String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

// Plain text with **bold** and \n line breaks; everything else is escaped.
const rich = (s) => esc(s).replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br>');

// Plain text with `code` spans; everything else is escaped.
const withCode = (s) => esc(s).replace(/`(.+?)`/g, '<code>$1</code>');

class SpecError extends Error {}

function fail(file, message) {
  throw new SpecError(`${file}: ${message}`);
}

function need(file, cond, message) {
  if (!cond) fail(file, message);
}

function isText(v) {
  return typeof v === 'string' && v.length > 0;
}

// ---------- blocks ----------

function photoHtml(b, file, inner = '') {
  const label = b.label ?? '';
  need(file, typeof label === 'string', 'photo label must be a string');
  const badge = b.badge ? `<span class="badge">${esc(b.badge)}</span>` : '';
  const extra = inner ? ' with-reject' : '';
  return `<div class="photo${b.big ? ' big' : ''}${extra}">${inner ? '' : esc(label)}${badge}${inner}</div>`;
}

function chipsHtml(items, file) {
  need(file, Array.isArray(items) && items.length > 0, 'chips needs a non-empty "items" array');
  const html = items.map((it) => {
    const chip = typeof it === 'string' ? { text: it } : it;
    need(file, isText(chip.text), 'every chip needs "text"');
    need(file, chip.size === undefined || CHIP_SIZES.includes(chip.size), `chip size must be one of ${CHIP_SIZES.join(', ')}`);
    need(file, chip.tone === undefined || CHIP_TONES.includes(chip.tone), `chip tone must be one of ${CHIP_TONES.join(', ')}`);
    const size = chip.size ? ' ' + chip.size : '';
    const tone = chip.tone ? ' ' + chip.tone : '';
    return `<span class="chip${size}${tone}${chip.on ? ' on' : ''}">${esc(chip.text)}</span>`;
  });
  return `<div class="chips">${html.join('')}</div>`;
}

// Rejection layer over a dish photo: taste reasons, a thin line, general reasons.
function rejectHtml(r, file) {
  need(file, r && typeof r === 'object', 'dish reject must be an object with "taste" and "general"');
  return `<div class="reject">${chipsHtml(r.taste, file)}<div class="reject-line"></div>${chipsHtml(r.general, file)}</div>`;
}

const blocks = {
  topbar(b, file) {
    need(file, isText(b.title), 'topbar needs "title"');
    let progress = '';
    if (b.progress !== undefined) {
      const { current, total } = b.progress;
      need(file, Number.isInteger(total) && total > 1 && Number.isInteger(current) && current >= 0 && current < total,
        'topbar progress needs integer "total" > 1 and "current" in 0..total-1');
      const dots = Array.from({ length: total }, (_, i) => `<i class="${i < current ? 'done' : i === current ? 'on' : ''}">${i + 1}</i>`);
      progress = `<span class="mini-steps" title="${esc(STEP_TITLE.replace('{current}', current + 1).replace('{total}', total))}">${dots.join('')}</span>`;
    }
    const aside = b.aside ? `<span class="aside">${esc(b.aside)}</span>` : '';
    if (b.tone === undefined) {
      for (const k of ['back', 'titleHint', 'titleHintOpen', 'partner', 'bar']) need(file, b[k] === undefined, `topbar ${k} needs "tone"`);
      return `<div class="topbar"><span class="title">${esc(b.title)}</span>${progress}${aside}</div>`;
    }
    // A day header: «‹», the step as the title, the partner's status and a thin step line
    need(file, DAY_TONES.includes(b.tone), `topbar tone must be one of ${DAY_TONES.join(', ')}`);
    need(file, b.progress === undefined && b.aside === undefined, 'a day topbar takes no "progress" or "aside"');
    need(file, b.back === undefined || isText(b.back), 'topbar back must be text');
    need(file, b.titleHint === undefined || isText(b.titleHint), 'topbar titleHint must be text');
    need(file, b.titleHintOpen === undefined || (b.titleHintOpen === true && b.titleHint !== undefined), 'topbar titleHintOpen must be true and needs "titleHint"');
    const p = b.partner;
    need(file, p === undefined || (USERS[p.user] && isText(p.status) && (p.initial === undefined || isText(p.initial)) && (p.hint === undefined || isText(p.hint))),
      'topbar partner needs "user" (A or B) and "status"; "initial" and "hint" are text');
    const back = b.back !== undefined ? `<span class="back-icon" title="${esc(b.back)}"></span>` : '';
    const tip = text => `<span class="hint">${esc(text)}</span>`;
    const title = b.titleHint === undefined ? `<span class="title">${esc(b.title)}</span>`
      : `<span class="title has-hint">${esc(b.title)}<span class="title-q">?</span>${b.titleHintOpen ? tip(b.titleHint) : ''}</span>`;
    // "…" is the partner still choosing: drawn as dots that fill in one by one
    const status = p?.status === '…' ? '<span class="typing"><b>.</b><b>.</b><b>.</b></span>' : esc(p?.status ?? '');
    const partner = p ? `<span class="partner user-${p.user.toLowerCase()}"><i>${esc(p.initial ?? USERS[p.user])}</i>${status}${p.hint ? tip(p.hint) : ''}</span>` : '';
    let bar = '';
    if (b.bar !== undefined) {
      const { current, total } = b.bar;
      need(file, Number.isInteger(total) && total > 1 && Number.isInteger(current) && current >= 0 && current < total,
        'topbar bar needs integer "total" > 1 and "current" in 0..total-1');
      bar = `<div class="steps-bar">${Array.from({ length: total }, (_, i) => `<i class="${i <= current ? 'on' : ''}"></i>`).join('')}</div>`;
    }
    return `<div class="topbar day tone-${b.tone}${bar ? '' : ' no-bar'}"><div class="row">${back}${title}${partner}</div>${bar}</div>`;
  },
  dish(b, file) {
    need(file, isText(b.name), 'dish needs "name"');
    need(file, b.tone === undefined || TONES.includes(b.tone), `dish tone must be one of ${TONES.join(', ')}`);
    const sub = b.sub ? `<div class="sub${b.tone ? ' ' + b.tone : ''}">${esc(b.sub)}</div>` : '';
    const reject = b.reject === undefined ? '' : rejectHtml(b.reject, file);
    return `<div class="dish${b.peek ? ' peek' : ''}">${photoHtml({ label: b.photo, badge: b.badge, big: b.big }, file, reject)}<div class="name">${esc(b.name)}</div>${sub}</div>`;
  },
  photo: photoHtml,
  name(b, file) {
    need(file, isText(b.text), 'name needs "text"');
    return `<div class="name">${esc(b.text)}</div>`;
  },
  text(b, file) {
    if (b.parts !== undefined) {
      need(file, b.text === undefined, 'text takes "text" or "parts", not both');
      need(file, Array.isArray(b.parts) && b.parts.length > 0, 'text "parts" needs a non-empty array');
      const html = b.parts.map((p) => {
        if (isText(p)) return esc(p);
        need(file, isText(p?.chip), 'a text part is a string or { "chip": "..." }');
        return `<span class="chip s">${esc(p.chip)}</span>`;
      }).join('');
      return `<div class="sub inline-chips">${html}</div>`;
    }
    need(file, isText(b.text), 'text needs "text"');
    return `<div class="sub">${esc(b.text)}</div>`;
  },
  field(b, file) {
    need(file, isText(b.label), 'field needs "label"');
    need(file, b.placeholder === undefined || typeof b.placeholder === 'string', 'field placeholder must be a string');
    let hints = '';
    if (b.suggestions !== undefined) {
      const sg = b.suggestions;
      need(file, Array.isArray(sg?.items) && sg.items.length > 0 && sg.items.every(isText), 'field "suggestions" needs a non-empty "items" array of strings');
      need(file, sg.label === undefined || isText(sg.label), 'field "suggestions" label must be text');
      const lead = sg.label ? `<span class="field-hints-label">${esc(sg.label)}</span>` : '';
      need(file, sg.inline === undefined || typeof sg.inline === 'boolean', 'field "suggestions" inline must be true or false');
      const chips = sg.items.map((t) => `<span class="chip s">${esc(t)}</span>`).join('');
      hints = sg.inline ? `<span class="field-hints">(${lead}${chips})</span>` : `<div class="field-hints">${lead}${chips}</div>`;
    }
    const label = `<span class="field-label">${esc(b.label)}</span>`;
    const head = b.suggestions?.inline ? `<div class="field-head">${label}${hints}</div>` : `${label}${hints}`;
    return `<div class="field">${head}<div class="field-box">${esc(b.placeholder ?? '')}</div></div>`;
  },
  bar(b, file) {
    const w = b.width ?? 100;
    need(file, Number.isInteger(w) && w >= 1 && w <= 100, 'bar width must be an integer 1-100');
    return `<div class="bar" style="width:${w}%"></div>`;
  },
  spacer() {
    return '<div class="spacer"></div>';
  },
  buttons(b, file) {
    need(file, Array.isArray(b.items) && b.items.length > 0, 'buttons needs a non-empty "items" array');
    const items = b.items.map((it) => {
      const btn = typeof it === 'string' ? { text: it } : it;
      need(file, isText(btn.text), 'every button needs "text"');
      const kind = btn.kind ?? 'plain';
      need(file, BUTTON_KINDS.includes(kind), `button kind must be one of ${BUTTON_KINDS.join(', ')}`);
      const html = `<div class="btn${kind === 'plain' ? '' : ' ' + kind}">${esc(btn.text)}</div>`;
      return btn.caption ? `<div class="btn-cell">${html}<div class="btn-caption">${esc(btn.caption)}</div></div>` : html;
    });
    return items.length > 1 ? `<div class="row">${items.join('')}</div>` : items[0];
  },
  chips(b, file) {
    return chipsHtml(b.items, file);
  },
  tabs(b, file) {
    need(file, Array.isArray(b.items) && b.items.length > 1, 'tabs needs an "items" array with 2+ entries');
    const active = b.active ?? 0;
    need(file, Number.isInteger(active) && active >= 0 && active < b.items.length, 'tabs "active" is out of range');
    const items = b.items.map((t, i) => `<div${i === active ? ' class="on"' : ''}>${esc(t)}</div>`);
    return `<div class="tabs">${items.join('')}</div>`;
  },
  tabbar(b, file) {
    need(file, Array.isArray(b.items) && b.items.length > 1, 'tabbar needs an "items" array with 2+ entries');
    const active = b.active ?? 0;
    need(file, Number.isInteger(active) && active >= 0 && active < b.items.length, 'tabbar "active" is out of range');
    return `<div class="tabbar">${b.items.map((t, i) => `<div${i === active ? ' class="on"' : ''}>${esc(t)}</div>`).join('')}</div>`;
  },
  toast(b, file) {
    need(file, isText(b.text), 'toast needs "text"');
    const action = b.action ? `<strong>${esc(b.action)}</strong>` : '';
    if (b.expanded) {
      need(file, isText(b.expanded.title), 'toast "expanded" needs "title"');
      const fold = b.expanded.collapse ? `<div class="toast-fold">${esc(b.expanded.collapse)}</div>` : '';
      return `<div class="toast open"><div class="toast-row"><span>${esc(b.text)}</span>${action}</div><div class="toast-body"><i class="thumb l"></i><span>${esc(b.expanded.title)}</span></div>${fold}</div>`;
    }
    return `<div class="toast${b.oneLine ? ' one-line' : ''}"><span>${esc(b.text)}</span>${action}</div>`;
  },
  list(b, file) {
    need(file, Array.isArray(b.rows) && b.rows.length > 0, 'list needs a non-empty "rows" array');
    const rows = b.rows.map((row) => {
      const muted = !Array.isArray(row) && row !== null && typeof row === 'object' && row.muted === true;
      const r = Array.isArray(row) ? row : row?.cells;
      need(file, Array.isArray(r) && r.length >= 1 && r.length <= 2,
        'every list row is [left], [left, right] or { "cells": [left, right], "muted": true }');
      let right = r[1] !== undefined ? `<span class="qty">${esc(r[1])}</span>` : '';
      if (!Array.isArray(row) && row.action !== undefined) {
        const act = typeof row.action === 'string' ? { text: row.action } : row.action;
        need(file, isText(act?.text), 'a list row "action" needs "text"');
        const kind = act.kind ?? 'plain';
        need(file, BUTTON_KINDS.includes(kind), `button kind must be one of ${BUTTON_KINDS.join(', ')}`);
        right = `<span class="row-end">${right}<span class="btn row-btn${kind === 'plain' ? '' : ' ' + kind}">${esc(act.text)}</span></span>`;
      }
      const thumb = b.thumbs ? `<i class="thumb${b.thumbs === 'l' ? ' l' : ''}"></i>` : '';
      const tone = Array.isArray(row) ? undefined : row.tone;
      need(file, tone === undefined || ['warn', 'danger'].includes(tone), 'a list row "tone" is warn or danger');
      return `<div class="list-row${muted ? ' muted' : ''}${tone ? ' ' + tone : ''}"><span>${thumb}${esc(r[0])}</span>${right}</div>`;
    });
    return `<div>${rows.join('')}</div>`;
  },
  // Side-by-side areas of a desktop screen: each column is { width, blocks }; width is px (number) or "1fr", "2fr"
  columns(b, file) {
    need(file, Array.isArray(b.cols) && b.cols.length > 1, 'columns needs a "cols" array with 2+ entries');
    const widths = b.cols.map((c) => {
      need(file, c && typeof c === 'object', 'every column is an object with "blocks"');
      const w = c.width ?? '1fr';
      need(file, (Number.isInteger(w) && w > 0) || (typeof w === 'string' && /^\d+(\.\d+)?fr$/.test(w)),
        'column width must be a positive integer (px) or a "<n>fr" string');
      return typeof w === 'number' ? `${w}px` : `minmax(0, ${w})`;
    });
    const cols = b.cols.map((c) => `<div class="col">${renderBlocks(c.blocks, file, 'columns')}</div>`);
    return `<div class="cols" style="grid-template-columns:${widths.join(' ')}">${cols.join('')}</div>`;
  },
  // A titled panel; tone marks the state (ok, warn, danger), muted fades it back
  card(b, file) {
    need(file, b.title === undefined || isText(b.title), 'card title must be text');
    need(file, b.aside === undefined || isText(b.aside), 'card aside must be text');
    need(file, b.tone === undefined || CARD_TONES.includes(b.tone), `card tone must be one of ${CARD_TONES.join(', ')}`);
    need(file, b.muted === undefined || typeof b.muted === 'boolean', 'card muted must be true or false');
    const head = b.title === undefined && b.aside === undefined ? ''
      : `<div class="card-head"><span class="card-title">${esc(b.title ?? '')}</span>${b.aside ? `<span class="aside">${esc(b.aside)}</span>` : ''}</div>`;
    return `<div class="card${b.tone ? ' ' + b.tone : ''}${b.muted ? ' muted' : ''}">${head}${renderBlocks(b.blocks, file, 'card')}</div>`;
  },
  // A labelled area of a page map (dashed outline); "on" highlights the area a flow is about.
  // Without "blocks" two faint bars under the title say the area has content.
  region(b, file) {
    // A map region may go without a name where it does not fit; the region a flow is about always has one.
    need(file, b.title === undefined ? !b.on : isText(b.title), b.on ? 'an "on" region needs "title"' : 'region "title" must be text');
    const title = b.title === undefined ? '' : `<div class="region-title">${esc(b.title)}</div>`;
    need(file, b.on === undefined || typeof b.on === 'boolean', 'region on must be true or false');
    need(file, b.blocks === undefined || (Array.isArray(b.blocks) && b.blocks.length > 0), 'region blocks must be a non-empty array');
    need(file, b.cover === undefined || (b.cover === true && b.blocks !== undefined), 'region cover must be true and needs "blocks"');
    // "cover": the blocks keep their real size and place (a page map drawn from the real page, so its proportions match
    // the full screen). Only the "on" region shows them, as a text-free skeleton; the others show two calm bars.
    if (b.cover) {
      const cover = `<div class="region-cover">${title}<div class="bar" style="width:40%"></div><div class="bar" style="width:25%"></div></div>`;
      return `<div class="region covered${b.on ? ' on' : ''}"><div class="region-content">${renderBlocks(b.blocks, file, 'region')}</div>${cover}</div>`;
    }
    const inner = b.blocks === undefined
      ? '<div class="bar" style="width:70%"></div><div class="bar" style="width:45%"></div>'
      : renderBlocks(b.blocks, file, 'region');
    return `<div class="region${b.on ? ' on' : ''}">${title}${inner}</div>`;
  },
};

// ---------- parts ----------

// A part is <mockups folder>/parts/<name>.json: a JSON array of blocks, expanded where a { "type": "part", "name" } block stands.
const partCache = new Map();
const partChain = []; // names being expanded right now, to catch a part that contains itself

const partPath = (name) => `${shownDir}/parts/${name}.json`;

function loadPart(name, file, where) {
  need(file, NAME_RE.test(name), `${where}: part name "${name}" must be lowercase words joined by hyphens`);
  if (partCache.has(name)) return partCache.get(name);
  const path = join(partsDir, `${name}.json`);
  need(file, existsSync(path), `${where}: unknown part "${name}" (no file ${partPath(name)})`);
  let list;
  try {
    list = JSON.parse(readFileSync(path, 'utf8'));
  } catch (e) {
    fail(partPath(name), `invalid JSON: ${e.message}`);
  }
  need(partPath(name), Array.isArray(list) && list.length > 0, 'a part must be a non-empty JSON array of blocks');
  partCache.set(name, list);
  return list;
}

function renderPart(b, file, where) {
  need(file, isText(b.name), `${where}: a part block needs "name"`);
  const extra = Object.keys(b).filter((k) => k !== 'type' && k !== 'name');
  need(file, extra.length === 0, `${where}: part "${b.name}" takes no other fields (${extra.join(', ')}); draw a changed state inline`);
  const list = loadPart(b.name, file, where);
  need(file, !partChain.includes(b.name), `${where}: parts include each other in a cycle: ${[...partChain, b.name].join(' -> ')}`);
  partChain.push(b.name);
  try {
    return renderBlocks(list, partPath(b.name), `part "${b.name}"`);
  } finally {
    partChain.pop();
  }
}

// Every part is rendered once on its own, so a broken part or a cycle fails even when no spec uses it yet.
function checkParts() {
  if (!existsSync(partsDir)) return;
  for (const f of readdirSync(partsDir).filter((f) => f.endsWith('.json')).sort()) {
    renderPart({ type: 'part', name: f.slice(0, -5) }, `${shownDir}/parts`, 'parts folder');
  }
}

function renderBlocks(list, file, where) {
  need(file, Array.isArray(list), `${where} needs a "blocks" array`);
  return list
    .map((b) => {
      need(file, b && typeof b === 'object' && isText(b.type), `${where}: every block needs a "type"`);
      if (b.type === 'part') return renderPart(b, file, where);
      const render = blocks[b.type];
      need(file, render, `${where}: unknown block type "${b.type}" (known: ${Object.keys(blocks).join(', ')}, part)`);
      return render(b, file);
    })
    .join('');
}

// ---------- phones, layout ----------

// A desktop screen: an optional menu rail (spec field "menu": { items, active }) and the content area.
// The menu is the admin shell's; a popup overlay dims the whole screen.
function renderScreen(id, p, file) {
  const where = `screen "${id}"`;
  need(file, p && typeof p === 'object', `${where} must be an object`);
  need(file, isText(p.caption), `${where} needs "caption"`);
  need(file, p.user === undefined, `${where}: "user" is for phone boards`);
  need(file, p.step === undefined || (Number.isInteger(p.step) && p.step > 0), `${where}: step must be a positive integer`);
  need(file, p.width === undefined || (Number.isInteger(p.width) && p.width >= SCREEN_W_MIN && p.width <= SCREEN_W_MAX),
    `${where}: width must be an integer ${SCREEN_W_MIN}-${SCREEN_W_MAX} (px)`);
  need(file, p.scale === undefined || (typeof p.scale === 'number' && p.scale >= 0.2 && p.scale <= 1),
    `${where}: scale must be a number 0.2-1`);
  // "map": the page map screen, folded by default under its caption so it does not take the board's space; it is
  // drawn at "scale" (default 0.4).
  need(file, p.map === undefined || p.map === true, `${where}: map must be true`);
  const scale = p.scale ?? (p.map ? 0.4 : undefined);
  let menu = '';
  if (p.menu !== undefined) {
    const m = p.menu;
    need(file, m && Array.isArray(m.items) && m.items.length > 1, `${where}: menu needs an "items" array with 2+ entries`);
    const active = m.active ?? 0;
    need(file, Number.isInteger(active) && active >= 0 && active < m.items.length, `${where}: menu "active" is out of range`);
    menu = `<nav class="menu">${m.items.map((t, i) => `<div${i === active ? ' class="on"' : ''}>${esc(t)}</div>`).join('')}</nav>`;
  }
  const o = p.overlay;
  need(file, o !== undefined || (Array.isArray(p.blocks) && p.blocks.length > 0), `${where} needs "blocks" or an "overlay"`);
  const main = `<div class="screen-body">${menu}<div class="main">${renderBlocks(p.blocks ?? [], file, where)}</div></div>`;
  let body = main;
  if (o) {
    need(file, o.type === 'popup', `${where}: a desktop overlay must be a "popup"`);
    const close = o.closable === false ? '' : '<span class="close">&times;</span>';
    body = `<div class="faded">${main}</div><div class="dim"></div><div class="popup">${close}${renderBlocks(o.blocks, file, `${where} overlay`)}</div>`;
  }
  const tag = p.step ? `<span class="user-tag">${p.step}</span>` : '';
  const style = [p.width ? `width:${p.width}px` : '', scale ? `zoom:${scale};--scale:${scale}` : ''].filter(Boolean).join(';');
  const screen = `<div class="screen${p.width ? ' sized' : ''}${scale ? ' scaled' : ''}"${style ? ` style="${style}"` : ''}>${body}</div>`;
  if (p.map) {
    // The chip is a compact strip, the same size folded and open: the caption, then a tiny thumbnail of the page (the
    // highlighted region filled, no names). Opening shows the readable map as a popover under the chip, so the board
    // does not move.
    const thumb = `<div class="screen scaled map-thumb" style="${p.width ? `width:${p.width}px;` : ''}zoom:${MAP_THUMB_SCALE};--scale:${MAP_THUMB_SCALE}">${body}</div>`;
    // A click on the opened map folds it again, like a click on the chip.
    const open = `<div class="map-open" onclick="this.closest('details').open = false">${screen}</div>`;
    return `<details class="map-fold"><summary class="caption"><span class="map-caption">${tag}${esc(p.caption)}</span>${thumb}</summary>${open}</details>`;
  }
  return `<div class="caption">${tag}${esc(p.caption)}</div>${screen}`;
}

function renderPhone(id, p, file, frame = 'phone') {
  if (frame === 'desktop') return renderScreen(id, p, file);
  need(file, p.menu === undefined, `phone "${id}": "menu" is for desktop boards`);
  need(file, p.width === undefined, `phone "${id}": "width" is for desktop boards; a phone has a fixed width`);
  need(file, p.scale === undefined && p.map === undefined, `phone "${id}": "scale" and "map" are for desktop boards`);
  const where = `phone "${id}"`;
  need(file, p && typeof p === 'object', `${where} must be an object`);
  need(file, isText(p.caption), `${where} needs "caption"`);
  const inner = renderBlocks(p.blocks ?? [], file, where);
  let body = inner;
  const o = p.overlay;
  if (o) {
    need(file, ['popup', 'sheet'].includes(o.type), `${where}: overlay type must be "popup" or "sheet"`);
    const content = renderBlocks(o.blocks, file, `${where} overlay`);
    if (o.type === 'popup') {
      const close = o.closable === false ? '' : '<span class="close">&times;</span>';
      body = `<div class="faded">${inner}</div><div class="dim"></div><div class="popup">${close}${content}</div>`;
    } else {
      const h = o.title ? `<h3>${esc(o.title)}</h3>` : '';
      body = `<div class="faded">${inner}</div><div class="dim"></div><div class="sheet">${h}${content}</div>`;
    }
  } else {
    need(file, Array.isArray(p.blocks) && p.blocks.length > 0, `${where} needs "blocks" or an "overlay"`);
  }
  need(file, p.user === undefined || p.user in USERS, `${where}: user must be one of ${Object.keys(USERS).join(', ')}`);
  need(file, p.step === undefined || (Number.isInteger(p.step) && p.step > 0), `${where}: step must be a positive integer`);
  const userClass = p.user ? ` user-${p.user.toLowerCase()}` : '';
  const label = `${p.user ? USERS[p.user] : ''}${p.step ?? ''}`;
  const tag = label ? `<span class="user-tag${userClass}">${label}</span>` : '';
  return `<div class="caption">${tag}${esc(p.caption)}</div><div class="phone${userClass}">${body}</div>`;
}

function cellKind(cell, file) {
  if (cell === null || (typeof cell === 'object' && Object.keys(cell).length === 0)) return 'empty';
  need(file, typeof cell === 'object', 'every layout cell is an object or null');
  const kinds = ['phone', 'link', 'note', 'branch'].filter((k) => k in cell);
  need(file, kinds.length === 1, `layout cell must have exactly one of phone, link, note, branch: ${JSON.stringify(cell)}`);
  return kinds[0];
}

function renderBoard(spec, file) {
  need(file, Array.isArray(spec.layout) && spec.layout.length > 0, '"layout" must be a non-empty array of rows');
  const screens = screensOf(spec);
  const frame = frameOf(spec);
  const used = new Set();
  const cells = []; // { row, col, span, kind, html }
  spec.layout.forEach((row, r) => {
    need(file, Array.isArray(row), `layout row ${r + 1} must be an array`);
    let col = 0;
    for (const cell of row) {
      const kind = cellKind(cell, file);
      const span = kind === 'empty' ? 1 : (cell.span ?? 1);
      need(file, Number.isInteger(span) && span >= 1, 'cell "span" must be a positive integer');
      need(file, span === 1 || kind === 'note', 'only notes can span several columns');
      let html = '';
      if (kind === 'phone') {
        need(file, screens[cell.phone], `layout uses unknown phone "${cell.phone}"`);
        need(file, !used.has(cell.phone), `phone "${cell.phone}" is placed twice`);
        used.add(cell.phone);
        html = `<div class="step${frame === 'desktop' ? ' wide' : ''}">${renderPhone(cell.phone, screens[cell.phone], file, frame)}</div>`;
      } else if (kind === 'link') {
        const dir = cell.dir ?? 'right';
        need(file, ['right', 'down'].includes(dir), 'link dir must be "right" or "down"');
        need(file, isText(cell.link), 'link needs a text');
        // Down: the action reads right after the screen it happens on, then the arrow. Right: label under the arrow.
        const glyph = `<span class="glyph">${dir === 'down' ? '&darr;' : '&rarr;'}</span>`;
        const text = `<span>${esc(cell.link)}</span>`;
        html = `<div class="link">${dir === 'down' ? text + glyph : glyph + text}</div>`;
      } else if (kind === 'note') {
        need(file, isText(cell.note), 'note needs a text');
        html = `<div class="note${span === 1 ? ' narrow' : ''}">${rich(cell.note)}</div>`;
      } else if (kind === 'branch') {
        need(file, row.length === 1, 'a branch header must be alone in its layout row');
        need(file, isText(cell.branch), 'branch needs a title');
        need(file, cell.given === undefined || isText(cell.given), 'branch "given" must be a non-empty string');
        const given = cell.given ? `<div class="branch-given">${rich(cell.given)}</div>` : '';
        html = `<div class="branch"><div class="branch-title">${esc(cell.branch)}</div>${given}</div>`;
      }
      cells.push({ row: r + 1, col: col + 1, span, kind, html });
      col += span;
    }
  });
  for (const id of Object.keys(screens)) need(file, used.has(id), `phone "${id}" is defined but not placed in "layout"`);

  const colCount = Math.max(...cells.map((c) => c.col + c.span - 1));
  const cols = [];
  for (let c = 1; c <= colCount; c++) {
    const inCol = cells.filter((x) => x.span === 1 && x.col === c && x.kind !== 'empty');
    cols.push(inCol.length > 0 && inCol.every((x) => x.kind === 'link') ? '110px' : 'auto');
  }
  const rows = spec.layout.map((_, r) => {
    const inRow = cells.filter((x) => x.row === r + 1 && x.kind !== 'empty');
    return inRow.length > 0 && inRow.every((x) => x.kind === 'link') ? '72px' : 'auto';
  });

  const items = cells
    .filter((c) => c.kind !== 'empty')
    .map((c) => {
      const colStyle = c.kind === 'branch' ? '1 / -1' : c.span > 1 ? `${c.col} / span ${c.span}` : `${c.col}`;
      return `  <div class="cell cell-${c.kind}" style="grid-column:${colStyle};grid-row:${c.row}">${c.html}</div>`;
    });
  return `<div class="board" style="grid-template-columns:${cols.join(' ')};grid-template-rows:${rows.join(' ')}">\n${items.join('\n')}\n</div>`;
}

// ---------- pages ----------

// Folds every opened page map on Escape or on a click outside it (a click on the chip or on the map is handled by the
// details element and the map's own onclick). Emitted once per page that has a map.
const MAP_SCRIPT = `<script>
const foldMaps = (keep) => document.querySelectorAll('details.map-fold[open]').forEach((d) => { if (!keep || !d.contains(keep)) d.open = false; });
document.addEventListener('click', (e) => foldMaps(e.target));
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') foldMaps(); });
</script>`;

function pageHtml(name, spec, file) {
  need(file, isText(spec.title), '"title" is required');
  need(file, FRAMES.includes(frameOf(spec)), `"frame" must be one of ${FRAMES.join(', ')}`);
  need(file, !(spec.phones !== undefined && spec.screens !== undefined), 'use "phones" or "screens", not both');
  need(file, spec.screens === undefined || frameOf(spec) === 'desktop', '"screens" is for a desktop board; a phone board uses "phones"');
  const screens = screensOf(spec);
  need(file, screens && typeof screens === 'object' && Object.keys(screens).length > 0, `"${frameOf(spec) === 'desktop' ? 'screens' : 'phones'}" is required`);
  // The page shows the viewer at most one short note. Service text (sources, what is approximated, decisions) goes to
  // "authorNotes", which stays in the JSON for the next editor and is never rendered; "source" is not rendered either.
  need(file, spec.notes === undefined || (Array.isArray(spec.notes) && spec.notes.length <= 1 && spec.notes.every((n) => isText(n) && n.length <= NOTE_MAX)),
    `"notes" is at most one line of up to ${NOTE_MAX} characters for the viewer; put service text in "authorNotes"`);
  need(file, spec.authorNotes === undefined || (Array.isArray(spec.authorNotes) && spec.authorNotes.every(isText)), '"authorNotes" must be an array of strings');
  const notes = (spec.notes ?? []).map((n) => `<p>${rich(n)}</p>`).join('\n  ');
  const board = renderBoard(spec, file);
  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(spec.title)}</title>
<style>
${pageCss}</style>
</head>
<body>
<!-- Generated by the web-kit mockup generator from src/${name}.json. Edit the spec, not this file. -->

<div class="page-head">
  <p><a href="index.html">&larr; All mockups</a></p>
  <h1>${esc(spec.title)}</h1>
  ${notes}
  <p>${esc(PAGE_NOTE)}</p>
</div>

${board}
${board.includes('class="map-fold"') ? MAP_SCRIPT : ''}
</body>
</html>
`;
}

function indexHtml(entries) {
  const frames = new Set(entries.map((e) => frameOf(e.spec)));
  const kindWord = frames.size === 1 ? (frames.has('desktop') ? 'desktop ' : 'mobile ') : '';
  const groups = new Map();
  for (const e of entries) {
    const g = e.spec.group ?? 'Other';
    if (!groups.has(g)) groups.set(g, []);
    groups.get(g).push(e);
  }
  const order = [...groups.keys()].sort((a, b) => (a === 'Other') - (b === 'Other') || a.localeCompare(b));
  const sections = order
    .map((g) => {
      const items = groups
        .get(g)
        .sort((a, b) => a.spec.title.localeCompare(b.spec.title))
        .map((e) => {
          const phones = Object.keys(screensOf(e.spec)).length;
          const meta = SCREEN_COUNT ? SCREEN_COUNT.replace('{count}', phones) : `${phones} screen${phones === 1 ? '' : 's'}`;
          const hay = esc(`${e.spec.title} ${e.spec.summary ?? ''} ${g}`.toLowerCase());
          return `    <a class="item" href="${e.name}.html" data-hay="${hay}"><strong>${esc(e.spec.title)}</strong><span>${esc(e.spec.summary ?? '')}</span><span class="meta">${esc(meta)}</span></a>`;
        });
      return `  <section class="group">\n    <h2>${esc(g)}</h2>\n${items.join('\n')}\n  </section>`;
    })
    .join('\n');
  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(INDEX_TITLE)}</title>
<style>
${pageCss}</style>
<style>
  .list { max-width: 1100px; margin: 0 auto; }
  .group h2 { margin: 24px 0 8px; font-size: 16px; color: var(--muted); }
  .group .item { display: block; margin-bottom: 8px; padding: 12px 16px; border: 1px solid var(--border); border-radius: 10px; background: var(--card); text-decoration: none; color: var(--text); }
  .group .item:hover { background: var(--hover); border-color: var(--text); }
  .item strong { display: block; margin-bottom: 2px; }
  .item span { display: block; color: var(--muted); font-size: 13px; }
  .item .meta { margin-top: 2px; font-size: 12px; }
  #filter { width: 100%; max-width: 420px; min-height: 32px; padding: 6px 10px; border: 1px solid var(--border); border-radius: 8px; background: var(--bg); color: var(--text); font: inherit; }
</style>
</head>
<body>
<!-- Generated by the web-kit mockup generator from src/*.json. Edit the specs, not this file. -->

<div class="page-head">
  <h1>${esc(INDEX_TITLE)}</h1>
  <p>${INDEX_INTRO ? esc(INDEX_INTRO.replace('{count}', entries.length)) : `Low-fidelity ${kindWord}wireframes of ${kindWord === 'desktop ' ? 'screens' : 'user flows'} (${entries.length}). Open any file in a browser; no server is needed.`}</p>
${config.indexNote ? `  <p>${withCode(config.indexNote)}</p>
` : ''}  <input id="filter" type="search" placeholder="${esc(FILTER_PLACEHOLDER)}" aria-label="${esc(FILTER_PLACEHOLDER)}">
</div>

<div class="list">
${sections}
</div>

<script>
  const filter = document.getElementById('filter');
  filter.addEventListener('input', () => {
    const q = filter.value.trim().toLowerCase();
    document.querySelectorAll('.item').forEach((i) => { i.hidden = q !== '' && !i.dataset.hay.includes(q); });
    document.querySelectorAll('.group').forEach((g) => { g.hidden = !g.querySelector('.item:not([hidden])'); });
  });
</script>
</body>
</html>
`;
}

// ---------- main ----------

let pageCss = '';

function main() {
  if (!existsSync(srcDir)) {
    console.error(`Mockups folder not found: ${shownDir}/src. Create it with the first spec, or pass --dir <mockups folder>.`);
    process.exit(1);
  }
  const specFiles = readdirSync(srcDir).filter((f) => f.endsWith('.json')).sort();
  const outputs = new Map();
  const entries = [];
  checkParts();
  // Pages carry the CSS inline so a single sent or copied file keeps its look.
  const cssPath = join(mockupsDir, 'mockups.css');
  const ownCss = existsSync(cssPath);
  pageCss = readFileSync(ownCss ? cssPath : join(dirname(fileURLToPath(import.meta.url)), 'default-mockups.css'), 'utf8').replace(/\r\n/g, '\n');
  if (!ownCss) outputs.set('mockups.css', pageCss);
  if (!pageCss.endsWith('\n')) pageCss += '\n';

  for (const f of specFiles) {
    const name = f.slice(0, -5);
    const file = `${shownDir}/src/${f}`;
    need(file, NAME_RE.test(name), 'file name must be lowercase words joined by hyphens');
    let spec;
    try {
      spec = JSON.parse(readFileSync(join(srcDir, f), 'utf8'));
    } catch (e) {
      fail(file, `invalid JSON: ${e.message}`);
    }
    outputs.set(`${name}.html`, pageHtml(name, spec, file));
    entries.push({ name, spec });
  }
  outputs.set('index.html', indexHtml(entries));

  const orphans = readdirSync(mockupsDir).filter((f) => f.endsWith('.html') && !outputs.has(f));
  if (orphans.length > 0) {
    throw new SpecError(`HTML files without a spec in src/: ${orphans.join(', ')}`);
  }

  const norm = (s) => s.replace(/\r\n/g, '\n');
  const stale = [];
  for (const [f, html] of outputs) {
    const path = join(mockupsDir, f);
    const current = existsSync(path) ? norm(readFileSync(path, 'utf8')) : null;
    if (current === html) continue;
    stale.push(f);
    if (!checkOnly) writeFileSync(path, html, 'utf8');
  }

  if (checkOnly) {
    if (stale.length > 0) {
      console.error(`Stale generated files: ${stale.join(', ')}. Run: ${RUN_HINT}`);
      process.exit(1);
    }
    console.log(`OK: ${entries.length} mockup(s), generated files are up to date.`);
  } else {
    console.log(`Built ${entries.length} mockup(s); wrote ${stale.length} file(s)${stale.length ? ': ' + stale.join(', ') : ''}.`);
  }
}

try {
  main();
} catch (e) {
  if (e instanceof SpecError) {
    console.error(`Mockup spec error: ${e.message}`);
    process.exit(1);
  }
  throw e;
}
