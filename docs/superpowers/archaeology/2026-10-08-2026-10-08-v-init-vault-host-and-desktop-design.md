# /v:init 1g host version and desktop-inert Code Archaeology

Spec: `docs/superpowers/specs/2026-10-08-v-init-vault-host-and-desktop-design.md`. Audit date 2026-10-08.
Method: Read/Grep only (the agent's Bash is clamped to git and the memory script, so no env probe and no run of any stub was possible). V-memory block in the prompt was used; its two research hits were checked against the code. Context7 was unavailable (OAuth not completed) and is not needed: the only external surface is two environment variables and `--version` output, neither of which Context7 documents.

## 1. Matrix

Step 1g today (`commands/v-init.md:296-343`) is prose that a model executes: three bash blocks (plugin list, plugin configure, none for the floor) plus judgement. Dimensions it branches by:

| Dimension | Values | Handled today | Handled by spec |
|---|---|---|---|
| Vault state (`plugin list`) | absent / disabled:<id> / <id> | yes (`:301-313`) | unchanged |
| Host | terminal CLI / desktop Code tab | no | change 2 |
| Host version source | PATH `claude` / `CLAUDE_CODE_EXECPATH` | PATH only (`:334`) | change 1 |
| Host version vs 2.1.287 | below / at-or-above / unparseable | below / above (`:340`); unparseable not specified | spec prints `unknown` but names no report state for it |
| Key state (`plugin configure`) | set / not set / unknown | yes (`:318-331`) | skipped on desktop |

Combinations the new text must define (spec change 2 gives the order `absent, disabled, desktop inert, below floor, key not set or unknown, key set`):

| Vault | Entrypoint | Version | Spec result | Gap |
|---|---|---|---|---|
| absent | any | any | absent | none |
| disabled | any | any | disabled | none |
| enabled | claude-desktop | any | desktop inert | none; key probe skipped |
| enabled | other/unset | < 2.1.287 | inert (< floor) | none |
| enabled | other/unset | `unknown` | UNDEFINED | no state, no floor decision for `unknown`; the old text had none either, because `claude --version` was assumed to work |
| enabled | other/unset | >= floor | key set / not set / unknown | none |
| enabled | `CLAUDE_CODE_EXECPATH` set, not executable | any | falls back to PATH `claude` | the fallback silently reads the wrong host again; only a desktop entrypoint check saves it |

Not verifiable here: whether Claude Code's Bash tool actually inherits `CLAUDE_CODE_ENTRYPOINT` and `CLAUDE_CODE_EXECPATH` in both hosts. The repo records `CLAUDE_CODE_EXECPATH` once, from a manual observation (research handoff `docs/superpowers/research/2026-10-05-jev-next-stage.md:68`). The literal value `claude-desktop` for `CLAUDE_CODE_ENTRYPOINT` appears only as a "decided direction" (`:86`) and in the spec; no file in the repo or in `plugins/` records it as observed. Treat it as UNVERIFIED.

## 2. Shared State

**Host version (new, produced by the new bash block)**
- Set: block prints `x.y.z` or `unknown`.
- Consumed by: model reading the 1g prose (floor check). There is no code consumer; there is no `ge`/semver helper in `commands/v-init.md`. The comparison is the model's judgement.
- Gap: `unknown` is a value the prose has to route. Without a rule it will be read as either "pass" or "inert"; the first is the original bug.

**`CLAUDE_CODE_ENTRYPOINT`**
- Spec change 2 names the variable but change 1 gives a fenced block only for the version. The entrypoint read has no block, so the model would have to invent a Bash call. Not set in a CI shell, so a test cannot exercise it end-to-end; the second test row (spec change 5) can only grep for the words.

**`<id>`** (probe output of `plugin list`): unchanged; Step 2 reuses it (`:363`).

**Key value**: never read. The existing row at `tests/test-vault-mod.sh:127-131` fails any bash line that mentions `plugin configure` without `2>/dev/null | python3`, and fails any bash code containing `inputs`. The new host block must contain neither string.

## 3. Sibling Code

- **`commands/v-init.md:247-259`, step 1f.** Same defect class, same command: gates on `claude --version` (`:255`, floor 2.1.261) and so reads the PATH CLI, not the host. On the desktop app with a bundled build older than the PATH one, 1f runs `claude -p '/skill-doctor'` via PATH `claude`, a different binary than the session. The spec scopes only 1g. Decision needed: fix 1f with the same block, or record it out of scope. Silence leaves a known twin.
- **`hooks/session-banner.sh:83-92`.** Same defect: `claude --version` on PATH drives the "< floor" warning (floor `CV_VERSION_FLOOR`, 2.1.219). In the desktop app it can report a PATH version that is not the running one. Out of the spec's scope; document it.
- **`tests/test-vault-mod.sh:20-28`, `tests/test-run-band-mod.sh:17`, `tests/test-jev-t3-mod.sh:21`.** Pick a CI CLI via `claude --version`. That is correct for them (they need a CLI that runs `plugin test`, not the session host). The new rows must not be "fixed" to use the host block.
- **Existing row `tests/test-vault-mod.sh:116-144`** extracts 1g with `^### 1g\..*?(?=^## |^### 1h|\Z)`. That terminates at `## Step 2`, so the section includes the trailing `---`. Fine. It joins all ```` ```bash ```` blocks of the section into `code`. Entry conditions that bind the new block:
  - a bash line containing `plugin configure` must also contain `2>/dev/null | python3` (`:128`);
  - `inputs` must not appear anywhere in the joined code (`:130`);
  - `disabled:` must appear in the joined code (`:132`);
  - the section text must still contain `/egress allow`, `2.1.287`, `/plugin enable` (`:134`).
- Latent: the test hardcodes the prose phrases; the 1g title line says "reports one of three states" (`:299`) and the real list already has five (`:338-343`). Stale already, will be six or seven after the spec.

## 4. External APIs

Context7 unavailable and not applicable. Contract facts the spec relies on, all UNVERIFIED in this environment:
- `CLAUDE_CODE_EXECPATH`: path to the running Claude Code binary; value observed once on the desktop app (`.../Application Support/Claude/claude-code/<version>/.../claude`, containing a space, so quoting is mandatory).
- `"$CLAUDE_CODE_EXECPATH" --version </dev/null`: assumed to print `x.y.z (Claude Code)` like the CLI. The desktop-bundled binary has not been shown to do so in this repo. If it prints something else or blocks, the block falls through to `claude --version`, i.e. back to the bug, silently.
- `CLAUDE_CODE_ENTRYPOINT=claude-desktop`: value not recorded as observed anywhere in the repo (see section 1).
- `claude plugin configure ... --json` shape and the 2.1.285 floor: already documented in `docs/superpowers/dogfood/2026-10-05-vault-optional-via-init-review.md` (V-memory hit); unchanged.

## 5. Regression Surface

- **Terminal users on the PATH CLI:** if `CLAUDE_CODE_EXECPATH` is set in terminal sessions to the same binary, behaviour is unchanged; if set to a stale path, the `-x` check or the `x.y.z` check must fall back. If the block mis-parses, a healthy install is reported `unknown` or inert.
- **Existing row `tests/test-vault-mod.sh:144`:** will break if the rewritten 1g drops `2.1.287`, `/egress allow`, `/plugin enable`, `disabled:`, or if the new block contains `inputs`.
- **Step 2 vault bullet (`:360-367`):** the "not set" branch asks the user to `/plugin configure`; on a desktop host that branch must not fire (the key cannot reach the vault), or the user is told to enter a key that will never be used.
- **Report order:** any user who has a stored key and a PATH CLI currently sees `installed, key set` in the desktop app; after the change they see inert. That is intended; it is the only user-visible change.
- **CI:** `.github/workflows/validate.yml:367` discovers `tests/**/*.sh` recursively, so the new rows run in CI with no registration. CI has neither `CLAUDE_CODE_EXECPATH` nor `CLAUDE_CODE_ENTRYPOINT`, so the new rows must set them explicitly and must not depend on the ambient shell.
- **Anti-ruflo / dead-link scans** (`.claude/rules/docs.md`): the README sentences must not print a measured figure; any new intra-repo link must resolve.

## 6. DRY Findings

- Version parse `grep -oE '^[0-9]+\.[0-9]+\.[0-9]+'` is written three times in tests (`test-vault-mod.sh:22`, `test-run-band-mod.sh:17`, `test-jev-t3-mod.sh:21`) plus `session-banner.sh:85-87` (bash regex). The new block adds a fourth. It lives in a markdown command, so it cannot import a helper; extend, do not refactor, but the version regex must match the existing `^[0-9]+\.[0-9]+\.[0-9]+` semantic (anchored: `2.1.286 (Claude Code)` passes; a leading banner line would not).
- Floor value `2.1.287` is repeated in: `commands/v-init.md:333,340,361`, `plugins/compound-v-vault/README.md:15`, `.claude-plugin/marketplace.json:21`, `README.md:22,104`, and three tests. Spec does not change the floor, so no edit, but any new host-block text must reuse the literal.
- No existing code reads `CLAUDE_CODE_EXECPATH` or `CLAUDE_CODE_ENTRYPOINT` (Grep over `plugins/` and the repo, excluding docs). The decision is "add the first reader"; there is no second path to merge with.

## 7. Design constraints for the spec

1. Define the report state and the floor decision for host version `unknown` (the 1g text must say what it prints; it must not pass the floor).
2. Give the entrypoint read its own fenced bash block (one line, printing only a fixed token), or state in prose exactly how the model reads it. Change 2 names the variable but supplies no probe.
3. Record that `CLAUDE_CODE_ENTRYPOINT=claude-desktop` is a maintainer-decided value not yet observed in the repo; either capture it (one `printenv` in a desktop session, quoted into the spec) or mark it as the assumption the second test row cannot verify.
4. The host-version block must: quote `"$CLAUDE_CODE_EXECPATH"` (path has a space), test `-x`, redirect stdin `</dev/null`, anchor the parse like `^[0-9]+\.[0-9]+\.[0-9]+` or an equivalent, print `unknown` otherwise, and contain neither `inputs` nor a `plugin configure` line.
5. Keep in the 1g section: `2.1.287`, `/egress allow`, `/plugin enable`, `disabled:`, and the filtered configure probe (the existing row at `tests/test-vault-mod.sh:116-144` must stay green).
6. Test row 1 must run the extracted block with an explicit environment (`env -i` or equivalent setting `PATH`, stub dir, and `CLAUDE_CODE_EXECPATH` only), because CI has neither variable and a developer shell may have both; the stub `claude` on PATH must win only when `CLAUDE_CODE_EXECPATH` is unset or non-executable. Add the non-executable case and the no-`x.y.z` case, since the spec lists both as fallback triggers but tests only two.
7. Test row 2, "floor check no longer reads `claude --version` directly": the section will legitimately still contain `claude --version` inside the host block. The assertion must be scoped to the prose floor paragraph (the line currently at `:333-334`), not the whole section.
8. Reword the 1g introduction at `commands/v-init.md:299` ("one of three states"); it is already stale.
9. Step 2's vault bullet (`:360-367`): the desktop-inert state must not offer `/plugin configure` as a remedy; the restart sentence (spec change 3) goes there.
10. Decide, in the spec, the two sibling defects of the same class: `commands/v-init.md:255` (step 1f) and `hooks/session-banner.sh:84`. Either in scope or listed under "Out of scope" by name.
11. Do not change the three CI-CLI selectors in `tests/test-*-mod.sh`; they correctly use PATH.
12. README sentences (`plugins/compound-v-vault/README.md`): add under Requirements/Setup; a test substring must be fixed in the spec so row 2 can grep it (the spec says "carries the desktop and restart sentences" without naming the strings).

## 8. File Touch Map

| File | Change | Shared |
|---|---|---|
| `commands/v-init.md` (1g, Step 2 vault bullet) | host-version block, desktop state, restart text, stale "three states" | no |
| `plugins/compound-v-vault/README.md` | desktop + restart sentences | no |
| `tests/test-vault-mod.sh` | two new rows; existing row at 116-144 must stay green | no |
| `hooks/session-banner.sh`, `commands/v-init.md` 1f | only if constraint 10 puts them in scope | no |
| `CHANGELOG.md` | release entry if the plugin version bumps | SHARED RESOURCE (append-order file) |
| `.claude-plugin/marketplace.json`, `plugins/compound-v-vault/.claude-plugin/plugin.json` | only if the vault version is bumped; versions must stay in lockstep (test at `test-vault-mod.sh:100`); spec says no vault code change, so no bump expected | SHARED RESOURCE |
