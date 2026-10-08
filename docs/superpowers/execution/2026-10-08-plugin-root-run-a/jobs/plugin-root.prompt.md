# Task A — CV from the harness substitution in 38 files, session-banner fallback, test

Compound V run `2026-10-08-plugin-root-run-a`, job `plugin-root`.

Implement Task A of docs/superpowers/plans/2026-10-08-plugin-root-run-a.md, every step in order (A1..A6). Read the spec docs/superpowers/specs/2026-10-08-plugin-root-run-a-design.md, ADR docs/superpowers/adr/0005-one-rule-per-root.md and both audits first. Tests first. Touch only your lane. Run python with -B; register your lane with a literal --cwd. You are unattended: decide and return.

## You are unattended

No one reads this session while it runs and no one will answer a question:
a turn that ends by asking for confirmation, approval or a preference does
NOTHING, and the job is then recorded as an absent implementation. Decide
with the spec, the plan and this prompt; when they are silent, choose the
smallest change that meets the acceptance, do it, run the checks, and return.

## Write-allowed (your lane — anything else is a scope violation)

- `agents/code-archaeologist.md`
- `agents/doc-validator.md`
- `agents/domain-expert.md`
- `agents/parallel-dispatcher.md`
- `agents/partition-reviewer.md`
- `agents/spec-reviewer.md`
- `commands/v-adr.md`
- `commands/v-collect.md`
- `commands/v-dispatch.md`
- `commands/v-epic.md`
- `commands/v-init.md`
- `commands/v-lessons.md`
- `commands/v-memory-refresh.md`
- `commands/v-models.md`
- `commands/v-onboard.md`
- `commands/v-orchestrate.md`
- `commands/v-remember.md`
- `commands/v-resume.md`
- `commands/v-review-plan.md`
- `commands/v-status.md`
- `commands/v-triage.md`
- `evals/README.md`
- `skills/backend-launcher/SKILL.md`
- `skills/backend-launcher/adapter-antigravity.md`
- `skills/backend-launcher/adapter-claude.md`
- `skills/backend-launcher/adapter-codex.md`
- `skills/backend-launcher/adapter-cursor.md`
- `skills/backend-launcher/adapter-opencode.md`
- `skills/compound-v/SKILL.md`
- `skills/compound-v/adr-capture.md`
- `skills/compound-v/cross-model-review.md`
- `skills/compound-v/execution-manifest.md`
- `skills/compound-v/memory.md`
- `skills/compound-v/onboarding.md`
- `skills/compound-v/phase-0-recon.md`
- `skills/compound-v/phase-2-disjoint-partitioning.md`
- `skills/compound-v/phase-3-parallel-opus-dispatch.md`
- `skills/compound-v/routing-policy.md`
- `hooks/session-banner.sh`
- `tests/test-plugin-root.sh`

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

- tests/test-plugin-root.sh green and each row fails on revert; lint-frontmatter and shellcheck clean; no old cache scan left; the other tests that read these files green.

Turn cap: 80 (default for tier deep; default light 30 / standard 50 / deep 80). Plan to finish inside it.

## What you must NOT report

Do not report `blocked`, `files_changed` or `violations`. Those are
enforcement fields, they are derived from git by the caller, and a
constrained party filling in its own enforcement fields is the
fabricated-evidence pattern.
