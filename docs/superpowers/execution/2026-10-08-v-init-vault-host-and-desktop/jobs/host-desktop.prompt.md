# Task A — 1g host version, desktop inert, restart note

Compound V run `2026-10-08-v-init-vault-host-and-desktop`, job `host-desktop`.

Implement Task A of docs/superpowers/plans/2026-10-08-v-init-vault-host-and-desktop.md, every step in order (A1..A7). Read the spec docs/superpowers/specs/2026-10-08-v-init-vault-host-and-desktop-design.md and both audits first; their section 7 constraints and the plan Global Constraints bind. Tests first. Touch only your lane. Run python with -B; register your lane with a literal --cwd. You are unattended: decide and return.

## You are unattended

No one reads this session while it runs and no one will answer a question:
a turn that ends by asking for confirmation, approval or a preference does
NOTHING, and the job is then recorded as an absent implementation. Decide
with the spec, the plan and this prompt; when they are silent, choose the
smallest change that meets the acceptance, do it, run the checks, and return.

## Write-allowed (your lane — anything else is a scope violation)

- `commands/v-init.md`
- `plugins/compound-v-vault/README.md`
- `tests/test-vault-mod.sh`

## Global constraints (binding on every job)

Project-wide, and binding on EVERY job in this run including yours.
Copied verbatim from the plan — do not reinterpret, relax or widen
them.

- `CLAUDE_CODE_EXECPATH` and `CLAUDE_CODE_ENTRYPOINT` are undocumented: the step never fails when either is unset, empty or malformed. Live capture, desktop Code tab, 2026-10-08: `CLAUDE_CODE_ENTRYPOINT=claude-desktop`, `CLAUDE_CODE_EXECPATH=~/Library/Application Support/Claude/claude-code/2.1.293/<hash>/claude.app/Contents/MacOS/claude`, whose `--version` prints `2.1.293 (Claude Code)`. Terminal transcripts record `entrypoint: cli`.
- Host-version block, one fenced bash block in 1g: run `"$CLAUDE_CODE_EXECPATH" --version` only after `[ -x ]`, with `</dev/null`, under `python3 "$CV/scripts/compound-v-run-with-timeout.py" --timeout 5 --`; take the first anchored `x.y.z`; otherwise fall back to `claude --version` (same timeout); otherwise `unknown`. It prints the version and its source on one line: `<x.y.z> host`, `<x.y.z> path` or `unknown`. The directory name of the path is never the primary source. It never reads `claude plugin configure` output.
- `unknown` never passes the 2.1.287 floor: report `installed, host version unknown (the vault needs Claude Code 2.1.287 or newer)`.
- Desktop: only the exact value `CLAUDE_CODE_ENTRYPOINT=claude-desktop` selects the state `installed, inert in the desktop app (observed 2026-10-08 on the bundled 2.1.293: the vault does not receive its key there) - use Jev from a terminal claude`. Worded as observed behaviour, not a documented guarantee. Do not use `CLAUDECODE` or `CLAUDE_CODE_CHILD_SESSION`. No gist is cited as the contract.
- State order: `absent`, `disabled`, desktop inert, host version unknown, below the floor, key not set or unknown, key set. The key probe is skipped in the desktop case. Fix the stale intro line ("one of three states").
- Step 2's vault bullet: on a desktop host it does not offer `/plugin configure` in place; it says to run it in a terminal `claude`. Everywhere the key is entered or changed, say it takes effect in a new session (restart `claude`).
- Step 1f's `/skill-doctor` floor reads the host version from the 1g block instead of `claude --version`.
- `hooks/session-banner.sh:84` has the same defect; out of scope (not in this lane), recorded as a follow-up.
- The filtered key probe and the existing 1g test row (`tests/test-vault-mod.sh:116-144`) stay green and unchanged in intent. Never read, print, request or forward the key value.
- README: one sentence on the desktop limitation (observed, dated), one on the restart.
- No version bump, CHANGELOG or release. Commit subjects are plain sentences, no Co-Authored-By trailer.

## Read-allowed (advisory — git cannot enforce reads)

- `**`

## Acceptance (your definition of done)

- test-vault-mod.sh green with both new rows, each failing when its change is reverted; lint-frontmatter clean; the existing filtered-probe row green; the host block run live once with its output quoted.

Turn cap: 80 (default for tier deep; default light 30 / standard 50 / deep 80). Plan to finish inside it.

## What you must NOT report

Do not report `blocked`, `files_changed` or `violations`. Those are
enforcement fields, they are derived from git by the caller, and a
constrained party filling in its own enforcement fields is the
fabricated-evidence pattern.
