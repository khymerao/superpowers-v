# Domain audit: compound-v-vault as a declared dependency of superpowers-v

Phase 1B (domain expert), 2026-10-05. Spec under audit:
`docs/superpowers/specs/2026-10-05-vault-as-dependency-design.md`. Trigger 0 recon: none (`kb_skip`).

## 1. Domain(s) Identified

- **claude-code-plugin-dependencies**: `plugin.json` `dependencies`, how a dependency is installed, enabled,
  disabled, updated and pruned, and how bare names resolve in a marketplace.
- **claude-code-plugin-secrets**: where a dependency's sensitive `userConfig` value gets entered and stored,
  and when it is deleted. This is already a KB domain (`_knowledge-base/claude-code-plugin-secrets.md`).
- **claude-code-marketplace-versioning**: the plugin cache key, relative-path sources, and auto-update.

There is no regulatory domain. The OpenRouter key-hygiene rule already in the KB still applies unchanged.

## 2. Sources Consulted

**V-memory.** The emit-time recall block, plus one search of my own ("plugin dependencies marketplace install
compound-v-vault"). It returned the spec itself and the Jev foundation plan's Task D and Task R. Task R had
already planned the marketplace entry `source: "./plugins/compound-v-vault"` at `0.1.0`. No prior decision
contradicts the spec.

**KB reused:** `docs/superpowers/expert/_knowledge-base/claude-code-plugin-secrets.md` (2026-10-05, primary
sources). **Agent memory:** `claude-code-mod-secret-scope.md`. It is a lead only. I re-checked it against the
manifest reference, and the quote below still holds.

**Primary docs fetched (2026-10-05):**
- [Plugin manifest reference](https://code.claude.com/docs/en/plugins-reference): `dependencies`, `defaultEnabled`,
  `userConfig`, `CLAUDE_PLUGIN_OPTION_<KEY>`
- [Plugin dependencies](https://code.claude.com/docs/en/plugins/dependencies)
- [Install and manage plugins](https://code.claude.com/docs/en/plugins/install), § Plugins with dependencies
- [Plugin commands reference](https://code.claude.com/docs/en/plugins/cli-reference): `uninstall`, `prune`,
  `configure`, `disable`, `enable`
- [Troubleshoot plugins](https://code.claude.com/docs/en/plugins/troubleshooting): § Dependency errors, § The
  `userConfig` dialog never appears
- [Plugin loading reference](https://code.claude.com/docs/en/plugins/loading): versions, cache, in-place loading
- [Marketplace reference](https://code.claude.com/docs/en/plugins/marketplace-reference) and
  [Create a marketplace](https://code.claude.com/docs/en/plugin-marketplaces)
- [Claude Code changelog](https://code.claude.com/docs/en/changelog): entries for 2.1.283 to 2.1.288

**Practitioner layer (GitHub issues, anthropics/claude-code):**
- [#89749](https://github.com/anthropics/claude-code/issues/89749): open, 2026-08-26, 2.1.246. `userConfig` is never
  collected when the plugin is installed from VS Code or the Desktop Code tab.
- [#68449](https://github.com/anthropics/claude-code/issues/68449): closed as not planned, 2026-06-14. An
  auto-installed dependency resolves only its own first dependency. The vault declares no dependencies, so this
  does not apply. I checked it and set it aside.
- [#39827](https://github.com/anthropics/claude-code/issues/39827) and
  [#39455](https://github.com/anthropics/claude-code/issues/39455): `userConfig` not prompted on install or enable
  in the terminal. #89749 says #39455 was fixed in 2.1.233.

**Audience layer:** a `site:reddit.com` search returned nothing relevant. The audience is plugin authors and
their users, and for them the practitioner channel is GitHub issues. Nothing below is presented as a community
consensus.

**Searches run:** a changelog query for when dependencies arrived, a GitHub issues query on userConfig and
dependency install, a Reddit query on dependencies and prune, and a query on the userConfig dialog for a
dependency.

## 3. Domain Constraints the Brainstorm Probably Missed

- **MUST NOT tell anyone to disable the vault to turn Jev off.** Once superpowers-v depends on the vault,
  disabling the vault breaks superpowers-v:
  - Install page: "**Disable**: when another enabled plugin still needs the one you named, Claude Code refuses
    and prints a chained command that disables both in the right order."
  - Troubleshooting: `Dependency "<dep>" is disabled`. The dependent plugin installs but stays disabled.
  - Loading page: a `false` at a higher-precedence scope (project `.claude/settings.json`, `.claude/settings.local.json`,
    managed) overrides a lower one.

  So a repository or user that sets `"compound-v-vault@procoders": false` gets no superpowers-v in that scope.
  The only supported way to turn Jev off is to leave the key unset or deny egress.
- **MUST treat the install dialog as unverified for a dependency's options.** The docs promise the dialog for the
  plugin being installed ("`/plugin install` in a session ... the dialog is part of this interactive install").
  Nothing says it also opens for the `userConfig` of an auto-installed dependency. `claude plugin install` from the
  shell "never prompts for `userConfig` values" and prints `N userConfig options not yet set — run /plugin
  configure <plugin>@<marketplace>` (troubleshooting). VS Code and Desktop have an open bug (#89749). The
  dependable path is `/plugin configure compound-v-vault@procoders`. `configure` "takes only the qualified form"
  (cli-reference), so the README must not write a bare `/plugin configure` (spec Change 3).
- **MUST accept that without a version bump, existing installs never see the dependency.** "a manifest that pins
  `"version": "1.0.0"` keeps every user on the cached copy until its author changes the string" (loading page).
  `superpowers-v` pins `3.8.3` in both manifests. Auto-update is "off for every other marketplace", which includes
  `procoders`. Until a release bumps the version, only fresh installs, and marketplaces added from a local
  directory (which load in place), pick up `dependencies`. After the bump, existing users run `claude plugin
  update superpowers-v@procoders` and then `/reload-plugins` to install the new dependency (dependencies page, "Update
  manually").
- **MUST keep the dev flow working.** With `--plugin-dir`, the dependent "stops loading whenever the local copy is
  disabled or absent". The error then "reports the dependency as not installed" (dependencies page). The
  parent-folder shortcut only applies "If the folder isn't itself a plugin", and the repository root is a plugin.
  So `claude --plugin-dir .` alone now leaves superpowers-v unloaded. The fix is `--plugin-dir . --plugin-dir
  plugins/compound-v-vault`, and the spec's Changes list does not cover the README Development section.
- **MUST keep the marketplace entry `version` equal to the vault's `plugin.json` version (`0.1.0`), or leave it
  out.** Marketplace reference: "`Entry declares version "x" but <path>/plugin.json says "y". At install time,
  plugin.json wins`" is a warning, and `--strict` turns warnings into failures.
- **SHOULD tell users how to remove the vault and its secret.** "Uninstall: auto-installed dependencies stay until
  you run `claude plugin prune`" (install page). Uninstalling from the last scope "also deletes the plugin's stored
  options and secrets" (cli-reference). So after uninstalling superpowers-v, the OpenRouter key stays in the
  credential store until the user runs `claude plugin uninstall superpowers-v@procoders --prune` or
  `claude plugin prune`. Prune "never removes a plugin you installed yourself". A user who installed the vault by
  hand before this change keeps it.
- **SHOULD know the dependency is enabled whatever its default says.** "A plugin that an enabled plugin depends
  on starts enabled regardless" (manifest reference, `defaultEnabled`). The vault's mod therefore loads in every
  superpowers-v session. That is acceptable only because the vault is inert without a key, which is the spec's
  own premise.
- **Holds as designed:** a bare name "resolve[s] against this plugin's own marketplace" (manifest reference). A
  same-marketplace dependency needs no `allowCrossMarketplaceDependenciesOn`. The dependency installs "at the same
  scope" (install page).

## 4. Common Traps in This Domain

1. **A disable becomes a kill.** An old `false` for the vault in any settings file silently takes superpowers-v
   down with it. `claude plugin list` shows the error, but no session banner does.
2. **"Pushed" is not "delivered."** A pinned `version` hides every commit, including a manifest change. The
   maintainer's own local-directory marketplace loads in place and shows the change, which hides the problem from
   the maintainer.
3. **The surface decides whether a prompt appears.** Session `/plugin install` prompts, shell `install` never
   does, and VS Code and Desktop are unreliable (#89749). A README that promises a dialog misleads most users.
4. **Orphaned secrets.** Uninstalling the dependent leaves the dependency's keychain secret behind until
   `prune` runs.
5. **Nested plugin in a root-sourced plugin.** `superpowers-v` has `source: "./"`, so its cache copy
   (`cache/procoders/superpowers-v/<version>/`) also contains `plugins/compound-v-vault/`. That copy is dead weight
   and is not loaded. No documented path auto-loads a nested plugin from a cached plugin. The repository's existing
   guard is `.tests/` (tests/test-vault-mod.sh:54-57), which keeps vault test files out of the root plugin's
   `claude plugin test .`.
6. **Dependency failures do not show up in validation.** `claude plugin validate` does not resolve dependencies.
   They fail only at install or load time. AC-1 cannot prove the dependency works. Only AC-3 can.

## 5. Regulatory / Compliance Notes

- None statutory.
- **Organisational policy now couples the two plugins.** If an organisation blocks the vault (for example, a rule
  against plugins that hold third-party API keys), superpowers-v can no longer be installed there: "`Plugin
  "<name>" depends on "<dep>", which is blocked by your organization's policy`" (troubleshooting). This is a new
  failure mode for organisations that accepted superpowers-v before.
- The key-scoping rationale holds. `CLAUDE_PLUGIN_OPTION_<KEY>` is "exported to hook processes for every option"
  (manifest reference, re-checked 2026-10-05), and the variable is per plugin. Declaring a dependency does not
  move the vault's options into superpowers-v's hook environment. The docs scope the export to the plugin's own
  hook processes, and nothing on the dependency page says otherwise.

## 6. Recent Breaking Changes (last 12 months)

- Dependency enforcement: `disable` refuses while a dependent is enabled, and `enable` turns on its dependencies.
  Also `claude plugin prune` and `uninstall --prune`. **Secondary source only:** a search summary of
  gradually.ai dates enforcement to 2026-05-15 and prune to 2.1.121. I could not confirm this in the official
  changelog extract. Primary evidence that the feature predates the repository floor (2.1.219): the dependencies
  page describes 2.1.196 behaviour for constraint resolution.
- 2.1.287 (2026-10-01, changelog): "Improved plugin listings to note when a plugin's dependencies were not
  installed, and updating a plugin now retries an install that did not finish".
- 2.1.285 (changelog and cli-reference): `claude plugin configure <plugin>` from the shell, and a VS Code
  options form after install. Below 2.1.285, users have only the in-session `/plugin configure`.
- 2.1.265 (dependencies page): a parent folder passed to `--plugin-dir` loads child plugins, but only when the
  parent is not itself a plugin. That condition fails for this repository.

## 7. Design Constraints for the Plan

1. **MUST** state in both READMEs that the vault must stay enabled while superpowers-v is enabled. Jev is
   turned off by leaving the key unset or by `/egress` denial, never by `claude plugin disable compound-v-vault`.
   Disabling it is refused, or, set to `false` in a settings file, it disables superpowers-v.
2. **MUST** make `/plugin configure compound-v-vault@procoders` (qualified id) the primary documented way to set
   the key. The install dialog may be described only as "may appear in an interactive `/plugin install`". Also
   give the shell form for ≥ 2.1.285 (`claude plugin configure compound-v-vault@procoders --values-stdin`), and
   say that `claude plugin install` from a shell never prompts.
3. **MUST** add a dev-flow line to the root README's Development section: load both plugins,
   `claude --plugin-dir . --plugin-dir plugins/compound-v-vault`. Otherwise superpowers-v does not load.
4. **MUST** word the root README sentence as true only for installs that receive the new manifest. Until
   `superpowers-v`'s `version` changes, existing installs are unchanged. After a release, existing users run
   `claude plugin update superpowers-v@procoders` then `/reload-plugins`. The README must not imply that current
   users already have the vault.
5. **MUST** give the marketplace entry for `compound-v-vault` either no `version`, or exactly the `version` in
   `plugins/compound-v-vault/.claude-plugin/plugin.json` (`0.1.0`). The test row (spec Change 5) **SHOULD** also
   assert this equality, so that a later vault bump cannot drift the two apart.
6. **MUST** keep AC-3 out of the maintainer's credential store. Use a scratch `CLAUDE_CONFIG_DIR`, never pass
   `--config openrouter_key=…`, and never run `/plugin configure` in that config. Sensitive values go to "the
   platform's secure credential store" (manifest reference). Nothing shows that store is scoped by
   `CLAUDE_CONFIG_DIR`.
7. **MUST** have AC-3 assert the dependency through both outputs: the install summary ("The success message lists
   them", install page) and `claude plugin list` showing `compound-v-vault@procoders` enabled at the same scope as
   `superpowers-v@procoders`.
8. **MUST** run the existing `claude plugin validate .` and `claude plugin test .` callers
   (`tests/test-run-band-mod.sh`, `tests/test-jev-t3-mod.sh`) after the change, under AC-4. No doc covers how
   `plugin test` treats an unresolved dependency.
9. **SHOULD** document removal: `claude plugin uninstall superpowers-v@procoders --prune` removes the vault, and
   the vault's last-scope uninstall deletes the stored key. Plain uninstall leaves both behind.
10. **SHOULD** keep `dependencies` as the bare string `"compound-v-vault"` with no version range. A range on a
    relative-path dependency resolves against `compound-v-vault--v<version>` tags on this repository, and none
    exist. Without a tag, the install uses the current copy and checks the range at load time (dependencies page).
11. **MUST NOT** add `allowCrossMarketplaceDependenciesOn`. Same-marketplace resolution needs none.

## 8. Open Questions for the Human

1. Organisations that block the vault, or that set it to `false`, now lose superpowers-v entirely. Is that
   acceptable, or should the README name the only workaround, which is to not install superpowers-v there?
2. Is there an existing user with `compound-v-vault@procoders: false` in any settings file (the maintainer's
   machine, a project `.claude/settings.json`)? If so, that setting disables superpowers-v the moment the
   dependency is delivered.
3. Should the spec's "no version bump" hold, knowing the change then reaches only fresh installs? Or should this
   ship with the 3.9.0 release the foundation plan already scheduled (Task R)?
4. Does `claude plugin eval .`, the human-run release gate, resolve a declared dependency, or does it load
   superpowers-v as `@inline` and disable it with "dependency not installed"? The docs do not say. Someone
   should run one case before the next scored eval.
5. Does an interactive `/plugin install superpowers-v@procoders` actually open the vault's options dialog? AC-3
   runs from the shell, so it cannot answer this. Checking needs one manual in-session install with no key
   entered.

## 9. Knowledge Base Updates

- Appended `## Updated 2026-10-05 - plugin dependencies (vault-as-dependency audit)` to
  `docs/superpowers/expert/_knowledge-base/claude-code-plugin-secrets.md`. It holds a dependency lifecycle matrix
  (install, enable, disable, uninstall, prune, update), the dev-flow rule, the cache-version rule, and where a
  dependency's `userConfig` gets entered.
