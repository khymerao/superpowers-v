# Review Gate — three passes against the spec (amendments first) and AC-1..AC-5

Compound V run `2026-10-05-jev-review-fixes`, job `spec-review`.

Your agent definition carries the three-pass Review Gate and a Step 0 (V-memory recall). Follow it within a HARD BUDGET of 50 tool calls; FIRST action after Step 0: create docs/superpowers/dogfood/2026-10-05-jev-review-fixes-review.md with the section skeleton and fill it as you verify. Review the two implementation jobs against docs/superpowers/specs/2026-10-05-jev-review-fixes-design.md (its Pre-flight amendments section overrides earlier sections) and the plan's Task R. Your memory directory is .claude/agent-memory/superpowers-v-spec-reviewer/. Run python with -B; register your lane with a literal --cwd. You are unattended: decide and return.

Prerequisites, already merged and COMMITTED into your base before this worktree was created: ui-sample, jev-reasons-prune.

## You are unattended

No one reads this session while it runs and no one will answer a question:
a turn that ends by asking for confirmation, approval or a preference does
NOTHING, and the job is then recorded as an absent implementation. Decide
with the spec, the plan and this prompt; when they are silent, choose the
smallest change that meets the acceptance, do it, run the checks, and return.

## Write-allowed (your lane — anything else is a scope violation)

- `docs/superpowers/dogfood/2026-10-05-jev-review-fixes-review.md`
- `.claude/agent-memory/superpowers-v-spec-reviewer/**`

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

## Read-allowed (advisory — git cannot enforce reads)

- `**`

## Acceptance (your definition of done)

- The review file exists with ## Recall, ## SPEC, ## QUALITY, ## INTEGRATION, ## Verdict; each acceptance criterion is run on the merged tree with its command and output quoted, including the parent review's original Issue 1 probe, a no_key response through parse, an empty git diff of vault.tsx and jev-t3.tsx against the run base, and the manifest full command; verdict APPROVED or ISSUES with a numbered list.

Turn cap: 80 (default for tier deep; default light 30 / standard 50 / deep 80). Plan to finish inside it.

## What you must NOT report

Do not report `blocked`, `files_changed` or `violations`. Those are
enforcement fields, they are derived from git by the caller, and a
constrained party filling in its own enforcement fields is the
fabricated-evidence pattern.
