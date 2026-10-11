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

Treat this as special:

- `main/manager-web/public/generator/assets/**` is generated output
- `main/manager-web/public/generator/index.html` is tied to that output

Do not hand-edit the built bundle unless absolutely necessary.

Preferred flow:

1. update generator source
2. rebuild generator
3. sync rebuilt assets into `main/manager-web/public/generator`

Generator source currently lives outside the main repo worktree during rebuild
work:

- `/tmp/xiaozhi-assets-generator`

If Han-script appears in the generated bundle, check generator source locales
first before attempting bundle surgery.

## Audit Workflow

Use the audit script after meaningful rebase batches:

```bash
./scripts/westernization_audit.sh
```

What it enforces:

- live source/docs must be clean of Han-script and Chinese locale tags
- path names must be clean of Han-script

Intentional exception zones:

- `main/manager-api/src/main/resources/db/changelog`
- `main/manager-web/public/generator/assets`

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
npm run build
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

## Practical Order On Future Rebases

When upstream moves a lot, use this order:

1. rebase or merge upstream into an integration branch
2. restore provider/runtime deletions and relocalization
3. restore admin API provider filtering and downstream cleanup migrations
4. restore web/mobile surface cleanup
5. restore docs/branding cleanup
6. rebuild generator from source if needed
7. run the audit script
8. run subsystem validation
9. only then promote the integration branch

## Final Reminder

The purpose of downstream is not "translate upstream."

The purpose is to preserve a westernized product surface while still inheriting
upstream engineering improvements.
