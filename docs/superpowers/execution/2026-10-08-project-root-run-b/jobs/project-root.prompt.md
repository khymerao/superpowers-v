# Task A — one project-root helper, triage-outcomes without __file__, one stream path, hooks walk up

Compound V run `2026-10-08-project-root-run-b`, job `project-root`.

Implement Task A of docs/superpowers/plans/2026-10-08-project-root-run-b.md, every step in order (A1..A6). Read the spec docs/superpowers/specs/2026-10-08-project-root-run-b-design.md, ADR docs/superpowers/adr/0005-one-rule-per-root.md and the archaeology audit (section 1c rows 15-28, section 7 constraints 9-15) first. Tests first. Touch only your lane. Run python with -B; register your lane with a literal --cwd. You are unattended: decide and return.

## You are unattended

No one reads this session while it runs and no one will answer a question:
a turn that ends by asking for confirmation, approval or a preference does
NOTHING, and the job is then recorded as an absent implementation. Decide
with the spec, the plan and this prompt; when they are silent, choose the
smallest change that meets the acceptance, do it, run the checks, and return.

## Write-allowed (your lane — anything else is a scope violation)

- `scripts/compound-v-project-config.py`
- `scripts/compound-v-triage-outcomes.py`
- `scripts/compound-v-preeval.py`
- `scripts/compound-v-fastpath-materialize.py`
- `scripts/compound-v-validate-manifest.py`
- `hooks/precompact-snapshot.sh`
- `hooks/run-band.tsx`
- `hooks/run-band.test.tsx`
- `hooks/brainstorm-trigger0-nudge.sh`
- `commands/v-orchestrate.md`
- `commands/v-collect.md`
- `commands/v-dispatch.md`
- `commands/v-status.md`
- `agents/parallel-dispatcher.md`
- `tests/test-project-root.sh`
- `tests/test-native-points.sh`
- `tests/test-skill-nudges.sh`

## Global constraints (binding on every job)

Project-wide, and binding on EVERY job in this run including yours.
Copied verbatim from the plan — do not reinterpret, relax or widen
them.

- Python 3.9 stdlib only; no `match`, no `X | Y` annotations. Every fix ships a test row that fails when reverted.
- `resolve_project_root(repo=None, start=None)` lives in `scripts/compound-v-project-config.py`: explicit `repo` (real path, a directory) wins; else `git -C <start> rev-parse --show-toplevel`, real path; outside git `ValueError` with a message. Never `__file__`, never the current directory as a guess.
- `scripts/compound-v-triage-outcomes.py`: `_repo_root()` removed; every former use takes the helper; CLI gains `--repo`; outside git with no `--repo` and no `--stream` it exits non-zero and writes nothing. `STREAM_RELPATH` is the only definition of the stream path; `compound-v-preeval.py` and `compound-v-fastpath-materialize.py` load and use it (selftest literals only where they assert its value).
- `compound-v-validate-manifest.py` `_find_repo_root` returns `None` instead of `os.getcwd()`; each caller handles `None` explicitly (fail closed where a root is required).
- `hooks/precompact-snapshot.sh`, `hooks/run-band.tsx` and `hooks/brainstorm-trigger0-nudge.sh` walk up to the nearest `.git` (dir or file) like `hooks/postcompact-resume.sh:85`, same bound, same not-found result; precompact and postcompact snapshot keys agree for a subdirectory cwd. Hook output and fail-silent behaviour otherwise unchanged.
- Command prose that calls triage-outcomes without `--stream` changes only if it runs from somewhere other than the project root (read each; edit only those).
- `compound-v-jev.py`, `compound-v-memory.py`, `hooks/lane-guard.sh`, `evals/` are not touched; the review record justifies in writing what stays (spec item 7).
- No version bump, CHANGELOG or release. Commit subjects are plain sentences, no Co-Authored-By trailer.

## Read-allowed (advisory — git cannot enforce reads)

- `**`

## Acceptance (your definition of done)

- All spec tests pass and each fails on revert; the five selftests, test-native-points, test-skill-nudges, test-run-band-mod, test-disabled-hooks, test-hook-recursion-guard, lint-frontmatter and shellcheck green.

Turn cap: 80 (default for tier deep; default light 30 / standard 50 / deep 80). Plan to finish inside it.

## What you must NOT report

Do not report `blocked`, `files_changed` or `violations`. Those are
enforcement fields, they are derived from git by the caller, and a
constrained party filling in its own enforcement fields is the
fabricated-evidence pattern.
