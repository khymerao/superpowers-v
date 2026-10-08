---
name: drift-plugin-root
description: Dated facts on CLAUDE_PLUGIN_ROOT inline substitution, plugins-root override, installed_plugins.json and version formats, checked 2026-10-08
metadata:
  type: reference
---

Leads only; re-verify before reuse. Detail in `docs/superpowers/library-audit/_knowledge-base/claude-code-plugin-root.md`.

- 2026-10-08: docs say `${CLAUDE_PLUGIN_ROOT}` is substituted inline in skill/command/agent Markdown bodies, and is NOT in the Bash tool env; the `${VAR:-default}` form is not documented as substituted. Live test not run (Bash clamped).
- 2026-10-08: plugins root moves with `CLAUDE_CODE_PLUGIN_CACHE_DIR`; `installed_plugins.json` holds scope/installPath/version but no enabled flag; `claude plugin list --json` fields undocumented.
- 2026-10-08: plugin versions can be a SHA or `unknown`; replaced versions linger 14 days.
- 2026-10-08: Context7 needed OAuth (not absent) again.
