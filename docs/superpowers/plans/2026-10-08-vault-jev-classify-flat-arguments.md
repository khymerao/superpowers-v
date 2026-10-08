# jev_classify Flat Arguments Implementation Plan

> **For agentic workers:** executed by Compound V on Engine C from one manifest
> (`docs/superpowers/execution/2026-10-08-vault-jev-classify-flat-arguments/manifest.yaml`). Steps use checkbox (`- [ ]`) syntax.

**Goal:** `jev_classify` reads `request_file` flat from the `tool.call` event, as Claude Code delivers it, and the tests
exercise that shape so they fail on the old handler.

**Architecture:** One implementation job (handler, header comment, test helper, regression row), then a deep three-pass review.

**Tech Stack:** TypeScript function-hooks module, `claude plugin test`, bash test runner.

**Spec:** `docs/superpowers/specs/2026-10-08-vault-jev-classify-flat-arguments-design.md`.
**Audits:** `docs/superpowers/archaeology/2026-10-08-2026-10-08-vault-jev-classify-flat-arguments-design.md`,
`docs/superpowers/library-audit/2026-10-08-2026-10-08-vault-jev-classify-flat-arguments-design.md` (1B skipped: internal plumbing).

## Global Constraints

- Contract source: the engine types (`ToolCallInput`: the tool's arguments spread beside `tool`, `e.command` for Bash);
  `$.tool.call` takes the same flat shape.
- No fallback to `e.input` in the handler. The hook passes `e.request_file` (the narrow form); `serveTool` takes the
  value, drops the `isRecord` unwrap, and keeps its own `typeof === 'string'` and absolute-path checks, because whether
  the engine enforces `inputSchema` before `tool.call` is unverified (1C §6.2).
- `isDisabled` still runs before the argument is read (1A §7.3). `tool.check` handling, if any, is untouched.
- The registration `tool.call{tool=mcp__compound-v-vault__jev_classify}` stays as is (`tests/test-vault-mod.sh:41`).
- No version bump: the vault stays `0.1.0`; the cv-dev refresh is an uninstall and install, which drops the cached copy.
- The pinned CLI (`PIN=2.1.289`) must also pass the suite (CI uses it); run it once through npx on a staged copy. If it
  fails only on the flat shape, stop and report instead of moving the pin.
- No key-shaped literal in `plugins/compound-v-vault` (the existing grep row).
- No version bump, CHANGELOG or release. Commit subjects are plain sentences, no Co-Authored-By trailer.

## Partition Map

| Job | Files (write) |
|---|---|
| `flat-args` | `plugins/compound-v-vault/hooks/vault.tsx`, `plugins/compound-v-vault/.tests/vault.test.tsx` |
| `spec-review` | `docs/superpowers/dogfood/2026-10-08-vault-jev-classify-flat-arguments-review.md`, `.claude/agent-memory/superpowers-v-spec-reviewer/**` |

No shared resources; no Task 0.

## Task A — flat-args

- [ ] **A1 Test first.** In `.tests/vault.test.tsx`, change the `toolCall` helper to `$.tool.call({ tool: TOOL, request_file })`.
  Add one test: a call whose argument sits under `input` (`$.tool.call({ tool: TOOL, input: { request_file: REQ_FILE } })`)
  answers exactly `refused: request_file must be an absolute path` and sends no fetch, and the same valid file passed
  flat returns `RESP_FILE` and sends one fetch. Describe the nested refusal as the handler's check, not schema
  enforcement. No `sk-or-` literal in new text.
- [ ] **A2 Watch it fail.** `bash tests/test-vault-mod.sh` fails on the current handler (tool tests refused).
- [ ] **A3 Fix.** In `hooks/vault.tsx`, the `tool.call` hook passes the event's `request_file` to `serveTool` (no `e.input`).
  Extend the `$.tool.register` header comment (lines 23-25): arguments arrive flat on the `tool.call` event (typings
  2.1.293, early access).
- [ ] **A4 Green.** `bash tests/test-vault-mod.sh` passes, all previous tests plus the new one.
- [ ] **A4b Pinned CLI.** Run the staged suite once with `npx -y @anthropic-ai/claude-code@2.1.289 plugin test`.
- [ ] **A5 Revert check.** Temporarily restore `e.input` in the handler, confirm the suite fails, restore the fix.
- [ ] **A6 Commit** on the job's lane.

## Review Gate — spec-review

Three passes (SPEC, QUALITY, INTEGRATION) against the spec's AC-1..AC-4, each AC run on the merged tree.
