/*
 * i18n consistency checker (westernized fork).
 *
 * Differences from upstream's version:
 *   - The fork removed zh_CN/zh_TW locales; the base locale is `en`.
 *   - Locale set is discovered from src/i18n/*.js instead of hardcoded.
 *   - Also verifies that every static translation key referenced anywhere in
 *     src/ ($t('a.b'), i18n.t('a.b'), this.$t('a.b'), t('a.b')) exists in the
 *     base locale. Upstream rebases repeatedly added views calling $t() for
 *     keys that were never added downstream, which renders raw keys/blank
 *     labels at runtime with no build error.
 */
const fs = require('fs');
const path = require('path');

const rootDir = path.resolve(__dirname, '..');
const i18nDir = path.join(rootDir, 'src/i18n');
const BASE = 'en';

function discoverLocales() {
  return fs
    .readdirSync(i18nDir)
    .filter((f) => f.endsWith('.js') && f !== 'index.js')
    .map((f) => ({ name: f.replace(/\.js$/, ''), file: `src/i18n/${f}` }))
    .sort((a, b) => (a.name === BASE ? -1 : b.name === BASE ? 1 : a.name.localeCompare(b.name)));
}

function evalLocale(file) {
  const src = fs.readFileSync(path.join(rootDir, file), 'utf8');
  const objText = src.replace(/^\s*import[^;]+;\s*$/gm, '').replace(/export\s+default\s*/, '');
  // Locale files are plain object literals; evaluate without importing (ESM).
  // eslint-disable-next-line no-new-func
  return new Function(`"use strict"; return (${objText});`)();
}

function readLocale(locale) {
  const flat = evalLocale(locale.file);
  const keys = Object.keys(flat);
  // duplicate detection on raw text (object literal would silently dedupe)
  const lines = fs.readFileSync(path.join(rootDir, locale.file), 'utf8').split(/\r?\n/);
  const seen = new Map();
  const duplicates = [];
  lines.forEach((line, index) => {
    const match = line.match(/^\s*['"]([^'"]+)['"]\s*:/);
    if (!match) return;
    if (!seen.has(match[1])) seen.set(match[1], []);
    seen.get(match[1]).push(index + 1);
  });
  seen.forEach((lineNumbers, key) => {
    if (lineNumbers.length > 1) duplicates.push({ key, lineNumbers });
  });
  return { ...locale, keys, keySet: new Set(keys), duplicates, flat };
}

function walk(dir, out = []) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) {
      if (e.name !== 'node_modules') walk(p, out);
    } else if (/\.(vue|js)$/.test(e.name) && !p.startsWith(i18nDir)) {
      out.push(p);
    }
  }
  return out;
}

function collectReferencedKeys() {
  const keys = new Map(); // key -> first file seen
  const re = /(?:\$t|\bt)\(\s*['"]([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+)['"]\s*[,)]/g;
  for (const f of walk(path.join(rootDir, 'src'))) {
    const src = fs.readFileSync(f, 'utf8');
    let m;
    while ((m = re.exec(src))) {
      if (!keys.has(m[1])) keys.set(m[1], path.relative(rootDir, f));
    }
  }
  return keys;
}

function diffKeys(left, right) {
  return [...left].filter((key) => !right.has(key)).sort();
}

function formatKeyList(keys) {
  return keys.length ? keys.map((k) => `    - ${k}`).join('\n') : '';
}

function main() {
  const results = discoverLocales().map(readLocale);
  const base = results.find((l) => l.name === BASE);
  if (!base) {
    console.error(`base locale "${BASE}" not found under src/i18n`);
    process.exit(1);
  }
  const errors = [];

  results.forEach((locale) => {
    locale.duplicates.forEach(({ key, lineNumbers }) => {
      errors.push(`${locale.file} has duplicate key "${key}" on lines ${lineNumbers.join(', ')}`);
    });
  });

  results
    .filter((locale) => locale !== base)
    .forEach((locale) => {
      const missing = diffKeys(base.keySet, locale.keySet);
      const extra = diffKeys(locale.keySet, base.keySet);
      if (missing.length) {
        errors.push(`${locale.file} is missing keys from ${base.file}:\n${formatKeyList(missing)}`);
      }
      if (extra.length) {
        errors.push(`${locale.file} has keys that do not exist in ${base.file}:\n${formatKeyList(extra)}`);
      }
    });

  const referenced = collectReferencedKeys();
  const unresolved = [...referenced].filter(([k]) => !base.keySet.has(k));
  if (unresolved.length) {
    errors.push(
      `referenced translation keys missing from ${base.file}:\n` +
        unresolved.map(([k, f]) => `    - ${k} (used in ${f})`).join('\n')
    );
  }

  if (errors.length) {
    console.error(`i18n check failed with ${errors.length} issue(s):`);
    console.error(errors.join('\n\n'));
    process.exit(1);
  }

  console.log(
    `i18n check passed: ${results.length} locales x ${base.keySet.size} keys, ` +
      `${referenced.size} referenced keys all resolve.`
  );
}

main();
