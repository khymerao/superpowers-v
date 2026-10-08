# /v:init Vault Host and Desktop Implementation Plan

> **For agentic workers:** executed by Compound V on Engine C from one manifest
> (`docs/superpowers/execution/2026-10-08-v-init-vault-host-and-desktop/manifest.yaml`). Steps use checkbox (`- [ ]`) syntax.

**Goal:** `/v:init` step 1g gates the vault on the Claude Code that runs the session, reports the vault as inert in the
desktop app, and says that a new key needs a restart; the vault README says the same.

**Architecture:** One implementation job (command prose, README, two test rows), then a deep three-pass review.

**Tech Stack:** Markdown command prose with fenced bash, bash test rows with stub binaries.

**Spec:** `docs/superpowers/specs/2026-10-08-v-init-vault-host-and-desktop-design.md`.
**Audits:** `docs/superpowers/archaeology/2026-10-08-2026-10-08-v-init-vault-host-and-desktop-design.md`,
`docs/superpowers/library-audit/2026-10-08-2026-10-08-v-init-vault-host-and-desktop-design.md` (1B skipped: internal plumbing).

## Global Constraints

- `CLAUDE_CODE_EXECPATH` and `CLAUDE_CODE_ENTRYPOINT` are undocumented: the step never fails when either is unset,
  empty or malformed. Live capture, desktop Code tab, 2026-10-08: `CLAUDE_CODE_ENTRYPOINT=claude-desktop`,
  `CLAUDE_CODE_EXECPATH=~/Library/Application Support/Claude/claude-code/2.1.293/<hash>/claude.app/Contents/MacOS/claude`,
  whose `--version` prints `2.1.293 (Claude Code)`. Terminal transcripts record `entrypoint: cli`.
- Host-version block, one fenced bash block in 1g: run `"$CLAUDE_CODE_EXECPATH" --version` only after `[ -x ]`, with
  `</dev/null`, under `python3 "$CV/scripts/compound-v-run-with-timeout.py" --timeout 5 --`; take the first anchored
  `x.y.z`; otherwise fall back to `claude --version` (same timeout); otherwise `unknown`. It prints the version and its
  source on one line: `<x.y.z> host`, `<x.y.z> path` or `unknown`. The directory name of the path is never the primary
  source. It never reads `claude plugin configure` output.
- `unknown` never passes the 2.1.287 floor: report `installed, host version unknown (the vault needs Claude Code 2.1.287
  or newer)`.
- Desktop: only the exact value `CLAUDE_CODE_ENTRYPOINT=claude-desktop` selects the state `installed, inert in the
  desktop app (observed 2026-10-08 on the bundled 2.1.293: the vault does not receive its key there) - use Jev from a
  terminal claude`. Worded as observed behaviour, not a documented guarantee. Do not use `CLAUDECODE` or
  `CLAUDE_CODE_CHILD_SESSION`. No gist is cited as the contract.
- State order: `absent`, `disabled`, desktop inert, host version unknown, below the floor, key not set or unknown, key
  set. The key probe is skipped in the desktop case. Fix the stale intro line ("one of three states").
- Step 2's vault bullet: on a desktop host it does not offer `/plugin configure` in place; it says to run it in a
  terminal `claude`. Everywhere the key is entered or changed, say it takes effect in a new session (restart `claude`).
- Step 1f's `/skill-doctor` floor reads the host version from the 1g block instead of `claude --version`.
- `hooks/session-banner.sh:84` has the same defect; out of scope (not in this lane), recorded as a follow-up.
- The filtered key probe and the existing 1g test row (`tests/test-vault-mod.sh:116-144`) stay green and unchanged in
  intent. Never read, print, request or forward the key value.
- README: one sentence on the desktop limitation (observed, dated), one on the restart.
- No version bump, CHANGELOG or release. Commit subjects are plain sentences, no Co-Authored-By trailer.

## Partition Map

| Job | Files (write) |
|---|---|
| `host-desktop` | `commands/v-init.md`, `plugins/compound-v-vault/README.md`, `tests/test-vault-mod.sh` |
| `spec-review` | `docs/superpowers/dogfood/2026-10-08-v-init-vault-host-and-desktop-review.md`, `.claude/agent-memory/superpowers-v-spec-reviewer/**` |

No shared resources; no Task 0.

## Task A — host-desktop

- [ ] **A1 Tests first.** In `tests/test-vault-mod.sh` add row 1: extract the host-version block from step 1g (by a
  stable marker comment in the block) and run it with `CV=$REPO_ROOT`, an explicit environment and stubs in a temp
  dir: stub EXECPATH printing `2.1.286 (Claude Code)` and stub `claude` on `PATH` printing `2.1.289 (Claude Code)` →
  `2.1.286 host`; EXECPATH unset → `2.1.289 path`; EXECPATH stub printing no version → `2.1.289 path`; EXECPATH
  pointing at a non-executable file → `2.1.289 path`; neither yields a version → `unknown`.
  Row 2: step 1g names `CLAUDE_CODE_ENTRYPOINT`, `claude-desktop`, the desktop-inert state and the host-unknown
  state; the floor paragraph (not the whole step) no longer runs `claude --version`; step 1f uses the host block; the
  README carries the desktop and restart sentences.
- [ ] **A2 Watch them fail** on the current tree.
- [ ] **A3 Implement** the 1g block, states, Step 2 bullet, 1f reference and README sentences.
- [ ] **A4 Green.** `bash tests/test-vault-mod.sh` and `python3 -B scripts/lint-frontmatter.py .` pass.
- [ ] **A5 Revert checks.** Swap the block's EXECPATH branch for plain `claude --version`: row 1 fails. Drop the
  desktop state or either README sentence: row 2 fails. Restore.
- [ ] **A6 Run the block live** once in this session and quote its output.
- [ ] **A7 Commit** on the job's lane.

## Review Gate — spec-review

Three passes (SPEC, QUALITY, INTEGRATION) against AC-1..AC-4. Cite the live capture above in the review record.
