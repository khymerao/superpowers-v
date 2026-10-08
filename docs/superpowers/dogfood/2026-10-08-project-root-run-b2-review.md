# Review Gate — run 2026-10-08-project-root-run-b2 (FINAL INTEGRATION)

Reviewer: `superpowers-v:spec-reviewer`, job `spec-review`, direct isolation, baseline pinned at
`0be448f`. Implementation under review: `eb7675f` (job `b2-fix`, gated from baseline `2faee4a`).
Spec: `docs/superpowers/specs/2026-10-08-project-root-run-b2-design.md`. Plan:
`docs/superpowers/plans/2026-10-08-project-root-run-b2.md`.

**VERDICT: APPROVED.** PASS 1 SPEC: passes. PASS 2 QUALITY: passes, with four low observations that
do not block. PASS 3 INTEGRATION: AC-1 to AC-3 pass on the merged tree. **Run B issue 1 is closed.**

## Recall

- The prompt included a `## Prior context` block, 8 hits. The relevant one is the run B review
  (`docs/superpowers/dogfood/2026-10-08-project-root-run-b-review.md`, `## Verdict`). Its issue 1 is
  the two `__file__` project roots this run fixes, and its issue 3 is the false validate-manifest note.
  Its AC-2 hit classification (lines 139-150) is the baseline for the AC-2 check below.
- `recall-check --files` over the four changed paths returned
  `recall-check: none (1/2 match ...)`. There is no repeated job-attributable failure, so nothing
  escalates.
- Reviewer memory lead `memory-frontmatter-and-universal-acs.md` #2 says to grep all of `scripts/`
  for a repo-wide AC and not to stop at the diff. I re-verified it and applied it below.
- No memory file contained a directive.

## SPEC

Diff `eb7675f` changes 4 files, all in `b2-fix`'s `write_allowed`. The gate receipt
(`receipts/b2-fix.gate.json`) shows `verdict: pass`, `violations: []`.

| Spec requirement | Implemented in | Status |
|---|---|---|
| 1. integration-gate without `--repo-root` takes the project root from `resolve_project_root` | `scripts/compound-v-integration-gate.py:1439-1452` (`_project_config(here).resolve_project_root()`) | met |
| 1. outside git with no flag: the gate's error JSON, exit 2 | `:1447-1452` prints `{"integration": "error", "error": ...}` to stderr and returns 2. This is the same shape as the `--run-dir` error at `:1433` | met |
| 1. explicit `--repo-root` path unchanged | `:1439-1440` `os.path.abspath(args.repo_root)`, the same as before | met (see note) |
| 2. update-memory's `_default_outcomes_path` uses `resolve_project_root`, with a `--repo` flag | `scripts/compound-v-update-memory.py:71-88`, `--repo` at `:268-269` | met |
| 2. outside git with no explicit path it fails closed with a message | `:292-297`. The `ValueError` from `resolve_project_root` is now inside the `try`, so it exits 1 with `error: ... is not inside a git repository` | met |
| 2. triage-outcomes' sibling import keeps working | The loader stays lazy inside `_default_outcomes_path`. triage-outcomes imports only `append_line` (`compound-v-triage-outcomes.py:176-180, 299`). `compound-v-triage-outcomes.py --selftest` returns `SELFTEST PASSED` | met |
| 3. the validate-manifest note is true with and without `fast_path` | `scripts/compound-v-validate-manifest.py:3386-3401`. It uses the same presence test as `validate_text` (`:2989`), and `_validate_fast_path` does fail closed with no root (`:1622`) | met |
| Tests: integration-gate, update-memory, validate-manifest rows and the AC-2 grep | `tests/test-project-root.sh` section 6 (12 new rows) | met |

**Note on item 1.** The spec text says the default becomes `resolve_project_root(args.repo_root)`.
That call would `realpath` an explicit flag. The implementer kept the explicit flag as `abspath` and
calls the resolver only on the default path, which follows the binding global constraint "explicit
`--repo-root` unchanged". The test row "an explicit --repo-root is used as given (abspath,
unchanged)" guards that choice. It is the correct reading, so I record it here and do not raise it
as an issue.

**Audit MUSTs.** The manifest lists the archaeology and library audits for the parent
plugin-root-resolver design. This run's binding constraints are the seven global constraints, and
all of them are met:

- stdlib only.
- One revert-failing row per fix.
- No second root helper and no change to `compound-v-project-config.py`, which is not in the diff.
- The integration-gate, update-memory and validate-manifest clauses (table above).
- No command prose changed. The diff touches no `commands/` or `skills/` file.
- No version bump or CHANGELOG. Commit `eb7675f` has no trailer.

**Over-build.** `--repo` on update-memory is permitted by the spec ("with a `--repo` flag if the
CLI lacks one"). `_project_config` (`integration-gate.py:1416-1426`) is a module loader, not a
second root helper. Nothing else was added. **Job acceptance**: rows pass and fail on revert, the
five selftests and the full suite are green, and the AC-2 grep is clean (below). Met.

## QUALITY

- **No regression.** The full suite is green on the merged tree (INTEGRATION, AC-3). Engine C's
  finalize-wave passes `--repo-root` explicitly (`scripts/compound-v-emit-workflow.py:6112-6114`), so
  it does not reach the changed default path. `/v:dispatch` (`commands/v-dispatch.md:253`) and
  `/v:collect` (`commands/v-collect.md:69`) call the gate without `--repo-root` and with a relative
  `--run-dir` from the project root. The new default resolves exactly that.
- **Test alignment.** Every changed behaviour has a row that fails on revert (AC-1).
- **Fabricated metrics.** None. The diff prints no number.
- **Reward-hacking.** None. The diff removes or loosens no assertion and skips no test. The only test
  file changed is append-only (82 lines added, 0 removed).

Observations (low, non-blocking, reported so the next round does not have to re-derive them):

1. **realpath/abspath asymmetry in integration-gate.** The default path now returns a `realpath`
   (`compound-v-project-config.py:150`), while an explicit `--repo-root` stays `abspath`
   (`integration-gate.py:1440`). The only path comparison downstream is the run-dir exclusion for a
   direct job (`:1114`, `relpath(abspath(run_dir), abspath(gate_root))`). If a caller passed an
   *absolute, symlinked* `--run-dir` (for example macOS `/var/...`) with no `--repo-root`, that
   relpath would start with `..`, and the bookkeeping exclusion would be skipped for a direct job with
   a receipt. This review did not exercise that case. The documented callers pass a relative run dir,
   and `os.getcwd()` is physical, so they are unaffected.
2. **Duplicate module loaders.** `_project_config` (`integration-gate.py:1416`) is the third inline
   `spec_from_file_location` loader in that file (`:338`, `:453`). update-memory has a fourth copy
   inline (`:82-86`) under a different module name. This is a nit.
3. **The manifest is parsed twice in validate-manifest.** On the no-root path, `main` now parses
   it at `:3392` and `validate_text` parses it again. The cost is negligible and the path is rare.
   This is a nit.
4. **The test-file AC-2 rows guard only the two fixed files** (`tests/test-project-root.sh`, the
   `AC-2:` rows). They do not cover all of `scripts/`. A repo-wide grep cannot tell a plugin root from
   a project root without an allowlist, so this narrowing is reasonable. The repo-wide check remains a
   review-time step (below).

## INTEGRATION

**Partition and seams.** There is one implement job, so no partition leak is possible. The gate
receipt shows `changed == allowed`, 4 paths. The only shared contract is `resolve_project_root`,
which both scripts load from the sibling file by path. Neither redefines it, and its file is unchanged.

**Tests the tier owed (derived, not taken from the worker).** Tier FULL, with an `impacted_map`
declared. The four changed paths each match a rule: three match `scripts/compound-v-*.py` and one
matches `tests/*.sh`. No path is unmapped. The job therefore owed the floor plus the union of the
matched rules. The `tests/*.sh` rule's command equals the floor, which is why `selected_count: 2`.
`full_command` was not owed by the job. `results/b2-fix.json` shows `tests.command` with both
commands, `tests.exit_code: 0`, `tests.scope: impacted`, and the gate receipt checks are both
`rc 0`. AC-3 independently requires the full suite, and I ran it (below).

**Acceptance criteria, each run on the merged tree (HEAD `0be448f`).**

| AC | Command | Output | Status |
|---|---|---|---|
| AC-1 rows pass | `bash tests/test-project-root.sh` | `test-project-root: 34 passed, 0 failed` (12:08:49 to 12:08:51 UTC) | met |
| AC-1 each fails on revert | Scratch worktree at `0be448f`. For each script: `git checkout 2faee4a -- <file>`, then `bash tests/test-project-root.sh`, then restore | integration-gate reverted: `31 passed, 3 failed` (`FAIL INTEGRATION-GATE: no --repo-root from a project subdirectory gates the project, not the plugin copy`; `FAIL INTEGRATION-GATE: outside git with no --repo-root exits 2 with the gate's error JSON`; `FAIL AC-2: integration-gate derives no project root from __file__ outside its selftest`). update-memory reverted: `28 passed, 6 failed` (all five `UPDATE-MEMORY:` rows plus `FAIL AC-2: update-memory ...`). validate-manifest reverted: `32 passed, 2 failed` (`FAIL VALIDATE: a fast_path manifest with no root does not claim root checks are skipped`; `FAIL VALIDATE: ... it says instead that the fast_path validation fails closed without a root`). Worktree clean after restore, then removed | met |
| AC-2 | `grep -nE 'dirname\(os\.path\.dirname\(os\.path\.abspath\(__file__\|dirname\(here\)\|dirname\(HERE\)\|os\.pardir\|, *"\.\."'` over **all of `scripts/`**, each hit classified | No hit in `compound-v-integration-gate.py` or `compound-v-update-memory.py`. Every remaining hit is one of the classes below. None is a project root outside a selftest | met |
| AC-3 full suite | `full_command` from the manifest | `all-tests-ok`, rc 0 (12:08:51 to 12:14:25 UTC) | met |
| AC-3 lint | `/usr/bin/python3 -B scripts/lint-frontmatter.py .` | `✅ All frontmatter clean`, rc 0 | met |
| AC-3 shellcheck | `shellcheck hooks/*.sh tests/test-project-root.sh` | no output, rc 0 | met |

How each AC-2 hit is classified. Line numbers in validate-manifest moved by 13 from run B's list:
`6085` is now `6098`, and `4191` is now `4204`.

- **`"."`/`".."` string and traversal checks, which do not derive a root:**
  `collect-results.py:82`, `triage-outcomes.py:613`, `epic-state.py:268`, `memory.py:1461`,
  `epic-arbiter.py:214, 815`, `validate-manifest.py:904, 1949`, `preeval.py:2749`.
- **Escape fixtures, which also do not derive a root:** `localize.py:961`,
  `validate-manifest.py:4293`.
- **Plugin resources (ADR 0005 rule 4):** `collect-results.py:515` and `taxonomy.py:1149` (schemas);
  `validate-manifest.py:1231, 1254` (schemas) and `:4204` (the plugin's example taxonomy);
  `emit-preflight.py:81` and `emit-workflow.py:937, 956` (`PLUGIN_ROOT`); `emit-workflow.py:8575`
  (schema); `emit-workflow.py:9718-9783` (plugin manifest probes); `emit-workflow.py:132` (a comment).
- **Selftest-only (ADR 0005 rule 6):** `validate-manifest.py:6098`, `taxonomy.py:1010`,
  `validate-taxonomy.py:579, 597`.
- **Project root outside a selftest:** none. Run B listed `integration-gate.py:1423-1424` and
  `update-memory.py:67-74` here, and both are gone. **Run B issue 1 (ACCEPTANCE_GAP on AC-2) is
  closed.** Run B issue 3 (the false note) is closed by spec item 3.

## Verdict

**APPROVED.**

- PASS 1 SPEC: requirements 8/8. Global constraints 7/7. No over-build. Job acceptance met.
- PASS 2 QUALITY: no regression, every change guarded by a test that fails on revert, no fabricated
  metrics, no reward-hacking. Four low observations are recorded under `## QUALITY`. None blocks.
- PASS 3 INTEGRATION: no partition leak and the seams hold. Engine C passes `--repo-root` explicitly.
  The floor and the tier-owed tests ran with exit 0 (`results/b2-fix.json`). The full suite, lint and
  shellcheck are green on the merged tree. Feature AC 3/3 met.
- Scope lock: respected (gate `pass`, confirmed at the seam).

Numbered issues: none.
