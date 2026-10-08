---
name: drift-host-detection
description: Dated facts on CLAUDE_CODE_EXECPATH / CLAUDE_CODE_ENTRYPOINT documentation status and desktop plugin behaviour, checked 2026-10-08
metadata:
  type: reference
---

Leads only; re-verify before reuse. Detail in `docs/superpowers/library-audit/_knowledge-base/claude-code-host-detection.md`.

- 2026-10-08: neither `CLAUDE_CODE_EXECPATH` nor `CLAUDE_CODE_ENTRYPOINT` is in the official env-vars page; only third-party gists name them (`claude-desktop` listed in one gist only).
- 2026-10-08: `claude --version` output format is undocumented ("Output the version number"); newest Claude Code was 2.1.294.
- 2026-10-08: Context7 needed OAuth again (not absent); Bash clamped, so live env could not be read.
