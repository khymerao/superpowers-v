# Task A — secret-bearing files leave the detect_ui sample

Compound V run `2026-10-05-jev-review-fixes`, job `ui-sample`.

Implement Task A of docs/superpowers/plans/2026-10-05-jev-review-fixes.md, every step in order. Read the spec docs/superpowers/specs/2026-10-05-jev-review-fixes-design.md first; its Pre-flight amendments section overrides the sections above it, and the three audits named in this manifest bind. Tests first: write the selftest rows, run and see them fail, then implement, then prove the revert. Touch only your lane. Run python with -B; register your lane with a literal --cwd. You are unattended: decide and return; if you approach your turn budget, commit what is complete and return a summary that says what is not.

## You are unattended

No one reads this session while it runs and no one will answer a question:
a turn that ends by asking for confirmation, approval or a preference does
NOTHING, and the job is then recorded as an absent implementation. Decide
with the spec, the plan and this prompt; when they are silent, choose the
smallest change that meets the acceptance, do it, run the checks, and return.

## Write-allowed (your lane — anything else is a scope violation)

- `scripts/compound-v-onboard.py`
- `skills/compound-v/onboarding.md`

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

- `_secret_named(path) -> bool` (pure, name only, case-insensitive) and `_has_credential_assignment(text) -> bool` in scripts/compound-v-onboard.py; `_ui_sample(repo)` keeps its signature and return shape.

## Read-allowed (advisory — git cannot enforce reads)

- `**`

## Acceptance (your definition of done)

- onboard --selftest green with the new rows (secret-named files skipped on the git and os.walk paths, credential-assignment rule, request holds lib/math.php and no planted value); each row fails with the predicates stubbed to False; onboarding.md:78-79 lists the rules and states the residual; lint-frontmatter clean.

Turn cap: 80 (default for tier deep; default light 30 / standard 50 / deep 80). Plan to finish inside it.

## What you must NOT report

Do not report `blocked`, `files_changed` or `violations`. Those are
enforcement fields, they are derived from git by the caller, and a
constrained party filling in its own enforcement fields is the
fabricated-evidence pattern.
