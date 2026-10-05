# Jev Classifier Foundation Implementation Plan (spec 1, shadow-first)

> **For agentic workers:** executed by Compound V on Engine C from one manifest
> (`docs/superpowers/execution/2026-10-05-jev-classifier-foundation/manifest.yaml`). Spec:
> `docs/superpowers/specs/2026-10-05-jev-classifier-foundation-design.md` — its "Plan-review amendments" section
> overrides the sections above it. Pre-flight audits (their §7 MUSTs bind; 1A line numbers are from 3.5.1, the anchors
> below are current for 3.8.0): `docs/superpowers/archaeology/2026-10-05-2026-10-05-jev-classifier-foundation-design.md`,
> `docs/superpowers/expert/2026-10-05-2026-10-05-jev-classifier-foundation-design.md`,
> `docs/superpowers/library-audit/2026-10-05-2026-10-05-jev-classifier-foundation-design.md`.
> `scripts/compound-v-preeval.py` (3,100+ lines) and `scripts/compound-v-onboard.py` (2,500+): grep for the named
> symbols and read only those ranges. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Put Jev (TypeSafe System One, via OpenRouter) beside Compound V's classifiers in shadow, measure it
on a committed corpus, and use it where it is safe today (UI detection and the onboarding layer draft), with the key
held only by a separate vault plugin.

**Architecture:** Plugin `compound-v-vault` holds the OpenRouter key in sensitive `userConfig`, declares the `$.jev`
noun (its only HTTP client), offers the model one tool (`jev_classify`) for request files, and records egress consent.
Compound V gains a key-free Python layer (`scripts/compound-v-jev.py`), a record `t3` block, a deterministic
`detect_ui` floor, and a second hooks module (`hooks/jev-t3.tsx`) that, in shadow, asks Jev the T3 question after
the existing triage hook has decided and stores the pair. No decision changes in spec 1 except `detect_ui` (monotonic)
and the onboarding draft (human-gated).

**Tech Stack:** Python 3.9 stdlib (`/usr/bin/python3 -B`), bash + shellcheck, TypeScript hooks modules
(Claude Code mods ≥ 2.1.287; tests pin 2.1.289 as `tests/test-run-band-mod.sh` does), jq, git.

## Global Constraints

- Python 3.9 syntax, stdlib only; no `typesafe_sdk`; no `match`; no `X | Y` annotations.
- Never Haiku. Jev is not a Claude tier and never appears in a manifest `tier`.
- The OpenRouter key exists only in the vault plugin: secure storage, `options`, the `$.http.fetch` header. Never in
  a Python process, an env var, argv, a file, a log line, a tool result or the transcript.
- The vault never answers a Bash tool call; `lane-guard.sh` and permission prompts stay in force.
- Request text never in argv. Local Jev data lives in `~/.claude/compound-v-jev/<repo-digest>/` (dir 0700, files
  0600; `<repo-digest>` = first 16 hex of sha256 of the repo's absolute real path); retention 30 days, pruned on write.
  Nothing Jev-related is written under the repository except the corpus fixture and the code.
- Error bodies from OpenRouter carry the account's `user_id`: never copy any part of an error body anywhere; record
  only the status class.
- `t3.mode` is `off|shadow` in spec 1. The triage decision, the record's tier and every existing hook output are
  byte-identical to today on every existing fixture.
- Model pinned `typesafe/jev-1.13`; record the resolved id the response returns (live: `typesafe/jev-1.13-20260917`).
- No fabricated metrics: `latency_ms` measured; `usage.cost` dropped; no cost or savings text (anti-ruflo regex,
  `.github/workflows/validate.yml:194`).
- Every behavioural change ships a selftest/test row that fails when the change is reverted.
- Docs: plain words, every claim true of HEAD, no line over 200 characters outside code/tables.
- Lane discipline: touch only your `write_allowed`; `register-lane` first, with a literal `--cwd`.
- Names fixed by the Interfaces below; do not rename. Commit subjects are plain sentences, no `feat:`/`fix:`.
- Not in any implementation job: version bump, CHANGELOG, marketplace entry, `.gitignore`, release (Task R).

## Live probe (maintainer, 2026-10-05, `jev-probe.py` outside the repo, 9 calls)

- `POST https://openrouter.ai/api/v1/systemone` → 200. Request `{model, state, questions: {<name>: {type,
  instructions, criteria}}}`.
- Choice answer `{type: "choice", choice, probabilities: {label: p}, confidence}`; Noul `{type: "noul", noul: p}`; top
  level adds `model`, `usage {input_tokens, output_tokens, cost}`, `id`, `provider`.
- `typesafe/jev-1.13` and `~typesafe/jev-latest` both resolved to `typesafe/jev-1.13-20260917`.
- `probabilities` key order is not preserved: parse by label. Clear case gave exact 0/1.
- Latency 268-657 ms on that machine. No rate-limit or `Retry-After` headers on success.
- 400 body: `{"error": {"message", "code"}, "user_id": …}`.

## Partition Map

| Job | Wave | write_allowed | depends_on |
|---|---|---|---|
| `record-t3` (A) | 1 | `scripts/compound-v-preeval.py`, `schemas/pre-eval-record.schema.json` | none |
| `config-jev` (B) | 1 | `scripts/compound-v-project-config.py`, `commands/v-init.md` | none |
| `jev-core` (C) | 1 | `scripts/compound-v-jev.py`, `tests/test-jev-core.sh` | none |
| `vault` (D) | 1 | `plugins/compound-v-vault/**`, `tests/test-vault-mod.sh` | none |
| `ui-floor` (E1) | 1 | `scripts/compound-v-onboard.py` | none |
| `corpus` (K) | 1 | `tests/fixtures/jev-t3-corpus.jsonl`, `tests/fixtures/README-jev-corpus.md` | none |
| `onboard-jev` (E2) | 2 | `scripts/compound-v-onboard.py`, `skills/compound-v/onboarding.md`, `commands/v-onboard.md` | ui-floor, jev-core, vault |
| `t3-hook-shadow` (F1) | 2 | `hooks/triage-prompt-nudge.sh`, `tests/test-native-points.sh` | record-t3, jev-core |
| `t3-mod-shadow` (F2) | 2 | `hooks/jev-t3.tsx`, `hooks/jev-t3.test.tsx`, `hooks/hooks.json`, `types/index.d.ts`, `tests/test-jev-t3-mod.sh`, `skills/compound-v/phase-preeval.md` | jev-core, vault, config-jev |
| `review` (H) | 3 | `.claude/agent-memory/superpowers-v-spec-reviewer/**` | all |
| release (R) | after H, maintainer session | `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.gitignore`, `CHANGELOG.md`, `README.md`, `AGENTS.md`, `TROUBLESHOOTING.md` | review |

Shared resources and their single owner: record shape (A); config loader (B); `hooks.json` and `types/index.d.ts`
(F2); `onboard.py` (E1 in wave 1, E2 in wave 2, never concurrently); marketplace (R). F1 and F2 meet only through the
pending-descriptor contract below and are tested against it independently.

---

### Task A: Record `t3` block and request file (`record-t3`)

**Files:** `scripts/compound-v-preeval.py` — `_verdict` (:794-842), `build_record` (:957-1021; optional keys
:1005-1007; digest :1020), `run_preeval` (:1200-1386), `triage_request` (:1519-1620), `_triage_cli` (:1623-1665),
`_selftest` (:1916; T3 rows :2151-2295, E2E :2683-2693). `schemas/pre-eval-record.schema.json` `properties` (:87-218).

**Interfaces (produced):**
- `triage` flags: `--request-file PATH` (third member of the required `--request | --request-env` group; UTF-8, one
  trailing newline stripped), `--t3-engine {claude,codex,parent}`, `--t3-probs-json JSON`, `--t3-model STR`,
  `--t3-catalogue-hash STR`. (`jev` is not a deciding engine in spec 1; the enum keeps room for it in the schema.)
- `run_preeval(..., t3_meta=None)`, `triage_request(..., t3_meta=None)`; `t3_meta = {"engine", "category",
  "probs"?, "model"?, "catalogue_hash"?}`.
- Record key `t3` (present only when `t3_meta` was given and `"T3" in tiers_signalled`); `triage` JSON echoes `t3`.

- [ ] **Step 1: Selftest rows first (must FAIL now).** (a) demotion fixture + `t3_category="plumbing"` +
  `t3_meta={"engine":"claude","category":"plumbing"}` → record `t3 == {"engine":"claude","category":"plumbing"}`,
  validates (`_schema_check`) — planted failure: omit `t3` from the optional-key loop; (b) digest changes when
  `t3.engine` changes — planted failure: assign after the digest; (c) `t3_meta` given, T3 not consulted → no `t3` key;
  (d) `t3_meta=None` → record bytes identical to a build without the parameter, for every existing T3 fixture;
  (e) `--request-file` reads the request; an empty file → `REFUSED` exit 2; (f) schema rejects `t3.engine:"jev2"`,
  a prob outside [0,1], and a `t3` without `category`; (g) the `predicted` event count is unchanged by `t3_meta`.
- [ ] **Step 2: Run** `/usr/bin/python3 -B scripts/compound-v-preeval.py --selftest` → only the new rows fail.
- [ ] **Step 3: Schema** — add to `properties`:
  ```json
  "t3": {
    "type": "object", "additionalProperties": false, "required": ["engine", "category"],
    "properties": {
      "engine": {"type": "string", "enum": ["jev", "claude", "codex", "parent"]},
      "category": {"type": "string", "enum": ["plumbing", "user-facing-minor", "user-facing-major", "unknown"]},
      "probs": {"type": "object", "additionalProperties": {"type": "number", "minimum": 0, "maximum": 1}},
      "model": {"type": "string", "maxLength": 80},
      "catalogue_hash": {"type": "string", "maxLength": 80}
    }
  }
  ```
- [ ] **Step 4: Plumbing.** `score()` unchanged. In `run_preeval`, when the verdict's `tiers_signalled` contains
  `"T3"` and `t3_meta` is not None, set `verdict["t3"]` to `t3_meta` without `None` fields. Extend the loop at
  :1005-1007 to `("flavor", "t3_demotion", "t3_reason", "t3")`.
- [ ] **Step 5: CLI.** Add the flags; `--t3-probs-json` must parse to an object of numbers, else exit 2
  `REFUSED: --t3-probs-json`. Build `t3_meta` only when `--t3-engine` is given, with `category = --t3-category`.
- [ ] **Step 6: Run** the selftest → green; `bash tests/test-native-points.sh`;
  `python3 tests/v2.9-e2e/test_fastpath_and_escalation.py`.
- [ ] **Step 7: Commit** `Record which engine answered T3, with its category and probabilities`.

---

### Task B: `jev` config resolver and `/v:init` seed (`config-jev`)

**Files:** `scripts/compound-v-project-config.py` (beside `resolve_pre_eval` :138-199; `load_project_config`
:100-118; `main` :215-232; `_selftest` :238-356). `commands/v-init.md` Step 4a seed (:549-592), bullets (:603-710).

**Interfaces (produced):** `JEV_DEFAULTS`; `resolve_jev(cfg) -> (values, warnings)`, never raises:
```python
{"enabled": True, "model": "typesafe/jev-1.13",
 "t3": {"mode": "shadow", "confidence_min": 0.8, "calibrated_model": None},
 "detect_ui": {"mode": "active", "confidence_min": 0.8},
 "onboard": {"mode": "active", "confidence_min": 0.8}}
```
`t3.mode` ∈ `off|shadow` (`active` → `shadow` + warning naming spec 1.5); `detect_ui.mode`/`onboard.mode` ∈
`off|active`; `confidence_min` float in (0, 1], not bool. CLI output gains `"jev"`.

- [ ] **Step 1: Selftest rows first:** defaults when absent; `t3.mode: "active"` → `"shadow"` + warning (planted
  failure: accept `active`); `confidence_min` 0 / 1.5 / `true` → 0.8 + warning; `model: ""` → default;
  `jev: []` → `load_project_config` raises `ValueError`.
- [ ] **Step 2: Run** `python3 scripts/compound-v-project-config.py --selftest` → new rows fail.
- [ ] **Step 3: Implement** in the `resolve_pre_eval` style; add the `jev` object check to `load_project_config`;
  print `"jev"` in `main`.
- [ ] **Step 4: `/v:init`:** add the `jev` block to the Step 4a seed and one bullet: committed team policy only;
  the key and egress consent live in the vault plugin, never here; `t3` is shadow-only until spec 1.5.
- [ ] **Step 5: Run** → green. **Commit** `Add the jev config block and its resolver`.

---

### Task C: `scripts/compound-v-jev.py` (`jev-core`)

**Files:** create `scripts/compound-v-jev.py`, `tests/test-jev-core.sh`.

**Interfaces (produced):**
- CLI (one JSON object on stdout; exit 0 unless usage error = 2; selftest via the literal `--selftest` flag so the CI
  sweep at `validate.yml:298-312` finds it):
  - `build --point {t3,detect_ui,onboard_layer} --state-file F --repo R` → writes
    `<data_dir>/req/<uuid>.req.json`, prints `{"status":"ok","request_file":…}` or
    `{"status":"error","reason":"bad_input"|"redaction"}`.
  - `parse --response-file F --repo R --mode M [--hook-budget-left-ms N]` →
    `{status, reason?, point, answers: {<name>: {type, answer, probs}}, latency_ms, model, catalogue_hash}`;
    appends one telemetry line.
  - `pair --request-file F --claude-category C --backend B --t3-reason R --repo R` → appends one shadow pair line.
  - `eval --t3 --prepare --corpus F [--pairs] --repo R` → `{"request_files": [...]}` (originals, a reversed-order
    variant and two alternate-wording variants each); `eval --t3 --report OUT --repo R` → writes the markdown report.
  - `data-dir --repo R` → prints the resolved data dir (creates it 0700).
- `<data_dir>` = `~/.claude/compound-v-jev/<repo-digest>/`; files: `req/`, `resp/`, `calls.jsonl`,
  `shadow-pairs.jsonl`. Every write prunes entries older than 30 days.
- Request file: `{"point", "catalogue_hash", "model", "body": {"model", "state", "questions"}, "timeout_ms",
  "context": "hook"|"offline", "repo"}`. Response file (written by the vault, Task D): `{"status":
  "ok"|"unavailable"|"error", "reason"?, "http_status"?, "latency_ms", "body"?}`.

- [ ] **Step 1: Tests first** (`--selftest` and `tests/test-jev-core.sh`, offline; fake response files):
  - catalogue: T3 options in order `unknown, user-facing-major, user-facing-minor, plumbing` with the
    `_CATEGORY_DEFS` descriptions loaded from `compound-v-classify-request.py` by path (one source); hash stable, and
    different when a description changes (planted failure: sort the options);
  - `build`: insertion order kept in the written JSON (no `sort_keys`); every string in `state` passes
    `compound-v-epic-arbiter.py` `redact_uncapped` (loaded by path) and `None` → `error(redaction)`; > 32,000
    estimated tokens (0.25/char) → `error(bad_input)`; file 0600, dirs 0700;
  - `parse`: Choice → `{type:"choice", answer, probs}` keyed by label regardless of order; Noul →
    `{type:"noul", answer:"yes"|"no", probs:{"yes":p}}`; unknown keys ignored; `usage.cost` dropped; `http_status`
    401/403 → `unavailable(auth)`, 402 → `credits`, 429 → `rate_limited`, 5xx/524/529 → `upstream`, 400/422 →
    `error(bad_input)`; no `answers` → `error(schema)`; a response file holding an error body with `user_id` →
    nothing from the body in stdout or telemetry (planted failure: log the body);
  - telemetry: exactly `{ts, point, status, reason?, answer?, probs?, latency_ms, hook_budget_left_ms?, model,
    catalogue_hash, mode}`; never under the repository; never the state text;
  - `pair` writes `{ts, request_file, claude_category, backend, t3_reason}`; pruning removes a 31-day-old line;
  - `eval`: Wilson 95% interval rows on known inputs; zero inversions reports `3/n`; a mixed model-id set marks the
    report "not usable for gating"; the report contains a probability histogram (10 bins) and the share of answers
    with max prob in {0, 1}; no word from the anti-ruflo regex;
  - no output, file or log contains `sk-or-` or `Bearer `.
- [ ] **Step 2: Run** `python3 scripts/compound-v-jev.py --selftest` → fails (missing file).
- [ ] **Step 3: Skeleton** (Python 3.9, stdlib):
  ```python
  #!/usr/bin/env python3
  """compound-v-jev: key-free Jev request/response layer for Compound V.

  Builds System One requests, parses the vault's responses, writes metadata-only
  telemetry and shadow pairs to a per-user data dir, and runs the T3 eval. It never
  does network I/O and never sees the API key: the compound-v-vault plugin is the
  only HTTP client. Python 3.9-safe, stdlib only.
  """
  import argparse, hashlib, importlib.util, json, math, os, sys, time, uuid

  HERE = os.path.dirname(os.path.abspath(__file__))
  MODEL_DEFAULT = "typesafe/jev-1.13"
  TOKEN_BUDGET = 32000
  TOKENS_PER_CHAR = 0.25
  RETENTION_S = 30 * 86400
  T3_ORDER = ("unknown", "user-facing-major", "user-facing-minor", "plumbing")
  STRICTNESS = {"unknown": 3, "user-facing-major": 2, "user-facing-minor": 1, "plumbing": 0}
  LAYERS = ("unknown", "ui", "api", "domain", "data", "infra", "tooling", "tests", "docs")

  def _load(name, filename):
      spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, filename))
      mod = importlib.util.module_from_spec(spec)
      spec.loader.exec_module(mod)
      return mod

  def data_dir(repo):
      real = os.path.realpath(os.path.abspath(repo))
      digest = hashlib.sha256(real.encode("utf-8")).hexdigest()[:16]
      d = os.path.join(os.path.expanduser("~"), ".claude", "compound-v-jev", digest)
      for sub in ("", "req", "resp"):
          os.makedirs(os.path.join(d, sub), mode=0o700, exist_ok=True)
      return d

  def wilson(k, n, z=1.96):
      if n == 0:
          return (0.0, 1.0)
      p = k / n
      den = 1 + z * z / n
      mid = (p + z * z / (2 * n)) / den
      half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
      return (max(0.0, mid - half), min(1.0, mid + half))
  ```
- [ ] **Step 4: Catalogue.** `catalogue()` → per point `{"type", "instructions", "options"}`:
  `t3` Choice over `T3_ORDER` with `_CATEGORY_DEFS` text, instructions "What kind of change does `request`
  describe, given `paths` and `hints`?"; `detect_ui` one Noul named `ui`, state `{"files": [{"path", "head"}, …]}`,
  instructions "Does any file in `files` render user-facing markup or UI (HTML, templates, components, views)?";
  `onboard_layer` Choice named `layer` over `LAYERS`, one sentence per layer written out in full. Two alternate
  wordings per point for the eval live in `ALT_WORDINGS`. `catalogue_hash(point, variant=0)` = first 16 hex of
  sha256 of the canonical JSON of that entry.
- [ ] **Step 5: `build`, `parse`, telemetry, `pair`, pruning, `eval`** per the Interfaces and Step 1 rows.
- [ ] **Step 6: Run** `python3 scripts/compound-v-jev.py --selftest`, `bash tests/test-jev-core.sh`,
  `shellcheck tests/test-jev-core.sh` → green.
- [ ] **Step 7: Commit** `Add the key-free Jev request, response, telemetry and eval layer`.

---

### Task D: Plugin `compound-v-vault` (`vault`)

**Files:** create `plugins/compound-v-vault/.claude-plugin/plugin.json`, `plugins/compound-v-vault/hooks/hooks.json`,
`plugins/compound-v-vault/hooks/vault.tsx`, `plugins/compound-v-vault/hooks/vault.test.tsx`,
`plugins/compound-v-vault/types/index.d.ts`, `plugins/compound-v-vault/README.md`, `tests/test-vault-mod.sh`.

**Interfaces (produced):**
```ts
export type JevRequest = { point: string; catalogue_hash: string; model: string;
  body: { model: string; state: unknown; questions: Record<string, unknown> };
  timeout_ms: number; context: 'hook' | 'offline'; repo: string }
export type JevResponse = { status: 'ok' | 'unavailable' | 'error'; reason?: string;
  http_status?: number; latency_ms: number; body?: unknown }
export type Jev = {
  classify: (req: JevRequest) => Promise<JevResponse>
  status: (repo: string) => Promise<{ on: boolean; reason?: string }>
}
declare module 'claude-code' { interface EngineInterface { jev: Jev } }
```
- Model tool `jev_classify({ request_file })` → text: the response file path, or `refused: <reason>`. Accepts only
  regular files under `~/.claude/compound-v-jev/*/req/` (realpath check, no symlinks); writes the response to the
  sibling `resp/` dir with the same base name.
- Command `/compound-v-vault:egress allow|deny|status`; consent stored with `$.store` under `egress:<repo realpath>`.

- [ ] **Step 1: Confirm the API on the pinned build first.** Run
  `npx -y @anthropic-ai/claude-code@2.1.289 plugin-types <tmpdir>` (or `/plugin-types` on a ≥ 2.1.289 CLI) and
  confirm: `engine.create` adds a noun; `$.http.fetch(url, {method, headers, body})` → `{status, ok, headers, text}`;
  `$.store`; `$.tool.register`; `$.command.register`; `$.ui.status`/`$.ui.toast`; `$.env.get`; `$.fs`;
  `session.append`; how to race a timeout with `$.clock`; whether `claude plugin test` can stub `http.fetch`. Record
  each signature as a comment at the top of `vault.tsx`. If a noun cannot be added, or `http.fetch` cannot be stubbed,
  STOP and report BLOCKED with the evidence.
- [ ] **Step 2: Tests first** (`vault.test.tsx`): one POST with `Authorization: Bearer <key>`,
  `Content-Type: application/json`, body = `req.body`; `ok` carries `latency_ms` and the parsed body; no key →
  `unavailable(no_key)`, no fetch; `CV_HEADLESS_CLASSIFY=1` → `unavailable(disabled)`, no fetch; egress unanswered
  → `unavailable(egress)` and one toast per session, `deny` → `unavailable(egress)`, `allow` → fetch; 401/403 →
  `auth`, 402 → `credits`, 429 → `rate_limited` (offline: one retry only when `retry-after` ≤ 1 s, absent = none),
  5xx/524/529 → `upstream`, timeout (hook 1,500 ms / offline 5,000 ms) → `timeout`, 400/422 → `error(bad_input)`
  with **no body copied**, non-JSON → `error(schema)`; `usage.cost` is removed from `body`; `jev_classify` refuses
  `../`, symlinks and paths outside `req/`; the key string never appears in any `fs.write`, tool result, `$.ui`
  text or appended row (planted failure: copy request headers into the response file).
- [ ] **Step 3: Implement.** `plugin.json`:
  ```json
  { "name": "compound-v-vault", "version": "0.1.0",
    "description": "Holds the OpenRouter key for Compound V's Jev classifier and is its only HTTP client",
    "types": "./types/index.d.ts",
    "userConfig": {
      "openrouter_key": { "type": "string", "sensitive": true,
        "title": "OpenRouter API key (use a dedicated key with a credit limit)" },
      "route": { "type": "string", "default": "https://openrouter.ai/api/v1/systemone",
        "title": "System One endpoint" } } }
  ```
  `hooks/hooks.json` = `{ "modules": ["./vault.tsx"] }` only (no settings hooks, so no `CLAUDE_PLUGIN_OPTION_*`
  export reaches any Compound V hook). `vault.tsx`: `engine.create` adds `jev`; `session.start` registers the tool
  and command and sets the status line `Jev: on` / `Jev: off (<reason>)`; `session.append` replaces the key with
  `[redacted]`.
- [ ] **Step 4: README:** install, set the key in `/config`, run `/compound-v-vault:egress allow` once per repo,
  what leaves the machine (request text ≤ 2,000 chars, paths, taxonomy hints, file heads for UI detection) and to
  whom (OpenRouter, TypeSafe), no zero-retention claim, credit-limit advice, the boundary (other mods earlier in the
  chain can observe the vault's calls), Claude Code ≥ 2.1.287.
- [ ] **Step 5: `tests/test-vault-mod.sh`** modelled on `tests/test-run-band-mod.sh` (`PIN="2.1.289"`):
  `claude plugin validate plugins/compound-v-vault` reports the module with `engine.create`, `session.start`,
  `session.append` and no settings hooks; `claude plugin test plugins/compound-v-vault` reports 0 failures.
- [ ] **Step 6: Run** → green; `shellcheck tests/test-vault-mod.sh`. **Commit**
  `Add the compound-v-vault plugin, the key holder and only Jev HTTP client`.

---

### Task E1: Deterministic `detect_ui` floor (`ui-floor`)

**Files:** `scripts/compound-v-onboard.py` — `UI_SIGNALS`/`UI_EXT`/`detect_ui` (:369-380), `_repo_files` (:716-728),
`build_parser` (:2431-2468), `main` `detect-ui` (:2492-2494), selftest (:1751-1758).

**Interfaces (produced):** `detect_ui(repo) -> bool` (unchanged contract), `detect_ui_reason(repo) -> (bool, str)`
with reason `deterministic:<signal>` or `none`; CLI `detect-ui --repo R [--reason]` (`--reason` prints
`ui deterministic:<signal>` / `no-ui none`; without it, output unchanged).

- [ ] **Step 1: Selftest rows first:** WordPress theme root (`style.css` with `Theme Name:`), `theme.json` root,
  `.blade.php`, `.twig`, `.liquid`, `.erb`, `.hbs`, `.astro`, `.swift` with `import SwiftUI`, `.php` with `<div>`
  outside `<?php ?>` → `True` with the matching reason; docs site with only `.html` → `False` (planted failure: add
  `.html`); non-git tree with a `.tsx` → `True` (switch to `_repo_files`); existing rows (:1751-1758) unchanged.
- [ ] **Step 2: Run** `python3 scripts/compound-v-onboard.py --selftest` → new rows fail.
- [ ] **Step 3: Implement** with `_repo_files` and bounded reads (`_read_bounded`, ≤ 64 KB, sorted, first match wins).
- [ ] **Step 4: Run** → green. **Commit** `Detect PHP, template-engine, SwiftUI and WordPress UIs deterministically`.

---

### Task K: T3 eval corpus (`corpus`)

**Files:** create `tests/fixtures/jev-t3-corpus.jsonl`, `tests/fixtures/README-jev-corpus.md`.

**Interfaces (produced):** one JSON object per line: `{"id", "request", "paths", "hints", "t3_reason",
"label_draft", "label_source": "implementer-draft", "human_label": null, "claude_label": null}`.

- [ ] **Step 1:** Write 80 synthetic T3-shaped requests (no real secrets, no customer data): 20 per category, of
  which at least 30 are deliberately ambiguous (minor-vs-major copy, refactors that touch auth paths, config
  constants, migrations named like tooling). Each `t3_reason` ∈ `unbanded|demotion|sensitive`, with paths a real
  taxonomy would route that way. `request` ≤ 2,000 chars.
- [ ] **Step 2:** README: purpose, schema, that `label_draft` is the implementer's guess, that `human_label` is filled
  by the maintainer and `claude_label` by running the existing classifier (`compound-v-classify-request.py
  --classify-headless`) before the eval, and that the corpus must never hold secrets.
- [ ] **Step 3:** Validate: every line parses, ids unique, categories in the enum, `request` under 2,000 chars,
  `compound-v-memory.py` `SECRET_RE` finds nothing. **Commit** `Add a synthetic T3 corpus for the Jev eval`.

---

### Task E2: Jev for UI detection and the onboarding layer draft (`onboard-jev`, wave 2)

**Files:** `scripts/compound-v-onboard.py` (`draft_taxonomy` :906-932, `emit_taxonomy_yaml` :851-890, CLI),
`skills/compound-v/onboarding.md` (:65-77, :144-148, :205-209), `commands/v-onboard.md` (:38-41, :87-88).

**Interfaces:** consumes Task C CLI (`build`, `parse`, `data-dir`) by subprocess with a minimal env (`PATH`, `HOME`,
`TMPDIR`, `LANG`) and the vault tool `jev_classify` through the documented command flow; produces CLI
`jev-requests --repo R --point {detect_ui,onboard_layer}` → `{"request_files": [...]}`,
`detect-ui --jev-responses DIR`, `draft-taxonomy … --jev-responses DIR`.

- [ ] **Step 1: Selftest rows first** (fake response files): `detect_ui` Jev runs only when the floor says `False`;
  one Noul over a sample of ≤ 12 files × 20 lines, sorted, excluding `.env`, `*.pem`, `*.key`, `.github/**`, Layer A
  sensitive globs and any file `scan_secrets` flags; `yes ≥ detect_ui.confidence_min` → `True` with reason
  `jev:sample`; a "no" never flips a deterministic `True`; mode `off` → no request. Layer draft: one request per
  top-level directory (cap 40; state = name + ≤ 30 paths); a layer answer only adds a row for a directory that has no
  row today, never lowers one, never touches `sensitive_path_list`; `emit_taxonomy_yaml` writes
  `# source: jev layer=<l> p=<p>` above that row and the YAML still validates.
- [ ] **Step 2: Run** → new rows fail. **Step 3: Implement.** Layer → bands table in one place
  (`ui`/`api` → medium/high; `domain`/`data` → medium/high; `infra` → medium/high; `tooling`/`tests`/`docs` →
  low/low; `unknown` → no row).
- [ ] **Step 4: Docs:** onboarding DETECT runs `detect-ui --reason`; when `no-ui` and `Jev: on`, run `jev-requests`,
  call `jev_classify` per file, then `detect-ui --jev-responses`; DIAGNOSE does the same for `onboard_layer`; WRITE
  keeps the per-row human gate. `v-onboard.md` non-negotiable 5 names both reason kinds.
- [ ] **Step 5: Run** → green. **Commit** `Ask Jev about UI and directory layers during onboarding, behind the floor and the gate`.

---

### Task F1: T3 shadow in the hook (`t3-hook-shadow`, wave 2)

**Files:** `hooks/triage-prompt-nudge.sh` (`_classify_headless` :382-423, re-entry :604-639), `tests/test-native-points.sh`
(T3 cases :519-606, pins :609-630).

**Interfaces (produced):** pending descriptor, written only when `CV_JEV_T3=1` and T3 was consulted and decided:
`<data_dir>/pending-<digest(proj|sid)>.json` = `{"pre_eval_id", "request_file", "t3_reason", "claude_category",
"backend", "proj", "sid"}` (0600; `request_file` from `compound-v-jev.py build --point t3`, state =
`{request (≤ 2,000 chars), paths, hints}` written to a 0600 temp file first and deleted after `build`).
`_classify_headless` prints `category<TAB>backend`; re-entry passes `--t3-engine <backend>`.

- [ ] **Step 1: Tests first:** every existing T3 case byte-identical in output with `CV_JEV_T3` unset and set
  (planted failure: change any context line when the flag is set); with `CV_JEV_T3=1`, case 1 writes a descriptor
  whose `claude_category` is `user-facing-minor` and `backend` is `claude`, and the record has
  `t3 == {"engine":"claude","category":"user-facing-minor"}`; without the flag, no descriptor and no `t3` engine
  change beyond `--t3-engine`; a `build` failure leaves the hook output unchanged and writes no descriptor; static
  pins unchanged (`_CLASSIFY_TIMEOUT_S=15`, timeout 25, no matcher, `|| true`).
- [ ] **Step 2: Run** `bash tests/test-native-points.sh` → new rows fail.
- [ ] **Step 3: Implement** after a decided T3 re-entry only; never before or instead of today's path; every new
  command `|| true`-guarded; `umask 077`; `jq` for JSON.
- [ ] **Step 4: Run** → green; `shellcheck hooks/triage-prompt-nudge.sh`; `bash tests/test-hook-recursion-guard.sh`.
- [ ] **Step 5: Commit** `Leave a T3 shadow descriptor for the Jev module, without changing the hook's decision`.

---

### Task F2: `hooks/jev-t3.tsx` shadow module (`t3-mod-shadow`, wave 2)

**Files:** create `hooks/jev-t3.tsx`, `hooks/jev-t3.test.tsx`, `tests/test-jev-t3-mod.sh`; modify `hooks/hooks.json`
(`modules`), `types/index.d.ts`, `skills/compound-v/phase-preeval.md` (T3 contract :91-115).

**Interfaces:** consumes the F1 descriptor, Task C (`parse`, `pair`), Task D `$.jev`, Task B `resolve_jev` (via
`python3 scripts/compound-v-project-config.py <repo>`).

- `session.start`: if `'jev' in $` and `(await $.jev.status(cwd)).on` and `resolve_jev` says `t3.mode == "shadow"`,
  `$.env.set("CV_JEV_T3", "1")` (a non-secret capability flag); else unset it.
- `classic.UserPromptSubmit`: `const res = await next(e)`; if `CV_HEADLESS_CLASSIFY=1` or no descriptor for this
  `(proj, sid)` → `return res`. Otherwise read the request file, `await $.jev.classify(req)`, write the response
  file, run `compound-v-jev.py parse --mode shadow --hook-budget-left-ms <n>` then `pair`, delete the descriptor,
  and `return res` **unchanged** (never touch `additionalContext`).
- Every `$.process.run` is an argv array with a 30 s cap and no secrets; script paths from `$.plugin.root`.
- `types/index.d.ts`: keep the existing `PluginState` block; add a local structural type for `$.jev` used through a
  runtime guard (`'jev' in $`), so the module compiles and validates with or without the vault installed.

- [ ] **Step 1: Tests first** (`claude plugin test`, stubbing `jev`, `process.run`, `fs`, `env`): no `$.jev` →
  `CV_JEV_T3` unset, passthrough; descriptor present → one `classify`, `parse` and `pair` argv in order, result
  deep-equal to `res` (planted failure: append a context line); `classify` → `unavailable` → `parse` still records
  it, result unchanged; `CV_HEADLESS_CLASSIFY=1` → nothing; t3 mode `off` → flag unset.
  `tests/test-jev-t3-mod.sh` (`PIN="2.1.289"`): `claude plugin validate .` lists both modules (`run-band.tsx`,
  `jev-t3.tsx`) and reports that `plugins/compound-v-vault` is not loaded as part of this plugin (if it is, STOP and
  report BLOCKED: Task R must move the marketplace root); `claude plugin test .` → 0 failures;
  `bash tests/test-run-band-mod.sh` still green.
- [ ] **Step 2: Run** → new rows fail. **Step 3: Implement**; append `"./jev-t3.tsx"` to `hooks.json` `modules`.
- [ ] **Step 4: Docs:** `phase-preeval.md` names the shadow route, where pairs live, and that no decision changes in
  spec 1.
- [ ] **Step 5: Run** all → green. **Commit** `Ask Jev the T3 question in shadow after the hook decides`.

---

### Task H: Review Gate (`review`, wave 3)

- [ ] `spec-reviewer` (Opus): the three passes against the spec (amendments section first) and the Global
  Constraints, with explicit checks: grep the diff for `sk-or-`, `Bearer`, `openrouter_key`, `user_id` outside
  `plugins/compound-v-vault/`; no network imports (`urllib`, `http.client`, `socket`) in `compound-v-jev.py`; every
  existing hook output byte-identical with and without `CV_JEV_T3`; no `$.process.run` argv carries request text;
  nothing Jev-related written under the repo except code, tests and the corpus.

---

### Task R: Release (maintainer session, after H)

- [ ] Marketplace entry for `compound-v-vault` (`source: "./plugins/compound-v-vault"`, `0.1.0`); `superpowers-v`
  `3.9.0` in `plugin.json` and `marketplace.json`; CHANGELOG `3.9.0`; README/AGENTS/TROUBLESHOOTING: setup, egress,
  status-line reasons, Claude Code ≥ 2.1.287 for the vault, where local Jev data lives and its retention, how to
  label the corpus and run `eval --t3`. Full CI locally. Commit `v3.9.0 Jev classifier in shadow and the
  compound-v-vault plugin`.

## After release: the eval that decides spec 1.5

1. Maintainer fills `human_label` in the corpus; runs the existing classifier to fill `claude_label`.
2. `compound-v-jev.py eval --t3 --prepare --corpus tests/fixtures/jev-t3-corpus.jsonl --pairs`, `jev_classify` over
   the listed files, then `eval --t3 --report docs/superpowers/research/<date>-jev-t3-eval.md`.
3. Spec 1.5 chooses on that report: "Jev decides only when it cannot lower the tier" versus provisional demotions
   confirmed at bind, the model-drift gate (`t3.calibrated_model`), and whether to gate on thresholds or on
   agreement (if most answers are hard 0/1).

## Self-review

- Spec coverage (amendments applied): vault → D; key-free layer, telemetry, eval → C; record `t3` → A; shadow → F1,
  F2; corpus → K; `detect_ui` floor → E1; Jev UI/onboard → E2; config → B; durable local data → C (data dir), F1/F2
  consumers; hook safety → F1 Step 1, F2 Step 1; AC1 → E1/F1/F2 identity rows; AC2 → F1, F2; AC3 (shadow-only) → B;
  AC4 → D, H; AC5 → C; AC6 → E1.
- Fable review findings: F1 scope cut (whole plan); F2, F3 (F1/F2 never stop or touch context); F4, F5, F8 deferred with
  active (F5's durable dir applied now); F6 (descriptor carries `claude_category`, `t3` has `category`); F7 (corpus,
  histogram); F9 (one Noul over the sample); F10 (E split); F11 (`types/index.d.ts` in F2, runtime guard); F12
  (validate check in F2); F13 (telemetry outside the repo); F14 (types from the pinned CLI); F15 (`category<TAB>backend`);
  F16 (`$.store`, README first-run step).
- Names checked across tasks: `t3_meta`, `--t3-engine`, `--t3-probs-json`, `--t3-model`, `--t3-catalogue-hash`,
  `--request-file`, `resolve_jev`, `data_dir()`, `CV_JEV_T3`, `pending-<digest>.json`, `shadow-pairs.jsonl`,
  `$.jev.classify`, `$.jev.status`, `jev_classify`, `detect_ui_reason`, `jev-requests`, `--jev-responses`.
