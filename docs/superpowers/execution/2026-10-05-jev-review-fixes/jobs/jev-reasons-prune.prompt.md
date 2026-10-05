# Task B — no_key survives parse; stale descriptors are pruned

Compound V run `2026-10-05-jev-review-fixes`, job `jev-reasons-prune`.

Implement Task B of docs/superpowers/plans/2026-10-05-jev-review-fixes.md, every step in order. Read the spec docs/superpowers/specs/2026-10-05-jev-review-fixes-design.md first; its Pre-flight amendments section overrides the sections above it, and the three audits named in this manifest bind. Do not edit plugins/compound-v-vault/hooks/vault.tsx or hooks/jev-t3.tsx. Tests first: write the test rows, run and see them fail, then implement, then prove the revert. Touch only your lane. Run python with -B; register your lane with a literal --cwd. You are unattended: decide and return; if you approach your turn budget, commit what is complete and return a summary that says what is not.

## You are unattended

No one reads this session while it runs and no one will answer a question:
a turn that ends by asking for confirmation, approval or a preference does
NOTHING, and the job is then recorded as an absent implementation. Decide
with the spec, the plan and this prompt; when they are silent, choose the
smallest change that meets the acceptance, do it, run the checks, and return.

## Write-allowed (your lane — anything else is a scope violation)

- `scripts/compound-v-jev.py`
- `tests/test-jev-core.sh`
- `docs/superpowers/specs/2026-10-05-jev-classifier-foundation-design.md`

## Global constraints (binding on every job)

Project-wide, and binding on EVERY job in this run including yours.
Copied verbatim from the plan — do not reinterpret, relax or widen
them.

- Python 3.9 syntax, stdlib only; no `match`; no `X | Y` annotations.
- `plugins/compound-v-vault/hooks/vault.tsx` and `hooks/jev-t3.tsx` stay byte-identical to the run's base.
- Every behavioural change ships a selftest/test row that fails when the change is reverted.
- The sample rules only remove files from what is sent; nothing new is ever sent.
- No text claims "no secrets are sent"; the residual is stated.
- No fabricated metrics; no cost or savings text (anti-ruflo regex, `.github/workflows/validate.yml:194`).
- Docs: plain words, every claim true of HEAD, no line over 200 characters outside code/tables.
- Lane discipline: touch only your `write_allowed`; `register-lane` first, with a literal `--cwd`. Run python with `-B`.
- Commit subjects are plain sentences, no `feat:`/`fix:`; no Co-Authored-By trailer.

## Interfaces (your only view of the neighbours)

You see only your own job. This block is the ONLY view you get of the
names and signatures neighbouring jobs rely on — implement exactly
these, and do not rename or re-shape them.

produces (what later jobs will call):

- `UNAVAILABLE_REASONS` in scripts/compound-v-jev.py contains `no_key`; `prune(dd, now=None)` keeps its signature and also removes regular pending-*.json files older than the cutoff.

## Read-allowed (advisory — git cannot enforce reads)

- `**`

## Acceptance (your definition of done)

- compound-v-jev.py --selftest and tests/test-jev-core.sh green; the contract check extracts every unavailable/failed literal from vault.tsx (zero for either status fails), feeds each to parse without http_status and gets it back unchanged; it fails with no_key removed; prune rows (old removed, fresh/future/symlink kept) fail with the new block removed; parent spec lines 68-70 and 219 carry no_key and the 401/403 auth wording.

Turn cap: 80 (default for tier deep; default light 30 / standard 50 / deep 80). Plan to finish inside it.

## What you must NOT report

Do not report `blocked`, `files_changed` or `violations`. Those are
enforcement fields, they are derived from git by the caller, and a
constrained party filling in its own enforcement fields is the
fabricated-evidence pattern.
