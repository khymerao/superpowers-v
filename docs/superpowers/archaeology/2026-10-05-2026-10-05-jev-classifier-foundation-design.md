# Jev classifier foundation Code Archaeology

Spec: `docs/superpowers/specs/2026-10-05-jev-classifier-foundation-design.md` (spec 1 of 2).
Recon (read, not repeated): `docs/superpowers/recon/2026-10-05-jev-system-one-classifier-via-openrouter.md`.
Checkout audited: plugin version 3.5.1 (`.claude-plugin/plugin.json:4`, `CHANGELOG.md:9`). The pipeline that launched this audit
runs from the installed 3.7.5 cache, so 3.6/3.7 deltas are NOT visible in this tree and are unknown here.

V-memory: the launch block returned the recon, the v2.9 pre-eval spec/plan and the v3.4.1 triage archaeology. All were re-verified
against the code below. Two extra searches (mod/hook composition; `detect_ui`/taxonomy) returned only this spec, `onboarding.md`
and the v2.9 plan. V-memory returned nothing about any "mod", `userConfig` or TypeScript in this repo, because there is none (finding 1).

Bash was clamped for this run (memory search + git only). Everything below was read with Read/Grep/Glob. No live call, no `git blame`.

## 1. Matrix

### 1a. T3 consultation: reason x answer x what Jev's answer does to the tier (`scripts/compound-v-preeval.py`)

| `t3_reason` (call site) | Gate (preeval.py) | Jev/Claude answer `plumbing`/`user-facing-minor` | `user-facing-major` | `unknown` | Direction of effect |
|---|---|---|---|---|---|
| `unbanded` (T1 cannot band the path) | 658-675 | bands (low,low)/(med,med) via `T3_TABLE` (232-237) | (high,high) -> FULL | (unknown) -> override #6 FULL | both directions: the answer CREATES the bands |
| `demotion` (broad glob, matrix would force FULL, fan_out<=2) | 696-724 | demotes to SCOPED (difficulty floored at medium, impact capped at medium) | recorded `applied:false` | recorded `applied:false` | can LOWER FULL -> SCOPED |
| `sensitive` (small exact edit on a sensitive path, fan_out<=2, not NEVER_DEMOTE) | 553-594 | FULL (override #2) becomes SCOPED + `scoped_plus` | stays override #2 FULL | stays override #2 FULL | can LOWER FULL -> SCOPED+ on a sensitive path |
| banded by T1, category supplied | 726-736 | override #4 FULL if T1 vs T3 differ by >=2 ranks, else impact may only rise | same | none | can RAISE to FULL |

`NEVER_DEMOTE_GLOBS` = `**/*.pem`, `**/*.key`, `**/*.env`, `.github/**` only (258). `auth`, `payments`, `migrations`, `*.sql`, `*.tf`
are sensitive but demotable. `DEMOTION_MAX_FAN_OUT = 2` (263).

### 1b. Who runs T3 (the engine never does)

| Caller | Mechanism | File | Gets the key via mod? |
|---|---|---|---|
| `UserPromptSubmit` hook | `--classify-headless` (nested `claude -p`, else `codex exec`), then re-enter `triage --t3-category` | `hooks/triage-prompt-nudge.sh:378-419, 600-635` | only if the mod runs the hook (spec C2) |
| `/v:triage` (agent) | `--classify-headless` or a parent light Task + `--parse` | `commands/v-triage.md:122-161` | only if the allowlist matches the agent's command text |
| `/v:orchestrate` / phase-preeval | parent Task contract | `skills/compound-v/phase-preeval.md:91-115` | no Bash for a Task reply |
| selftests / e2e | `--t3-category` literal | `tests/v2.9-e2e/test_fastpath_and_escalation.py:198` | n/a |

### 1c. Jev availability x consumer x context

| State | T3 hook | T3 `/v:triage` | `detect_ui` | onboard classification |
|---|---|---|---|---|
| no mod / no function hooks / non-Claude backend | key absent -> `no_key` | same | deterministic only | deterministic only |
| mod loaded, key set, `egress: ask` unanswered | `unavailable(egress)` (a hook cannot prompt, finding 9) | same | same | same |
| mod loaded, allowlist miss (command text not exact) | no key | no key | no key | no key |
| nested `claude -p` (headless classify) | must stay inert (`CV_HEADLESS_CLASSIFY`, finding 7) | n/a | n/a | n/a |
| hook running inside an active run | silent already (`_has_active_run`, hook:552) | n/a | n/a | n/a |

### 1d. `detect_ui` inputs today (`scripts/compound-v-onboard.py:325-336`)

| Signal | Source | Needs git? |
|---|---|---|
| `tailwind.config.js/ts`, `postcss.config.js` at repo root | `os.path.exists` | no |
| tracked `*.tsx *.jsx *.vue *.svelte` | `_git_tracked` (`git ls-files -z`, returns `[]` on any failure, 24-29) | yes |

Spec C4 adds `.blade.php .twig .liquid .html .erb .hbs .astro`, SwiftUI import sniffing, WP theme root, PHP-with-markup. Every added
signal except the root-file ones needs file listing and file reads.

## 2. Shared State

**Plugin root / script path.** Set in hooks as `CLAUDE_PLUGIN_ROOT` (`hooks/triage-prompt-nudge.sh:250`, `hooks.json` commands). NOT set in the
agent Bash environment (this agent's own definition says so; the documented command forms never use it). `commands/v-triage.md:107,139`,
`skills/compound-v/onboarding.md:44-56` and `commands/v-onboard.md:17` all say `python3 scripts/compound-v-*.py` relative to cwd.
In a downstream project cwd has no `scripts/compound-v-*.py`. Gap: the spec's "resolved under the plugin root" allowlist has no input for
the plugin root in `tool.call`, and the canonical command text is a relative path with an env prefix
(`V_TRIAGE_REQUEST='...' python3 scripts/compound-v-preeval.py triage ... \` at `commands/v-triage.md:107`). Whether the mod API exposes
the plugin root is a 1C question: UNKNOWN here.

**`CV_JEV_KEY` (new).** Deleted from `os.environ` only inside `compound-v-jev.py` (spec C1). The three other allowlisted scripts hold it for
their whole life:

| Script | Child processes it starts with inherited env | Evidence |
|---|---|---|
| `compound-v-classify-request.py` | nested `claude -p`, `codex exec`, via `env=_headless_env()` = `dict(os.environ)` + marker | `classify-request.py:84-92, 386-390, 544-548` |
| `compound-v-onboard.py` | `npx --yes @google/design.md lint` (network fetch and execute), `git` | `onboard.py:345, 25, 389` (no `env=` passed, so inherited) |
| `compound-v-preeval.py` | none in the engine body; imports siblings (`localize`, `triage`, `churn`) whose subprocess use was not audited | `preeval.py` has `subprocess.run` only in the selftest (2835). UNKNOWN for siblings |

`tests/test-hook-recursion-guard.sh:24` greps for the literal `env=_headless_env()`, so that line is pinned.

**Hook once-per-session marker.** `${TMPDIR}/compound-v-triage-nudge/nudged-<sha256(proj|sid)>`, written BEFORE the engine runs
(`triage-prompt-nudge.sh:557-562`). Set by the first hook process that reaches it; every later one returns silent (542).

**`request` text.** Not persisted anywhere after scoring. Record has `request_slug` (<=60 chars, `slugify`, `preeval.py:350-359`) and the intent
file has only the sha256 fingerprint (`write_intent_record`, 892-911). The localization artifact has paths/flags only (read one: no request).

**Telemetry path.** `triage_request` pins the outcome stream to the TARGET repo because `default_stream_path()` derives from the module
location, which in an installed plugin is the plugin cache (`preeval.py:1556-1566`). Same trap applies to `jev-calls.jsonl`.

**Config.** `compound-v-project-config.py:100-118` validates only `models`, `pre_eval`, `brainstorm` as objects. `resolve_pre_eval` coerces every bad value to a
safe default and never raises (138-148). There is no `jev` reader, validator or defaults table. `.claude/compound-v.json` is declared
"Committed team POLICY only - never machine-local capability" (`commands/v-init.md:439`; `v-init.md:680-682` calls machine-local data in it
a fixed mistake). The machine-local file is `~/.claude/compound-v-capabilities.json` (`TROUBLESHOOTING.md:216`).

**`detect_ui` result.** `bool`; consumers: `draft_taxonomy` (`onboard.py:869`), CLI `detect-ui` printing `ui|no-ui` (2420-2421),
`onboarding.md:56,259` (gates `DESIGN.md` generation and the `npx` design-lint), selftests asserting `is True` / `is False` (1683, 1686).

## 3. Sibling Code

**3a. `compound-v-classify-request.py` (read in full to line 800).** Template for any external-classifier path.
- Entry: engine returns `needs_t3` (`preeval.py:660-669, 698-707, 572-583`); caller supplies one enum.
- Contract: strict enum parse, anything else -> `unknown` -> FULL (`parse_category`, 225-269). Bounds: 2000 request chars, 20 paths, 40
  hints, 8000 prompt (103-109). Categories have prose definitions (`_CATEGORY_DEFS`, 133-148) that Jev's `--instructions` must reuse.
- Two enum copies already exist: `CATEGORIES` (`classify-request.py:100`) and `T3_TABLE`/`T3_CATEGORIES` (`preeval.py:232-238`); the spec adds a
  third ordering ("unknown first").
- Latent: `classify_headless` returns the first backend's answer whenever `exit_code == 0` (627-630), so a Jev route inserted "first"
  must report `backend`-style provenance the hook already reads (`triage-prompt-nudge.sh:392-408`: only `claude|codex` count as reported;
  any other backend string is treated as "nothing classified" and degrades to the reminder). A `jev` backend value is rejected by that case.
- Request text crosses processes via `--request-env`/`--prompt-file`, deliberately not argv (hook:319-321; classify-request.py:698-704).

**3b. `hooks/triage-prompt-nudge.sh` (read in full).** Fail-open contract: `trap 'exit 0'`, `|| true` suffix in `hooks.json:50`, stdout withheld unless
`hook_main` returns 0 (700-705). Registration: single entry, no matcher, `timeout: 25` (`hooks.json:45-56`), pinned by
`tests/test-native-points.sh:622-623, 759-766`. Budget: classify 15 s + 3 s supervisor grace, two engine runs around it (354, 170-186).
Needs `jq` (458). `CV_HEADLESS_CLASSIFY=1` -> exit 0 first thing (194); the same guard is in nine hooks (grep; `tests/test-hook-recursion-guard.sh:12`). Output is `additionalContext` only.
Latent bug (inherited): a session whose first scoring attempt fails is spent for the session (marker before engine, documented 112-124).

**3c. `compound-v-onboard.py` `detect_ui` / `draft_taxonomy` (read 300-336, 585-921).**
- `draft_taxonomy` drafts glob rows from extensions and directory segments that exist, not per top-level directory (`_draft_path_patterns`, 714-739).
  `emit_taxonomy_yaml` writes only `glob`, `difficulty_band`, `impact_band` per row (824-827); the `evidence` field exists in the JSON proposal and is
  dropped from the YAML. A `source: jev` + probability marker (spec C5) would not survive WRITE unless emitted some other way.
- `detect_ui` uses `_git_tracked` only. `draft_taxonomy` falls back to an `os.walk` for an uncommitted tree via `_repo_files` (672-684) but `detect_ui` does not.
  Latent bug: on a not-yet-committed or non-git tree `detect_ui` sees no files, so `ui` is False even with `.tsx` present, and `shared_token`/`a11y` rows are
  offered `False` (`_draft_content_patterns`, 751-765).
- `ui=True` adds four content rows with `impact_band: high` (`--color-`, `theme.tokens`, `aria-label`, `alt=medium`; 643-652). Content rows only raise
  impact, so a false-positive `detect_ui` makes more requests FULL in that repo.
- `scan_secrets`/`SECRET_RE`/`PEM_RE` are imported from `compound-v-memory.py` (`onboard.py:5-18`): the canonical pre-egress filter already exists.
- `_read_bounded(path, cap, allow_symlink=True)` returns `(data, why, code)` (144-171); a second copy lives in `compound-v-postdiff-reclassify.py:301`.

**3d. Pre-eval record writer (`preeval.py:957-1021`, schema `schemas/pre-eval-record.schema.json`).** Write-once (`_write_once_text` O_EXCL), `digest` over the whole
record, schema top level `additionalProperties: false` (schema line 7). T3 evidence today: `tiers_signalled` contains `T3`, `t3_reason`, `t3_demotion{from,category,applied,sensitive}`.
Record is written only after T3 resolved (`run_preeval` returns before writing on `needs_t3`, 1332-1342). There is no `t3` object, no `engine`, no `probs`, no `shadow`.
The record's own `tier` is pinned to `decision` by `allOf` conditionals because `hooks/epic-goal-stop.sh` prefers `tier` (schema 140-145).

**3e. `scripts/lane-guard` / `hooks/lane-guard.sh`.** Matcher `Write|Edit|MultiEdit|NotebookEdit|Bash` (`hooks.json:33`). It inspects Bash command strings
heuristically and is a floor; the git scope gate is the authority (`.claude/rules/hooks.md`, `lane-guard.sh:1122-1152`).

## 4. External APIs (via context7)

NOT performed here: Phase 1C owns library/API currency, and the Context7 server for this session was not exercised in this run. The following are the
unverified items this audit depends on, so they are findings, not TODOs:
- The mod API (`register(on, options)`, `userConfig.sensitive`, `tool.call`, `classic.UserPromptSubmit`, `session.append`, `$.process.run` env semantics, event order vs
  `PreToolUse` hooks) has no in-repo reference at all: no `userConfig` in `plugin.json`, no TypeScript, no `mods/` dir, no mention in `CONVENTIONS.md`/`README.md`/`TROUBLESHOOTING.md`
  (grep). Every mod claim in spec C2 is unverified from this tree.
- OpenRouter System One path/body/BYOK and the pin question (`jev-1.13` vs `~typesafe/jev-latest`) are recon "UNVERIFIED LEADS" and remain so here.
- Whether `CLAUDE_ENV_FILE` reaches hook processes (recon lead) is still unknown; the spec dropped that design in favour of the mod, which does not remove the need to know how the hook gets the key.

## 5. Regression Surface

| Path | If the new code breaks it, what breaks for existing users |
|---|---|
| `hooks/triage-prompt-nudge.sh` (every first prompt of every session) | a crash/hang in the Jev branch loses the session's single triage attempt (marker already written) and, past 25 s, the context line; a parse error rejects the user's prompt (`exit 2` semantics, hook header 126-135) |
| `triage-prompt-nudge.sh` `backend` handling (392-408) | a new `jev` backend string degrades every Jev answer to "no classifier ran" -> reminder text |
| `compound-v-preeval.py` record shape + `digest` | any new top-level key not in the schema makes the record schema-invalid; any key added after `build_record` silently breaks the digest (docstring 969-973) |
| `hooks/epic-goal-stop.sh`, `compound-v-validate-manifest.py --require-triage` | they read records off disk and the `tier`/`decision` pairing; a record they cannot read is not an exemption, so a malformed Jev-era record blocks Stop or `/v:dispatch` |
| `docs/superpowers/memory/triage-outcomes.jsonl` (circuit breaker input) | shadow runs must not append extra `predicted` events; a duplicate pollutes the miscalibration rate |
| `detect_ui` -> `draft_taxonomy`, `onboarding.md` DESIGN.md gate | `.html`/`.php` signals flip many non-UI repos to `ui`, which adds high-impact content rows and triggers `DESIGN.md` + `npx --yes @google/design.md` |
| `tests/test-native-points.sh` T3 checks (614-631), `tests/test-hook-recursion-guard.sh:24` | pin hook text tokens, the 25 s timeout, no matcher, and `env=_headless_env()` |
| CI `validate.yml` script sweep (298-312) | a new `scripts/*.py` is discovered only if it contains the literal `--selftest` and then is run as `python3 <file> --selftest` under 3.9; spec's `selftest` subcommand is not that |
| `hooks/lane-guard.sh` + git scope gate | a mod answering a Bash tool call itself may skip PreToolUse hooks (unknown); the three allowlisted scripts include write-capable subcommands |
| V-memory index | `jev-calls.jsonl` under `docs/superpowers/memory/`, if tracked, is indexed (`compound-v-memory.py:317-350`: tracked `*.md`/`*.jsonl` under `docs/superpowers`) |
| plugin release | `plugin.json`, `marketplace.json`, `CHANGELOG` lockstep (`validate.yml:43-79`); a `userConfig`/mod change needs all three |

## 6. DRY Findings

| Area | Existing | Decision input |
|---|---|---|
| secret filter before egress | `scan_secrets`, `SECRET_RE`, `PEM_RE` (`onboard.py:5-18`, from `compound-v-memory.py`) | reuse; a third pattern list is forbidden by `.claude/rules/scripts.md` |
| bounded file read | `_read_bounded` in `onboard.py:144` and `postdiff-reclassify.py:301` | spec names the onboard one; do not add a third |
| project config load | `compound-v-project-config.py` `load_project_config`/`resolve_pre_eval` | `jev` needs a sibling resolver with the same never-raise coercion, not ad hoc JSON reads in each script |
| T3 enum + category definitions | `CATEGORIES`/`_CATEGORY_DEFS` (classify-request) and `T3_TABLE` (preeval) | one source for the label list; Jev options order is a presentation of it, not a new copy |
| timeout supervision / headless env marker | `compound-v-run-with-timeout.py`, `_headless_env()` | any new subprocess from a script that holds the key must go through one env-scrubbing helper, not a fourth spawn idiom |
| per-repo vs module-relative path | `triage_request` stream pin (`preeval.py:1556-1566`) | reuse the same rule for telemetry |
| duplicate producers of triage | hook and `commands/v-triage.md` share `triage_request` (doc 1393-1415) | Jev wiring must go through the shared subcommand, not a second copy in the hook |

## 7. Design constraints for the spec

Numbered; each is derived from a finding above and is non-negotiable for the plan.

1. **No mod exists to extend.** The vault mod is net-new infrastructure: TypeScript, `userConfig`/`sensitive`, function hooks. The repo has no toolchain, no CI job, no
   `plugin.json` field, and no test for any of it. The plan MUST state where the mod lives in the shipped tree, how it is verified (CI runs only `jq`, shellcheck, Python
   selftests, `tests/**`), and the `plugin.json`/`marketplace.json`/`CHANGELOG` lockstep bump. Every mod-API claim in C2 is unverified until 1C answers it.
2. **Engine stays model-free.** The "preeval triage T3 call site" does not exist: the engine returns `needs_t3` and the callers run the classifier (1b). Jev wiring goes in the
   callers (hook `_classify_headless`, `commands/v-triage.md`, phase-preeval prose) and enters the engine only as `--t3-category` plus new pass-through flags.
3. **State where Jev may move the tier, per `t3_reason`.** The spec's "only in the safe direction" and its Security bound ("SCOPED instead of FULL on a non-sensitive path") are
   false for T3: `sensitive` lets a `plumbing` answer turn override #2 into SCOPED+ on `auth/payments/migrations/*.sql/*.tf` paths (`preeval.py:553-592`), `demotion` lowers FULL to SCOPED,
   `unbanded` creates the bands, and a T1-banded request can be raised to FULL by override #4. The plan MUST say which of these Jev may drive in `active`, and keep
   `NEVER_DEMOTE_GLOBS` (`preeval.py:258`) as a code floor Jev cannot move. "Layer A first" is true only for overrides 1, 3, 5, 7 and the non-scoped-plus branch of #2.
4. **Record shape.** `t3.engine`, `t3.probs`, `t3.shadow` do not exist; the schema is closed at top level; the record is write-once and digest-covered, and is written only at
   re-entry. The plan MUST specify the schema change, how the values reach `build_record` BEFORE the digest (new `run_preeval`/`triage_request` parameters, not post-hoc edits), how they
   coexist with `t3_demotion`/`t3_reason`, and what a shadow run records when T3 was never consulted. A resumed `pre_eval_id` cannot be re-recorded.
5. **Provenance string.** The hook accepts only `backend` in `{claude, codex}` as "classified" (`triage-prompt-nudge.sh:401-404`). The plan MUST define how a Jev answer is reported to the hook
   and how Jev `unavailable`/`error` falls through to the existing route without spending the session's one attempt.
6. **Key containment is wider than `compound-v-jev.py`.** Every allowlisted script that inherits `CV_JEV_KEY` passes it to its children: nested `claude -p`/`codex exec`
   (`classify-request.py:84-92`) and `npx --yes @google/design.md` (`onboard.py:345`). The plan MUST either deliver the key only to the Jev client process or scrub it in every
   child spawn of those scripts, and keep `env=_headless_env()` literal (`tests/test-hook-recursion-guard.sh:24`). A grep/test for the key must cover child environments of these scripts, not only Jev's.
7. **Allowlist matching must fit the real command text.** Canonical commands are relative-path, env-prefixed, multi-line (`commands/v-triage.md:107`) and the plugin root is not in the agent Bash env.
   The plan MUST define the parse (env prefixes, `\` continuations, `python3` vs `$CV` forms, redirections, pipes), where the plugin root comes from, and what happens on a miss (no key, silent). It MUST also
   decide allowlisting per script versus per subcommand: `compound-v-onboard.py` has write subcommands (`staleness --write`, `scan-output`, `pack`, `rules-lint`), and `compound-v-preeval.py triage` writes records.
8. **Do not bypass lane enforcement.** A mod that answers a Bash call itself may skip the `PreToolUse` lane guard (`hooks.json:33`) and the scope gate's view of the command. The plan MUST verify event order
   with 1C and record the answer; if unknown, treat the mod path as unable to run inside a dispatched job.
9. **Hook composition.** One hook registration exists and its marker is written before the engine (`:557-562`). If the plugin hook and the mod-run copy both fire, the key-less one that fires first spends the session
   and Jev is never reached. The plan MUST specify which instance runs, how the other is suppressed, and the order. The mod wrapper MUST honour `CV_HEADLESS_CLASSIFY=1` (finding 131 recurs otherwise:
   nested `claude -p` loads the same extensions). `hooks.json` registration constraints in `tests/test-native-points.sh:622-623, 759-766` (timeout 25, no matcher, `|| true`) stay.
10. **Request text never in argv.** Spec C1 shows `--state <json|@file>`. The hook and engine pass request text via env or file on purpose (`:319-321`; `classify-request.py:698-704`). The plan MUST use stdin/`@file`
    for `state` and questions in every consumer, since a mod-run command line is also part of the tool call.
11. **Egress for C4.** C3 sends no file contents; C4 sends the first 20 lines of up to 12 tracked files. The plan MUST filter with `scan_secrets` and refuse `.env/.pem/.key` and NEVER_DEMOTE-class paths before egress, and
    make file selection deterministic (sorted, bounded, via `_repo_files` not only `_git_tracked`).
12. **Egress consent storage.** `ask` cannot prompt inside a hook and `.claude/compound-v.json` is committed team policy (`v-init.md:439`): committing `egress: allow` consents for every clone, and writing a
    per-user answer into it is the documented mistake. The plan MUST pick the store (machine-local capabilities file vs committed key), define the default while unanswered (spec: `unavailable(egress)`), and say who can answer and how.
13. **Config.** Add a `jev` resolver beside `resolve_pre_eval` with never-raise coercion: unknown `t3.mode` -> `shadow` or off, unknown `egress` -> `deny`/`ask`, `confidence_min` outside (0,1] -> default 0.8,
    timeouts clamped. `load_project_config` currently does not type-check a `jev` block. Seed it through `/v:init` Step 4a (committed policy only; no key, no consent).
14. **Telemetry path and tracking.** The Jev client must take the target repo from cwd/`--repo`, never from its own location (plugin cache). The plan MUST decide tracked vs gitignored for `jev-calls.jsonl`
    (tracked `*.jsonl` under `docs/superpowers` is indexed by V-memory; an untracked file under a lane is a scope-gate input) and honour the hook's "present-only" rule (hook:534-535): no creation of `docs/superpowers/memory/` in a non-Compound-V repo.
15. **`eval --t3` cannot replay what the spec says.** Committed records do not store the request: only a <=60 char slug and a fingerprint. Of 24 committed records, 6 carry `T3` in `tiers_signalled`; the raw T3 category is
    recorded only when `t3_demotion` exists. `actual` events exist only for fast-path parents. The "<=2000 chars request" T3 input is unreproducible and the "30 pairs" gate is unreachable from committed data
    (at most 6 T3-consulted records). The plan MUST define the labelled corpus honestly (new capture in shadow mode, with its own retention and secret rules) or drop the replay claim. Reports under `docs/` are scanned by
    the anti-ruflo grep (`validate.yml:194`): no "tokens saved"/"cost savings" phrasing.
16. **`detect_ui` contract.** Keep `detect_ui(repo) -> bool` for `onboard.py:1683,1686`, `draft_taxonomy` and `onboarding.md`, or change all of them together with the CLI output (`ui|no-ui`). Add the reason as a second function/field.
    Fix the git-only listing (use `_repo_files`). Justify `.html` and PHP-with-markup as UI signals: they flip repos into `shared_token`/`a11y` high-impact rows and the `DESIGN.md`/`npx` path.
17. **Onboarding bands are new policy.** The "layer -> bands" table is a safety mapping that can lower a directory from the evidence-driven bands. The plan MUST keep `sensitive_path_list` and `NEVER_DEMOTE` evidence-driven only
    (Jev never adds or removes), say how `source: jev` survives `emit_taxonomy_yaml` (it emits only glob + two bands, 824-827; `evidence` is JSON-only), and keep the human GATE per-row.
18. **CI discovery.** The Jev client's selftest MUST be a `--selftest` flag (the sweep greps for that literal and calls it, `validate.yml:298-312`) and pass under Python 3.9 stdlib. Mod tests sit outside every current CI job.
19. **Banner.** `session-banner.sh` is bash-only (no `jq`, `:86-129`) and cannot read the mod's secure storage. "Jev: on | off (<reason>)" needs a defined channel from the mod; absent one, the banner cannot be truthful.
20. **Version skew.** This tree is 3.5.1; the runtime is 3.7.5. The plan MUST reconcile against the current tree before editing `hooks.json`, `plugin.json` or the pre-eval schema.

## 8. File Touch Map (for Phase 2 partitioning)

| File | Change | Flag |
|---|---|---|
| `scripts/compound-v-jev.py` (new) | Jev client, telemetry, selftest | |
| `scripts/compound-v-preeval.py` | `triage` flags for engine/probs/shadow, `build_record` pass-through | SHARED RESOURCE (engine imported by hook, e2e tests, 3 callers) |
| `schemas/pre-eval-record.schema.json` | `t3` block, closed top level | SHARED RESOURCE (type/schema read by hook `jq`, validate-manifest, epic-goal-stop) |
| `scripts/compound-v-classify-request.py` | Jev route / provenance, env scrub | SHARED RESOURCE (pinned by `tests/test-hook-recursion-guard.sh`) |
| `hooks/triage-prompt-nudge.sh` | Jev branch in `_classify_headless` / T3 re-entry | pinned by `tests/test-native-points.sh` |
| `hooks/hooks.json` | only if composition needs a registration change | SHARED RESOURCE (registry; order matters; tests pin it) |
| `hooks/session-banner.sh` | `Jev:` line | |
| `scripts/compound-v-onboard.py` | `detect_ui`, `draft_taxonomy`, secret filter, `design_lint` env | SHARED RESOURCE (selftests, CLI used by `onboarding.md`) |
| `scripts/compound-v-project-config.py` | `jev` loader/resolver | SHARED RESOURCE (config loader for every consumer) |
| `commands/v-init.md` | seed `jev` block | |
| `commands/v-triage.md`, `skills/compound-v/phase-preeval.md`, `skills/compound-v/onboarding.md` | Jev route prose, `detect-ui` wording | |
| `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `CHANGELOG.md` | `userConfig`, version lockstep | SHARED RESOURCE (CI lockstep guard) |
| mod source (new; location undecided) | `compound-v-vault` | no CI coverage today |
| `tests/test-native-points.sh`, `tests/test-hook-recursion-guard.sh`, new `tests/test-*.sh` | new cases | |
| `.github/workflows/validate.yml` | only if a mod/TS job is added | SHARED RESOURCE |
| `docs/superpowers/memory/jev-calls.jsonl` | telemetry (tracking undecided) | V-memory indexes tracked `*.jsonl` |
