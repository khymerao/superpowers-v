# Review Gate — run 2026-10-08-phase-t-jev-shadow

Job reviewed: `phase-t-shadow` (Task A), merged as `5af6510` on baseline `c5e4003`; bookkeeping `47a9861`.
Reviewed against `docs/superpowers/specs/2026-10-08-phase-t-jev-shadow-design.md` (its eleven pre-flight
amendments override the body), the plan `docs/superpowers/plans/2026-10-08-phase-t-jev-shadow.md` (A1..A6), the
manifest's global constraints, and the MUST/MUST NOT lists of both audits. Every command below was run by the
reviewer on the merged tree (`47a9861`), not read from the job's report.

## Recall

- Prior context handed in the prompt (V-memory, review intent): spec 1 review
  (`docs/superpowers/dogfood/2026-10-05-jev-classifier-foundation-review.md`), the F1/F2 plan tasks and the
  research note "Shadow covers only the hook path". They agree with the spec's problem statement: the hook was the
  only T3 shadow producer. Nothing recalled contradicts the current code.
- Bridge over the diff:

  ```text
  $ compound-v-memory.py recall-check --files scripts/compound-v-jev.py hooks/triage-prompt-nudge.sh commands/v-triage.md tests/test-jev-core.sh tests/test-native-points.sh
  recall-check: none (1/2 match on ...)
    not counted (not attributable to a job's own work): harness_fault 5, pipeline_bookkeeping 3, recall_exclude 3, test_timeout 1, unattributed 3
  ```

  `none`: no escalation.
- Reviewer memory: no directive found in `.claude/agent-memory/superpowers-v-spec-reviewer/`.

## SPEC

**Scope lock.** `results/phase-t-shadow.json` `files_changed` = the five `write_allowed` paths exactly; gate receipt
`verdict: pass`, `violations: []`. `hooks/jev-t3.tsx` and `plugins/compound-v-vault/**` untouched. No version
bump, no CHANGELOG. Commit subject has no conventional prefix and no Co-Authored-By trailer.

| Requirement (spec + amendments + global constraints) | Implemented in | Status |
|---|---|---|
| `t3-request --repo --request-env NAME --prompt-file --context hook\|offline`, `allow_abbrev=False`, `--context` required | `scripts/compound-v-jev.py` `_parser` (`tr = sub.add_parser("t3-request", allow_abbrev=False)`); choices `tuple(TIMEOUT_MS)` = `hook`, `offline` only (`:59`) | ✅ |
| Request only through the environment, empty/unset refused | `main` → `_env_text(args.request_env)`; `t3_request` refuses `not request.strip()` with `bad_input` + `REFUSED` on stderr | ✅ |
| Config via `resolve_jev(load_project_config(repo))`; off unless enabled and `t3.mode` = shadow; active coerced; malformed config no traceback; warnings stderr | `t3_off_reason` | ✅ |
| Off writes nothing | gate runs before the prompt is read or `build_request` is called | ✅ |
| Otherwise prints what `build --point t3` prints | `return build_request("t3", state, repo, context=context)` | ✅ |
| Byte-equivalent extraction: codepoint cap, LAST paths header, blank-line terminator, `(none resolved)` dropped from paths only, 20/40 | `t3_state`, `_t3_items` | ✅ |
| Caps imported from `compound-v-classify-request.py` | `_t3_caps` (`MAX_REQUEST_CHARS`, `MAX_PATHS`, `MAX_TAXONOMY_CATEGORIES`) | ✅ |
| Hook calls `t3-request --context hook`; descriptor keys, gating, stdout unchanged | `hooks/triage-prompt-nudge.sh:464-492`; descriptor `jq -n` block unchanged | ✅ |
| Prompt temp file removed on every exit path | `:465` (write failure) and `:470` (unconditional, before any later `exit`) | ✅ |
| `_T3_STATE_MAX_CHARS` removed | gone; guarded by the native-points row "the hook keeps no cap of its own and no jq extraction" | ✅ |
| `cv-jev-state.*` asserts repointed, not deleted | `tests/test-native-points.sh` rows now find `cv-jev-prompt.*` | ✅ |
| Prose: keep `t3_reason` from the first `needs_t3` result, default `unbanded` | `commands/v-triage.md` "Keep `t3_reason` from this first result" | ✅ |
| Prose: re-invocation adds `--t3-category` and `--t3-engine <claude\|codex\|parent>`; never with `backend: none` or a timeout | `v-triage.md` re-invocation block and the paragraph after it | ✅ |
| Prose: DIFFERENT-content refusal → re-run without `--t3-engine`, say so, skip T2b | `v-triage.md:202-205` | ✅ |
| T2b only when T3 decided; ToolSearch for `mcp__compound-v-vault__jev_classify` | `### T2b.` step 1 | ✅ |
| `t3-request --context offline`; non-path result ends the step | steps 2-3 | ✅ |
| `parse --mode shadow --request-file` | step 4 | ✅ |
| `unavailable` + `no_key`/`egress`/`disabled` → `rm -f` the request file, no pair; every other status pairs with carried category, engine, reason | step 5 | ✅ |
| Same `--repo .`; one-line report; never skips T3; no response body or key in transcript | T2b preamble and closing paragraph | ✅ |

**Audit MUSTs.** Library audit: `--context` with a selftest row reading the written `context` (✅ "t3-request offline
context is 5,000 ms" / "hook context is 1,500 ms"); ToolSearch before absent (✅); only an absolute existing path
reaches `parse` (✅); `t3_reason` sourced, never invented (✅); `--t3-engine` together with `--t3-category`, no
weakening of the `backend: none` rule (✅); byte-equivalence on a shared fixture incl. multibyte straddle (✅ six
fixtures); request through the environment only (✅ for the process argv; see O-2); no new API parameter (✅); 2,000
cap only, not 4,000 (✅); no `t3.shadow` (✅). Archaeology §7: empty request refused (#6 ✅, subprocess argv
asserted), hook rewrite keeps subshell/umask/`<dd>/req` check/`.pending`+`mv` (#8 ✅), seven-key descriptor rows not
weakened (#9 ✅), failure isolation and pair-on-non-ok resolved by amendments 1 and 11 (#10 ✅), deferred-tool rule
(#14 ✅).

**Plan A1..A6.** A1 tests-first and A5 revert checks: the reviewer re-ran revert checks in scratch copies (below);
A4's named suites all green; A6 commit present.

**Over-build.** None found. `_utf8_text`/`_env_text` (invalid UTF-8 from the environment becomes U+FFFD instead of a
crash) and the `MAX_INPUT_BYTES` prompt bound are input hardening for the new entry point, not features.

**Job acceptance.** "All new rows pass and each fails when its change is reverted; ... selftests, test-native-points,
test-jev-core, test-jev-t3-mod, lint-frontmatter and shellcheck green": met (evidence below).

## QUALITY

- **Code quality.** Clear names, one source of truth for the caps, a config gate that cannot traceback, and the
  hook shrinks from a 25-line jq program to one call. No dead code left behind (`cv-jev-state`, `CV_JEV_PROMPT` and
  `_T3_STATE_MAX_CHARS` are absent from the hook, guarded by a row).
- **No regression.** Hook stdout is byte-identical with and without `CV_JEV_T3=1` on all four T3 cases, and on a
  refusing `t3-request`. The config gate inside `t3-request` adds no hook-visible change: `hooks/jev-t3.tsx:109`
  already consumed descriptors only when `enabled === true && t3.mode === 'shadow'`.
- **Revert checks (reviewer-run, scratch copies of `scripts/` only):**

  ```text
  == lastheader (t3_state uses parts[1] instead of parts[-1])     rc=1
  FAIL t3_state reads the LAST paths header, not one inside the request
  == cfggate (t3_off_reason bypassed)                              rc=1
  FAIL t3-request is off when jev.enabled is false
  FAIL t3-request is off when jev.t3.mode is off
  FAIL t3-request is off on a malformed config, with no traceback
  FAIL t3-request off writes nothing: no data dir for that repo
  FAIL t3-request coerces t3.mode active to shadow, warning on stderr only
  == emptyreq (empty-request refusal removed)                      rc=1
  FAIL t3-request refuses an empty request
  FAIL t3-request refuses an unset request variable
  == argvenv (request read from the env NAME's literal, not the env) rc=1
  FAIL t3-request state equals t3_state of the env request and the prompt file
  FAIL t3-request process: the request arrives through the environment
  ```

  The hook cleanup and the prose carry their own planted failures (prompt-leak mutant; five prose-token removals;
  a prose copy without `--t3-engine` writes no `t3` block), all passing.
- **Test alignment.** Every MUST above has a row that fails when it breaks, except the prose-only rules
  (`no_key/egress/disabled` → no pair, never skips T3), which are guarded textually by `prose_check` in
  `tests/test-jev-core.sh` — the ceiling for slash-command prose.
- **Fabricated metrics.** None. The `latency_ms: 900` and probabilities in `tests/test-jev-core.sh` are a fixture
  response body, not a reported measurement.
- **Reward hacking.** None. The two reworded native-points rows (`cv-jev-state.*` → `cv-jev-prompt.*`; "refused
  build" → "refused t3-request") are the repointing amendment 6 orders; no assertion was dropped or loosened.
- **§2.6** not applicable (no marathon blocker).

## INTEGRATION

- **Partition / seams.** Single implementation job; no shared file edited twice. The hook and Phase T now share
  one builder; the native-points end-to-end row shows the old route (jq → state file → `build`) and `t3-request
  --context hook` write the same `body.state`, `context`, `timeout_ms` and `catalogue_hash`.
- **Tests the tier owed.** Tier FULL with a declared `impacted_map`; all five changed paths match a rule, so the
  impacted union was owed. The job result records `tests.scope: impacted`, `selected_count: 5` (floor + the four
  matching rules), `tests.exit_code: 0`. Correct.

### Acceptance criteria, run on the merged tree

**AC-1** — selftest covers `t3-request`.

```text
$ /usr/bin/python3 -B scripts/compound-v-jev.py --selftest
selftest: 112 rows ok
jev-selftest rc=0
```

Rows include: caps from `compound-v-classify-request.py`; LAST paths header; codepoint cap with a straddling `é`;
`(none resolved)` dropped from paths and kept in hints; 20/40 caps; off on `enabled: false`, `t3.mode: off`,
malformed config; active coerced with the warning on stderr only; empty and unset request refused; no argv form;
a real subprocess whose argv lacks the request marker while the request still arrives. Each reverts to a failure
(QUALITY). ✅

**AC-2** — hook rows with `_write_t3_descriptor` calling `t3-request`.

```text
$ bash tests/test-native-points.sh
PASS JEV SHADOW: T3 case 1 prints byte-identical output with CV_JEV_T3=1   (cases 2-4 likewise)
PASS JEV SHADOW: the descriptor has the seven contract keys, 0600, and a t3 request file in <dd>/req
PASS JEV SHADOW: the prompt temp file is deleted after t3-request
PASS JEV SHADOW: a refused t3-request leaves the output byte-identical
PASS JEV SHADOW: ...and leaves no prompt temp file behind
PASS JEV SHADOW: the hook calls t3-request --context hook, once
PASS JEV SHADOW: the request reaches t3-request through the environment, never argv
PASS PLANTED FAILURE: a prompt temp file left by the hook is caught by the find
PASS JEV SHADOW: t3-request's extraction equals the old jq on all 6 fixtures (6 same)
PASS JEV SHADOW: old jq + build and t3-request --context hook write the same request state
157 passed, 0 failed
native-points rc=0
```

✅

**AC-3** — prose passes `--t3-engine` and names the four Jev-step commands; a row fails when either is removed.

```text
$ bash tests/test-jev-core.sh
PASS v-triage prose: --t3-engine and the Jev step
PASS planted: prose without '--t3-engine' fails the check
PASS planted: prose without 't3-request' fails the check
PASS planted: prose without 'jev_classify' fails the check
PASS planted: prose without 'parse --mode shadow' fails the check
PASS planted: prose without '" pair --request-file' fails the check
all jev-core tests pass
jev-core rc=0
```

✅

**AC-4** — the prose re-invocation, run as written against a fixture repo, writes a record with a `t3` block.

```text
PASS prose T2 on the fixture asks for T3
PASS prose re-invocation writes a record with a t3 block
PASS prose t3-request builds an offline request
PASS prose parse reads the answer
PASS prose pair writes the carried category, engine and reason
PASS prose Jev request lands in the per-user data dir
PASS no Jev file under the fixture repo
PASS planted: a re-invocation without --t3-engine writes no t3 block
```

The bash blocks are extracted from `commands/v-triage.md` itself and only their `<placeholders>` filled. ✅

**AC-5** — full suite, `lint-frontmatter.py`, `shellcheck hooks/*.sh`.

```text
$ /usr/bin/python3 -B scripts/compound-v-preeval.py --selftest
SELFTEST PASSED
$ bash tests/test-jev-t3-mod.sh
tests/test-jev-t3-mod.sh: 14 passed, 0 failed
$ /usr/bin/python3 -B scripts/lint-frontmatter.py .
✅ All frontmatter clean
$ shellcheck hooks/*.sh
shellcheck rc=0
$ <manifest full_command: every scripts/compound-v-*.py --selftest, then every tests/*.sh>
all-tests-ok
wall=334s
rc=0
```

✅

### Observations (non-blocking; for the spec owner, not the implementer)

- **O-1. A vault refusal leaves an unpaired request file.** `serveTool` returns the string `refused: disabled`
  when `CV_HEADLESS_CLASSIFY` is set at call time (`plugins/compound-v-vault/hooks/vault.tsx:283`), before
  `classify` runs, so the `unavailable`/`disabled` response that amendment 1 deletes on cannot arrive through the
  tool. T2b step 3 (as the global constraint prescribes) ends the step on a non-path result without `rm -f` of the
  request file, so in that case a 0600 request file stays in `~/.claude/compound-v-jev/<digest>/req/` with no
  pair. The window is narrow (the tool is registered only when that variable is unset:
  `docs/superpowers/archaeology/2026-10-08-2026-10-08-phase-t-jev-shadow-design.md:67`) and the
  file stays in the per-user directory, so this is a spec gap, not a deviation: the implementation matches
  amendment 1 and the constraint word for word. Suggested follow-up: also delete the request file on any
  `refused:` result.
- **O-2. The env prefix shows the request text in the shell command.** The Phase T blocks use
  `V_TRIAGE_REQUEST='<the request text>' python3 ...`, so the text is in the Bash command line but not in the
  Python process argv. That is the T2 pattern already in the file, and amendment 9 narrowed the transcript claim
  for exactly this reason, which settles the library audit's "MUST NOT interpolate request text into a command
  line" in the implementation's favour.

## Verdict

**APPROVED.**

- PASS 1 SPEC: requirements 19/19 · audit MUSTs met · over-build clean · job acceptance met · scope lock respected
  (gate `pass`, confirmed at the seam).
- PASS 2 QUALITY: no regression · every code MUST has a row that fails when reverted (four reverted by the reviewer)
  · no fabricated metrics · no reward hacking.
- PASS 3 INTEGRATION: no partition leak · the hook and Phase T share one builder, old and new requests identical ·
  owed tests ran with exit 0 · AC 5/5 met on the merged tree, full suite `all-tests-ok`.

Open issues: none. O-1 and O-2 are recorded above for the spec owner.
