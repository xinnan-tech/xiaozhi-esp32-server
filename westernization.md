# Westernization Rebase Guide

This file is a downstream rebase playbook for re-westernizing the project after
syncing from upstream.

It is written for future-me first: follow this instead of relying on memory.

## Goal

The downstream branch exists to keep the upstream project fully westernized.

That means:

- remove Chinese-facing product surface
- preserve downstream provider deletions
- preserve downstream provider relocalization
- keep multilingual support where useful, but default the product to English
- backport upstream bug fixes and framework improvements without restoring
  Chinese-only integrations

## Core Rules

Always apply these rules during rebase conflict resolution:

1. If a provider was deleted downstream, keep it deleted.
2. If a provider was re-localized downstream, keep it re-localized and add any
   new upstream locale strings in the downstream style.
3. If upstream added a new provider, check whether it is Chinese-only or
   Chinese-focused. If yes, do not surface it downstream.
4. Keep backend logic improvements and upstream fixes whenever possible, but
   port them into the downstream provider set instead of reintroducing removed
   providers.
5. Upstream wins for core abstractions, bug fixes, security fixes, framework
   updates, schema history, and generated artifacts.
6. Downstream wins for locale defaults, western provider allow-lists, public
   copy, branding, legal pages, and removal of Chinese-facing surfaces.

## Rebase Strategy

Do not treat the downstream overlay as one giant replay.

Rebuild the downstream shape in these slices:

1. `providers-runtime`
2. `admin-api`
3. `admin-web-mobile`
4. `docs-branding`
5. `ops-tests`

Use an integration branch first. Do not rewrite downstream `main` in place
until the integration branch is validated.

## What To Check In Each Slice

### 1. Providers Runtime

Files and areas:

- `main/xiaozhi-server/core/providers/**`
- `main/xiaozhi-server/core/utils/**`
- `main/xiaozhi-server/plugins_func/**`
- `main/xiaozhi-server/config/**`
- `main/xiaozhi-server/requirements.txt`
- server Docker and compose files

Actions:

- remove Chinese-only ASR/LLM/TTS/news providers from shipped/default runtime
- keep western or provider-neutral replacements
- preserve downstream provider naming and localization
- keep runtime prompts, errors, MCP/tool text, and logs English-first
- keep server-facing defaults provider-neutral where possible

### 2. Admin API

Files and areas:

- `main/manager-api/src/main/java/**`
- `main/manager-api/src/main/resources/i18n/**`
- `main/manager-api/src/main/resources/db/changelog/**`

Actions:

- preserve provider filtering and downstream westernized metadata
- never rewrite Liquibase history destructively
- add follow-up migrations only; keep changelog append-only
- keep Chinese-only providers out of surfaced configs, selectors, and defaults
- keep upstream backend fixes even when downstream surface differs

Important:

- historical Liquibase SQL is an intentional exception zone
- do not "clean it up" casually if it would rewrite shipped history
- if a new migration adds Chinese-facing defaults, add a downstream cleanup
  migration rather than editing old history

### 3. Admin Web And Mobile

Files and areas:

- `main/manager-web/src/**`
- `main/manager-web/public/**`
- `main/manager-mobile/src/**`

Actions:

- keep supported languages shared and non-duplicated
- default to English
- keep non-Chinese locales where useful
- remove Chinese-facing public routes, legal pages, selectors, assets, and
  fallback copy from shipped downstream surfaces
- preserve upstream UI/framework improvements

### 4. Docs And Branding

Files and areas:

- `README*`
- `docs/**`
- internal reference docs used by downstream maintainers

Actions:

- rewrite docs in English or westernized multilingual form
- remove Chinese screenshots/copy where they are part of downstream surface
- prefer compact English reference docs over huge translated carry-overs

### 5. Ops And Tests

Files and areas:

- setup scripts
- Dockerfiles
- CI/test harnesses
- `main/xiaozhi-server/test/**`

Actions:

- keep tests runnable after rebase
- keep public or interactive test harness text English-first
- preserve useful downstream validation tools

## Generator Rule

The device-theme generator is a separate Vite/Vue app. Its built output is
vendored into this repo:

- `main/manager-web/public/generator/assets/**` is generated output
- `main/manager-web/public/generator/index.html` is tied to that output
- `main/manager-web/public/generator/static/**` is functional device data
  (charset codepoint tables, CJK font glyph tables, emoji gifs, wakeword
  model blobs) shipped byte-for-byte to the firmware toolchain

Do not hand-edit the built bundle unless absolutely necessary.

The generator source repo is a separate checkout:

- remote: `https://github.com/78/xiaozhi-assets-generator`
  (westernization branch, translated locales/comments, relative asset base)
- working copy during rebuild work: `/tmp/xiaozhi-assets-generator`

Rebuild flow:

1. update generator source (never the bundle directly)
2. `cd web && npm run build` (default base `./` so the bundle works under
   whatever path the console mounts it at, e.g. `/generator/`)
3. replace `main/manager-web/public/generator` with the fresh `web/dist`
4. run `./scripts/westernization_audit.sh`

If Han-script appears in the generated code bundle, fix the generator source
first before attempting bundle surgery. The audit treats the code bundle as
live source; only `generator/static` data is exempt.

## Verification Tooling (run these, don't trust the build)

`npm run build` treats broken Vue templates as *warnings* and the unit suites
do not mount full views, so a rebase can merge real breakage while everything
stays green. The 2026-10 rebase shipped three such silent regressions (blank
models page, `ReferenceError: request is not defined` when opening a role,
provider management rendered as garbage). All are now machine-checked:

| Check | Command | Catches |
| --- | --- | --- |
| Integrity | `node main/manager-web/scripts/integrity-check.js` | undefined identifiers (lost imports, dropped function params/`const request` bindings), mismatched template tags, duplicated keys in `export default` options and inside `watch`/`computed`/`methods`/`data` (later value silently clobbers the first) |
| i18n | `cd main/manager-web && npm run check:i18n` | duplicate keys, cross-locale drift vs `en`, `$t('...')` keys with no definition in any locale |
| Snapshot contract | `npm run test:snapshot` | agent snapshot API shape (`restoreAgentSnapshot` etc. were silently deleted once, while `AgentSnapshotDialog.vue` still called them) |
| Han audit | `./scripts/westernization_audit.sh` | Chinese text/paths outside exception zones |
| Everything | `./scripts/westernization_rebase_check.sh` | one gate chaining all of the above plus build and smoke suites |

CI runs the same set: `Westernization audit` job plus the `Vue (manager-web)`
job (`integrity-check -> check:i18n -> test:snapshot -> test:contract ->
test:unit`). A nightly `Upstream Sync Check` workflow dry-merges
`upstream/main` and runs the web gates on the merged result, so an incoming
breaking merge alerts the night before a human syncs.

### Known merge-corruption failure classes (2026-10 postmortem)

These are the shapes the auto-merge produced; the integrity checker flags all
of them, but knowing the shapes speeds up conflict resolution:

1. **Lost import** - `components: { CustomDialog }` shorthand with no matching
   `import`. The chunk throws at eval time; webpack 5 caches the failed module,
   so vue-router silently registers `default === undefined` and the page
   renders `<!---->` with no console error.
2. **Dropped signature params / const bindings** - method bodies referencing
   `request`, `onTerminalFailure`, `retryCount`, `retryWindowStartedAt`,
   `failCallback` after the merge kept the old one-line signature. Compare
   against `upstream/main` when a method looks half-converted.
3. **Whole methods deleted** while callers survive in another merged file
   (`getRAGModels`, snapshot API). The integrity checker cannot see this (no
   undefined identifier), so `Api.*` cross-reference plus the snapshot contract
   tests exist; re-run the cross-reference from the postmortem after big
   merges (snippet in commit `583c5304` message area, or grep `Api\.\w+\.\w+`
   and diff against module exports).
4. **Interleaved implementations** - both an old `el-table` block and a new
   `CustomTable` block merged into one view (ProviderManagement). When tags
   mismatch like this, prefer taking upstream's newer version wholesale and
   re-applying the few translation strings, instead of surgical repair.
5. **Half-converted components** - root tag converted (`el-dialog` ->
   `CustomDialog`) but closing tag/footer wiring left behind
   (FirmwareDialog, AddWisdomBodyDialog, CustomDialog's duplicated `computed`).
6. **Duplicate keys inside option maps** - the 2026-10-11 merge left two
   `dialogVisible` handlers inside `watch:` in ModelEditDialog.vue (the
   later, trivial one clobbered the version holding the `loadModelData()`
   open-trigger, so the model edit form opened empty), plus dead duplicate
   `handleSearch` in home.vue and duplicate `formatFileSize` in
   KnowledgeBaseManagement.vue (the latter two survived into the pushed
   tree). Top-level `computed:` duplication was caught earlier; keys nested
   in `watch`/`methods` are just as silent. `integrity-check.js` now parses
   the options object and its `watch`/`computed`/`methods`/`data` maps and
   fails on any duplicate key. After any rebase touching a `.vue` file that
   exists on both sides, diff its option maps against upstream, not just
   the template.

### Translation tool

The Han->English batch translator used for sweeps is vendored:

```bash
# needs the local OpenAI-compatible endpoint (override via env)
TRANSLATE_API=http://10.0.1.9:2000/v1/chat/completions \
TRANSLATE_MODEL=qwen3.8:instruct \
python3 scripts/translate_han_llm.py [path ...]   # no args = whole repo
```

It is placeholder-safe (printf/brace/tag/URL masking), batched, cached
(`scripts/.translate_cache.json`, gitignored) and resumable. Never translate
inside the generator bundle - fix generator source (see Generator Rule) and
rebuild.

## Audit Workflow

Use the audit script after meaningful rebase batches:

```bash
./scripts/westernization_audit.sh
```

The audit is a single Python implementation
(`scripts/westernization_audit.py`, wrapped by
`scripts/westernization_audit.sh`) so local and CI runs cannot diverge.
It scans `git ls-files -co --exclude-standard`, i.e. tracked files are
inspected even when a broad gitignore rule (e.g. `*.json`) hides them from
ripgrep; files with a NUL byte or media/font/model extensions are skipped as
binary blobs.

What it enforces:

- live source/docs must be clean of Han-script and Chinese locale tags
- this includes the vendored generator code bundle
  (`main/manager-web/public/generator/assets/**` and `index.html`)
- this includes vendored model metadata (`.cdi3.json`, `.physics3.json`) which
  ships editable display names
- path names must be clean of Han-script

Intentional exception zones:

- `main/manager-api/src/main/resources/db/changelog` (append-only Liquibase
  history; fresh installs are migrated and cleaned to English by the append
  downstream changeset)
- `main/manager-web/public/generator/static/**` (functional device data shipped
  byte-for-byte: charset codepoint lists, CJK glyph tables, wakeword blobs)
- one allowlisted line inside the generator bundle: the third-party opentype.js
  LCID-to-BCP47 font-name table (it maps locale ids such as 1028)

If the audit fails outside those areas, fix the violations before moving on.

## Verification Workflow

Run the owning subsystem checks after each slice when possible.

### Python server

```bash
cd main/xiaozhi-server
PYTHONPATH=. pytest tests/ -q
```

Or the interactive harness:

```bash
cd main/xiaozhi-server && PYTHONPATH=. python3 ../digital-human/test_runner.py
```

### Manager API

```bash
cd main/manager-api
mvn -q -DskipTests compile
mvn test -q
```

Liquibase final-state validation matters here. Do not rely only on compile or
Spring tests that skip Liquibase.

Use the dedicated fresh-DB integration harness too:

```bash
cd main/manager-api
mvn -q -Dtest=LiquibaseWesternizationIntegrationTest test
```

What it checks:

- replays the full changelog chain on a fresh H2 database
- applies downstream append-only cleanup migrations
- writes a final seed dump to
  `main/manager-api/target/liquibase-h2-seed-dump.txt`
- asserts that westernized final-state rows are present
- asserts that Chinese-facing seeded rows/tokens do not survive in the final
  surfaced data

Harness files:

- `main/manager-api/src/test/java/xiaozhi/modules/sys/LiquibaseWesternizationIntegrationTest.java`
- `main/manager-api/src/test/java/xiaozhi/modules/sys/H2JsonFunctions.java`

### Manager Web

```bash
cd main/manager-web
npm run check:integrity   # AST/template/option-key checks (see tooling table)
npm run check:i18n
npm test
npm run build
```

Or from the repo root, everything at once:

```bash
./scripts/westernization_rebase_check.sh
```

### Manager Mobile

```bash
cd main/manager-mobile
pnpm build:h5
pnpm type-check
```

If a verification step fails because of an upstream baseline issue, note that
clearly and avoid mixing that fix with unrelated westernization work unless it
blocks progress.

## High-Risk Areas

Be extra careful in these zones:

- Liquibase history
- provider metadata and seeded defaults
- generated web assets
- locale registries
- firmware/device dictionaries and model voice lists
- anything that can silently re-surface a removed Chinese provider

## Good Outcomes

A rebase is in good shape when all of these are true:

- deleted downstream providers stay deleted
- relocalized downstream providers stay relocalized
- upstream fixes are retained in surviving abstractions
- web/mobile shipped surfaces are English-first and non-Chinese-facing
- server runtime prompts and tool text are westernized
- docs and filenames are clean outside intentional exception zones
- `./scripts/westernization_audit.sh` passes
- `./scripts/westernization_rebase_check.sh` passes (integrity, i18n, web tests, build)
- `mvn -q -Dtest=LiquibaseWesternizationIntegrationTest test` passes

## Bad Smells

Stop and correct course if any of these happen:

- a removed provider reappears in config, UI, migrations, or docs
- Chinese locale assumptions return as defaults
- generated assets are edited directly without checking source
- large translated docs get copied forward when a shorter English reference
  would do
- old migrations are rewritten instead of adding cleanup migrations
- the branch drifts into a single giant mixed overlay again
- the web build is green but a page renders blank - the build only *warns* on
  broken templates; run `scripts/integrity-check.js`, it makes those errors
  fatal
- a merged view/API file "looks fine" but half its function signatures changed
  style - diff the file against `upstream/main`, not just against HEAD~1

## Practical Order On Future Rebases

When upstream moves a lot, use this order:

1. rebase or merge upstream into an integration branch
2. scan the merge result for the five corruption shapes listed under "Known
   merge-corruption failure classes" (`integrity-check.js` finds 1, 2, 4, 5)
3. restore provider/runtime deletions and relocalization
4. restore admin API provider filtering and downstream cleanup migrations
5. restore web/mobile surface cleanup
6. restore docs/branding cleanup
7. rebuild generator from source if needed
8. run `./scripts/westernization_rebase_check.sh` (audit + web gates)
9. run subsystem validation (mvn, pytest)
10. only then promote the integration branch

## Final Reminder

The purpose of downstream is not "translate upstream."

The purpose is to preserve a westernized product surface while still inheriting
upstream engineering improvements.
