---
name: v-init-1g-map
description: Where /v:init step 1g lives, which test row pins it, and which siblings read the PATH claude version
metadata:
  type: reference
---

Map facts as of 2026-10-08. Leads, not verdicts: re-verify.

- `/v:init` step 1g (Jev vault) is prose in `commands/v-init.md` (### 1g, ends at `## Step 2`); the only test pinning it is the `init_check` python block in `tests/test-vault-mod.sh` (joins all bash blocks of the section; fails on `inputs`, on an unfiltered `plugin configure` line, and on a missing `disabled:`, `/egress allow`, `2.1.287`, `/plugin enable`).
- Same PATH-`claude --version` defect class as 1g: `commands/v-init.md` step 1f and `hooks/session-banner.sh` (version floor warning). The three `tests/test-*-mod.sh` CI-CLI selectors use PATH on purpose.
- No code anywhere reads `CLAUDE_CODE_EXECPATH` / `CLAUDE_CODE_ENTRYPOINT`; the `claude-desktop` value was never recorded as observed in the repo (only in the research handoff as a decided direction).
