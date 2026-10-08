# Review Gate — three passes against the spec (amendments first) and AC-1..AC-4

Compound V run `2026-10-05-engine-c-refinalize-and-lane-guard`, job `spec-review`.

Your agent definition carries the three-pass Review Gate and a Step 0 (V-memory recall). Follow it within a HARD BUDGET of 50 tool calls; FIRST action after Step 0: create docs/superpowers/dogfood/2026-10-05-engine-c-refinalize-and-lane-guard-review.md with the section skeleton and fill it as you verify. Review the two implementation jobs against docs/superpowers/specs/2026-10-05-engine-c-refinalize-and-lane-guard-design.md (its Pre-flight amendments section overrides earlier sections) and the plan's Task R. Pay particular attention to whether the lane-guard change can ever weaken enforcement for a registered job. Your memory directory is .claude/agent-memory/superpowers-v-spec-reviewer/. Run python with -B; register your lane with a literal --cwd. You are unattended: decide and return.

Prerequisites, already merged and COMMITTED into your base before this worktree was created: refinalize, lane-boundary.

## You are unattended

No one reads this session while it runs and no one will answer a question:
a turn that ends by asking for confirmation, approval or a preference does
NOTHING, and the job is then recorded as an absent implementation. Decide
with the spec, the plan and this prompt; when they are silent, choose the
smallest change that meets the acceptance, do it, run the checks, and return.

## Write-allowed (your lane — anything else is a scope violation)

- `docs/superpowers/dogfood/2026-10-05-engine-c-refinalize-and-lane-guard-review.md`
- `.claude/agent-memory/superpowers-v-spec-reviewer/**`

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

## Read-allowed (advisory — git cannot enforce reads)

- `**`

## Acceptance (your definition of done)

- The review file exists with ## Recall, ## SPEC, ## QUALITY, ## INTEGRATION, ## Verdict; each acceptance criterion is run on the merged tree with its command and output quoted, including AC-4 on a full-depth scratch clone and revert proofs for row A and the nested-worktree row; verdict APPROVED or ISSUES with a numbered list.

Turn cap: 80 (default for tier deep; default light 30 / standard 50 / deep 80). Plan to finish inside it.

## What you must NOT report

Do not report `blocked`, `files_changed` or `violations`. Those are
enforcement fields, they are derived from git by the caller, and a
constrained party filling in its own enforcement fields is the
fabricated-evidence pattern.
