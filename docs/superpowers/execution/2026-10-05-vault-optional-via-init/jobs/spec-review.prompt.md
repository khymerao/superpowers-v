# Review Gate — deep, three passes against the spec and AC-1..AC-4

Compound V run `2026-10-05-vault-optional-via-init`, job `spec-review`.

Your agent definition carries the three-pass Review Gate and a Step 0 (V-memory recall). HARD BUDGET of 40 tool calls; FIRST action after Step 0: create docs/superpowers/dogfood/2026-10-05-vault-optional-via-init-review.md with the section skeleton. Review the job against docs/superpowers/specs/2026-10-05-vault-optional-via-init-design.md and the plan. Check in particular that the /v:init step cannot print or forward the key. Your memory directory is .claude/agent-memory/superpowers-v-spec-reviewer/. Run python with -B; register your lane with a literal --cwd. You are unattended: decide and return.

Prerequisites, already merged and COMMITTED into your base before this worktree was created: vault-optional.

## You are unattended

No one reads this session while it runs and no one will answer a question:
a turn that ends by asking for confirmation, approval or a preference does
NOTHING, and the job is then recorded as an absent implementation. Decide
with the spec, the plan and this prompt; when they are silent, choose the
smallest change that meets the acceptance, do it, run the checks, and return.

## Write-allowed (your lane — anything else is a scope violation)

- `docs/superpowers/dogfood/2026-10-05-vault-optional-via-init-review.md`
- `.claude/agent-memory/superpowers-v-spec-reviewer/**`

## Global constraints (binding on every job)

Project-wide, and binding on EVERY job in this run including yours.
Copied verbatim from the plan — do not reinterpret, relax or widen
them.

- No `dependencies` field in superpowers-v's `.claude-plugin/plugin.json`.
- The marketplace entry's `version` is byte-equal to the vault plugin.json `version` (`0.1.0`).
- Never tell users to set the key in `/config`; the documented path is `/plugin configure compound-v-vault@procoders`.
- `/v:init` never reads, prints, requests or forwards the key value.
- No version bump, CHANGELOG or release.
- Docs: plain words, every claim true of HEAD, no line over 200 characters outside code/tables.
- Lane discipline; `register-lane` first, with a literal `--cwd`. Commit subjects are plain sentences, no Co-Authored-By trailer.

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
