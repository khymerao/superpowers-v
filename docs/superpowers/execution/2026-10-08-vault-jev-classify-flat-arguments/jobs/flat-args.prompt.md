# Task A — jev_classify reads request_file flat

Compound V run `2026-10-08-vault-jev-classify-flat-arguments`, job `flat-args`.

Implement Task A of docs/superpowers/plans/2026-10-08-vault-jev-classify-flat-arguments.md, every step in order (A1..A6). Read the spec docs/superpowers/specs/2026-10-08-vault-jev-classify-flat-arguments-design.md and both audits first; their section 7 constraints bind. Tests first: watch the suite fail on the old handler before fixing. Touch only your lane. Run python with -B; register your lane with a literal --cwd. You are unattended: decide and return.

## You are unattended

No one reads this session while it runs and no one will answer a question:
a turn that ends by asking for confirmation, approval or a preference does
NOTHING, and the job is then recorded as an absent implementation. Decide
with the spec, the plan and this prompt; when they are silent, choose the
smallest change that meets the acceptance, do it, run the checks, and return.

## Write-allowed (your lane — anything else is a scope violation)

- `plugins/compound-v-vault/hooks/vault.tsx`
- `plugins/compound-v-vault/.tests/vault.test.tsx`

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

- test-vault-mod.sh green with the flat helper and the new regression row; the suite fails with e.input restored; the pinned CLI 2.1.289 passes the staged suite; no sk-or- literal added.

Turn cap: 80 (default for tier deep; default light 30 / standard 50 / deep 80). Plan to finish inside it.

## What you must NOT report

Do not report `blocked`, `files_changed` or `violations`. Those are
enforcement fields, they are derived from git by the caller, and a
constrained party filling in its own enforcement fields is the
fabricated-evidence pattern.
