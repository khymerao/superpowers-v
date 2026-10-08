# Fix — integration-gate and update-memory project root, validate-manifest note

Compound V run `2026-10-08-project-root-run-b2`, job `b2-fix`.

Implement docs/superpowers/plans/2026-10-08-project-root-run-b2.md Task A (A1..A6). Read the spec docs/superpowers/specs/2026-10-08-project-root-run-b2-design.md and the run B review docs/superpowers/dogfood/2026-10-08-project-root-run-b-review.md (Verdict issues 1 and 3) first. Tests first. Touch only your lane. Run python with -B; register your lane with a literal --cwd. You are unattended: decide and return.

## You are unattended

No one reads this session while it runs and no one will answer a question:
a turn that ends by asking for confirmation, approval or a preference does
NOTHING, and the job is then recorded as an absent implementation. Decide
with the spec, the plan and this prompt; when they are silent, choose the
smallest change that meets the acceptance, do it, run the checks, and return.

## Write-allowed (your lane — anything else is a scope violation)

- `scripts/compound-v-integration-gate.py`
- `scripts/compound-v-update-memory.py`
- `scripts/compound-v-validate-manifest.py`
- `tests/test-project-root.sh`

## Global constraints (binding on every job)

Project-wide, and binding on EVERY job in this run including yours.
Copied verbatim from the plan — do not reinterpret, relax or widen
them.

- Python 3.9 stdlib only. Every fix ships a test row that fails when reverted.
- Use the existing `resolve_project_root(repo=None, start=None)` in `scripts/compound-v-project-config.py`; do not add a second helper and do not change it.
- integration-gate: no `__file__`-derived repo root; explicit `--repo-root` unchanged (Engine C passes it); outside git with no flag: error JSON, exit 2.
- update-memory: no `__file__`-derived outcomes path; `compound-v-triage-outcomes.py`'s sibling import keeps working.
- validate-manifest: the note is true for manifests with and without a `fast_path` block.
- Command prose is not changed (its callers run from the project root).
- No version bump, CHANGELOG or release. Commit subjects are plain sentences, no Co-Authored-By trailer.

## Read-allowed (advisory — git cannot enforce reads)

- `**`

## Acceptance (your definition of done)

- The spec's rows pass and each fails on revert; the five selftests and the full suite green; AC-2 grep clean.

Turn cap: 80 (default for tier deep; default light 30 / standard 50 / deep 80). Plan to finish inside it.

## What you must NOT report

Do not report `blocked`, `files_changed` or `violations`. Those are
enforcement fields, they are derived from git by the caller, and a
constrained party filling in its own enforcement fields is the
fabricated-evidence pattern.
