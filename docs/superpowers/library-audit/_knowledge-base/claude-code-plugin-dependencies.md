# Claude Code Plugin Dependencies Knowledge Base

Maintained by Compound V Phase 1C validator. Append at the bottom.

---

## Updated 2026-10-05 - vault-as-dependency-design

Sources (fetched 2026-10-05): https://code.claude.com/docs/en/plugins-reference (manifest reference), /docs/en/plugin-dependencies, /docs/en/plugins/install, /docs/en/plugins/marketplace-reference, /docs/en/plugins/loading, /docs/en/plugins/troubleshooting, /docs/en/plugins/cli-reference, CHANGELOG.md on github.com/anthropics/claude-code (newest 2.1.289). Context7 unavailable (needs authentication); WebFetch only.

- `dependencies` in plugin.json or marketplace entry: `"name"`, `"name@marketplace"` or `{name, marketplace, version}`. Bare name resolves in the declaring plugin's own marketplace. Honoured from plugin.json even if the entry omits it since 2.1.110 (changelog via search, not read in full).
- Install: dependencies are installed and enabled at the same scope; success message lists them. Uninstall leaves auto-installed dependencies until `claude plugin prune`. Disable of a needed plugin is refused. A missing/disabled/out-of-range dependency leaves the dependent plugin disabled (`Dependency "<dep>" is not installed` / `is disabled` / `Requires "<dep>" <range>, installed <v>`).
- Version constraints resolve against git tags `<plugin>--v<version>`; a relative-path plugin falls back to the marketplace's current copy when no tag matches. Cross-marketplace needs `allowCrossMarketplaceDependenciesOn` in the root marketplace.
- `claude plugin validate` has no documented check that a `dependencies` name exists in the marketplace. Entry `version` vs `plugin.json` version mismatch is a warning (plugin.json wins).
- userConfig prompt: documented for the installed plugin only (`/plugin install` in a session, Discover tab). `claude plugin install` in a shell never prompts and prints `N userConfig options not yet set`. Dependency prompting is UNDOCUMENTED. `/plugin configure <plugin>@<marketplace>` and `claude plugin configure` (full id only) need >= 2.1.285. Sensitive options are not `/config` rows.
- An unrecognized top-level plugin.json field is stripped silently (warning only in `validate`).
- Relative-path plugins in a local-path marketplace load in place; no cache copy, edits apply at next session or `/reload-plugins`.
