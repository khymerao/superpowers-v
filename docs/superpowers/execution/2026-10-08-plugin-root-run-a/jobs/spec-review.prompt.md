# Review Gate — deep, three passes against the spec, the ADR and AC-1..AC-4

Compound V run `2026-10-08-plugin-root-run-a`, job `spec-review`.

Your agent definition carries the three-pass Review Gate and a Step 0 (V-memory recall). HARD BUDGET of 40 tool calls; FIRST action after Step 0: create docs/superpowers/dogfood/2026-10-08-plugin-root-run-a-review.md with the section skeleton. Review the job against docs/superpowers/specs/2026-10-08-plugin-root-run-a-design.md, ADR 0005 and the plan. Check that no :- form of CLAUDE_PLUGIN_ROOT remains in the 38 files, the prose matches the new rule, session-banner never runs a project file, and revert checks fail (scratch copy only). AC-4 is post-merge; mark it pending for the orchestrator. Your memory directory is .claude/agent-memory/superpowers-v-spec-reviewer/. Run python with -B; register your lane with a literal --cwd. You are unattended: decide and return.

Prerequisites, already merged and COMMITTED into your base before this worktree was created: plugin-root.

## You are unattended

No one reads this session while it runs and no one will answer a question:
a turn that ends by asking for confirmation, approval or a preference does
NOTHING, and the job is then recorded as an absent implementation. Decide
with the spec, the plan and this prompt; when they are silent, choose the
smallest change that meets the acceptance, do it, run the checks, and return.

## Write-allowed (your lane — anything else is a scope violation)

- `docs/superpowers/dogfood/2026-10-08-plugin-root-run-a-review.md`
- `.claude/agent-memory/superpowers-v-spec-reviewer/**`

## Global constraints (binding on every job)

Project-wide, and binding on EVERY job in this run including yours.
Copied verbatim from the plan — do not reinterpret, relax or widen
them.

- The three canonical lines are exactly those in the spec, byte-for-byte, in all 38 files, replacing the old two (the `evals/README.md` copy had a shorter second line; it gets the same three).
- Live evidence (2026-10-08, Claude Code 2.1.294, `--plugin-dir`): the bare `${CLAUDE_PLUGIN_ROOT}` is substituted in command, skill and agent bodies; `${CLAUDE_PLUGIN_ROOT:-...}` is not. Do not use the `:-` form anywhere in these files.
- No cache scan, no `claude plugin list`, no marketplace name, no `~/.claude/plugins` path in the canonical lines.
- `evals/lib/cv-fixture-lib.sh` is not changed; `evals/README.md` explains the new rule and that under `claude plugin eval` `CV` is the substituted plugin source.
- `hooks/session-banner.sh`: `CLAUDE_PLUGIN_ROOT`, else the directory above the hook script; the banner's output is otherwise unchanged and it still fails silent.
- `tests/test-plugin-root.sh` is executable and shellcheck-clean; each row fails when its change is reverted.
- Project-root code (ADR 0005 rules 5-8) is not touched: that is run B.
- No version bump, CHANGELOG or release. Commit subjects are plain sentences, no Co-Authored-By trailer.

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
