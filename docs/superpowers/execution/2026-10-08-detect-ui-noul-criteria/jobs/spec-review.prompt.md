# Review Gate — deep, three passes against the spec and AC-1..AC-3

Compound V run `2026-10-08-detect-ui-noul-criteria`, job `spec-review`.

Your agent definition carries the three-pass Review Gate and a Step 0 (V-memory recall). HARD BUDGET of 30 tool calls; FIRST action after Step 0: create docs/superpowers/dogfood/2026-10-08-detect-ui-noul-criteria-review.md with the section skeleton. Review against docs/superpowers/specs/2026-10-08-detect-ui-noul-criteria-design.md and its amendments. AC-3 is post-merge; mark it pending for the orchestrator. Revert checks only in a scratch copy. Your memory directory is .claude/agent-memory/superpowers-v-spec-reviewer/; keep memory frontmatter valid YAML. Run python with -B; register your lane with a literal --cwd. You are unattended: decide and return.

Prerequisites, already merged and COMMITTED into your base before this worktree was created: noul.

## You are unattended

No one reads this session while it runs and no one will answer a question:
a turn that ends by asking for confirmation, approval or a preference does
NOTHING, and the job is then recorded as an absent implementation. Decide
with the spec, the plan and this prompt; when they are silent, choose the
smallest change that meets the acceptance, do it, run the checks, and return.

## Write-allowed (your lane — anything else is a scope violation)

- `docs/superpowers/dogfood/2026-10-08-detect-ui-noul-criteria-review.md`
- `.claude/agent-memory/superpowers-v-spec-reviewer/**`

## Global constraints (binding on every job)

Project-wide, and binding on EVERY job in this run including yours.
Copied verbatim from the plan — do not reinterpret, relax or widen
them.

- Change only `NOUL_CRITERIA` (`scripts/compound-v-jev.py:111`) to an object with string keys `true` and `false`; the `false` text keeps the exclusions (build scripts, documentation tooling, tests, data files).
- Do not touch the Choice branch of `questions_for`, `_request_meta`, `_parse_answer` or the vault.
- Selftest row over `questions_for(catalogue_entry(p, v))` for every point and variant: a `noul` question's `criteria` is absent or an object whose keys are a subset of `{"true", "false"}` with non-empty string values; it fails on the string form. No hand-typed catalogue hash.
- Python 3.9 stdlib only. No version bump, CHANGELOG or release. Commit subjects are plain sentences, no Co-Authored-By trailer.

## Read-allowed (advisory — git cannot enforce reads)

- `**`

## Acceptance (your definition of done)

- The review file exists with ## Recall, ## SPEC, ## QUALITY, ## INTEGRATION, ## Verdict; each AC run on the merged tree with command and output quoted; verdict APPROVED or ISSUES with a numbered list.

Turn cap: 80 (default for tier deep; default light 30 / standard 50 / deep 80). Plan to finish inside it.

## What you must NOT report

Do not report `blocked`, `files_changed` or `violations`. Those are
enforcement fields, they are derived from git by the caller, and a
constrained party filling in its own enforcement fields is the
fabricated-evidence pattern.
