# /v:init 1g reads the running host and reports the desktop vault as inert - design

Triage: `docs/superpowers/pre-eval/2026-10-08T055210Z-v-init-step-1g-read-the-running-host-claude-code-version-fro-0d3a.json`
(FULL). Handoff: `docs/superpowers/research/2026-10-05-jev-next-stage.md`, sections "Finding from the first live attempt"
and "Confirmed by the maintainer".

## Problem

1. `/v:init` step 1g checks the vault's 2.1.287 floor with `claude --version`, which reports the CLI on `PATH`, not the
   Claude Code running the session. The desktop app's Code tab runs its own bundled build
   (`CLAUDE_CODE_EXECPATH=~/Library/Application Support/Claude/claude-code/<version>/.../claude`). On 2026-10-05 that
   was 2.1.286 while `PATH` had 2.1.289, so 1g would have passed a host that cannot load the vault.
2. In the desktop app the vault never receives its key, whatever the version. Evidence, 2026-10-08: with the key set and
   working in a terminal `claude` (2.1.294, nine `ok` calls at 08:13), a desktop session started at 08:15 on the bundled
   2.1.293 (above the floor) showed `Jev: off (no_key)`. So 1g reports `installed, key set` for a vault that is inert.
3. The vault reads its key once, when its module loads. After `/plugin configure` the running session keeps the old
   value: on 2026-10-08 a changed key still got nine `401` answers until `claude` was restarted, then nine `ok`.

## Change

1. **Host version.** Step 1g gets one fenced bash block that prints the running host's version: when
   `CLAUDE_CODE_EXECPATH` is set and executable, `"$CLAUDE_CODE_EXECPATH" --version </dev/null`; otherwise (unset, not
   executable, or no `x.y.z` in its output) `claude --version`. It prints only the `x.y.z`, or `unknown`. The floor
   check uses that value. `claude plugin configure` (the key-state probe) still runs the `PATH` CLI; that is correct,
   it is a separate command, not the host.
2. **Desktop.** When `CLAUDE_CODE_ENTRYPOINT` is `claude-desktop`, an installed and enabled vault is reported as
   `installed, inert in the desktop app - use Jev from a terminal claude`, whatever its version or key state. Order of
   the states: `absent`, `disabled`, desktop inert, below the floor, key not set or unknown, key set. The key probe is
   not needed in the desktop case and is skipped.
3. **Restart.** The `installed, key set` report and Step 2's vault bullet say that a key entered or changed with
   `/plugin configure` takes effect in a new session (restart `claude`).
4. **README** (`plugins/compound-v-vault/README.md`): one sentence that the vault is inert in the Claude desktop app's
   Code tab (it does not receive the key there; use a terminal `claude`), and one that a new or changed key takes
   effect after a restart.
5. **Tests** (`tests/test-vault-mod.sh`): one row extracts the host-version block from step 1g and runs it with a stub
   `CLAUDE_CODE_EXECPATH` printing `2.1.286 (Claude Code)` and a stub `claude` on `PATH` printing
   `2.1.289 (Claude Code)`: it must print `2.1.286`; with `CLAUDE_CODE_EXECPATH` unset it must print `2.1.289`. A second
   row checks that step 1g names `CLAUDE_CODE_ENTRYPOINT`, `claude-desktop` and the desktop-inert state, the README
   carries the desktop and restart sentences, and the floor check no longer reads `claude --version` directly.
   Each row fails when its change is reverted.

## Out of scope

The Anthropic issue about the desktop app not passing a plugin's sensitive `userConfig`; any vault code change; Phase T
(item 3); the plugin-root resolver (item 4).

## Acceptance Criteria

1. `tests/test-vault-mod.sh` passes, including both new rows.
2. Reverting the host-version block to `claude --version` makes the first new row fail; removing the desktop state or
   either README sentence makes the second fail.
3. `/v:init` step 1g never reads, prints, requests or forwards the key value (the existing filtered-probe row stays green).
4. `scripts/lint-frontmatter.py .` passes.
