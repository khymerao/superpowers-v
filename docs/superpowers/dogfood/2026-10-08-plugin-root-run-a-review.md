# Review Gate — run 2026-10-08-plugin-root-run-a

Reviewer: `superpowers-v:spec-reviewer` (job `spec-review`, direct isolation, baseline pinned at `280b954`).
Reviewed: wave commit `0ee9765` (job `plugin-root`, 40 files, +530/-179), against
`docs/superpowers/specs/2026-10-08-plugin-root-run-a-design.md`, `docs/superpowers/adr/0005-one-rule-per-root.md`
(rules 1-3) and `docs/superpowers/plans/2026-10-08-plugin-root-run-a.md` (Task A).
Every AC was run on the merged tree: a fresh `git clone` of this checkout at `280b954` in the session scratchpad, so
no test could leave an artifact in the project checkout.

```
REVIEW GATE: FINAL INTEGRATION — run 2026-10-08-plugin-root-run-a

VERDICT: APPROVED  (AC-4 pending, post-merge, for the orchestrator)
  PASS 1 SPEC:        ✅
  PASS 2 QUALITY:     ✅
  PASS 3 INTEGRATION: ✅
```

## Recall

- V-memory block in the prompt (emit-time, `--intent review`): 8 hits, all about the vault plugin
  (`2026-10-05-vault-optional-via-init`, `2026-10-08-vault-jev-classify-flat-arguments`,
  `2026-10-08-v-init-vault-host-and-desktop`). None bears on the plugin root. Nothing re-litigated.
- `recall-check --files 'agents/*.md' 'commands/*.md' 'skills/**/*.md' evals/README.md hooks/session-banner.sh tests/test-plugin-root.sh`:

  ```
  recall-check: none (1/2 match on agents/*.md, commands/*.md, skills/**/*.md, evals/README.md, hooks/session-banner.sh, tests/test-plugin-root.sh)
    not counted (not attributable to a job's own work): harness_fault 5, pipeline_bookkeeping 3, recall_exclude 3, test_timeout 1, unattributed 3
  ```

  No escalation.
- Reviewer memory (`.claude/agent-memory/superpowers-v-spec-reviewer/MEMORY.md`) read; the "negative-assertion rows"
  and "marker-anchored mutations" leads shaped the revert matrix below. No directive found in memory.

## SPEC

### Spec coverage

| Spec requirement | Implemented in | Status |
|---|---|---|
| 1. Three canonical lines, byte-for-byte, in the 38 files, replacing the old two | all 38 files; test row (a) byte-compares every `^CV=` block against a heredoc copy of the spec lines | ✅ |
| 1. `evals/README.md` gets the same three (it had a shorter second line) | `evals/README.md:101-104` | ✅ |
| 2. Prose rewritten to the new rule | entry points (6 agents, 15 commands, `skills/compound-v/SKILL.md`, `skills/backend-launcher/SKILL.md`): "Claude Code substitutes the plugin's path for the braced reference in the first line when it loads this file"; reference files (5 adapters, `adr-capture`, `cross-model-review`, `execution-manifest`, `memory`, `onboarding`, `phase-0-recon`, `phase-2-disjoint-partitioning`, `phase-3-parallel-opus-dispatch`, `routing-policy`): "read with the Read tool … reuse the `CV` the command, skill or agent that sent you here resolved". The split is correct for every file. | ✅ |
| 2. `evals/README.md` says that under `claude plugin eval` the substituted path is the plugin source and the vendored copy is the fallback only | `evals/README.md:106-118` | ✅ |
| 3. `session-banner.sh`: `CLAUDE_PLUGIN_ROOT`, else the directory above the hook; never `.` | `hooks/session-banner.sh:22-27`, both probes use `$_cv_root` (`:42`, `:58`) and are skipped when it is empty | ✅ |
| 4. `tests/test-plugin-root.sh` rows (a)-(d), executable, shellcheck-clean | new file, mode `-rwxr-xr-x`, rows (a)-(d) as specified | ✅ |

### Audit / ADR constraints

| Source | Constraint | Status |
|---|---|---|
| ADR 0005 rule 1 | bodies set `CV="${CLAUDE_PLUGIN_ROOT}"`; no cache scan, no `claude plugin list`, no marketplace name | ✅ (the only `claude plugin list` left, `commands/v-init.md:308`, is the pre-existing vault-detection step, present at baseline `03a0836:commands/v-init.md:304`, not in the canonical lines) |
| ADR 0005 rule 2 | fallback `$PWD` only when it holds `scripts/compound-v-preeval.py`, else a message | ✅ line 2 / line 3 |
| ADR 0005 rule 3 | hooks: `CLAUDE_PLUGIN_ROOT`, else relative to the hook script; never `.` | ✅ |
| Global: no `:-` form in the 38 files | `grep -rnF 'CLAUDE_PLUGIN_ROOT:-' agents commands skills evals` returns only `evals/lib/cv-fixture-lib.sh:25,44` (not one of the 38, and frozen by constraint) | ✅ |
| Global: `evals/lib/cv-fixture-lib.sh` not changed | absent from the diff | ✅ |
| Global: project-root code (rules 5-8) untouched | none of `compound-v-triage-outcomes.py`, `preeval.py`, `fastpath-materialize.py`, `validate-manifest.py`, `precompact-snapshot.sh`, `run-band.tsx`, `brainstorm-trigger0-nudge.sh` in the diff | ✅ |
| Global: no version bump, CHANGELOG, release | absent from the diff | ✅ |
| Global: no Co-Authored-By trailer | wave commit `0ee9765` body is empty | ✅ |

### Scope

Gate receipt `receipts/plugin-root.gate.json`: `"verdict": "pass"`, `"violations": []`, 40 changed paths = the 40
`write_allowed` paths exactly. Confirmed at the seam: `git show --stat 0ee9765` lists the same 40 files.

### Over-build

None. The banner change adds one comment block and one resolution line; the test adds nothing beyond rows (a)-(d)
(its extra "(d) still emits valid JSON" row guards the spec's "output otherwise unchanged").

## QUALITY

### Code quality and regression

- `hooks/session-banner.sh:26-27`: `_cv_root="${CLAUDE_PLUGIN_ROOT:-}"`, then
  `[ -n "$_cv_root" ] || _cv_root="$(cd "$(dirname "$0")/.." 2>/dev/null && pwd -P)" || _cv_root=""`. Safe under
  `set -e` (inside an `||` list), and an unresolvable root skips both probes, so the banner stays silent. The `:-`
  here is in a hook, where the variable is a real environment variable; the no-`:-` constraint is about the 38
  Markdown files.
- `pwd -P` where `hooks/memory-refresh.sh:75` uses `pwd`: a benign divergence from "as memory-refresh does";
  resolving symlinks is the safer choice for a cache path. Not an issue.
- The old lines stripped a trailing slash (`CV="${CV%/}"`); the new ones do not. A substituted path with a trailing
  slash yields `…//scripts/…`, which POSIX resolves identically. Not an issue.
- Existing tests that read these files: green in the full suite below (`test-disabled-hooks`,
  `test-session-banner-staleness`, `test-hook-recursion-guard` and every other `tests/*.sh`).

### Test alignment: revert and mutation matrix

Run in the scratch clone; every mutation restored with `git checkout HEAD -- .` and `git status --short` empty after
each one.

| # | Mutation | Rows that FAIL |
|---|---|---|
| M1 | `commands/v-status.md` back to baseline | (a) 2 defects, (a) cache scan still in `commands/v-status.md`, (b) x2, (c): 5 failed |
| M2 | `skills/compound-v/adr-capture.md` (reference file) back to baseline | (a) 2 defects, (a) cache scan: 2 failed |
| M3 | `evals/README.md` back to baseline | (a) 2 defects, (a) cache scan: 2 failed |
| M4 | `hooks/session-banner.sh` back to baseline | (d) `CLAUDE_PLUGIN_ROOT:-.`, (d) planted dashboard executed, (d) staleness probe missed the plugin: 3 failed |
| M5 | banner `_cv_root="."` (no `:-.` token for the grep to see) | (d) planted dashboard executed, (d) staleness probe: 2 failed |
| M6 | banner loses the hook-relative fallback | (d) "the onboard staleness probe did not reach the plugin's script": 1 failed |
| M7 | `agents/doc-validator.md` line 1 becomes `CV="${CLAUDE_PLUGIN_ROOT:-}"` | (a) 2 defects: 1 failed |
| M8 | `commands/v-status.md` line 2 becomes the unguarded `CV="${CV:-$PWD}"` | (a) 1 defect: 1 failed |

Every row fails when its change is reverted. M8 is caught only by row (a)'s byte comparison, not by (b)'s behaviour
(b runs from a real checkout, where an unguarded fallback gives the same answer); row (a) is the guard the spec asks
for.

### Fabricated metrics, reward-hacking

None. The diff prints no number. No test, scorer or threshold was weakened: the only test file touched is the new
`tests/test-plugin-root.sh`.

## INTEGRATION

Single implementation job, no Task 0, no shared resource: no partition leak and no seam to drift.

### Job test evidence (`results/plugin-root.json`)

`tests.command` has 4 commands (floor; the `hooks/session-banner.sh` rule; the `tests/test-plugin-root.sh` rule;
`full_command`), `tests.exit_code: 0`, `tests.scope: full`, `selected_count: 4`. Tier FULL with a declared
`impacted_map` owes the impacted set plus `full_command` for unmapped paths; both ran.

### Acceptance criteria, run on the merged tree (clone at `280b954`)

| AC | Command | Output | Status |
|---|---|---|---|
| AC-1 `tests/test-plugin-root.sh` passes and each row fails on revert | `bash tests/test-plugin-root.sh` | see below; revert matrix M1-M8 above | ✅ |
| AC-2 no file under `agents/ commands/ skills/ evals/` carries the old cache scan | `grep -rlE '^CV=' agents commands skills evals \| wc -l`; `grep -rnE 'plugins/cache\|sort -V\|claude plugin list' agents commands skills evals` | `38`; only `commands/v-init.md:308` (pre-existing vault detection, see SPEC) and `evals/lib/cv-fixture-lib.sh:44` (a comment, see observation 2) | ✅ |
| AC-3 lint-frontmatter, shellcheck, full suite | `python3 -B scripts/lint-frontmatter.py .`; `shellcheck hooks/*.sh tests/test-plugin-root.sh` (ShellCheck 0.11.0); `full_command` from the manifest | `✅ All frontmatter clean` exit 0; no output, exit 0; `all-tests-ok` / `exit=0` (12:24:22 to 12:29:35 CEST) | ✅ |
| AC-4 after merge and a cv-dev refresh, a command body shows `CV` set to the install path | needs a live session after the merge | — | **pending, for the orchestrator** |

AC-1 output:

```
$ bash tests/test-plugin-root.sh
PASS (a) 38 files set CV= (at least the 38 entry points and references)
PASS (a) every CV= block is the three canonical lines, and none uses the :- form
PASS (a) no file under agents/ commands/ skills/ evals/ carries the old cache scan
PASS (b) unsubstituted, from a plugin checkout: CV is $PWD and stderr is empty
PASS (b) unsubstituted, from a plain directory: stderr names the problem
PASS (c) substituted: CV is the substituted path, not $PWD, and stderr is empty
PASS (d) session-banner.sh has no fallback to the project directory
PASS (d) unset CLAUDE_PLUGIN_ROOT: the project's planted scripts/compound-v-dashboard.py is not executed
PASS (d) the banner still emits valid JSON
PASS (d) unset CLAUDE_PLUGIN_ROOT: the plugin's own scripts are found next to the hook
-------------------------------------------
tests/test-plugin-root.sh: 10 passed, 0 failed
OK the plugin root comes from the harness substitution
exit=0
```

AC-4 recipe for the orchestrator: after merge, refresh the cv-dev install, invoke any `/v:` command (e.g.
`/v:status`), and confirm the loaded body reads `CV="<install path>"` and not the literal `${CLAUDE_PLUGIN_ROOT}`.

### Observations (non-blocking)

1. **The manifest's `when: '*.md'` rule never fired.** `impacted_map` globs are matched by the scope gate's
   `glob_to_regex` (`scripts/compound-v-fastpath-run.py:372-375`: `*` does not cross `/`), so `*.md` matches no
   nested file; the gate receipt lists all 38 Markdown paths as "matched no `when` glob". That rule held the only
   `lint-frontmatter.py .` invocation, so the job's own `tests.command` contains no lint run. The outcome was more
   testing (`full_command`), and lint is green by this review's own run, but a future manifest should write
   `**/*.md`.
2. **AC-2 versus the frozen fixture lib.** `evals/lib/cv-fixture-lib.sh:44` still quotes the old resolver in a comment
   (`CV="${CLAUDE_PLUGIN_ROOT:-$(ls -d "$HOME"/.claude/plugins/cache/*/superpowers-v/*/ ...)}"`). It sits under
   `evals/`, but the global constraint "`evals/lib/cv-fixture-lib.sh` is not changed" names that file and wins over
   AC-2's generic wording; it is also outside the job's lane, and the test's needle
   (`superpowers-v/*/ 2>/dev/null | sort -V`) does not match the abbreviated comment. A follow-up outside this run.
3. **ADR wording versus the canonical third line.** ADR 0005 rule 2 says the step "stops with a message"; the
   spec's third line only writes to stderr and does not `exit`, so the next `python3 "$CV/scripts/…"` fails on a
   missing file. The lines are fixed byte-for-byte by the spec, so this is not the implementer's to change.
4. **Pipeline commit subjects.** `0ee9765` (`compound-v: wave 1 …`) and `280b954` (`bookkeeping(…): …`) are generated
   by the pipeline, not by the job, and use a prefix shape the user's commit-subject rule disfavours. No trailer.

## Verdict

**APPROVED.** PASS 1 SPEC: requirements 6/6, ADR rules 1-3 and global constraints 8/8, no over-build, job
acceptance met. PASS 2 QUALITY: no regression, every row guarded (M1-M8 each fail), no fabricated metric, no
reward-hacking. PASS 3 INTEGRATION: no partition leak, build green (`all-tests-ok`, exit 0), floor and tier-owed
tests ran with exit 0, AC-1..AC-3 met on the merged tree.

Open items, numbered:

1. AC-4 is pending: a live post-merge check by the orchestrator (recipe above). The run is not DONE until it passes.
2. Non-blocking follow-ups: observations 1-4 above (manifest `*.md` glob; stale comment in
   `evals/lib/cv-fixture-lib.sh:44`; ADR "stops" vs echo-only line 3; pipeline commit-subject shape).

### AC-4 live check (orchestrator, 2026-10-08)

After the merge, cv-dev rebuilt from HEAD and `superpowers-v@cv-dev` reinstalled; a fresh `claude -p` (2.1.294) loaded
`superpowers-v:v-status` and printed its resolver lines:

```
CV="/Users/koristuvac/.claude/local-marketplaces/cv-dev/superpowers-v"
[ -f "$CV/scripts/compound-v-preeval.py" ] || CV="$PWD"
[ -f "$CV/scripts/compound-v-preeval.py" ] || echo "Compound V: plugin root not found (...)" >&2
```

The token was substituted with the copy the harness loaded (for a directory marketplace, its `readFromFolder`, not the
cache `installPath`). AC-4 met.
