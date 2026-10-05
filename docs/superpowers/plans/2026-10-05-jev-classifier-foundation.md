# Jev Classifier Foundation Implementation Plan

> **For agentic workers:** executed by Compound V on Engine C from one manifest
> (`docs/superpowers/execution/2026-10-05-jev-classifier-foundation/manifest.yaml`). Spec:
> `docs/superpowers/specs/2026-10-05-jev-classifier-foundation-design.md`. Pre-flight audits:
> `docs/superpowers/archaeology/2026-10-05-2026-10-05-jev-classifier-foundation-design.md` (1A, written on
> 3.5.1: its line numbers are stale, the anchors below are current for 3.8.0),
> `docs/superpowers/expert/2026-10-05-2026-10-05-jev-classifier-foundation-design.md` (1B),
> `docs/superpowers/library-audit/2026-10-05-2026-10-05-jev-classifier-foundation-design.md` (1C). Their §7
> MUSTs bind. `scripts/compound-v-preeval.py` is 3,100+ lines and `scripts/compound-v-onboard.py` 2,500+:
> grep for the named symbols and read only those ranges. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Jev (TypeSafe System One, through OpenRouter) assists T3 triage, `detect_ui` and the onboarding
layer draft, with the key held by a separate vault plugin and every Jev failure degrading to today's behaviour.

**Architecture:** A new plugin `compound-v-vault` holds the OpenRouter key in sensitive `userConfig`, declares a
`$.jev` noun (`classify(request) -> response`) as its only HTTP client, offers the model one tool
(`jev_classify`) for offline request files, and records egress consent. Compound V gains a key-free Python
layer (`scripts/compound-v-jev.py`: question catalogue, request build, response parse, the T3 policy,
telemetry, eval, bind confirmation), a record `t3` block, and a second hooks module (`hooks/jev-t3.tsx`) that
drives T3 around the existing `UserPromptSubmit` hook when `$.jev` exists. Without the vault nothing changes.

**Tech Stack:** Python 3.9 stdlib (`/usr/bin/python3 -B`), bash + shellcheck, TypeScript hooks modules
(Claude Code mods, ≥ 2.1.287; tests pin 2.1.289 like `tests/test-run-band-mod.sh`), jq, git.

## Global Constraints

- Python 3.9 syntax, stdlib only; no `typesafe_sdk`; no `match`; no `X | Y` annotations.
- Never Haiku. Jev is not a Claude tier and never appears in a manifest `tier`.
- The OpenRouter key exists only in the vault plugin: secure storage, `options`, the `$.http.fetch` header.
  Never in a Python process, an env var, argv, a file, a log line or the transcript.
- The vault never answers a Bash tool call; `lane-guard.sh` and permission prompts stay in force.
- Request text never in argv: files under `$TMPDIR/compound-v/jev/` (mode 0600, dir 0700) or env.
- Model pinned `typesafe/jev-1.13` (config `jev.model`); every telemetry line and report records the
  resolved model id the response returned.
- Every Jev failure is `unavailable|error` with exit 0 and today's path; nothing blocks on Jev.
- No fabricated metrics: `latency_ms` is measured; `usage.cost` is dropped; no cost or savings text
  (anti-ruflo regex in `.github/workflows/validate.yml:194`).
- Every behavioural change ships a selftest/test row that fails when the change is reverted.
- Docs: plain words, every claim true of HEAD, no line over 200 characters outside code/tables.
- Lane discipline: touch only your `write_allowed`; `register-lane` first, with a literal `--cwd`.
- Field, flag and function names are fixed by the Interfaces below; do not rename them.
- Commit subjects are plain sentences, no `feat:`/`fix:` prefixes.
- Not in any implementation job: the version bump, CHANGELOG, release (Task R).

## Partition Map

| Job | Wave | write_allowed | depends_on |
|---|---|---|---|
| `record-t3` (Task A) | 1 | `scripts/compound-v-preeval.py`, `schemas/pre-eval-record.schema.json` | none |
| `config-jev` (Task B) | 1 | `scripts/compound-v-project-config.py`, `commands/v-init.md` | none |
| `jev-core` (Task C) | 1 | `scripts/compound-v-jev.py`, `tests/test-jev-core.sh` | none |
| `vault` (Task D) | 1 | `plugins/compound-v-vault/**`, `tests/test-vault-mod.sh` | none |
| `onboard-ui` (Task E) | 1 | `scripts/compound-v-onboard.py`, `skills/compound-v/onboarding.md`, `commands/v-onboard.md` | none |
| `t3-wiring` (Task F) | 2 | `hooks/triage-prompt-nudge.sh`, `hooks/jev-t3.tsx`, `hooks/jev-t3.test.tsx`, `hooks/hooks.json`, `tests/test-native-points.sh`, `tests/test-jev-t3-mod.sh` | record-t3, config-jev, jev-core, vault |
| `bind-docs` (Task G) | 2 | `commands/v-orchestrate.md`, `commands/v-triage.md`, `skills/compound-v/phase-preeval.md` | jev-core, record-t3 |
| `review` (Task H) | 3 | `.claude/agent-memory/superpowers-v-spec-reviewer/**` | all |
| release (Task R) | after review, by the maintainer session | `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `CHANGELOG.md`, `README.md`, `AGENTS.md`, `TROUBLESHOOTING.md` | review |

Shared resources: `preeval.py` and the schema (record shape) live only in `record-t3`; the config loader only
in `config-jev`; `hooks.json` only in `t3-wiring`; `marketplace.json` only in release (the vault job does not
register itself; Task R adds the marketplace entry). Wave 1 jobs consume each other only through the
Interfaces below, never by reading unmerged code.

---

### Task A: Record `t3` block, request file, successor records (`record-t3`)

**Files:**
- Modify: `scripts/compound-v-preeval.py` — `_verdict` (:794-842), `build_record` (:957-1021), `run_preeval`
  (:1200-1386), `triage_request` (:1519-1620), `_triage_cli` (:1623-1665), `_selftest` (:1916; T3 rows near
  :2151-2295, E2E near :2683-2693).
- Modify: `schemas/pre-eval-record.schema.json` — `properties` (:87-218).
- Test: `python3 scripts/compound-v-preeval.py --selftest`.

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `triage` CLI flags: `--request-file PATH` (third member of the required `--request | --request-env`
    group; the file is read as UTF-8 and stripped of one trailing newline), `--t3-engine {jev,claude,codex,parent}`,
    `--t3-probs-json JSON` (object label->float), `--t3-model STR`, `--t3-catalogue-hash STR`, `--t3-provisional`
    (flag), `--supersedes PRE_EVAL_ID`.
  - `run_preeval(..., t3_meta=None, supersedes=None)` and `triage_request(..., t3_meta=None, supersedes=None)`
    keyword parameters; `t3_meta` is `{"engine": str, "probs": dict|None, "model": str|None,
    "catalogue_hash": str|None, "provisional": bool}`.
  - Record keys: `t3` (object, present only when `t3_meta` was given and T3 was consulted) and `supersedes`
    (string, present only on a successor). A successor's `pre_eval_id` is `<predecessor>-c<N>` (N = 1, 2, …,
    first free).
  - `triage` JSON output gains `t3` (echo of the recorded block or null) and `supersedes` (or null).

- [ ] **Step 1: Selftest rows first (they must FAIL now).** Next to the T3 rows:
  (a) `run_preeval` with `t3_category="plumbing"` on the demotion fixture and
  `t3_meta={"engine":"jev","probs":{"plumbing":0.97,"unknown":0.01,"user-facing-major":0.01,"user-facing-minor":0.01},
  "model":"jev-1.13.0","catalogue_hash":"abc","provisional":True}` → the record has
  `t3 == {"engine":"jev","probs":{...},"model":"jev-1.13.0","catalogue_hash":"abc","provisional":True}` and the
  record validates (`_schema_check`) — planted failure: drop `t3` from `build_record`;
  (b) the same record's `digest` changes when `t3.provisional` flips — planted failure: set `rec["t3"]` after the digest;
  (c) `t3_meta` given but T3 never consulted (a T1-banded non-demotion fixture) → no `t3` key;
  (d) `t3_meta=None` → record bytes identical to today for every existing T3 fixture (compare against a
  record built without the parameter);
  (e) `supersedes="P"` with the same request → new id `P-c1`, record has `supersedes: "P"`, the predecessor file is
  untouched; a second successor → `P-c2`;
  (f) `_triage_cli` with `--request-file` reads the request; `--request-file` with an empty file → REFUSED exit 2;
  (g) schema: `t3.engine` outside the enum fails validation; `t3.probs` value outside [0,1] fails.
- [ ] **Step 2: Run** `/usr/bin/python3 -B scripts/compound-v-preeval.py --selftest` → only the new rows fail.
- [ ] **Step 3: Schema.** Add to `properties`:
  ```json
  "t3": {
    "type": "object", "additionalProperties": false, "required": ["engine", "provisional"],
    "properties": {
      "engine": {"type": "string", "enum": ["jev", "claude", "codex", "parent"]},
      "probs": {"type": "object", "additionalProperties": {"type": "number", "minimum": 0, "maximum": 1}},
      "model": {"type": "string", "maxLength": 80},
      "catalogue_hash": {"type": "string", "maxLength": 80},
      "provisional": {"type": "boolean"}
    }
  },
  "supersedes": {"type": "string", "maxLength": 120}
  ```
- [ ] **Step 4: Plumbing.** `score()` is unchanged. In `run_preeval`, after `score(...)` returns a verdict with
  `"T3" in tiers_signalled` and `t3_meta` is not None, set `verdict["t3"] = _clean_t3_meta(t3_meta)` (drops
  `None` fields; `provisional` defaults False). In `build_record` extend the optional-key loop at :1005-1007 to
  `("flavor", "t3_demotion", "t3_reason", "t3", "supersedes")` so both land before the digest at :1020. For
  `supersedes`, `run_preeval` computes the successor id before `write_record` (loop `-c1`, `-c2`, … until
  `write_record` does not report `already_existed`; cap 20, then raise `RuntimeError`), and skips
  `find_pre_eval_id_by_request` for successors.
- [ ] **Step 5: CLI.** Add the flags in `_triage_cli`; parse `--t3-probs-json` with `json.loads`, reject a
  non-object or non-numeric value with exit 2 and `REFUSED: --t3-probs-json`. Build `t3_meta` only when
  `--t3-engine` is given. Echo `t3` and `supersedes` in the output dict (:1609-1620 and the needs_t3 case).
- [ ] **Step 6: Run the selftest** → green; run `bash tests/test-native-points.sh` and
  `python3 tests/v2.9-e2e/test_fastpath_and_escalation.py` (existing callers unchanged).
- [ ] **Step 7: Commit** `Record the T3 engine, probabilities and provisional flag; successor records`.

---

### Task B: `jev` config resolver and `/v:init` seed (`config-jev`)

**Files:**
- Modify: `scripts/compound-v-project-config.py` — beside `resolve_pre_eval` (:138-199), `load_project_config`
  (:100-118), `main` (:215-232), `_selftest` (:238-356).
- Modify: `commands/v-init.md` — Step 4a seed (:549-592) and per-key bullets (:603-710).

**Interfaces:**
- Produces: `JEV_DEFAULTS`; `resolve_jev(cfg) -> (values, warnings)` never raises, values shape:
  `{"enabled": bool, "model": str, "confidence_min": float, "t3": {"mode": "off"|"shadow"|"active",
  "theta_demote": float}, "detect_ui": {"mode": "off"|"active"}, "onboard": {"mode": "off"|"active"}}`;
  CLI output gains `"jev"`.

- [ ] **Step 1: Selftest rows first.** Defaults when absent: `enabled True, model "typesafe/jev-1.13",
  confidence_min 0.8, t3.mode "shadow", t3.theta_demote 0.95, detect_ui.mode "active", onboard.mode "active"`;
  `t3.mode: "turbo"` → `"shadow"` + warning; `confidence_min: 0` or `1.5` or `true` → 0.8 + warning;
  `theta_demote` below `confidence_min` → raised to `confidence_min` + warning; `model: ""` → default;
  `jev: []` → `load_project_config` raises `ValueError` (planted failure: remove the type check).
- [ ] **Step 2: Run** `python3 scripts/compound-v-project-config.py --selftest` → new rows fail.
- [ ] **Step 3: Implement** `JEV_DEFAULTS` and `resolve_jev` in the same never-raise style as `resolve_pre_eval`
  (floats accept int or float, not bool, in (0, 1]); add the `jev` object check to `load_project_config`;
  print `"jev"` in `main`.
- [ ] **Step 4: `/v:init`.** Add the `jev` block to the Step 4a JSON seed with the defaults above and one bullet:
  committed team policy only; no key and no egress consent ever go here (they live in the vault plugin);
  `t3.mode: active` is a human decision taken on an eval report (link the spec's C6).
- [ ] **Step 5: Run** the selftest → green. **Commit** `Add the jev config block and its resolver`.

---

### Task C: `scripts/compound-v-jev.py` (`jev-core`)

**Files:**
- Create: `scripts/compound-v-jev.py`, `tests/test-jev-core.sh`.

**Interfaces:**
- Consumes (at runtime, via subprocess, never by import of unmerged code): `compound-v-preeval.py triage`
  flags from Task A; `compound-v-classify-request.py --classify-headless --prompt-file` (exists today).
- Produces (CLI, all print one JSON object, exit 0 unless usage error = 2):
  - `build --point {t3,detect_ui,onboard_layer} --state-file F --repo R [--out F]` → writes the request file
    (default `$TMPDIR/compound-v/jev/<uuid>.req.json`) and prints `{"status":"ok","request_file":...}` or
    `{"status":"error","reason":"bad_input"|"redaction"}`.
  - `parse --response-file F --repo R [--mode M]` → `{status, reason?, point, answers, latency_ms, model,
    catalogue_hash}`; appends one telemetry line.
  - `t3-decide --response-file F --t3-reason {unbanded,demotion,sensitive} --repo R` →
    `{"use": "jev"|"claude", "category": str|null, "provisional": bool, "probs": {...}, "model": str,
    "catalogue_hash": str}` (rules below).
  - `confirm --record F --repo R` → runs the Claude classifier on the stored request and prints
    `{"agree": bool, "claude_category": str|null, "action": "clear"|"successor"|"successor_fail_closed"}`.
  - `eval --t3 --pairs F --repo R` (two phases, see Step 7).
  - `--selftest`.
- Request file shape (consumed by the vault, Task D):
  `{"point", "catalogue_hash", "model", "body": {"model", "state", "questions"}, "timeout_ms", "context":
  "hook"|"offline", "repo"}`. Response file shape (written by the vault):
  `{"status": "ok"|"unavailable"|"error", "reason"?, "http_status"?, "latency_ms", "body"?}`.

- [ ] **Step 1: Tests first** in `--selftest` and `tests/test-jev-core.sh` (offline; a fake response file stands
  in for the vault):
  - catalogue: T3 options in order `unknown, user-facing-major, user-facing-minor, plumbing`; descriptions are
    the `_CATEGORY_DEFS` text loaded from `compound-v-classify-request.py` by path (one source); the hash is
    stable across runs and changes when any description changes (planted failure: sort the options);
  - `build` keeps insertion order in the written JSON (no `sort_keys`), writes mode 0600 in a 0700 dir, runs
    every string in `state` through `compound-v-epic-arbiter.py` `redact_uncapped` (loaded by path) and returns
    `error(redaction)` when it returns `None`; over 32,000 estimated tokens (0.25/char) → `error(bad_input)`;
  - `parse`: Choice answer `{"choice","confidence","probabilities"}` and Noul `{"noul": p}` normalise to
    `{type, answer, probs}` (Noul probs `{"yes": p}`, answer `yes` when p ≥ 0.5); unknown keys ignored;
    `http_status` 401/403 → `unavailable(auth)`, 402 → `credits`, 429 → `rate_limited`, 5xx/524/529 →
    `upstream`, 400/422 → `error(bad_input)`, a body without `answers` → `error(schema)`;
  - telemetry line has exactly `{ts, point, status, reason?, answer?, probs?, latency_ms, model, catalogue_hash,
    mode}`, is written only when `<repo>/docs/superpowers/memory/` already exists, and never contains the
    state text (planted failure: log `state`);
  - `t3-decide` rule table (Step 5), one row per rule;
  - no output, file or log written by the script contains a string matching `sk-or-` or `Bearer `.
- [ ] **Step 2: Run** `python3 scripts/compound-v-jev.py --selftest` → fails (file missing).
- [ ] **Step 3: Skeleton** (Python 3.9, stdlib):
  ```python
  #!/usr/bin/env python3
  """compound-v-jev: key-free Jev request/response layer for Compound V.

  Builds System One requests, parses the vault's responses, applies the T3 policy,
  writes metadata-only telemetry, confirms provisional T3 demotions and runs the
  prospective eval. It never performs network I/O and never sees the API key:
  the compound-v-vault plugin is the only HTTP client. Python 3.9-safe, stdlib only.
  """
  import argparse, hashlib, importlib.util, json, os, sys, tempfile, time, uuid

  HERE = os.path.dirname(os.path.abspath(__file__))
  MODEL_DEFAULT = "typesafe/jev-1.13"
  TOKEN_BUDGET = 32000
  TOKENS_PER_CHAR = 0.25
  T3_ORDER = ("unknown", "user-facing-major", "user-facing-minor", "plumbing")
  STRICTNESS = {"unknown": 3, "user-facing-major": 2, "user-facing-minor": 1, "plumbing": 0}
  LAYERS = ("unknown", "ui", "api", "domain", "data", "infra", "tooling", "tests", "docs")

  def _load(name, filename):
      spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, filename))
      mod = importlib.util.module_from_spec(spec)
      spec.loader.exec_module(mod)
      return mod

  def jev_dir():
      d = os.path.join(tempfile.gettempdir(), "compound-v", "jev")
      os.makedirs(d, mode=0o700, exist_ok=True)
      return d
  ```
  Then `catalogue()` returning `{point: {"instructions": str, "options": [(name, description), …] | None,
  "type": "choice"|"noul"}}` (T3 descriptions from `_CATEGORY_DEFS`; the `detect_ui` Noul instruction "Does this
  file render user-facing markup or UI (HTML, templates, components, views)?"; the layer descriptions written
  out in full, one sentence each), and `catalogue_hash(point)` = sha256 of the canonical JSON of that entry,
  first 16 hex chars.
- [ ] **Step 4: `build` / `parse` / telemetry** per the Interfaces and Step 1 rows. Questions:
  `{"t3": {"type": "choice", "instructions": ..., "criteria": {name: description, …}}}` (dict built in
  `T3_ORDER`); `detect_ui` sends one Noul per sampled file named `f0`…`f11` with the state
  `{"files": [{"path", "head"}, …]}` and instructions pointing at `files[i]`; `onboard_layer` one Choice named
  `layer`. Telemetry path: `os.path.join(repo, "docs", "superpowers", "memory", "jev-calls.jsonl")` (never the
  module location; 1A constraint 14).
- [ ] **Step 5: `t3-decide`.** Inputs: parsed T3 answer, `--t3-reason`, `resolve_jev` values (load
  `compound-v-project-config.py` by path; tolerate its absence with `JEV_DEFAULTS`-equivalent literals):
  ```python
  def t3_decide(parsed, reason, cfg):
      if parsed["status"] != "ok":
          return {"use": "claude", "category": None, "provisional": False}
      ans = parsed["answers"]["t3"]
      cat, p = ans["answer"], max(ans["probs"].values() or [0.0])
      if cfg["t3"]["mode"] != "active" or cat == "unknown":
          return {"use": "claude", "category": None, "provisional": False}
      demotes = reason in ("demotion", "sensitive") and cat in ("plumbing", "user-facing-minor")
      if not demotes:
          return {"use": "jev", "category": cat, "provisional": False} if p >= cfg["confidence_min"] \
              else {"use": "claude", "category": None, "provisional": False}
      if p >= cfg["t3"]["theta_demote"]:
          return {"use": "jev", "category": cat, "provisional": True}
      return {"use": "claude", "category": None, "provisional": False}
  ```
  `unbanded` answers that create bands are "not demoting" here: the T1 outcome without T3 is FULL (override #6),
  and the bound is the T3_TABLE row; record this reasoning in a comment. Add `probs`, `model`,
  `catalogue_hash` to the output.
- [ ] **Step 6: `confirm`.** Reads the record; returns `{"agree": true, "action": "clear"}` unless
  `record["t3"]["provisional"]`. Finds the stored request at `jev_dir()/<pre_eval_id>.t3.req.json` (written by
  Task F); missing → `{"agree": false, "action": "successor_fail_closed", "claude_category": null}`. Otherwise
  writes the stored `state.request`-derived prompt (`classify-request.py` `build_prompt` loaded by path) to a 0600
  temp file, runs `classify-request.py --classify-headless --prompt-file F --cwd R --timeout 15`, and compares
  `category` with `record["t3_demotion"]["category"]`. Agree → `clear`; differ, `none` backend or timeout →
  `successor` with `claude_category` (or `successor_fail_closed`). It does not write records: Task G's prose
  runs the successor `triage` call with `--supersedes`.
- [ ] **Step 7: `eval --t3`.** Phase one (`--pairs F --prepare`) writes one request file per pair (pairs come
  from `jev_dir()/shadow-pairs.jsonl`, lines `{request_file, claude_category, actual?}` written by Task F) plus a
  reversed-order and two alternate-wording variants per pair, and prints the list for `jev_classify`. Phase two
  (`--pairs F --report OUT`) parses the responses and writes the markdown report: n; agreement with the Claude
  category and with `actual` where present, each with a 95% Wilson interval; strictness inversions (Jev less
  strict than Claude) with `3/n` as the upper bound when zero; order-flip rate; wording-perturbation flip rate;
  latency p50/p95; the resolved model id(s) (a mixed set is reported as such and marks the report unusable for
  `active`). No cost text.
- [ ] **Step 8: Run** `python3 scripts/compound-v-jev.py --selftest` and `bash tests/test-jev-core.sh` → green;
  `shellcheck tests/test-jev-core.sh`.
- [ ] **Step 9: Commit** `Add the key-free Jev request, response and policy layer`.

---

### Task D: Plugin `compound-v-vault` (`vault`)

**Files:**
- Create: `plugins/compound-v-vault/.claude-plugin/plugin.json`, `plugins/compound-v-vault/hooks/hooks.json`,
  `plugins/compound-v-vault/hooks/vault.tsx`, `plugins/compound-v-vault/hooks/vault.test.tsx`,
  `plugins/compound-v-vault/types/index.d.ts`, `plugins/compound-v-vault/README.md`, `tests/test-vault-mod.sh`.

**Interfaces:**
- Consumes: the request/response file shapes from Task C.
- Produces:
  - Noun `$.jev` declared in `types/index.d.ts`:
    ```ts
    export type JevRequest = { point: string; catalogue_hash: string; model: string;
      body: { model: string; state: unknown; questions: Record<string, unknown> };
      timeout_ms: number; context: 'hook' | 'offline'; repo: string }
    export type JevResponse = { status: 'ok' | 'unavailable' | 'error'; reason?: string;
      http_status?: number; latency_ms: number; body?: unknown }
    export type Jev = {
      classify: (req: JevRequest) => Promise<JevResponse>
      status: () => Promise<{ on: boolean; reason?: string }>
    }
    declare module 'claude-code' { interface EngineInterface { jev: Jev } }
    ```
  - Model tool `jev_classify` with input `{ request_file: string }` → text result: the response file path, or
    `refused: <reason>`.
  - Command `/compound-v-vault:egress allow|deny|status`.

- [ ] **Step 1: Read the build's API first.** Run `/plugin-types` (or read the plugin-authoring skill's
  `types/claude-code.d.ts`) and confirm these names before writing code: `engine.create` returning a noun;
  `$.http.fetch(url, { method, headers, body })` → `{ status, ok, headers, text }`; `$.store.get/set`;
  `$.tool.register(spec)`; `$.command.register`; `$.ui.status`; `$.ui.toast`; `$.env.get`; `$.fs` read/write;
  `session.append`; how a timeout is raced (`$.clock`). Record each confirmed signature as a comment at the
  top of `vault.tsx`. If `engine.create` cannot add a noun on this build, STOP and report BLOCKED.
- [ ] **Step 2: Tests first** in `vault.test.tsx` (`claude plugin test`, stubbing `http.fetch`, `fs`, `store`):
  - `classify` sends exactly one POST to the configured route with `Authorization: Bearer <key>` and
    `Content-Type: application/json`, body = `req.body`; returns `ok` with `latency_ms` and the parsed body;
  - no key → `unavailable(no_key)` and no fetch; `CV_HEADLESS_CLASSIFY=1` → `unavailable(disabled)`, no fetch;
  - egress: unanswered `ask` → `unavailable(egress)` + one toast per session; `deny` → `unavailable(egress)`;
    `allow` recorded under `$.store` key `egress:<repo>` → fetch proceeds;
  - status mapping: 401/403 → `unavailable(auth)`, 402 → `unavailable(credits)`, 429 → `unavailable(rate_limited)`
    (offline context: exactly one retry only when `retry-after` ≤ 1 s), 5xx/524/529 → `unavailable(upstream)`,
    timeout (hook 1,500 ms / offline 5,000 ms) → `unavailable(timeout)`, 400/422 → `error(bad_input)`, a
    non-JSON body → `error(schema)`;
  - `jev_classify` refuses any path outside `$TMPDIR/compound-v/jev/` (including `..` and symlink tricks the
    stubbed fs exposes) and writes `<name>.resp.json` beside the request;
  - the key string never appears in: any `fs.write` content, any tool result, any `$.ui` text, any appended row
    after `session.append` redaction (planted failure: echo the request headers into the response file).
- [ ] **Step 3: Implement** `plugin.json`:
  ```json
  { "name": "compound-v-vault", "version": "0.1.0",
    "description": "Holds the OpenRouter key for Compound V's Jev classifier and is its only HTTP client",
    "types": "./types/index.d.ts",
    "userConfig": {
      "openrouter_key": { "type": "string", "sensitive": true, "title": "OpenRouter API key (use a dedicated key with a credit limit)" },
      "route": { "type": "string", "default": "https://openrouter.ai/api/v1/systemone", "title": "System One endpoint" }
    } }
  ```
  `hooks/hooks.json`: `{ "modules": ["./vault.tsx"] }` and nothing else (no settings hooks, so no
  `CLAUDE_PLUGIN_OPTION_*` export reaches any Compound V hook). `vault.tsx`: `engine.create` adds `jev`;
  `session.start` registers the tool and the command and sets the status line `Jev: on` or
  `Jev: off (<reason>)`; `session.append` replaces the key value with `[redacted]`. The route stays a
  `userConfig` value so the live probe's finding can change it without a code change.
- [ ] **Step 4: README.** Setup (install, set the key in `/config`, `egress allow`), what leaves the machine
  (request text ≤ 2,000 chars, paths, taxonomy hints, file heads for UI detection) to OpenRouter and TypeSafe, no
  zero-retention claim, the credit-limit recommendation, and the honest boundary: other mods earlier in the chain
  can observe the vault's calls.
- [ ] **Step 5: `tests/test-vault-mod.sh`** modelled on `tests/test-run-band-mod.sh` (same `PIN="2.1.289"` npx
  fallback): `claude plugin validate plugins/compound-v-vault` lists `engine.create`, `session.start`,
  `session.append` and no settings hooks; `claude plugin test plugins/compound-v-vault` reports 0 failures.
- [ ] **Step 6: Run** the test → green; `shellcheck tests/test-vault-mod.sh`.
- [ ] **Step 7: Commit** `Add the compound-v-vault plugin: key holder and only Jev HTTP client`.

---

### Task E: `detect_ui` floor and Jev, onboarding layer draft (`onboard-ui`)

**Files:**
- Modify: `scripts/compound-v-onboard.py` — `UI_SIGNALS`/`UI_EXT`/`detect_ui` (:369-380), `_repo_files`
  (:716-728), `draft_taxonomy` (:906-932), `emit_taxonomy_yaml` (:851-890), `build_parser` (:2431-2468), `main`
  (:2470), selftest detect_ui rows (:1751-1758) and draft rows (:1876-1998).
- Modify: `skills/compound-v/onboarding.md` (:65-77, :144-148, :205-209), `commands/v-onboard.md` (:38-41, :87-88).

**Interfaces:**
- Consumes: Task C CLI (`build --point detect_ui|onboard_layer`, `parse`) and the vault tool `jev_classify`
  through the documented command flow; never imports `compound-v-jev.py` internals.
- Produces: `detect_ui(repo) -> bool` (unchanged contract); `detect_ui_reason(repo) -> (bool, str)`;
  CLI `detect-ui --repo R [--reason]` (`--reason` prints `ui deterministic:<signal>` / `no-ui none`);
  `jev-requests --repo R --point {detect_ui,onboard_layer}` prints `{"request_files": [...]}`;
  `detect-ui --repo R --jev-responses DIR` and `draft-taxonomy … --jev-responses DIR`.

- [ ] **Step 1: Selftest rows first.** Fixtures: WordPress theme root (`style.css` with `Theme Name:`), a
  `theme.json` root, `.blade.php`, `.twig`, `.liquid`, `.erb`, `.hbs`, `.astro`, a `.swift` file with
  `import SwiftUI`, a `.php` file with `<div>` outside `<?php ?>` → each `True` with the right
  `deterministic:<signal>` reason; a docs site with only `.html` → `False` (planted failure: add `.html` to
  `UI_EXT`); an uncommitted (non-git) tree with a `.tsx` → `True` (uses `_repo_files`, fixes the 1A latent bug);
  existing rows at :1751-1758 unchanged. Jev rows with fake response files: a `yes ≥ confidence_min` turns
  `False` into `True` with reason `jev:<path>`; a fake "no" never turns a deterministic `True` into `False`;
  sampling excludes sensitive globs (`.env`, `*.pem`, `*.key`, `.github/**`) and any file `scan_secrets` flags,
  is sorted and capped at 12 files × 20 lines. Draft rows: per-directory `onboard_layer` requests (cap 40, each
  its own state of name + ≤ 30 paths); a layer answer adds a commented evidence line
  `# source: jev layer=<l> p=<p>` above the row in `emit_taxonomy_yaml` output and never touches
  `sensitive_path_list`; the YAML still validates (`_validate_taxonomy_text`).
- [ ] **Step 2: Run** `python3 scripts/compound-v-onboard.py --selftest` → new rows fail.
- [ ] **Step 3: Implement** the floor (bounded reads via `_read_bounded`, listing via `_repo_files`), the
  reason function, the request builders (write each state to a 0600 temp file and call
  `compound-v-jev.py build` by subprocess with an explicit minimal env: `PATH`, `HOME`, `TMPDIR`, `LANG`), and the
  response merge. Layer → band mapping is one table in the script (`ui`/`api` → impact high; `domain`/`data` →
  medium/high; `tooling`/`tests`/`docs` → low/low; `infra` → medium/high; `unknown` → no row) and it can only add
  rows for directories that today get no row; it never lowers an existing row.
- [ ] **Step 4: Docs.** `onboarding.md` DETECT step: run `detect-ui --reason`; when the vault is on and the result
  is `no-ui`, run `jev-requests --point detect_ui`, call `jev_classify` for each file, then
  `detect-ui --jev-responses`. DIAGNOSE step: the same for `onboard_layer`; WRITE keeps the human gate per row.
  `v-onboard.md` non-negotiable 5 names both deterministic and Jev reasons.
- [ ] **Step 5: Run** the selftest → green. **Commit** `Widen deterministic UI detection and add Jev-assisted UI
  and layer drafts`.

---

### Task F: T3 wiring: hook, `hooks/jev-t3.tsx` (`t3-wiring`, wave 2)

**Files:**
- Modify: `hooks/triage-prompt-nudge.sh` — `_classify_headless` (:382-423), T3 re-entry block (:604-639),
  tier/message rendering (:641-700).
- Create: `hooks/jev-t3.tsx`, `hooks/jev-t3.test.tsx`, `tests/test-jev-t3-mod.sh`.
- Modify: `hooks/hooks.json` (`modules`), `tests/test-native-points.sh` (static pins :609-630, T3 cases :519-606).

**Interfaces:**
- Consumes: Task A flags, Task C CLI, Task D `$.jev`.
- Produces:
  - Env flag `CV_JEV_T3=1` set by `jev-t3.tsx` with `$.env.set` at `session.start` when `$.jev` exists and
    `(await $.jev.status()).on`. It is a non-secret capability flag.
  - Hook behaviour when `CV_JEV_T3=1` and `needs_t3`: the hook writes the T3 state (request ≤ 2,000 chars, paths,
    hints) to a 0600 file, runs `compound-v-jev.py build --point t3`, copies the request file to
    `jev_dir()/<pre_eval_id>.t3.req.json`, and writes a pending descriptor
    `jev_dir()/pending-<digest(proj|sid)>.json` = `{pre_eval_id, request_file, t3_reason, request_text_file,
    proj, sid, base_commit}`. Mode `shadow`: the hook then classifies with Claude exactly as today and passes
    `--t3-engine claude|codex` on re-entry. Mode `active`: the hook stops before the Claude classify and emits
    the context line `TIER: pending (T3 via Jev)`.
  - Hook render entry: `triage-prompt-nudge.sh --render-context <triage-json-file>` prints the same
    `additionalContext` text the hook prints for that triage JSON (single source of the message).
- `jev-t3.tsx` on `classic.UserPromptSubmit`: `const res = await next(e)`; read the pending descriptor (none →
  return `res`); `const resp = await $.jev.classify(request)`; write the response file; run
  `compound-v-jev.py parse` then:
  - shadow: append `{request_file, claude_category, ts}` to `jev_dir()/shadow-pairs.jsonl` (the Claude category
    comes from the record the hook just wrote); return `res` unchanged;
  - active: run `t3-decide`; `use: jev` → `preeval.py triage --request-file <request_text_file> --t3-category
    <cat> --t3-engine jev --t3-probs-json … --t3-model … --t3-catalogue-hash … [--t3-provisional]
    --repo --session-id --base-commit`; `use: claude` → `classify-request.py --classify-headless --prompt-file …`
    then the same re-entry with `--t3-engine claude|codex`; render with `--render-context`; return
    `{ ...res, additionalContext: [rendered] }` replacing the pending line.
  - Every `$.process.run` uses an argv array, a 30 s cap, and passes no secrets. Delete the pending descriptor
    and the request-text file when done; keep `<pre_eval_id>.t3.req.json` only when the record is provisional
    (Task C `confirm` needs it).
  - `CV_HEADLESS_CLASSIFY=1` → the module does nothing.

- [ ] **Step 1: Tests first.** `tests/test-native-points.sh`: keep every existing T3 case green with
  `CV_JEV_T3` unset (planted failure: make the hook check `CV_JEV_T3` with the wrong polarity); new cases with
  `CV_JEV_T3=1`: shadow writes the pending descriptor and still calls the fake Claude; active writes the
  descriptor, makes no Claude call and prints `TIER: pending`; `--render-context` reproduces the exact text of
  case 1; static pins keep `_CLASSIFY_TIMEOUT_S=15`, timeout 25, no matcher, `|| true`. `jev-t3.test.tsx`
  (`claude plugin test`, stubbing `jev`, `process.run`, `fs`): no `$.jev` → passthrough; shadow → pair appended,
  result unchanged; active + fake `t3-decide` `use: jev` → the re-entry argv contains `--t3-engine jev` and no
  request text; `use: claude` → the classify-headless argv precedes the re-entry; Jev `unavailable` in active →
  Claude path; `CV_HEADLESS_CLASSIFY=1` → nothing. `tests/test-jev-t3-mod.sh`: `claude plugin validate .` lists
  both modules and `claude plugin test .` reports 0 failures (pin 2.1.289).
- [ ] **Step 2: Run** them → new rows fail.
- [ ] **Step 3: Implement** the hook branch (bash; reuse `_store_dir` digest; files via `mktemp` with `umask 077`;
  `jq` already required) and `--render-context` by factoring the existing message block (:641-700) into one
  function both paths call. Add `"./jev-t3.tsx"` to `hooks.json` `modules` after `"./run-band.tsx"`.
- [ ] **Step 4: Implement** `jev-t3.tsx` per the Interfaces; resolve script paths from `$.plugin.root`.
- [ ] **Step 5: Run** all tests → green; `shellcheck hooks/*.sh tests/test-jev-t3-mod.sh`;
  `bash tests/test-hook-recursion-guard.sh`; `bash tests/test-run-band-mod.sh`.
- [ ] **Step 6: Commit** `Drive T3 through Jev when the vault is present, shadow by default`.

---

### Task G: Bind-time confirmation and T3 docs (`bind-docs`, wave 2)

**Files:**
- Modify: `commands/v-orchestrate.md` (Step 0a :27-63, before the manifest freezes at Step 5 :86),
  `commands/v-triage.md` (T2 :114-188), `skills/compound-v/phase-preeval.md` (T3 contract :91-115).

**Interfaces:**
- Consumes: Task C `confirm`, Task A `--supersedes`.

- [ ] **Step 1:** In `v-orchestrate.md` Step 0a add sub-step **0a-iii, provisional T3**: when the record has
  `t3.provisional: true`, run `python3 "$CV/scripts/compound-v-jev.py" confirm --record <record> --repo .`.
  `clear` → continue (the record stays as written; the confirmation is logged in the run's `state.json` notes).
  `successor` → run `triage --request-file <stored request> --t3-category <claude_category> --t3-engine claude
  --supersedes <pre_eval_id>` and use the successor record from here on. `successor_fail_closed` → the same with
  `--t3-category unknown`. Commit the successor with the run substrate. A provisional record is never bound
  without this step.
- [ ] **Step 2:** `v-triage.md` T2: when the vault is on, the agent path mirrors the hook: build the request, call
  `jev_classify`, `parse`, `t3-decide`, and pass the `--t3-*` flags on re-entry; otherwise today's text.
  `phase-preeval.md`: name Jev as a T3 engine, the asymmetric rule, and the bind confirmation.
- [ ] **Step 3:** Run the dead-link scan locally
  (`grep -o '\]([^)#]*' commands/v-orchestrate.md commands/v-triage.md skills/compound-v/phase-preeval.md`
  and check each path exists). **Commit** `Confirm provisional Jev demotions at bind; document the Jev T3 route`.

---

### Task H: Review Gate (`review`, wave 3)

- [ ] `spec-reviewer` (Opus) runs the three passes against the spec's Acceptance Criteria 1-6 and the Global
  Constraints, with explicit checks: grep the whole diff for `sk-or-`, `Bearer`, `openrouter_key` outside
  `plugins/compound-v-vault/`; confirm no Python file performs network I/O (`urllib`, `http.client`, `socket`)
  in `compound-v-jev.py`; confirm `CV_JEV_T3` unset reproduces today's hook output byte for byte on the
  existing T3 fixtures; confirm every `$.process.run` argv carries no request text.

---

### Task R: Release (maintainer session, after review)

- [ ] Add the `compound-v-vault` entry to `.claude-plugin/marketplace.json` (`source: "./plugins/compound-v-vault"`,
  version `0.1.0`); bump `superpowers-v` to `3.9.0` in `plugin.json` and `marketplace.json`; CHANGELOG `3.9.0`
  entry; README/AGENTS/TROUBLESHOOTING sections (setup, egress, status line reasons, Claude Code ≥ 2.1.287 for
  the vault, how to read `jev-calls.jsonl`, how to run `eval --t3`). Run the full CI locally. Commit
  `v3.9.0 Jev classifier foundation and the compound-v-vault plugin`.

## Live probe dependency

The route (`/api/v1/systemone`) and the response shape are doc-derived until the maintainer runs
`/Users/koristuvac/compound/jev-probe.py` (outside the repo, key read without echo, result in
`jev-probe-result.json`). The route is a vault `userConfig` default and the parser tolerates unknown keys, so a
different finding changes one default and possibly the `parse` field names in Task C; dispatch waits for the
probe result only if it shows a different answer shape.

## Self-review

- Spec coverage: C1 → C; C2 → D; C3 → A, C, F, G; C4 → E; C5 → E; C6 → C (eval), F (pairs); C7 → B; Security →
  D, F, H; Error handling → C, D; Testing → every task; AC1 → F step 1, E step 1; AC2/AC3 → F, A; AC4 → D, H; AC5
  → C step 7; AC6 → E step 1.
- Deviation from the spec, stated: shadow-mode Jev answers live in the local `shadow-pairs.jsonl`, not in the record
  (the record is written by the hook before the vault's answer arrives and records are write-once); the record's
  `t3` block names the deciding engine only. The `Jev:` indicator is the vault's status line, not the
  `session-banner.sh` line (1A constraint 19).
- Names checked across tasks: `t3_meta`, `--t3-engine`, `--t3-probs-json`, `--t3-model`, `--t3-catalogue-hash`,
  `--t3-provisional`, `--supersedes`, `--request-file`, `resolve_jev`, `jev_dir()`, `CV_JEV_T3`,
  `pending-<digest>.json`, `<pre_eval_id>.t3.req.json`, `shadow-pairs.jsonl`, `$.jev.classify`, `jev_classify`.
