# Task A — gate toolchain_artifacts via the scope-check reader; resolve-model project config default

Compound V run `2026-10-08-gate-toolchain-and-model-config`, job `gate-model`.

Implement Task A of docs/superpowers/plans/2026-10-08-gate-toolchain-and-model-config.md (A1..A6). Read the spec docs/superpowers/specs/2026-10-08-gate-toolchain-and-model-config-design.md and its Pre-flight amendments, and both audits (section 7) first. Tests first. Touch only your lane. Run python with -B; register your lane with a literal --cwd. You are unattended: decide and return.

## You are unattended

No one reads this session while it runs and no one will answer a question:
a turn that ends by asking for confirmation, approval or a preference does
NOTHING, and the job is then recorded as an absent implementation. Decide
with the spec, the plan and this prompt; when they are silent, choose the
smallest change that meets the acceptance, do it, run the checks, and return.

## Write-allowed (your lane — anything else is a scope violation)

- `scripts/compound-v-scope-check.py`
- `scripts/compound-v-integration-gate.py`
- `scripts/compound-v-emit-workflow.py`
- `scripts/compound-v-resolve-model.py`
- `tests/test-integration-gate.sh`
- `tests/test-resolve-model.sh`
- `agents/parallel-dispatcher.md`
- `skills/compound-v/phase-3-parallel-opus-dispatch.md`
- `skills/compound-v/routing-policy.md`
- `skills/compound-v/execution-manifest.md`

## Global constraints (binding on every job)

Project-wide, and binding on EVERY job in this run including yours.
Copied verbatim from the plan — do not reinterpret, relax or widen
them.

- Python 3.9 stdlib only. Every fix ships a test row that fails when reverted.
- The `toolchain_artifacts` reader lives once, in `scripts/compound-v-scope-check.py`; the emitter and the gate call it; no copy. The gate passes each glob as `--toolchain-artifact` in `run_scope_check`.
- Claims are limited to `contradicted` and false `blocked`; `.DS_Store`-style files stay violations unless declared.
- The gate test uses a direct job, a really gitignored file and a receipt made with `--toolchain-artifact`.
- resolve-model: the new default lives in `main()` only; one root for models and the effort cap; fail closed outside git, except `--explicit-model`. `resolve()` and `load_config_models` are unchanged for in-process callers.
- `resolve_job_model` in the emitter and `agents/parallel-dispatcher.md:150` pass `--repo-dir`.
- The five docs named in spec amendment 6 are updated in the same change.
- No version bump, CHANGELOG or release. Commit subjects are plain sentences, no Co-Authored-By trailer.

## Read-allowed (advisory — git cannot enforce reads)

- `**`

## Acceptance (your definition of done)

- Gate and resolve-model rows pass and fail on revert; the four selftests, test-integration-gate, test-engine-c-contract and lint green; docs updated.

Turn cap: 80 (default for tier deep; default light 30 / standard 50 / deep 80). Plan to finish inside it.

## What you must NOT report

Do not report `blocked`, `files_changed` or `violations`. Those are
enforcement fields, they are derived from git by the caller, and a
constrained party filling in its own enforcement fields is the
fabricated-evidence pattern.
