# Task A — optional vault, offered by /v:init

Compound V run `2026-10-05-vault-optional-via-init`, job `vault-optional`.

Implement Task A of docs/superpowers/plans/2026-10-05-vault-optional-via-init.md, every step in order. Read the spec docs/superpowers/specs/2026-10-05-vault-optional-via-init-design.md first, and treat the audits of the superseded dependency design as constraints. Read the real `claude plugin configure <id> --json` shape on this machine before writing the probe, and never print an option value. Tests first. Touch only your lane. Run python with -B; register your lane with a literal --cwd. You are unattended: decide and return.

## You are unattended

No one reads this session while it runs and no one will answer a question:
a turn that ends by asking for confirmation, approval or a preference does
NOTHING, and the job is then recorded as an absent implementation. Decide
with the spec, the plan and this prompt; when they are silent, choose the
smallest change that meets the acceptance, do it, run the checks, and return.

## Write-allowed (your lane — anything else is a scope violation)

- `.claude-plugin/marketplace.json`
- `commands/v-init.md`
- `plugins/compound-v-vault/README.md`
- `README.md`
- `hooks/jev-t3.tsx`
- `tests/test-vault-mod.sh`

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

- test-vault-mod.sh green with the lockstep and README rows, each failing when reverted; test-jev-t3-mod.sh and test-run-band-mod.sh green; both plugin validations pass; lint-frontmatter clean; the /v:init step prints only absent / key set state, never a value.

Turn cap: 80 (default for tier deep; default light 30 / standard 50 / deep 80). Plan to finish inside it.

## What you must NOT report

Do not report `blocked`, `files_changed` or `violations`. Those are
enforcement fields, they are derived from git by the caller, and a
constrained party filling in its own enforcement fields is the
fabricated-evidence pattern.
