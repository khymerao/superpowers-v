# Claude Code Plugin Root Library Knowledge Base

Maintained by Compound V Phase 1C validator. Append at the bottom.

---

## Updated 2026-10-08 - plugin-root-resolver-design

Sources (fetched 2026-10-08, WebFetch; Context7 needed OAuth, not used): https://code.claude.com/docs/en/plugins-reference (Environment variables), https://code.claude.com/docs/en/plugins/loading (Find plugins on disk, Cleanup of previous versions, Versions and updates), https://code.claude.com/docs/en/env-vars (CLAUDE_CODE_PLUGIN_CACHE_DIR), https://code.claude.com/docs/en/plugins/cli-reference.

- 2026-10-08: `${CLAUDE_PLUGIN_ROOT}` resolves inline "anywhere in the Markdown body" of skill, command and agent content; Claude Code substitutes the path when it loads the content. Docs: "The variables aren't present in the environment of commands Claude runs through the Bash tool, in the main session or in a subagent. In skill, command, and agent content, write the `${...}` reference in the Markdown body instead". Only the exact `${NAME}` form is documented; a `${NAME:-default}` form is not documented as substituted.
- 2026-10-08: Env-var export of CLAUDE_PLUGIN_ROOT is to hook commands, MCP stdio servers and LSP servers only (monitor commands: not exported).
- 2026-10-08: Plugins root is `~/.claude/plugins` unless `CLAUDE_CODE_PLUGIN_CACHE_DIR` is set ("sets the parent directory, not the cache itself"). Layout `cache/<marketplace>/<plugin>/<version>/`.
- 2026-10-08: `installed_plugins.json` (under the plugins root) "records each install with its `scope`, `installPath`, and `version`". Documented file. `settings.json` `enabledPlugins` holds enabled state, merged across six sources by precedence; the CLI is the only documented merger of them.
- 2026-10-08: `claude plugin list --json` is named in docs ("the id ... is what you see in settings files and in `claude plugin list --json`") but no page fetched documents its field names or a minimum version. `--json` on install/uninstall/update/enable/disable requires >= 2.1.268. The `installPath`/`enabled` fields were observed locally per the spec, not in docs.
- 2026-10-08: Version string is NOT necessarily numeric: manifest `version` first, else marketplace-entry `version`, else a 12-char commit SHA, a SHA-256 prefix, or the literal `unknown`.
- 2026-10-08: Replaced version directories get an `.orphaned_at` marker and are deleted by a background sweep 14 days later; so superseded copies coexist on disk for up to 14 days, and the sweep runs only while `installed_plugins.json` records at least one install.
- 2026-10-08: `--plugin-dir`, `--plugin-url`, `CLAUDE_CODE_PLUGIN_DIRS` plugins (id `@inline`) load in place and never appear in the cache; a relative-path plugin from a locally-added marketplace also loads in place.
- 2026-10-08: Same manifest name from several origins: `--plugin-dir` beats installed marketplace plugin silently.
- 2026-10-08: `${CLAUDE_PROJECT_DIR}` documented as "The project root" for hook commands and LSP; not in the Bash tool environment.
