# Phase T Jev Shadow Code Archaeology

Spec: `docs/superpowers/specs/2026-10-08-phase-t-jev-shadow-design.md`. Checkout: branch `jev-practical`.
Method: Read/Grep only (the agent Bash is clamped to memory search and git read). Context7 is not authenticated in this
session and no third-party API is touched: the only external contract is the in-repo vault tool, read from source (section 4).
V-memory: the prompt's recall block was used; one claim in it is stale (section 3, F-9).

## 1. Matrix

Dimensions the new Phase T step branches by, and which cell each existing path covers.

| Dimension | Values | Hook shadow (today) | Phase T step (spec) |
|---|---|---|---|
| Who answered T3 | headless `claude`, headless `codex`, Task route (`parent`), headless `none`/timed out | claude/codex only; `none`/timeout degrades to reminder, no descriptor (`triage-prompt-nudge.sh:416-423`, `:755`) | claude/codex/parent. `none` is not an answer and falls to the Task route (`v-triage.md:164-168`) |
| Why T3 ran (`t3_reason`) | `unbanded`, `demotion`, `sensitive` | read from the FIRST (`needs_t3`) engine output (`:700`) | same, but see F-3: the re-invocation output does NOT carry it |
| Jev gate | vault absent / no key / egress deny / egress unanswered / allow; config `enabled`, `t3.mode` off or shadow | `CV_JEV_T3=1` only when `jev.status` is `on` (key + route + egress allow) AND config resolves to shadow (`jev-t3.tsx:118-131`) | tool present, then config only (spec change 1). No key or consent check (F-1) |
| Record already exists for the request | none; hook-written (uncommitted); Phase T-written | n/a | T2 is skipped when the hook's record carries this session id (`v-triage.md:40`), so no step. A forced re-run with a different `--t3-engine` is refused by the engine (F-5) |
| Request context | `hook` (1,500 ms) / `offline` (5,000 ms) | `build --point t3` default = `hook` (`compound-v-jev.py:52`) | `t3-request` "does what `build --point t3` does", so also `hook` 1,500 ms, in an attended command (F-7) |
| Jev answer | ok / unavailable(reason) / error(reason) | parse + pair run for every status (`jev-t3.tsx:229-254`) | spec step 4 writes the pair; the "non-ok changes nothing" sentence contradicts it unless pair is scoped (F-6) |
| Tool delivery in the session | registered at `session.start` when `CV_HEADLESS_CLASSIFY` unset (`vault.tsx:353-363`) | n/a (module calls `$.jev.classify`) | MCP tool `mcp__compound-v-vault__jev_classify`, may be deferred (needs ToolSearch) |

Cell tested today: hook + claude + `user-facing-minor` (`test-native-points.sh:546-570`, `:700-757`). No test touches Phase T prose at all.

## 2. Shared State

**`t3_reason`.** Set on the `needs_t3` result (`preeval.py:711/749/624`, printed `:1669`). The result of the re-invocation (`:1673-1686`) prints
`t3` (engine, category) but not `t3_reason`; the record carries `t3_reason` only for `demotion`/`sensitive` (`:755`, `:1051`), never for `unbanded`.
Gap: Phase T prose that reads `t3_reason` from the re-invocation output gets nothing. It must be captured from the first call, as the hook does (`:700`).
Allowed values for `pair --t3-reason` are `^[a-z][a-z0-9_-]{0,39}$` (`compound-v-jev.py:72`); a missing value is an argparse usage error (`required=True`, exit 2).

**`backend`.** Hook value is `claude|codex` (`:716-719`). Phase T adds `parent`. `pair --backend` accepts it (token regex); `--t3-engine` accepts it (`T3_CLI_ENGINES`, `preeval.py:274`).
`jev-t3.tsx` validates descriptor tokens with `SAFE_NAME`, a hook-only consumer. `eval_report` reads `backend` from nowhere (`_pair_items` copies `claude_category` and `t3_reason` only), so `parent` is inert downstream.

**Request text.** Hook: raw `$request` into jq env, capped `[0:2000]` (`:479`). Python equivalent must slice codepoints (jq slices codepoints, Python `str[:n]` too).
`classify-request.py` already owns the three caps (`MAX_REQUEST_CHARS=2000`, `MAX_PATHS=20`, `MAX_TAXONOMY_CATEGORIES=40`, lines 104-107); the hook re-declares 2000 as `_T3_STATE_MAX_CHARS` (`:453`).
Empty or unset `--request-env`: `build_request` only checks `isinstance(request, str)` (`_check_state`, `:377`), so an empty request builds a valid request file. `preeval.py:1751-1753` refuses an empty request; `t3-request` must do the same.

**Data dir.** `data_dir(repo)` hashes `realpath(repo)`. `pair` refuses a request file not under `data_dir(--repo)/req` (`main`, `:971-973`). `t3-request --repo X` and `pair --repo Y` must resolve to the same real path or pair returns `bad_input`. Phase T is "from the repo root" with `--repo .`; a worktree has its own digest (this very session is one).

**Config.** Two readers exist and agree: `jev-t3.tsx:104-110` reads the RESOLVED output of `compound-v-project-config.py` (so absent config means `enabled: true`, `t3.mode: shadow`, `JEV_DEFAULTS` `:87-93`; `active` is coerced to `shadow` with a warning, `:300-302`). `compound-v-jev.py` reads no config today (grep: no `project-config` reference).
Gap: spec says "unless `jev.enabled` is true and `jev.t3.mode` resolves to `shadow`". A raw read of the JSON file would turn "absent config" into off; only `resolve_jev(load_project_config(repo))` matches the module. `load_project_config` RAISES on a malformed file or non-object `jev` (`:122-143`); `resolve_jev` never raises but returns warnings. `t3-request` must catch the raise (-> off or error, never a traceback) and keep warnings off stdout (one-JSON-object contract, docstring `:9`).

## 3. Sibling Code

Sibling A: `_write_t3_descriptor`, `hooks/triage-prompt-nudge.sh:457-511`.
- Entry gate: `[ -n "$t3_backend" ] && [ "${CV_JEV_T3:-}" = "1" ]` after the record is written (`:755`); stdout discarded; failure only logs.
- Inputs: request, the engine's own `t3_prompt`, pid/key/sid, reason/cat/backend.
- Flow: `umask 077` (subshell), jq builds state into `mktemp cv-jev-state.*` (`:465-485`), `build --point t3` (`:486`), temp deleted (`:488`), checks request file is `<dd>/req/*`, writes `pending-<key>.json` via `.pending.XXXXXX` + `mv`.
- After the change the jq block and state temp file disappear, but a NEW temp file is needed for `--prompt-file` (`_classify_headless` already does `mktemp cv-t3-prompt.XXXXXX`, `:397-403`, and removes it on every path). The subshell has several `exit 1` paths; the prompt temp must be removed on all of them or it leaks the request text into `$TMPDIR` (the old design held it only in env).
- Latent: the `[ "$(basename "$rdir")" = "req" ]` check trusts the printed `request_file` path. `t3-request` printing `status: off` has no `request_file`, so the hook takes the `exit 1` branch and logs "no T3 shadow descriptor was written"; that is correct behaviour but changes the log line meaning (it will now also fire for config off, which the module already filters).
- Latent (pre-existing, not introduced): `jev-t3.tsx` `findPending` reads the first 50 names sorted, arbitrary slice (memory `jev-seams-map`); untouched by this spec.

Sibling B: `_classify_headless`, `:393-434`, and the module `runShadow`, `jev-t3.tsx:204-255`.
- The module writes the response file itself (`$.fs.write(respFile)`); in Phase T the vault TOOL does (`vault.tsx:309-317`). Same path shape `<dd>/resp/<name>.resp.json`; `parse` derives the sibling request from it only when `--request-file` is omitted (`_request_for_response`, `:452`). Spec passes `--request-file`, which is the safer form.
- The module calls `parse --hook-budget-left-ms`; Phase T has none, the flag is optional (`:915`) and omission just leaves it out of `calls.jsonl` (`telemetry_line`, `:597`).

Sibling C: `skills/compound-v/onboarding.md:75-91` (Jev for UI), the other prose that calls `jev_classify`. Its gate is "the status line shows `Jev: on` (vault installed, has a key, egress allowed for this repo)", and it states "No vault, `jev.enabled: false` or `mode: off`: the step is skipped". The spec's Phase T gate is weaker (F-1).
The tool returns `refused: <reason>` as a plain string instead of a path (`serveTool`, `vault.tsx:282-306`); onboarding handles it ("a refusal just means Jev has nothing to add"). The Phase T step must too, before `parse --response-file`.

Latent bugs and stale claims:
- F-9. The recall hit "Shadow covers only the hook path" (`research/2026-10-05-jev-next-stage.md`) is accurate against the code: `v-triage.md` has no `jev`/`--t3-engine` text (grep over `commands/`: only `v-onboard.md:43` mentions `jev_classify`). Verified, not stale. The architecture block in the prompt that says `t3.shadow` does not exist is also still true (`schemas/pre-eval-record.schema.json:187-196` has `engine/category/probs/model/catalogue_hash` only).
- `hooks/triage-prompt-nudge.sh:353-355` comment says the engine "never lets it change the tier"; verified (`preeval.py:1725-1726`, help text).

## 4. External APIs

No third-party API. Context7 was not usable (server needs authorization); nothing here needs it. In-repo contracts read from source:
- **Vault tool** `mcp__compound-v-vault__jev_classify({request_file})`: absolute path, no `.`/`..`, regular file, real path under `~/.claude/compound-v-jev/<dir>/req/<name>.req.json`, writes `<dir>/resp/<name>.resp.json` 0600, returns that path or `refused: <reason>` (`vault.tsx:282-317`). Registered only when `CV_HEADLESS_CLASSIFY` is unset (`:353`). Arguments are read flat from the event (`e.request_file`, `:405`); typings version dependent (early access per the file header, lines 23-26).
- `classify` (`vault.tsx:235-258`): `unavailable('no_key')` with no key, `unavailable('egress')` plus a one-per-session toast `EGRESS_ASK` when consent is not `allow`; sends only on `allow`. So the tool is registered and callable without a key or consent, and answers with a non-ok body. Request `context` must be `hook` or `offline` (`validRequest`, `:140-146`), `repo` absolute.
- Timeout: `hook` 1,500 ms, `offline` 5,000 ms (`vault.tsx:47-48`); a 429 retry exists only for `offline` (`:220`).
- Python 3.9 floor for `compound-v-jev.py` (docstring `:7`; CI `validate.yml:298-312`).

## 5. Regression Surface

- Hook T3 shadow descriptor: any change to `_write_t3_descriptor` breaks the Jev shadow data silently (stdout discarded, failure only logs). If it breaks, `shadow-pairs.jsonl` stops filling and nothing else fails. Covered by `test-native-points.sh:700-765`, which asserts the descriptor, the request state (`:741-752`: keys `hints/paths/request`, `request == request[:2000]`, `hints == ["legal_copy"]`, path `src/uploader.py`).
- Hook byte-identical output with `CV_JEV_T3=1` (`:692-698`) and the flag-leak mutant (`:783-805`): the new `t3-request` subprocess must stay behind the same gate and after the decision, stdout and stderr discarded.
- The hook's UserPromptSubmit budget: `hooks.json` gives 25 s, headless classify cap 15 s + 3 s grace (`test-native-points.sh:821-824`). `t3-request` adds one Python process (config load + redactor import of `epic-arbiter`) to the hook path where there used to be one `jq` plus one `build`; `build` already loaded the redactor, so the delta is the config read. Unmeasured; no figure should be claimed.
- Pre-eval record digest: `--t3-engine` lands in `t3` before the digest (`:1051-1066`). Any Phase T record for a request that was previously recorded WITHOUT a `t3` block (an older Phase T run, or the same request re-run) now differs in content: `write_record` refuses it and `triage` exits 1 with "already exists with DIFFERENT content" (`:1115-1119`), the CLI prints `triage failed` (`:1787-1789`).
- `compound-v-jev.py --selftest` and `tests/test-jev-core.sh`: a new subcommand must be reachable through `_run_cli` and must not import a network module (`test-jev-core.sh:36`) or contain anti-ruflo phrasing (`:44`); CI greps `scripts/` and `docs/`.
- Triage-outcomes stream and the T3 commit step: unchanged if the Jev step runs between T2 and T3 and writes only under `~/.claude/compound-v-jev/`. A failure inside the step must not skip T3 (an uncommitted record is the v2.6.4 loss shape, `v-triage.md:194-195`).
- `calls.jsonl` / `shadow-pairs.jsonl`: both gain rows from a second producer. `eval --t3 --prepare --pairs` (`:643-664`) rebuilds requests from every pair row whose request file still exists, with the Claude label as the reference; rows from Phase T are indistinguishable from hook rows (no `source` field).

## 6. DRY Findings

1. Three copies of the same bound are or would be present: `classify-request.py` `MAX_REQUEST_CHARS/MAX_PATHS/MAX_TAXONOMY_CATEGORIES`, the hook's `_T3_STATE_MAX_CHARS`, and the new `t3-request`. Decision required: `t3-request` imports the constants from `compound-v-classify-request.py` via `_load` (already how `_t3_defs` works, `:144-147`) and the hook constant is deleted, or the duplication is justified. A silent fourth literal 2000/20/40 in `compound-v-jev.py` is the DRY failure to avoid.
2. Parsing the engine's own prompt back into paths/hints is an inverse of `build_prompt` (`classify-request.py:166-216`) that lives in jq today and would live in Python tomorrow. The prompt format (`RESOLVED FILE PATHS (may be empty or approximate):`, `- (none resolved)`, `PROJECT IMPACT-TAXONOMY CATEGORIES (context only):`) is a literal in two places (producer, parser). The producer also hard-caps the prompt at 8,000 chars and can truncate the tail (`:211-215`), which cuts the hints block mid-list; the parser must tolerate that. A shared parse helper next to `build_prompt` removes the third copy; if the parser stays in `compound-v-jev.py`, the selftest must build its fixture by calling `build_prompt`, not by hand-writing the format.
3. Config resolution already exists (`resolve_jev`); do not reimplement the `active -> shadow` coercion.
4. `jev_classify` calling sequence is prose-duplicated in `onboarding.md` and `v-onboard.md:43`; the new step is a third prose copy of "call tool, then parse". Acceptable, but reuse its wording for `refused:` handling.

## 7. Design constraints for the spec

1. **Gate parity (F-1).** The Phase T step must not write a request file (redacted request text, outside the repo) for a user whose vault has no key or whose egress is not `allow`. The hook never does: `CV_JEV_T3` requires `jev.status` on. Config-only gating plus "tool present" writes `req/*.req.json` and `shadow-pairs.jsonl` rows for every T3-deciding Phase T run on any machine with the vault installed, consent or not (the tool is registered without a key). Either gate on `Jev: on` as `onboarding.md:75-76` does, or state that the data is written regardless and why that is acceptable. Resolve it in the spec.
2. **`t3-request` resolves config through `resolve_jev(load_project_config(repo))`**, not a raw file read; absent config is `on/shadow`; a raising `load_project_config` and any warning output must not reach stdout or crash. The `off` result carries a reason string and never an exit code other than 0.
3. **Phase T must capture `t3_reason` from the `needs_t3` output** and carry it to `pair`. The re-invocation result does not print it (F-3).
4. **Backend value for `pair`** is the same token passed to `--t3-engine`: `claude`, `codex` or `parent`. State that `parent` is a new value on the pair stream.
5. **Same repo argument for `t3-request` and `pair`** (both `--repo .`, from the repo root); a mismatch yields `bad_input` and no pair.
6. **`--request-env` empty or unset is refused**, as the engine does; the request is never read from argv (selftest must assert the argv of the subprocess, not only the absence of the text in output).
7. **Single source for caps.** Import the 2,000 / 20 / 40 bounds from `compound-v-classify-request.py`; delete `_T3_STATE_MAX_CHARS` from the hook. Selftest builds its fixture prompt with `build_prompt` and also covers: request containing the header text (last header wins), prompt truncated by the 8,000-char ceiling, `(none resolved)`, 20 and 40 caps, request over 2,000 characters, non-ASCII, empty hints block.
8. **Hook rewrite.** `_write_t3_descriptor` keeps: subshell + `umask 077`, gate order, discarded stdout, the `<dd>/req` check, `.pending` + `mv`. It gains a prompt temp file that is removed on every exit path (including the `build`-equivalent failing and `status: off`); add a test that no `cv-t3-prompt.*` / equivalent remains in `$TMPDIR` after success and after a refusing `t3-request`. The existing `cv-jev-state.*` assertion (`test-native-points.sh:759-760`, `:764`) becomes vacuous and must be repointed at the new temp name. The refused-build stub (`:769-773`) answers every subcommand and still works.
9. **Descriptor shape stays seven keys**, `claude_category`/`backend`/`t3_reason` token-valid, 0600, request file in `<dd>/req`, state keys `hints/paths/request` (asserted at `test-native-points.sh:730-753`). The spec's AC2 is already enforced by those rows; do not weaken them.
10. **Phase T step failure isolation.** Each of the four sub-steps can fail (tool absent, `refused: <reason>` instead of a path, parse non-ok, pair error). The step must reach T3 (commit) in every case. Define explicitly whether `pair` runs when Jev answered non-ok: the hook path pairs unconditionally (`jev-t3.tsx:242`), the spec's sentence "a non-`ok` Jev answer ... changes nothing" reads the opposite (F-6).
11. **Context.** Decide `hook` (1,500 ms, default of `build --point t3`) or `offline` (5,000 ms, 429 retry) for the attended Phase T path; the spec text says "same as `build --point t3`", which silently picks `hook`. If `hook` is intended, say it; `calls.jsonl` latency stats will then mix two producers with the same context value.
12. **Record write-once conflict (F-5).** Phase T prose must say what to do on `triage failed ... DIFFERENT content`: a request already recorded without a `t3` block, or recorded by the hook with another engine, cannot be re-written with `--t3-engine`. Do not tell the agent to hand-edit the record or drop `--t3-engine` silently.
13. **Transcript claim.** "No request text ... reaches the transcript" cannot hold: T2's command line already contains `V_TRIAGE_REQUEST='<the request text>'` in the Bash tool call (`v-triage.md:121`), and the new step repeats it. Scope the claim to command OUTPUT and file contents; the request text appearing in the typed command is existing behaviour.
14. **Tool availability test in prose.** `mcp__compound-v-vault__jev_classify` may be a deferred tool; the prose needs a rule for "has the tool" (ToolSearch, or the status line) and for `refused: ...` strings, including `refused: disabled` under `CV_HEADLESS_CLASSIFY`.
15. **Prompt file for the Task route.** The headless route writes `$PROMPT_FILE` (location unspecified, `v-triage.md:150-155`); the Task route has no file. `t3-request` needs one in both, and the prose must say where it lives and delete it.
16. **Test home for AC3.** No test greps `commands/v-triage.md` today (tests reference `commands/v-*.md` only in `test-vault-mod.sh` and `test-usage-workflow.sh`). The new row needs a home (`tests/test-native-points.sh` is the nearest fit, using its `check "..." "$(grep -q ... && echo 1 || echo 0)"` pattern at `:813-818`) and must be shown to fail when the named tokens are removed (the file already plants mutants, `:783-805`).
17. **AC4 test.** A test that runs `triage --t3-category X --t3-engine Y` as the prose says is a restatement of existing coverage (`preeval.py` selftest `T3META`, `:3243-3368`; `test-native-points.sh:565-570`). To be more than that, it should drive the exact argv the prose prints (extract it from the markdown) against a fixture repo.
18. **Docs that describe the shadow** will go stale: `skills/compound-v/phase-preeval.md:108-109`, `plugins/compound-v-vault/README.md`, `compound-v-jev.py` docstring CLI list (`:9-16`), `AGENTS.md`, `CHANGELOG.md`. Anti-ruflo applies to all of them.

## 8. File Touch Map

| File | Change | Flag |
|---|---|---|
| `scripts/compound-v-jev.py` | new `t3-request` subparser + handler + selftest; docstring CLI list; imports caps via `_load` | |
| `scripts/compound-v-classify-request.py` | only if a shared prompt-parse helper is placed next to `build_prompt` (DRY item 2) | SHARED RESOURCE (imported by `compound-v-jev.py` `_t3_defs` and by the hook's `--classify-headless`) |
| `hooks/triage-prompt-nudge.sh` | `_write_t3_descriptor` calls `t3-request`; drop jq block and `_T3_STATE_MAX_CHARS`; prompt temp lifecycle | shellcheck-gated; header comment `:172-176`, `:436-453` to update |
| `commands/v-triage.md` | T2 re-invocation `--t3-engine`; new Jev step between T2 and T3; capture `t3_reason` | |
| `tests/test-native-points.sh` | repoint temp-file asserts; new prose row; mutants | |
| `tests/test-jev-core.sh` | optional: end-to-end `t3-request` through the real CLI | |
| `skills/compound-v/phase-preeval.md` | shadow description lines ~100-110 | |
| `plugins/compound-v-vault/README.md`, `AGENTS.md`, `CHANGELOG.md` | description of the Phase T producer | |
| `scripts/compound-v-preeval.py`, `scripts/compound-v-project-config.py`, `plugins/compound-v-vault/hooks/vault.tsx`, `hooks/jev-t3.tsx`, `schemas/pre-eval-record.schema.json` | none (read-only dependencies) | |
