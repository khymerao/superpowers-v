# Phase T asks Jev in shadow and records its t3 block - design

Triage: `docs/superpowers/pre-eval/2026-10-08T055405Z-phase-t-in-v-triage-never-asks-jev-commands-v-triage-md-step-e332.json`
(FULL). Handoff: `docs/superpowers/research/2026-10-05-jev-next-stage.md`, section "Shadow covers only the hook path".

## Problem

1. Spec 1 wires the T3 shadow only to the prompt hook: `hooks/triage-prompt-nudge.sh` leaves a pending descriptor
   (`_write_t3_descriptor`) and `hooks/jev-t3.tsx` consumes it after the hook returns. `/v:triage` Phase T
   (`commands/v-triage.md` T2) classifies with `compound-v-classify-request.py --classify-headless` and asks Jev
   nothing. In real use most T3 decisions go through Phase T (the hook sizes only the first change request of a
   session), so the shadow collects almost no pairs.
2. Phase T re-invokes `triage --t3-category <enum>` without `--t3-engine`, so its records carry no `t3` block even
   when T3 decided the tier. The hook path passes `--t3-engine`.

## Change

1. **One request builder.** New subcommand `compound-v-jev.py t3-request --repo R --request-env NAME --prompt-file P`
   builds the T3 request from the request text and the engine's own `t3_prompt`, with the same bounded state the hook
   builds today: the request capped at 2,000 characters, the paths under the LAST `RESOLVED FILE PATHS` header (at
   most 20, `(none resolved)` dropped) and the hints under `PROJECT IMPACT-TAXONOMY CATEGORIES` (at most 40). It then
   does what `build --point t3` does and prints the same JSON (`status`, `request_file`). The request text arrives
   through the environment, never argv. Before building, it reads the committed config: unless `jev.enabled` is true
   and `jev.t3.mode` resolves to `shadow` (`active` is coerced to `shadow`, as spec 1 does), it prints
   `{"status": "off", "reason": ...}`, writes nothing and exits 0.
2. **The hook uses it.** `_write_t3_descriptor` calls `t3-request` instead of its own jq extraction plus `build`. Its
   descriptor, its gating (`CV_JEV_T3=1`, after the decision, stdout discarded) and its output are unchanged.
3. **Phase T records `t3`.** In `commands/v-triage.md` T2, the `--t3-category` re-invocation also passes
   `--t3-engine <backend>`: the `backend` the headless classify printed (`claude` or `codex`), or `parent` when the
   Task route answered.
4. **Phase T asks Jev in shadow.** A new step after T2 (before T3's commit), run only when T3 decided the tier and the
   session has the `mcp__compound-v-vault__jev_classify` tool:
   1. `compound-v-jev.py t3-request` with the request and the same `t3_prompt`; `status: off` ends the step.
   2. Call `jev_classify` with the printed `request_file`; it returns the response file path.
   3. `compound-v-jev.py parse --response-file <resp> --repo . --mode shadow --request-file <req>` (writes one
      `calls.jsonl` line, whatever the status).
   4. `compound-v-jev.py pair --request-file <req> --claude-category <cat> --backend <backend> --t3-reason <reason>
      --repo .` (writes one `shadow-pairs.jsonl` line).
   Any failure or a non-`ok` Jev answer is reported in one line and changes nothing: the record, the tier and the
   commit are exactly what they would be without the step. No request text, response body or key reaches the
   transcript beyond the file paths and the parsed answer.

## Out of scope

Recording Jev's answer on the record (`t3.shadow`); T3 `active` (spec 1.5); the hook path's behaviour; `/v:init`.

## Acceptance Criteria

1. `compound-v-jev.py --selftest` covers `t3-request`: same state as the hook extraction on a fixture prompt (request
   cap, last paths header, 20/40 caps, `(none resolved)` dropped), `off` when Jev is disabled or `t3.mode` is `off`,
   request text never on argv.
2. The hook's T3 shadow test still passes with `_write_t3_descriptor` calling `t3-request`, and the descriptor is
   byte-identical in shape.
3. `commands/v-triage.md` T2 passes `--t3-engine` on the re-invocation, and its Jev step names `t3-request`,
   `jev_classify`, `parse --mode shadow` and `pair`; a test row checks both and fails when either is removed.
4. A Phase T run on a request that reaches T3 writes a record with a `t3` block (engine and category), demonstrated
   by a test that runs `triage` with `--t3-category` and `--t3-engine` as the prose instructs.
5. Full suite and `lint-frontmatter.py` green.

## Pre-flight amendments (2026-10-08)

These override the sections above where they differ. Sources: the 1A and 1C audits of this spec, section 7 of each.

1. **Opt-in parity.** Phase T cannot read `$.jev.status`, and the vault tool is registered without a key or egress
   consent. So: when the response is `unavailable` with reason `no_key`, `egress` or `disabled`, Phase T deletes the
   request file and writes no pair. The `calls.jsonl` line from `parse` stays (it carries no request text). Every other
   status (`ok`, `timeout`, `upstream`, `auth`, ...) is paired, as the hook path does.
2. **`t3_reason`** comes from the first `needs_t3` result (`t3_reason`, default `unbanded`) and is carried to `pair`;
   never invented.
3. **Record conflict.** T2 runs only when no record covers the request (unchanged). If the re-invocation with
   `--t3-engine` is refused because a record with different content exists, re-run it without `--t3-engine`, report
   that the record keeps no `t3` block, and skip the Jev step.
4. **Context.** `t3-request` takes `--context hook|offline`; the hook passes `hook`, Phase T passes `offline` (5,000 ms).
5. **Config** is read with the existing resolver (`resolve_jev(load_project_config(repo))`): no config means the
   defaults, a malformed config never tracebacks, warnings stay on stderr.
6. **Byte equivalence.** The Python extraction matches the hook's jq: codepoint cap 2,000, the LAST paths header,
   blank-line terminator, `(none resolved)` dropped from paths only. Caps are imported from
   `compound-v-classify-request.py` where it defines them; the hook's `_T3_STATE_MAX_CHARS` goes. An empty request is
   refused. The hook's `--prompt-file` temp file is removed on every exit path; the existing descriptor (seven keys) and
   hook rows stay green, and asserts on the old `cv-jev-state.*` temp file are repointed, not deleted.
7. **Tool discovery.** Mod tools are deferred since 2.1.293: Phase T loads `jev_classify` with ToolSearch before
   treating it as absent. A result that is not an absolute path to an existing file (for example `refused: ...`) ends
   the step with one line.
8. **Same `--repo`** for `t3-request`, `parse` and `pair`.
9. **Transcript claim** narrowed: no response body and no key reach the transcript (T2's own command already carries
   the request text).
10. **Tests.** AC3's prose row lives in `tests/test-jev-core.sh`, with a planted-failure check. AC4 is replaced by: the
    prose's `--t3-engine` re-invocation, run as written against a fixture repo, yields a record with a `t3` block.
11. A failure anywhere in the Jev step never skips T3's commit.
