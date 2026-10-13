#!/usr/bin/env node
/*
 * Post-rebase web integrity checker.
 *
 * The upstream rebase has repeatedly produced *silent* runtime breakage that
 * `vue-cli-service build` does NOT fail on and that unit tests (which do not
 * mount full views) do not catch. Three classes of corruption have bitten us:
 *
 *   1. Lost/duplicated imports -> shorthand component/object references to an
 *      identifier that was never imported/declared (e.g. `components:
 *      { CustomDialog }` with no import). Throwing module factory makes
 *      webpack cache a half-initialized module and vue-router silently renders
 *      a blank page (no console error).
 *
 *   2. Dropped function-signature parameters / const bindings (e.g. a method
 *      body that references `request`, `onTerminalFailure`, `retryCount`,
 *      `retryWindowStartedAt`, `failCallback` after the merge deleted them
 *      from the signature). Throws ReferenceError at call time.
 *
 *   3. Interleaved / half-converted Vue templates -> mismatched tags
 *      (`<el-button>` ... `</CustomButton>`, `<CustomDialog>` ... `</el-dialog>`)
 *      and duplicated option keys (`computed:` twice) that silently clobber
 *      each other.
 *
 * This script fails hard (exit 1) if any of those reappear, so a future
 * rebase cannot merge them in silently. Run via `npm run check:integrity`
 * (wired into CI and into scripts/westernization_rebase_check.sh).
 */
const fs = require('fs');
const path = require('path');
const acorn = require('acorn');
const { analyze } = require('eslint-scope');
const { parseComponent, compile } = require('vue-template-compiler');

const ROOT = path.resolve(__dirname, '..');
const SRC = path.join(ROOT, 'src');

// Browser/ES/Node globals that legitimately resolve outside module scope.
const GLOBALS = new Set([
  'window', 'document', 'navigator', 'location', 'localStorage', 'sessionStorage', 'console',
  'setTimeout', 'clearTimeout', 'setInterval', 'clearInterval', 'requestAnimationFrame',
  'cancelAnimationFrame', 'Promise', 'JSON', 'Math', 'Date', 'Array', 'Object', 'String',
  'Number', 'Boolean', 'Symbol', 'Map', 'Set', 'WeakMap', 'WeakSet', 'Proxy', 'Reflect',
  'Error', 'TypeError', 'RangeError', 'SyntaxError', 'EvalError', 'ReferenceError',
  'URIError', 'RegExp', 'encodeURIComponent', 'decodeURIComponent', 'encodeURI', 'decodeURI',
  'parseInt', 'parseFloat', 'isNaN', 'isFinite', 'fetch', 'URL', 'URLSearchParams', 'Blob',
  'File', 'FileReader', 'FormData', 'AbortController', 'AbortSignal', 'atob', 'btoa',
  'Image', 'Audio', 'XMLHttpRequest', 'WebSocket', 'EventSource', 'MutationObserver',
  'IntersectionObserver', 'ResizeObserver', 'performance', 'crypto', 'process', 'Function',
  'alert', 'confirm', 'prompt', 'getComputedStyle', 'matchMedia', 'CSS', 'DOMParser',
  'XMLSerializer', 'TextEncoder', 'TextDecoder', 'Uint8Array', 'Int8Array', 'Uint16Array',
  'Int16Array', 'Uint32Array', 'Int32Array', 'Float32Array', 'Float64Array',
  'Uint8ClampedArray', 'DataView', 'ArrayBuffer', 'Notification', 'caches', 'indexedDB',
  'self', 'globalThis', 'structuredClone', 'queueMicrotask', 'Intl', 'eval', 'arguments',
  'AudioContext', 'webkitAudioContext', 'Element', 'Node', 'HTMLElement', 'SVGElement',
  'Event', 'CustomEvent', 'KeyboardEvent', 'MouseEvent', 'DOMException', 'devicePixelRatio',
  'screen', 'history', 'Worker', 'IDBKeyRange', 'SpeechSynthesisUtterance', 'Range', 'Text',
  'undefined', 'NaN', 'Infinity', 'global', 'module', 'require', 'exports', 'Buffer',
  '__dirname', '__filename', 'Response', 'Request', 'Headers', 'importScripts',
  // ServiceWorker scope (src/service-worker.js, injected by workbox)
  'workbox', 'skipWaiting', 'clients', 'registration', 'serviceWorker',
]);

// Vue SFC macros available inside <script setup>.
const SETUP_MACROS = new Set(['defineProps', 'defineEmits', 'defineExpose', 'defineSlots', 'withDefaults', 'withDefaults', 'defineModel', 'useSlots', 'useAttrs', 'defineOptions', 'defineComponent']);

function walk(dir, out = []) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (e.name === 'node_modules' || e.name === 'tests') continue;
    const p = path.join(dir, e.name);
    if (e.isDirectory()) walk(p, out);
    else if (/\.(js|vue)$/.test(e.name)) out.push(p);
  }
  return out;
}

function scriptsOf(file, raw) {
  if (!file.endsWith('.vue')) return [{ code: raw, offset: 1, setup: false }];
  const parts = [];
  const re = /<script\b([^>]*)>([\s\S]*?)<\/script>/gi;
  let m;
  while ((m = re.exec(raw))) {
    const attrs = m[1] || '';
    const start = m.index + m[0].indexOf(m[2]);
    parts.push({
      code: m[2],
      offset: raw.slice(0, start).split('\n').length,
      setup: /\bsetup\b/.test(attrs),
    });
  }
  return parts;
}

const errors = [];
function addError(kind, file, line, msg) {
  errors.push(`${kind}  ${path.relative(ROOT, file)}${line ? ':' + line : ''}  ${msg}`);
}

// ---- Pass 1: undefined free identifiers (classes 1 & 2) ------------------
for (const f of walk(SRC)) {
  const raw = fs.readFileSync(f, 'utf8');
  for (const s of scriptsOf(f, raw)) {
    let ast;
    try {
      ast = acorn.parse(s.code, {
        ecmaVersion: 'latest', sourceType: 'module', locations: true, ranges: true,
        allowReturnOutsideFunction: true, allowAwaitOutsideFunction: true,
      });
    } catch (e) {
      addError('PARSE', f, s.offset, e.message);
      continue;
    }
    const sm = analyze(ast, { ecmaVersion: 13, sourceType: 'module' });
    const globalScope = sm.scopes.find((sc) => sc.type === 'global');
    for (const ref of globalScope.through) {
      const name = ref.identifier.name;
      if (GLOBALS.has(name)) continue;
      if (s.setup && SETUP_MACROS.has(name)) continue;
      // `Function` and other globals already filtered; report the rest.
      const loc = ref.identifier.loc;
      addError('UNDEF', f, loc ? s.offset + loc.start.line - 1 : s.offset, name);
    }
  }
}

// ---- Pass 2: Vue template compile errors (class 3) -----------------------
for (const f of walk(SRC)) {
  if (!f.endsWith('.vue')) continue;
  const sfc = parseComponent(fs.readFileSync(f, 'utf8'));
  if (!sfc.template || !sfc.template.content.trim()) continue;
  const res = compile(sfc.template.content, { preserveWhitespace: false });
  if (res.errors && res.errors.length) {
    for (const e of res.errors.slice(0, 6)) addError('TEMPLATE', f, null, String(e).slice(0, 140));
  }
}

// ---- Pass 3: duplicated top-level Vue options keys (class 3) -------------
const OPTION_KEYS = new Set([
  'name', 'components', 'directives', 'mixins', 'props', 'data', 'computed',
  'methods', 'watch', 'created', 'mounted', 'beforeMount', 'updated',
  'beforeUpdate', 'destroyed', 'beforeDestroy', 'activated', 'deactivated',
  'render', 'template', 'inheritAttrs', 'model', 'provide', 'inject', 'filters',
]);
function dupOptionKeys(scriptCode) {
  // Find `export default { ... }` object and read depth-1 keys.
  const i = scriptCode.indexOf('export default');
  if (i < 0) return [];
  const start = scriptCode.indexOf('{', i);
  if (start < 0) return [];
  const keys = [];
  let depth = 0, k = start, str = null;
  while (k < scriptCode.length) {
    const ch = scriptCode[k];
    if (str) {
      if (ch === '\\') { k += 2; continue; }
      if (ch === str) str = null;
      k++; continue;
    }
    if (ch === '"' || ch === "'" || ch === '`') { str = ch; k++; continue; }
    if (ch === '{') { depth++; k++; continue; }
    if (ch === '}') { depth--; if (depth === 0) break; k++; continue; }
    if (depth === 1) {
      const mm = /^([A-Za-z_$][\w$]*)\s*:/.exec(scriptCode.slice(k, k + 60));
      if (mm) {
        const ls = scriptCode.lastIndexOf('\n', k);
        if (scriptCode.slice(ls + 1, k).trim() === '') {
          keys.push(mm[1]);
          k += mm[0].length - 1;
        }
      }
    }
    k++;
  }
  const seen = new Map();
  for (const key of keys) seen.set(key, (seen.get(key) || 0) + 1);
  return [...seen].filter(([key, n]) => n > 1 && OPTION_KEYS.has(key)).map(([key]) => key);
}
for (const f of walk(SRC)) {
  if (!f.endsWith('.vue')) continue;
  const raw = fs.readFileSync(f, 'utf8');
  const sfc = parseComponent(raw);
  const opts = sfc.script ? sfc.script.content : '';
  for (const dup of dupOptionKeys(opts)) {
    addError('DUP-OPT', f, null, `duplicate options key "${dup}" (later block clobbers the first)`);
  }
}

// ---- Report --------------------------------------------------------------
if (errors.length) {
  console.error(`web integrity check FAILED with ${errors.length} issue(s):`);
  for (const e of errors) console.error('  ' + e);
  process.exit(1);
}
console.log('web integrity check passed: no undefined identifiers, template errors, or duplicate option keys.');
