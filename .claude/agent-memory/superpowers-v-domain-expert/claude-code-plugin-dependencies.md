---
name: claude-code-plugin-dependencies
description: Claude Code plugin.json dependencies - disabling a dependency kills the dependent, --plugin-dir needs both, pinned version hides new deps, dependency userConfig dialog unverified
metadata:
  type: reference
---

Verified 2026-10-05 against code.claude.com docs (plugins/install, plugins/dependencies, plugins/loading,
plugins/cli-reference, plugins/troubleshooting):

1. Disabling a dependency is refused while a dependent is enabled. A settings `false` for it at a higher scope
   leaves the dependent disabled (`Dependency "<dep>" is disabled`).
2. `--plugin-dir .` alone fails when the root declares a dependency. Pass the dependency's dir too. The
   parent-folder shortcut is skipped when the parent is itself a plugin.
3. A pinned manifest `version` is the cache key: new `dependencies` reach existing users only after a bump.
4. Docs promise the install dialog only for the plugin being installed, not a dependency. Shell install never
   prompts. Use `/plugin configure <dep>@<marketplace>` (qualified only).
5. Uninstalling the dependent leaves the dependency and its secret until `claude plugin prune`.

**How to apply:** leads for any spec touching superpowers-v -> compound-v-vault packaging. Re-verify before citing.
Detail: docs/superpowers/expert/_knowledge-base/claude-code-plugin-secrets.md. Related: [[claude-code-mod-secret-scope]]
