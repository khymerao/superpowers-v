# Library audit (Phase 1C): /v:init 1g host version and desktop-inert state

Spec: `docs/superpowers/specs/2026-10-08-v-init-vault-host-and-desktop-design.md`. Checked 2026-10-08.

The spec adds no third-party library. Its only external surfaces are two Claude Code environment variables
(`CLAUDE_CODE_EXECPATH`, `CLAUDE_CODE_ENTRYPOINT`), the `--version` output format, and the desktop app's plugin behaviour.
All four are checked here.

## 1. Tools Available

- Context7: NOT usable. `ToolSearch` for `context7` returned no tools; the session reports `plugin:context7:context7` as
  needing authentication (not absent). DEGRADED: WebSearch/WebFetch only. Nothing below is cited to Context7.
- Bash was clamped to fixed command forms, so I could not read the live environment of this session or run `claude --version`.
- Manifests: none relevant. The change touches `commands/v-init.md`, `plugins/compound-v-vault/README.md` and
  `tests/test-vault-mod.sh` only (no dependency manifest).
- V-memory: the prompt carried the recall block; I used `docs/superpowers/research/2026-10-05-jev-next-stage.md` (read
  lines 55-105). No second search run.
- Agent memory read: `drift-jev-and-mods.md`, `drift-plugin-dependencies.md`, `drift-system-toolchain.md`. KB read:
  `claude-code-mods.md`. No directive found in any memory file.

## 2. Libraries Mentioned

| Name | Spec context | Current (2026-10-08) | Repo pinned | Last release | Maintenance | Status |
|---|---|---|---|---|---|---|
| Claude Code (host) | floor 2.1.287 for the vault | 2.1.294 (changelog, 2026-10-08) | floor in `commands/v-init.md:333` = 2.1.287; AGENTS.md floor 2.1.219 | 2026-10-08 | active | OK |
| `CLAUDE_CODE_EXECPATH` | pick the running host's binary | not in official env-vars page | none | n/a | undocumented | see 4.1 |
| `CLAUDE_CODE_ENTRYPOINT` | detect desktop host (`claude-desktop`) | not in official env-vars page | none | n/a | undocumented | see 4.2 |
| Claude desktop app (Code tab) | vault inert there | bundled build 2.1.293 observed by maintainer | n/a | n/a | active | see 5.3 |

## 3. API Signatures Verified

| Signature | Source | Result |
|---|---|---|
| `claude --version` / `-v` | `code.claude.com/docs/en/cli-reference`: "Output the version number" | Exists. The docs give no output format; `2.1.286 (Claude Code)` is the maintainer's observation. Parse with an `x.y.z` regex, as the spec does. |
| `claude plugin configure <plugin>` | changelog 2.1.285 | Exists, 2.1.285 and up. Matches the existing 1g text. |
| `CLAUDE_CODE_EXECPATH` | official env-vars page (first 100k chars and the tail) and changelog (first 100k chars): no mention. Community gist (mculp, v2.1.104, 2026-04-13): "Binary path (auto-injected)" | Not an official contract. |
| `CLAUDE_CODE_ENTRYPOINT` | same pages: no mention (only `OTEL_METRICS_INCLUDE_ENTRYPOINT`). Community gist (unkn0wncode): "Identifies how Claude Code was launched (e.g., cli, sdk-ts/sdk-py/sdk-cli, mcp, claude-vscode, ... claude-desktop ..." ; another gist (mculp) lists "local-agent, remote..." and not `claude-desktop` | Not an official contract; `claude-desktop` is only third-party-listed. |
| `CLAUDECODE=1`, `CLAUDE_CODE_CHILD_SESSION=1` | official env-vars page: set in Bash tool, hook commands, status line subprocesses | Documented, but they say "inside Claude Code", not which host. Not usable for the desktop test. |

## 4. Critical Findings

None. No library is deprecated or archived.

## 5. High-Priority Findings

### 5.1 `CLAUDE_CODE_EXECPATH` is undocumented and unconfirmed in the Bash-tool environment
- Evidence it exists: the maintainer saw it in a desktop session on 2026-10-05 (`research/2026-10-05-jev-next-stage.md:68`) and a
  community gist calls it "auto-injected". Not in `code.claude.com/docs/en/env-vars` (I read the table to its alphabetical end
  across both fetch windows; no row).
- Not established: that it is exported to the Bash tool subprocess in a terminal `claude`, in the desktop app, and in a headless
  `claude -p` run. 1g's block runs through the Bash tool, which is the context that matters. If it is unset in some host the
  spec's fallback (`claude --version` on `PATH`) silently reintroduces the original bug in exactly that host.
- Alternative if it proves unreliable: none official. Candidates to verify live: `process.execPath`-style values are not exposed
  to shell; the `claude --version` of the binary named by `command -v claude` is the same PATH problem. Recommend recording, in
  the report line, WHICH source supplied the version (`host` vs `PATH fallback`) so a fallback is visible rather than silent.

### 5.2 `CLAUDE_CODE_ENTRYPOINT=claude-desktop` is not an official value
- Only third-party gists list `claude-desktop`; one April 2026 gist (v2.1.104) does not. The official page documents the
  related marker pairs (`CLAUDECODE`, `CLAUDE_CODE_CHILD_SESSION`) but not this one. Anthropic may rename or split the value
  (the desktop docs describe Desktop hosting Claude Code via the Agent SDK `canUseTool` callback, and the SDK is known to
  overwrite the entrypoint with `sdk-*` values in some launch paths, per an omnigent issue).
- Required evidence before the plan relies on it: one live capture of `CLAUDE_CODE_ENTRYPOINT` from a desktop Code-tab Bash call.
  The 2026-10-05 handoff names the value (`research/...:86`) but the quoted observation covers EXECPATH only; I could not tell
  whether ENTRYPOINT was actually observed or inferred.
- Consequence if wrong: the desktop state never fires and 1g again reports `installed, key set` for an inert vault, with the
  new tests green (they use stubs).

## 6. Medium Findings

### 6.1 Reported cause changed; docs do not explain why desktop drops the key
- The 2026-10-05 note blamed bundled 2.1.286 (< floor). The spec's 2026-10-08 evidence (bundled 2.1.293, key set, still
  `no_key`) removes the version explanation. Nothing in the desktop docs, changelog (read to 2.1.285 plus matched lines), or
  plugin docs says the desktop app skips sensitive `userConfig` for hook modules. Desktop docs only say plugins are managed
  through the "+" menu / Manage plugins, and 2.1.290 changed the desktop `/plugin` reply to point there. So "inert in the desktop
  app" is an empirical claim from one machine and one key store; it may change in any desktop release. The report text should
  say it was observed, and 1g should keep working if a later desktop build starts delivering the key (see constraint 5).

### 6.2 Other non-terminal hosts are unaddressed
- The KB records WSL Desktop sessions as mods-off; the desktop docs say plugins are unavailable in WSL sessions and not in
  cloud sessions; SSH sessions run Claude Code on a remote host. `CLAUDE_CODE_ENTRYPOINT` also takes `claude-vscode`, `sdk-*`,
  `remote_*`. The spec handles only `claude-desktop`; `claude -p` under 1g's own probe runs with the SDK entrypoint family.
  Not a blocker, but state it as out of scope rather than imply coverage.

## 7. Design Constraints for the Plan

MUST:
1. Treat both variables as undocumented: parse defensively, and never fail the step if either is unset or malformed.
2. Run `"$CLAUDE_CODE_EXECPATH" --version </dev/null` only after `[ -x ]` and with a timeout (the repo has
   `scripts/compound-v-run-with-timeout.py`, used by step 1f); a hung host binary must not hang `/v:init`.
3. Extract the version with an anchored `x.y.z` match from the first line of output; print `unknown` otherwise; and define in the
   step what `unknown` does to the floor check (the spec's state order does not say). Do not treat `unknown` as "above the floor".
4. Keep the test stubs for `--version` output as `N.N.N (Claude Code)`, and add one stub whose output has no `x.y.z`, to prove
   the fall-through to `claude --version`.
5. Word the desktop state as observed behaviour, not a guarantee, and keep the key probe unrun there (as specified).
6. Keep the filtered key probe unchanged; the host-version block must not touch `claude plugin configure` output.
7. Obtain one live capture of `CLAUDE_CODE_ENTRYPOINT` and `CLAUDE_CODE_EXECPATH` from a desktop Code-tab Bash call and from a
   terminal Bash call before merge, and cite it in the dogfood record.

MUST NOT:
1. Rely on `CLAUDECODE` / `CLAUDE_CODE_CHILD_SESSION` to tell hosts apart; they are set in every host.
2. Cite the community gists as the contract in `commands/v-init.md`; cite the maintainer's observation and its date.
3. Parse the version out of the EXECPATH directory name as the primary route; the directory layout is not documented.

## 8. Open Questions for the Human

1. Was `CLAUDE_CODE_ENTRYPOINT=claude-desktop` actually printed in a desktop session, or inferred? If inferred, run the one-line
   capture first (`printenv | grep -E '^CLAUDE_CODE_(ENTRYPOINT|EXECPATH)='` in a desktop Code-tab session).
2. Are VS Code (`claude-vscode`) and SSH-hosted desktop sessions in scope for the same "inert" line? The spec says no; confirm.
3. Should the "inert in the desktop app" text name a date/version of the observation (2026-10-08, desktop-bundled 2.1.293) so a
   later desktop fix is recognisable?

## 9. Knowledge Base Updates

- Created `docs/superpowers/library-audit/_knowledge-base/claude-code-host-detection.md` (new topic).
- Agent memory: added `drift-host-detection.md` and an index line.
