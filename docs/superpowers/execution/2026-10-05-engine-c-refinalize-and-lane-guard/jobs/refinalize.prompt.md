# Task A — idempotent re-finalize of an integrated wave

Compound V run `2026-10-05-engine-c-refinalize-and-lane-guard`, job `refinalize`.

Implement Task A of docs/superpowers/plans/2026-10-05-engine-c-refinalize-and-lane-guard.md, every step in order. Read the spec docs/superpowers/specs/2026-10-05-engine-c-refinalize-and-lane-guard-design.md first; its Pre-flight amendments section overrides the sections above it, and the three audits named in this manifest bind. Tests first: write the rows, run and see them fail, then implement, then prove the revert. Touch only your lane. Run python with -B; register your lane with a literal --cwd. You are unattended: decide and return; if you approach your turn budget, commit what is complete and return a summary that says what is not.

## You are unattended

No one reads this session while it runs and no one will answer a question:
a turn that ends by asking for confirmation, approval or a preference does
NOTHING, and the job is then recorded as an absent implementation. Decide
with the spec, the plan and this prompt; when they are silent, choose the
smallest change that meets the acceptance, do it, run the checks, and return.

## Write-allowed (your lane — anything else is a scope violation)

- `scripts/compound-v-emit-workflow.py`
- `scripts/compound-v-scope-check.py`

## Global constraints (binding on every job)

Project-wide, and binding on EVERY job in this run including yours.
Copied verbatim from the plan — do not reinterpret, relax or widen
them.

- Python 3.9 syntax, stdlib only; no `match`; no `X | Y` annotations or `isinstance(x, A | B)`.
- The hook stays filesystem-only on its resolution path: no `git` subprocess.
- Every behavioural change ships a test row that fails when the change is reverted.
- The short-circuit merges nothing and writes nothing; it never weakens what the authority decides for a wave it runs on.
- No fabricated metrics; no timing numbers in docs; no cost or savings text.
- Docs: plain words, every claim true of HEAD, no line over 200 characters outside code/tables.
- Lane discipline: touch only your `write_allowed`; `register-lane` first, with a literal `--cwd`. Run python with `-B`.
- Not in any implementation job: version bump, CHANGELOG, `plugin.json`, `marketplace.json`.
- Commit subjects are plain sentences, no `feat:`/`fix:`; no Co-Authored-By trailer.

## Interfaces (your only view of the neighbours)

You see only your own job. This block is the ONLY view you get of the
names and signatures neighbouring jobs rely on — implement exactly
these, and do not rename or re-shape them.

produces (what later jobs will call):

- `_wave_commit_subject(wave, run_id, merged) -> str` and `_already_integrated_wave(run_dir, repo_root, wave, job_ids)` (dict or None) in scripts/compound-v-emit-workflow.py; `lane-guard-unresolved.jsonl` in RUN_DIR_EXEMPT_BY_NAME.

## Read-allowed (advisory — git cannot enforce reads)

- `**`

## Acceptance (your definition of done)

- the scope-check.py docstring list of RUN_DIR_EXEMPT_BY_NAME entries (around its lines 47 and 353) names lane-guard-unresolved.jsonl, docstring only; emit-workflow --selftest green with rows A-E and the exempt row; row A fails with the short-circuit call removed and the exempt row fails with the entry removed; AC-4 run on a full-depth scratch clone exits 0 with state.json unchanged, output quoted in the summary.

Turn cap: 80 (default for tier deep; default light 30 / standard 50 / deep 80). Plan to finish inside it.

## What you must NOT report

Do not report `blocked`, `files_changed` or `violations`. Those are
enforcement fields, they are derived from git by the caller, and a
constrained party filling in its own enforcement fields is the
fabricated-evidence pattern.
