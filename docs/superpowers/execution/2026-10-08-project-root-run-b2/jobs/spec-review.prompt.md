# Review Gate — deep, three passes against the B2 spec and AC-1..AC-3

Compound V run `2026-10-08-project-root-run-b2`, job `spec-review`.

Your agent definition carries the three-pass Review Gate and a Step 0 (V-memory recall). HARD BUDGET of 40 tool calls; FIRST action after Step 0: create docs/superpowers/dogfood/2026-10-08-project-root-run-b2-review.md with the section skeleton. Review against docs/superpowers/specs/2026-10-08-project-root-run-b2-design.md. Run the AC-2 grep over all of scripts/ (not only the lane) and say whether run B issue 1 is now closed. Revert checks only in a scratch copy. Your memory directory is .claude/agent-memory/superpowers-v-spec-reviewer/; keep any memory file frontmatter valid YAML (quote values containing a colon). Run python with -B; register your lane with a literal --cwd. You are unattended: decide and return.

Prerequisites, already merged and COMMITTED into your base before this worktree was created: b2-fix.

## You are unattended

No one reads this session while it runs and no one will answer a question:
a turn that ends by asking for confirmation, approval or a preference does
NOTHING, and the job is then recorded as an absent implementation. Decide
with the spec, the plan and this prompt; when they are silent, choose the
smallest change that meets the acceptance, do it, run the checks, and return.

## Write-allowed (your lane — anything else is a scope violation)

- `docs/superpowers/dogfood/2026-10-08-project-root-run-b2-review.md`
- `.claude/agent-memory/superpowers-v-spec-reviewer/**`

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

- The review file exists with ## Recall, ## SPEC, ## QUALITY, ## INTEGRATION, ## Verdict; each AC run on the merged tree with command and output quoted; verdict APPROVED or ISSUES with a numbered list.

Turn cap: 80 (default for tier deep; default light 30 / standard 50 / deep 80). Plan to finish inside it.

## What you must NOT report

Do not report `blocked`, `files_changed` or `violations`. Those are
enforcement fields, they are derived from git by the caller, and a
constrained party filling in its own enforcement fields is the
fabricated-evidence pattern.
