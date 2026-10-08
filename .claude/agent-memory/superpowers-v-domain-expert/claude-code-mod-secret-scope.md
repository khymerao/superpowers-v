---
name: claude-code-mod-secret-scope
description: Claude Code userConfig secrets reach every settings hook of the plugin, and a mod answering tool.call skips plugin PreToolUse hooks (lane-guard), permissions and the sandbox
metadata:
  type: reference
---

Two domain constraints, verified 2026-10-05 against code.claude.com docs:

1. `CLAUDE_PLUGIN_OPTION_<KEY>` is "exported to hook processes for every option", sensitive ones included
   (https://code.claude.com/docs/en/plugins-reference). A secret in superpowers-v's own userConfig reaches
   lane-guard.sh and every other hook in hooks/hooks.json. It does NOT reach the Bash tool env.
2. A mod `tool.call` hook that returns `{ result }` without `next(e)` keeps plugin `PreToolUse` hooks from
   running, shows no permission prompt, and the process it starts runs outside the sandbox
   (https://code.claude.com/docs/en/plugins/mods/events, /mods/overview).

**How to apply:** treat these as leads when any spec puts a key in userConfig or has a mod run commands. Re-verify
the docs (mods need ≥2.1.287; behaviour may move). Detail: docs/superpowers/expert/_knowledge-base/claude-code-plugin-secrets.md.
Related: [[system-one-classifier-calibration]]
