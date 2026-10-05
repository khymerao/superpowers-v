---
name: drift-jev-and-mods
description: Dated version/API drift facts for TypeSafe Jev via OpenRouter and Claude Code mods, checked 2026-10-05
metadata:
  type: reference
---

Leads only; re-verify before reuse. Detail in `docs/superpowers/library-audit/_knowledge-base/typesafe-jev-openrouter.md` and `claude-code-mods.md`.

- 2026-10-05: Jev current is `jev-1.13.0`; `jev-latest` and `jev-preview` alias it. OpenRouter path `/api/v1/systemone` (doc-derived, not live-verified).
- 2026-10-05: Choice `criteria` is a map option -> description; questions are a named object; Noul answer is a single `noul` float.
- 2026-10-05: Claude Code mods need >= 2.1.287, on by default; `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS` ignored since then. Repo AGENTS.md floor (2.1.219) predates mods.
- 2026-10-05: `$.process.run` takes argv; official docs show `init` = cwd, timeoutMs only (env unconfirmed).
- 2026-10-05: `userConfig` sensitive values still export as `CLAUDE_PLUGIN_OPTION_<KEY>` to all plugin hook processes.
- 2026-10-05: Context7 tools were not surfaced by ToolSearch in this Workflow-spawned run (only a failed tessl server was named); fallback was WebFetch. Same result in the later review-fixes run (two ToolSearch queries, empty); Bash was clamped to memory/git forms, so use Read/Grep.
- 2026-10-05: `compound-v-jev.py` parser ignores vault `reason` when `http_status` is non-2xx (routes by `_classify_http`); `prune` unlinks old symlinks via lstat. Check lines before reuse.
