# Project Root Run B Implementation Plan

> **For agentic workers:** executed by Compound V on Engine C from one manifest
> (`docs/superpowers/execution/2026-10-08-project-root-run-b/manifest.yaml`). Steps use checkbox (`- [ ]`) syntax.

**Goal:** one project-root rule: an explicit `--repo`, else the git toplevel of the current directory, failing closed
outside git, never from `__file__`; one definition of the triage stream path; hooks walk up to `.git` alike.

**Architecture:** one implementation job (the helper, its four Python consumers and three hooks share one rule and one
test file), then a deep three-pass review.

**Spec:** `docs/superpowers/specs/2026-10-08-project-root-run-b-design.md`. **Decision:** `docs/superpowers/adr/0005-one-rule-per-root.md`.
**Audits:** `docs/superpowers/archaeology/2026-10-08-2026-10-08-plugin-root-resolver-design.md` (section 1c rows 15-28,
section 7 constraints 9-15), `docs/superpowers/library-audit/2026-10-08-2026-10-08-plugin-root-resolver-design.md`.

## Global Constraints

- Python 3.9 stdlib only; no `match`, no `X | Y` annotations. Every fix ships a test row that fails when reverted.
- `resolve_project_root(repo=None, start=None)` lives in `scripts/compound-v-project-config.py`: explicit `repo` (real
  path, a directory) wins; else `git -C <start> rev-parse --show-toplevel`, real path; outside git `ValueError` with a
  message. Never `__file__`, never the current directory as a guess.
- `scripts/compound-v-triage-outcomes.py`: `_repo_root()` removed; every former use takes the helper; CLI gains
  `--repo`; outside git with no `--repo` and no `--stream` it exits non-zero and writes nothing. `STREAM_RELPATH` is the
  only definition of the stream path; `compound-v-preeval.py` and `compound-v-fastpath-materialize.py` load and use it
  (selftest literals only where they assert its value).
- `compound-v-validate-manifest.py` `_find_repo_root` returns `None` instead of `os.getcwd()`; each caller handles
  `None` explicitly (fail closed where a root is required).
- `hooks/precompact-snapshot.sh`, `hooks/run-band.tsx` and `hooks/brainstorm-trigger0-nudge.sh` walk up to the nearest
  `.git` (dir or file) like `hooks/postcompact-resume.sh:85`, same bound, same not-found result; precompact and
  postcompact snapshot keys agree for a subdirectory cwd. Hook output and fail-silent behaviour otherwise unchanged.
- Command prose that calls triage-outcomes without `--stream` changes only if it runs from somewhere other than the
  project root (read each; edit only those).
- `compound-v-jev.py`, `compound-v-memory.py`, `hooks/lane-guard.sh`, `evals/` are not touched; the review record
  justifies in writing what stays (spec item 7).
- No version bump, CHANGELOG or release. Commit subjects are plain sentences, no Co-Authored-By trailer.

## Partition Map

| Job | Files (write) |
|---|---|
| `project-root` | `scripts/compound-v-project-config.py`, `scripts/compound-v-triage-outcomes.py`, `scripts/compound-v-preeval.py`, `scripts/compound-v-fastpath-materialize.py`, `scripts/compound-v-validate-manifest.py`, `hooks/precompact-snapshot.sh`, `hooks/run-band.tsx`, `hooks/run-band.test.tsx`, `hooks/brainstorm-trigger0-nudge.sh`, `commands/v-orchestrate.md`, `commands/v-collect.md`, `commands/v-dispatch.md`, `commands/v-status.md`, `agents/parallel-dispatcher.md`, `tests/test-project-root.sh`, `tests/test-native-points.sh`, `tests/test-skill-nudges.sh` |
| `spec-review` | `docs/superpowers/dogfood/2026-10-08-project-root-run-b-review.md`, `.claude/agent-memory/superpowers-v-spec-reviewer/**` |

No shared resources; no Task 0.

## Task A — project-root

- [ ] **A1 Tests first**, per the spec's Tests section; `tests/test-project-root.sh` is new, executable, shellcheck-clean.
- [ ] **A2 Watch them fail.**
- [ ] **A3 Implement** items 1-6 of the spec.
- [ ] **A4 Green.** Selftests of the five scripts, `tests/test-project-root.sh`, `tests/test-native-points.sh`,
  `tests/test-skill-nudges.sh`, `tests/test-run-band-mod.sh`, `tests/test-disabled-hooks.sh`,
  `tests/test-hook-recursion-guard.sh`, `lint-frontmatter.py .`, `shellcheck hooks/*.sh tests/test-project-root.sh`.
- [ ] **A5 Revert checks** per row; restore.
- [ ] **A6 Commit** on the job's lane.

## Review Gate — spec-review

Three passes against the spec's AC and ADR rules 5-8, each on the merged tree, plus the written justification of what
stays (spec item 7).
