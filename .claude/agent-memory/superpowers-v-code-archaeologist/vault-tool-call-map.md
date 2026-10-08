---
name: vault-tool-call-map
description: Where the vault tool.call hook, its test helper and the CLI pin live, and the couplings that decide a vault fix
metadata:
  type: reference
---

Map facts as of 2026-10-08. Leads, not verdicts: re-verify.

- The only `tool.call` hook is `plugins/compound-v-vault/hooks/vault.tsx` (`on('tool.call', { tool: 'mcp__compound-v-vault__jev_classify' }`); its test helper `toolCall` is in `plugins/compound-v-vault/.tests/vault.test.tsx`. Only 9 of 32 tests go through it; the 7 `REFUSALS` rows match `^refused: ` only, so they pass vacuously if the reader is broken.
- CI pin for the vault tests is `PIN` in `tests/test-vault-mod.sh` (2.1.289), floor 2.1.287; the same floor is repeated in the vault README, `commands/v-init.md` 1g and the marketplace description. A fix that depends on a newer CLI behaviour touches all of them.
- `plugin.json` and `.claude-plugin/marketplace.json` versions must match (shell test enforces lockstep).
- In an agent run with a bash clamp, Bash is limited to git log/show/blame and memory-script commands; use Grep/Glob/Read.
