# Claude Code Plugin Secrets (userConfig / mods) Knowledge Base

Maintained by Compound V Phase 1B advisor. Append at the bottom on each pass.

---

## Updated 2026-10-05 - key vault for a hosted classifier (Jev foundation audit)

### Where a `userConfig` value goes

| Consumer | Sensitive value reaches it? | Source |
|---|---|---|
| Secure storage (keychain / credentials file) | stored there instead of `settings.json` | [manifest reference](https://code.claude.com/docs/en/plugins-reference) |
| **Every settings-hook process of the plugin** | yes, as `CLAUDE_PLUGIN_OPTION_<KEY>` ("exported to hook processes for every option"), plus their children | same |
| Exec-form hook `args`, MCP/LSP config | yes, via `${user_config.KEY}` | same |
| Skill/agent content | no, placeholder | same |
| Shell-form hook command, monitor, MCP `headersHelper` | `${user_config.*}` rejected; monitors and headersHelper get no option env | same |
| Bash tool (main session or subagent) | **no**: the variables "aren't present in the environment of commands Claude runs through the Bash tool" | same |
| A mod's `register(on, options)` | yes, `options` holds the userConfig values | [mods reference](https://code.claude.com/docs/en/plugins/mods/reference) |

Implication: putting a secret in `userConfig` of a plugin that also has settings hooks gives the secret to all of those hooks. To scope a secret to one process, use a separate plugin with no settings hooks, or have each hook unset the variable.

### Mod `tool.call` short-circuit: what it skips

- Returning `{ result }` without `next(e)`: "no permission prompt appears and the tool doesn't run".
- "A mod that answers `tool.call` without calling `next` keeps [plugin and non-managed `PreToolUse` hooks] from running." Managed-settings `PreToolUse` hooks still run first.
- "a process that a mod starts runs outside [the sandbox]".

Sources: [mods events](https://code.claude.com/docs/en/plugins/mods/events), [mods overview](https://code.claude.com/docs/en/plugins/mods/overview).

### Where mods run / do not run

- Require Claude Code ≥ 2.1.287, on by default. `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS` is ignored from 2.1.287 on.
- Hooks run in the terminal, Desktop Code tab, VS Code chat, `claude -p`, Agent SDK, Remote Control, and cloud sessions (if the plugin reaches them). Not in Desktop WSL sessions.
- Off under `--safe-mode`, `disableAllHooks`, managed `allowManagedModsOnly`. An org guard can refuse a mod at `plugin.register` after reading `e.uses` (incl. env vars).
- Limits: hook own time 10 s; `$.process.run` 30 s default, 10 min max.

Sources: [mods overview](https://code.claude.com/docs/en/plugins/mods/overview), [mods reference](https://code.claude.com/docs/en/plugins/mods/reference).

### Known storage gaps (both closed as not planned)

- [#62442](https://github.com/anthropics/claude-code/issues/62442): sensitive `userConfig` not persisted across restart (reported on 2.1.150, macOS). Re-verify on the current version before relying on persistence.
- [#79124](https://github.com/anthropics/claude-code/issues/79124): no way to supply plugin `userConfig` secrets to cloud sessions.

### Key hygiene (OpenRouter)

- Set a credit limit on every key. OpenRouter is a GitHub secret-scanning partner and emails on detected exposure (no auto-revoke stated) ([OpenRouter auth](https://openrouter.ai/docs/api_reference/authentication)).
