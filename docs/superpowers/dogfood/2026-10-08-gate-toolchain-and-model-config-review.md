# Review Gate — run 2026-10-08-gate-toolchain-and-model-config

Reviewer: `superpowers-v:spec-reviewer` (job `spec-review`, direct isolation). Reviewed on the merged tree,
HEAD `e0e392e` (the implement job `gate-model` landed as `2a488e7`; pre-change tree `cf58e03` = `2a488e7^`).
Spec: `docs/superpowers/specs/2026-10-08-gate-toolchain-and-model-config-design.md` — its "Pre-flight
amendments" override the sections above them, and were reviewed as the binding text.

## Recall

- The V-memory block in the job prompt was read. The two `project-root-run-b2` review records and plan are the
  ADR 0005 background this change builds on (`resolve_project_root` as the one rule for a project root). No recalled
  record describes a prior failure of the integration gate's `toolchain_artifacts` threading or of resolve-model's
  config default. One recalled row cites `docs/superpowers/execution/2026-10-06-multi-object-closeout.md`, which is
  not in this repository (flagged `missing_paths` by the recall layer itself); the spec quotes its content
  (`.DS_Store`, `.phpunit.cache`, `.baseline` read as `contradicted`/`forged`), and that is the claim reviewed here.
- Reviewer memory leads used (each re-verified, none taken as a finding): the review-job Bash clamp (every probe ran
  as `bash <script>` from the scratchpad); `impacted_map` `when: '*.md'` never matches a nested path — confirmed again
  here, see INTEGRATION. No directive was found in any memory file.

## SPEC

Scope lock: the receipt `receipts/gate-model.gate.json` lists 10 changed paths, all 10 inside the job's
`write_allowed` (10 entries), `violations: []`, `verdict: pass`. Read from the receipt, not the summary.

| Requirement (spec + amendment) | Implemented in | Status |
|---|---|---|
| A1. One `toolchain_artifacts` reader, owned by the scope gate | `scripts/compound-v-scope-check.py:596-619` `manifest_toolchain_artifacts` | met |
| A1. Emitter calls it, no copy | `scripts/compound-v-emit-workflow.py:2159-2182` `_toolchain_artifacts_spec` loads the scope gate by path and calls the reader; the old inline parse is deleted | met |
| A1. Gate calls it, no copy | `scripts/compound-v-integration-gate.py:462-479` (wrapper loads the scope gate, calls its reader), read once in `evaluate_run` `:1371-1380` | met |
| A1. Selftest cases move with the reader | `compound-v-scope-check.py:1494-1522` (six reader cases, all-or-nothing) | met |
| Change 1. Gate passes each glob as `--toolchain-artifact` in `run_scope_check` | `compound-v-integration-gate.py:811-812`, threaded through both re-derivations in `evaluate_job` (`:1137`, `:1239`) | met |
| A2. Claims limited to `contradicted` and false `blocked`; `.DS_Store`/`.phpunit.cache` stay violations unless declared, said in the gate docstring | module docstring `compound-v-integration-gate.py:56-68`, `run_scope_check` docstring `:794-801`; no name/extension exemption added anywhere | met |
| A3. Gate test: direct job, really gitignored file, honest receipt made with `--toolchain-artifact`; glob removed ⇒ caught | `tests/test-integration-gate.sh` section 5d (`:413-496`): `isolation: direct`, `.gitignore` committed before the baseline plus a `check-ignore` precondition row, receipt built from the real scope gate's output with `--toolchain-artifact 'build/**'` | met |
| A4. resolve-model default in `main()` only; root = `--repo-dir` or `resolve_project_root()`; config `<root>/.claude/compound-v.json`; same root to `default_settings_paths` | `compound-v-resolve-model.py:574-594`, `:614-615`, helper `_cli_project_root` `:622-637` loads `resolve_project_root` through the existing explicit-path loader `_project_config_module` | met |
| A4. `resolve()` and `load_config_models` unchanged for in-process callers | the diff's hunks are at `:11`, `:44`, `:529`, `:539`, `:549`, `:568` (docstring and `main()` only); no `def resolve(` / `def load_config_models(` / `def default_settings_paths(` / `def apply_effort_cap(` line changed (probe below) | met |
| A4. Fail closed outside git, except `--explicit-model` | `compound-v-resolve-model.py:585-590` returns 2 with a JSON error; `--explicit-model` skips the config entirely | met (probed) |
| A5. Emitter `resolve_job_model` passes `--repo-dir` | `compound-v-emit-workflow.py:1868-1869`; all four `build_plan` call sites pass `repo_dir=abs_repo_root` (`:2381`, `:2659`, `:2707`, `:2730`) | met |
| A5. `agents/parallel-dispatcher.md:150` passes `--repo-dir "$PWD"` | `agents/parallel-dispatcher.md:154` (`set -- "$@" --repo-dir "$PWD"`; the line moved by the 3 added comment lines) | met |
| A6. Five docs updated | resolver docstring `:14-28` and `--repo-dir` help `:558-567`; `agents/parallel-dispatcher.md:141-145`; `skills/compound-v/phase-3-parallel-opus-dispatch.md:168-173,182`; `skills/compound-v/routing-policy.md:380-385`; `skills/compound-v/execution-manifest.md:150` | met |
| A7. resolve-model test: subdirectory ⇒ cap and models from the same root; `--explicit-model` outside git succeeds; outside git without flags exits non-zero | `tests/test-resolve-model.sh` rows 2, 4, 7, 8 (plus root, `--repo-dir`, explicit `--config`, no-config-file rows) | met |
| Job acceptance: "Gate and resolve-model rows pass and fail on revert; the four selftests, test-integration-gate, test-engine-c-contract and lint green; docs updated" | AC-1 below; the four selftests and both tests ran in the job's impacted command (receipt `tests.checks[1]`, rc 0); lint is AC-2 below | met |

**The one-reader grep, read correctly.** `grep` for a `toolchain_artifacts` parse over `scripts/*.py` returns 7 hits.
Only `compound-v-scope-check.py:616` reads the list off a manifest for the exemption. `compound-v-emit-workflow.py:2236`
reads the plan `entry` the reader already filled; `:4591` and `:11308` read the scope gate's *output* (`raw_stdout`,
a receipt in the selftest); `compound-v-scope-check.py:1469,1491` are selftest assertions on CLI output; and
`compound-v-validate-manifest.py:2420` is the refusal site amendment 1 itself names ("where it is REFUSED"), which
predates this change and decides validity, not the exemption. No copy.

**Over-build.** None found. `skills/compound-v/phase-3-parallel-opus-dispatch.md:182` gains the same
`set -- "$@" --repo-dir "$PWD"` line the dispatcher got; that file mirrors the dispatcher snippet and is one of the
five docs amendment 6 names, so it is the doc staying true, not a new feature. The emitter's new
`_SCOPE_CHECK_MODULE` one-slot cache is the minimum needed to avoid reloading the scope gate per job.

**A design edge, recorded rather than raised.** `--repo-dir` pointing at a directory that is not in git resolves
(`resolve_project_root(repo=X)` returns any existing directory, `compound-v-project-config.py:133-137`), finds no
config and prints the built-in `sonnet`, rc 0 (probe below). Spec Change 2 scopes fail-closed to "no `--repo-dir` and
no `--config`", and ADR 0005 makes an explicit root win, so this is "absent file = built-in table", not a fail-closed
gap. No test row pins it either way.

## QUALITY

- **Code quality.** The integration gate splits `load_scope_matcher` into `load_scope_module` + two thin callers,
  so the matcher and the reader share one hardened from-source loader (private `pycache_prefix`, refuses when the
  cache dir cannot be made) instead of a second loader. Failure modes are strict in both places: the emitter treats
  an unloadable scope gate as "nothing declared" (per-job gate stricter, never looser,
  `compound-v-emit-workflow.py:2173-2174`), and the integration gate raises, which `main()` reports as
  `{"integration": "error"}` (`compound-v-integration-gate.py:1377-1380`, `:1552`). A manifest with no
  `toolchain_artifacts` key costs no extra import (`:471-472`). No dead code left behind.
- **No regression.** The full suite on the merged tree is AC-2 below. The in-process resolve-model API is unchanged
  (probe). The emitter selftest's `_rk_std` resolution now passes `repo_dir=tmp` (`:10320-10322`): the plan it is
  compared with was built for that same `tmp` root, so both sides resolve against one root. That is the test staying
  hermetic now that the resolver reads a project config by default, not a loosened assertion.
- **Test alignment.** Every code MUST has a row that fails when its change is reverted — proven, not inferred:
  old gate ⇒ 52 passed / 1 failed; a mutation that removes only the `--toolchain-artifact` threading in
  `run_scope_check` ⇒ 52/1; old resolver ⇒ 3 passed / 5 failed. The emitter's `--repo-dir` hand-off is guarded by the
  selftest row "resolve_job_model passes the project root as --repo-dir" (`:11364-11376`, a fake resolver that echoes
  the argument), and the shared reader by "A5: the emitter's reader IS the scope gate's" (`:11356-11361`). The two
  doc-only MUSTs (dispatcher line, five docs) are guarded by `lint-frontmatter.py` and this review's reading; amendment 6
  frames them as "docs in the same change", not fixes, so the "every fix ships a test row" constraint does not reach a
  prose line. Decision recorded, not left implicit.
- **No fabricated metrics.** None printed, logged or documented.
- **No reward-hacking.** `tests/test-integration-gate.sh` lost no assertion: its only modified pre-existing line is
  `literal_digest`, which gains an optional baseline argument defaulting to `$BASE`, so every existing caller is
  unchanged. No test skipped, no threshold moved, no scorer edited.
- §2.6 (confirmed-blocker integrity) does not apply: not a marathon run.

## INTEGRATION

**Partition and seams.** One implement job, so no partition leak is possible. The seam that matters is the
reader shared by three scripts: the emitter and the gate both reach `manifest_toolchain_artifacts` by explicit path
(`SCOPE_CHECK_DEFAULT`, and the gate's `scope_check` argument), never by import of each other, which respects the
existing "emitter imports the gate" direction (amendment 1).

**Tests the tier owed (derived here, not taken from the worker).** `triage.tier: FULL`, a declared `impacted_map`.
Of the 10 changed paths, the 4 `scripts/compound-v-*.py` match rule 1 and the 2 `tests/*.sh` match rule 2. The 4 `.md`
paths (`agents/…`, `skills/compound-v/…`) match **no** rule — `when: '*.md'` is a top-level glob and never matches a
nested path; the receipt's own `contract_notes` say so ("matched no `when` glob"). So the job owed floor ∪ impacted ∪
`full_command`. The job result records four commands (floor, rule 1, rule 2, full), `tests.exit_code: 0`,
`tests.scope: full`, `selected_count: 4` — the obligation is met. Consequence: `lint-frontmatter.py .` (rule 3) never
ran inside the job; it runs in AC-2 below.

### AC-1 — the gate row and the resolve-model rows pass and each fails when its change is reverted

Script `ac1.sh` (scratchpad). Reverts were done only on copies of `scripts/` in the scratchpad, selected through the
tests' own `INTEGRATION_GATE_SRC` / `RESOLVE_MODEL_SRC` overrides; the checkout was not touched.

```text
merged HEAD: e0e392eadca13d615ec5d7032d7e53e8d6ea1c70  pre-change: cf58e0323301e6899e87d0fc515d72cd0d959190
== merged tree: tests/test-integration-gate.sh
rc=0
PASS 5d precondition: build/out.js is really gitignored in the gated tree
PASS 5d precondition: the per-job gate forgives the artifact (pass)
PASS a declared, gitignored toolchain artifact ⇒ PASS at the run-wide gate (direct job, honest receipt)
53 passed, 0 failed
== merged tree: tests/test-resolve-model.sh
PASS no --config, from the root ⇒ the project's models (opus), not the built-in sonnet
PASS no --config, from a subdirectory ⇒ still the toplevel's models (opus)
PASS no --config, --repo-dir names the project ⇒ its models (opus)
PASS from a subdirectory the effort cap comes from the same root as the models
PASS an explicit --config is still the config read
PASS a project with no .claude/compound-v.json ⇒ the built-in table (sonnet)
PASS --explicit-model outside git ⇒ succeeds
PASS outside git with neither --config nor --repo-dir ⇒ exits non-zero
8 passed, 0 failed
rc=0
== REVERT the gate only (pre-change compound-v-integration-gate.py, everything else merged)
rc=1
PASS 5d precondition: build/out.js is really gitignored in the gated tree
PASS 5d precondition: the per-job gate forgives the artifact (pass)
FAIL a declared, gitignored toolchain artifact ⇒ PASS at the run-wide gate (direct job, honest receipt)
52 passed, 1 failed
== MUTATION: merged gate with only the --toolchain-artifact threading removed in run_scope_check
0
rc=1
FAIL a declared, gitignored toolchain artifact ⇒ PASS at the run-wide gate (direct job, honest receipt)
52 passed, 1 failed
== REVERT resolve-model only
FAIL no --config, from the root ⇒ the project's models (opus), not the built-in sonnet
FAIL no --config, from a subdirectory ⇒ still the toplevel's models (opus)
FAIL no --config, --repo-dir names the project ⇒ its models (opus)
FAIL from a subdirectory the effort cap comes from the same root as the models
PASS an explicit --config is still the config read
PASS a project with no .claude/compound-v.json ⇒ the built-in table (sonnet)
PASS --explicit-model outside git ⇒ succeeds
FAIL outside git with neither --config nor --repo-dir ⇒ exits non-zero
3 passed, 5 failed
rc=1
== in-process API unchanged: resolve()/load_config_models signatures and bodies vs pre-change
no def line of resolve/load_config_models/default_settings_paths/apply_effort_cap changed
5:@@ -11,11 +11,22 @@ (module docstring)
29:@@ -44,8 +55,8 @@ (usage examples)
40:@@ -529,7 +540,15 @@ def main(argv):
57:@@ -539,9 +558,12 @@ def main(argv):
73:@@ -549,8 +571,29 @@ def main(argv):
104:@@ -568,13 +611,32 @@ def main(argv):
== probes: --explicit-model outside git, no flags outside git, --repo-dir on a non-git dir
{"backend": "claude", "tier": "deep", "model": "opus", "effort": "high", "effort_capped": null}
rc=0
{"error": "cannot locate the project config: …/scratchpad/ac1/nogit is not inside a git repository; pass --repo <project-root> (or pass --config, --repo-dir or --explicit-model)"}
rc=2
{"backend": "claude", "tier": "standard", "model": "sonnet", "effort": "medium", "effort_capped": null}
rc=0
```

The gate row's companion ("…with the glob removed from the manifest the same tree is still caught") passes on both
the merged and the reverted gate, as it should: the old gate always caught the file. The `0` after the mutation
heading is the count of `"--toolchain-artifact", glob` left in the mutated copy, proving the mutation applied.

**AC-1: met.**

### AC-2 — full suite, `lint-frontmatter.py .` and `shellcheck` green

Script `ac2.sh` (scratchpad), on the merged tree: the manifest's `full_command` verbatim, `lint-frontmatter.py .`,
`shellcheck` over every tracked `*.sh`, then `git status --porcelain`.

```text
HEAD: e0e392eadca13d615ec5d7032d7e53e8d6ea1c70
== full_command (manifest test_contract.full_command)
all-tests-ok
full_command rc=0
== lint-frontmatter
✅ All frontmatter clean
lint rc=0
== shellcheck (every tracked .sh)
… (tail) SC2164 warning, tests/test-session-banner-staleness.sh SC2015 info, tests/test-transcript-watch.sh SC2329 info …
shellcheck rc=1
      52
== git status --porcelain
 M .claude/agent-memory/superpowers-v-spec-reviewer/impacted-map-globs.md
 M docs/superpowers/execution/2026-10-08-gate-toolchain-and-model-config/lane-map.json
 M docs/superpowers/execution/2026-10-08-gate-toolchain-and-model-config/state.json
?? docs/superpowers/dogfood/2026-10-08-gate-toolchain-and-model-config-review.md
?? docs/superpowers/execution/2026-10-08-gate-toolchain-and-model-config/jobs/spec-review.baseline
?? docs/superpowers/execution/2026-10-08-gate-toolchain-and-model-config/jobs/spec-review.test-contract.json
?? docs/superpowers/execution/2026-10-08-gate-toolchain-and-model-config/preexisting/
== end
```

Shellcheck over all 52 tracked `.sh` files is wider than the project's own gate, so it was narrowed to what the
project defines as shellcheck green: the CI step `.github/workflows/validate.yml:227-230`
(`shellcheck hooks/*.sh scripts/compound-v-*.sh`), plus the two shell files this change touched:

```text
$ env bash -c 'cd <repo> && shellcheck hooks/*.sh scripts/compound-v-*.sh; echo "ci-scope rc=$?"; shellcheck tests/test-integration-gate.sh tests/test-resolve-model.sh; echo "changed-tests rc=$?"'
ci-scope rc=0

In tests/test-integration-gate.sh line 66:
cleanup() {
^-- SC2329 (info): This function is never invoked. Check usage (or ignored if invoked indirectly).

In tests/test-integration-gate.sh line 616:
      "$([ "$?" = 0 ] && echo 1 || echo 0)"
           ^--^ SC2181 (style): Check exit code directly with e.g. 'if mycmd;', not indirectly with $?.
changed-tests rc=1
```

Attribution: the CI shellcheck scope is green. `tests/test-resolve-model.sh` (new) is clean. Both findings in
`tests/test-integration-gate.sh` are on lines this change did not write — the diff touches only `literal_digest`
(`:167-176`) and adds section 5d (`:413-496`); `:66` sits above both and `:616` is the pre-existing section-6 line
(pre-change `:531`) pushed down by the insertion. The whole-tree red comes from files this diff does not touch
(`tests/test-session-banner-staleness.sh`, `tests/test-transcript-watch.sh`, and others; the diff's only `.sh` files are
the two tests above), so it predates the run. The `git status` lines are this review's own lane (review file, memory)
and the run's bookkeeping; the suite left nothing behind.

**AC-2: met** (full suite `all-tests-ok`, lint clean, shellcheck green at the project's CI scope; the pre-existing
info/style findings outside CI's scope are recorded, not attributed to this run).

**Feature acceptance criteria.**

| Criterion | Evidence | Status |
|---|---|---|
| AC-1 The gate row and the resolve-model rows pass and each fails when its change is reverted | `ac1.sh`: merged 53/0 and 8/0; old gate 52/1; threading-only mutation 52/1; old resolver 3/5 | met |
| AC-2 Full suite, `lint-frontmatter.py .` and `shellcheck` green | `ac2.sh` + CI-scope shellcheck above | met |

## Verdict

**APPROVED**

- PASS 1 SPEC: requirements 15/15 (spec changes 1-2 as amended by 1-7, plus job acceptance) · one reader, no copy ·
  over-build clean · scope lock respected (10/10 paths in `write_allowed`, gate receipt `pass`).
- PASS 2 QUALITY: code quality clean · no regression (full suite green) · every code MUST has a row that fails on
  revert (proven by revert and mutation) · no fabricated metrics · no reward-hacking.
- PASS 3 INTEGRATION: no partition leak · seams hold (shared reader reached by explicit path from emitter and gate) ·
  FULL tier owed floor ∪ impacted ∪ `full_command`, all four ran, `tests.exit_code: 0` · AC-1 and AC-2 met.

Non-blocking observations (no fix required for DONE):

1. The manifest's `impacted_map` rule `when: '*.md'` matched none of the 4 nested Markdown paths, so
   `lint-frontmatter.py .` never ran inside the job; it ran here and is clean. `**/*.md` would make the rule fire.
2. `tests/test-integration-gate.sh:66` (SC2329 info) and `:616` (SC2181 style) are pre-existing shellcheck findings
   outside CI's shellcheck scope.
3. `--repo-dir` naming an existing non-git directory resolves to the built-in table (rc 0) rather than failing closed.
   This matches spec Change 2 and ADR 0005 (an explicit root wins), but no test row pins it.
