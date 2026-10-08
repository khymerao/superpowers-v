# Review Gate — deep, three passes against the spec and AC-1..AC-4

Compound V run `2026-10-08-vault-jev-classify-flat-arguments`, job `spec-review`.

Your agent definition carries the three-pass Review Gate and a Step 0 (V-memory recall). HARD BUDGET of 40 tool calls; FIRST action after Step 0: create docs/superpowers/dogfood/2026-10-08-vault-jev-classify-flat-arguments-review.md with the section skeleton. Review the job against docs/superpowers/specs/2026-10-08-vault-jev-classify-flat-arguments-design.md and the plan. Check in particular AC-2 by reverting the handler to e.input in a scratch copy (never in the tree) and confirming the suite fails, and that no e.input fallback exists. Your memory directory is .claude/agent-memory/superpowers-v-spec-reviewer/. Run python with -B; register your lane with a literal --cwd. You are unattended: decide and return.

Prerequisites, already merged and COMMITTED into your base before this worktree was created: flat-args.

## You are unattended

No one reads this session while it runs and no one will answer a question:
a turn that ends by asking for confirmation, approval or a preference does
NOTHING, and the job is then recorded as an absent implementation. Decide
with the spec, the plan and this prompt; when they are silent, choose the
smallest change that meets the acceptance, do it, run the checks, and return.

## Write-allowed (your lane — anything else is a scope violation)

- `docs/superpowers/dogfood/2026-10-08-vault-jev-classify-flat-arguments-review.md`
- `.claude/agent-memory/superpowers-v-spec-reviewer/**`

## Global constraints (binding on every job)

Project-wide, and binding on EVERY job in this run including yours.
Copied verbatim from the plan — do not reinterpret, relax or widen
them.

- Contract source: the engine types (`ToolCallInput`: the tool's arguments spread beside `tool`, `e.command` for Bash); `$.tool.call` takes the same flat shape.
- No fallback to `e.input` in the handler. The hook passes `e.request_file` (the narrow form); `serveTool` takes the value, drops the `isRecord` unwrap, and keeps its own `typeof === 'string'` and absolute-path checks, because whether the engine enforces `inputSchema` before `tool.call` is unverified (1C §6.2).
- `isDisabled` still runs before the argument is read (1A §7.3). `tool.check` handling, if any, is untouched.
- The registration `tool.call{tool=mcp__compound-v-vault__jev_classify}` stays as is (`tests/test-vault-mod.sh:41`).
- No version bump: the vault stays `0.1.0`; the cv-dev refresh is an uninstall and install, which drops the cached copy.
- The pinned CLI (`PIN=2.1.289`) must also pass the suite (CI uses it); run it once through npx on a staged copy. If it fails only on the flat shape, stop and report instead of moving the pin.
- No key-shaped literal in `plugins/compound-v-vault` (the existing grep row).
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
