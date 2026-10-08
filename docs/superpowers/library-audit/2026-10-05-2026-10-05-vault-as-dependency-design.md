# Library audit: vault as a declared dependency (2026-10-05)

Spec: `docs/superpowers/specs/2026-10-05-vault-as-dependency-design.md`. Phase 1C. Checked 2026-10-05.

## 1. Tools Available

- Context7: NOT USABLE. `ToolSearch context7` returned no tool; the session reports `plugin:context7:context7` as needing authentication (OAuth not started; the user must authorize it via `/mcp`). DEGRADED: WebFetch/WebSearch against code.claude.com docs and the claude-code CHANGELOG.
- Bash was clamped to memory/git forms, so `claude --version` and `claude plugin validate` were NOT run. Every statement below is documentation-derived, not behaviour-verified; AC-1/AC-3 remain the only live checks.
- V-memory recall: block in prompt only; it held nothing about plugin dependencies. Agent memory: `drift-jev-and-mods.md` (consistent, extended below).
- Manifests read: `.claude-plugin/plugin.json` (superpowers-v 3.8.3), `.claude-plugin/marketplace.json` (marketplace `procoders`, one entry, `source: "./"`), `plugins/compound-v-vault/.claude-plugin/plugin.json` (0.1.0). No package manifests apply. No Trigger 0 recon doc (`kb_skip`).

## 2. Libraries Mentioned

Platform features (Claude Code plugin system), not packages. Newest changelog entry seen: 2.1.289 (no date in the changelog file). Repo test pin: 2.1.289.

| Feature | Spec context | Current state (2026-10-05) | Repo state | Status |
|---|---|---|---|---|
| `plugin.json` `dependencies` | `["compound-v-vault"]` | Array of `"name"`, `"name@marketplace"` or `{name, marketplace, version}`; bare name resolves in the declaring plugin's own marketplace. Honoured in plugin.json even when the marketplace entry omits it since 2.1.110 (changelog, via search) | not present yet | 🟢 OK |
| marketplace `source: "./plugins/compound-v-vault"` | vault entry | Relative path from marketplace root, must start `./`, no `..`; loaded in place from a local-path marketplace | `superpowers-v` entry already uses `"./"` | 🟢 OK |
| `userConfig` `sensitive` | key entry | Secure credential store, masked, not a `/config` row; still exported as `CLAUDE_PLUGIN_OPTION_<KEY>` to every hook process of that plugin | vault declares `openrouter_key` sensitive | 🟢 OK |
| `/plugin configure <plugin>@<marketplace>` | key entry later | Exists, opens the userConfig dialog; shell form `claude plugin configure` and `--config KEY=VALUE` need 2.1.285 | not documented anywhere in repo | 🟡 floor, see F2 |
| mods (function hooks) | vault runtime | needs >= 2.1.287 (KB 2026-10-05) | root README states 2.1.219 floor; vault README states 2.1.287 | 🟡 see F3 |

## 3. API Signatures Verified

| Spec claim | Docs say | Verdict |
|---|---|---|
| `"dependencies": ["compound-v-vault"]`, bare name resolves against own marketplace | manifest reference `dependencies`: "Bare names resolve against this plugin's own marketplace" | Correct |
| Marketplace entry `{name, source: "./plugins/compound-v-vault", version, description}` | Entry fields `name`, `source`, `description`, `version` valid; entry `version` loses to `plugin.json` version and `validate` warns on mismatch | Correct, with F4 |
| Installing brings the vault, same scope | "Claude Code also installs and enables the plugin's declared dependencies at the same scope. The success message lists them." | Correct |
| Key "entered in the install dialog Claude Code opens for unset options" | Docs describe the dialog only for the plugin being installed. Nothing says a dependency's `userConfig` is prompted when it is auto-installed. Shell `claude plugin install` never prompts and prints `N userConfig options not yet set - run /plugin configure <plugin>@<marketplace>` | UNVERIFIED, probably wrong for the dependency. See F1 |
| `/plugin configure compound-v-vault@procoders` | `/plugin configure <plugin>` in the session table; `claude plugin configure` requires the full `name@marketplace` | Correct |
| Sensitive options not listed in `/config` | "each option ... appears as a row in `/config`, except `sensitive` options and `multiple` lists" | Correct. Vault README step 2 (`/config`) is wrong today, spec change 3 fixes it |
| Every `userConfig` value exported to every command hook of that plugin | "`CLAUDE_PLUGIN_OPTION_<KEY>`: exported to hook processes for every option" | Correct (spec premise holds) |
| Dependency cost is nil without a key | Not what the docs say about coupling, see F5 | Overstated |

## 4. Critical Findings 🔴

None.

## 5. High-Priority Findings 🟠

None by the maintenance scale. The two items below are the highest-risk spec claims.

**F1 (HIGH-risk claim, UNVERIFIED): the dependency's key prompt.** The spec (Decision bullet 4, Change 3, Change 4) tells users the key is entered in the install dialog. The documented dialog belongs to the plugin being installed (`superpowers-v` declares no `userConfig`). The docs never say an auto-installed dependency's `userConfig` is prompted. Shell installs (`claude plugin install`) are documented to never prompt, and a VS Code install before 2.1.285 showed no form. Plan for `/plugin configure compound-v-vault@procoders` as the only guaranteed path and treat "install dialog" as unproven until AC-3 observes it (AC-3 as written checks only `claude plugin list`, not the prompt).

**F5 (HIGH-risk design coupling): a dependency makes the vault load-critical.** Docs: a plugin whose dependency is not installed, disabled, or out of range "can fail to install, or install and stay disabled" (`Dependency "<dep>" is disabled`, `Dependency "<dep>" is not installed`). `claude plugin disable compound-v-vault` is refused while an enabled plugin needs it. So (a) a user cannot opt out of the vault without disabling `superpowers-v`, (b) a vault that fails to load or that an org blocks would take `superpowers-v` down with it, not only Jev. The spec's "costs nothing for anyone who does not use Jev" holds for the inert-without-key runtime path only. A managed-settings block of the vault, or a Claude Code < 2.1.287 (vault mod not loaded, see F3) are the realistic failure routes. Cross-check: the existing mod-load failure behaviour of the vault is not documented as "plugin still loads".

## 6. Medium Findings 🟡

**F2: version floor of the dependency feature and of `/plugin configure`.** `dependencies` in plugin.json is honoured from 2.1.110 per changelog (search summary, not fetched in full). `/plugin configure` and `claude plugin configure` need 2.1.285. A CLI that does not know `dependencies` strips the top-level key silently (unrecognized top-level fields are stripped, plugin loads), so the vault would not arrive and nothing would say so. The root README floor is 2.1.219; the spec states no floor for the new instructions. Not verified: whether 2.1.219 is above 2.1.110 only by number (it is), so the dependency feature is covered; `/plugin configure` is not.

**F3: floor mismatch for the vault.** The vault is a mod needing >= 2.1.287; `superpowers-v` supports >= 2.1.219. Installing the dependency on 2.1.219 to 2.1.286 satisfies the dependency but the vault's mod does not load (README: "older versions do not load it"). Dependency satisfied, Jev dead, no error documented. The README sentence the spec adds should state the 2.1.287 floor for Jev.

**F4: marketplace entry `version` drift.** Entry `version` for the vault must equal `plugins/compound-v-vault/.claude-plugin/plugin.json` (0.1.0 today). On mismatch `plugin.json` wins and `claude plugin validate` emits `Entry declares version "x" but <path>/plugin.json says "y"`, a warning that `--strict` turns into failure. Omitting the entry `version` removes the drift risk; the spec says to copy it. Also note the spec's "no version bump" is safe: with `plugin.json` version pinned at 0.1.0, edits to the vault are not delivered to installed copies until its version changes (applies to non-local marketplaces).

**F6: `claude plugin validate` does not check dependency resolution.** The marketplace validation table lists no message for a `dependencies` name absent from `plugins[]`. Failure appears only at install/load time. This confirms the need for the spec's test row (AC-2); AC-1 cannot catch it.

**F7: no version constraint is possible yet.** A constraint object (`{name, version}`) on a relative-path plugin resolves against git tags `compound-v-vault--v<version>` in the marketplace repository. No such tag exists and the spec adds none. A bare string is correct here.

**F8: stale existing doc.** `plugins/compound-v-vault/README.md:21` tells users to find the key in `/config`; sensitive options are not listed there. Spec change 3 already covers it.

## 7. Design Constraints for the Plan

MUST
- Declare the dependency as the bare string `"compound-v-vault"` (matches the docs' form; both plugins live in marketplace `procoders`).
- Make the vault entry's `name` in `marketplace.json` exactly `compound-v-vault`, equal to its `plugin.json` `name`, `source` starting `./`.
- Either omit the entry `version` or keep it byte-equal to the vault's `plugin.json` version.
- Document `/plugin configure compound-v-vault@procoders` as the guaranteed way to set the key, with the full `name@marketplace` form; state that it needs Claude Code >= 2.1.285 and that Jev needs >= 2.1.287.
- Make the new test row also fail on a name mismatch between the marketplace entry and the source directory's `plugin.json`, as the spec says, and run it against a staged copy so a removed `dependencies` entry is a real failure (AC-2).
- Have AC-3 additionally record whether a prompt for `openrouter_key` appears during the install (observe, do not assume).

MUST NOT
- State in README or vault README that the key is entered "in the install dialog" as fact, unless AC-3 observed it.
- Add a `version` constraint object to the dependency, or a `marketplace` field (no tags exist; cross-marketplace needs `allowCrossMarketplaceDependenciesOn`).
- Add `userConfig` to `superpowers-v`'s plugin.json to proxy the key (re-opens the `CLAUDE_PLUGIN_OPTION_*` exposure to its hooks).
- Claim the dependency is costless or opt-out-able; say the vault is inert without a key and cannot be disabled while `superpowers-v` is enabled.
- Tell users to look for the key in `/config`.

## 8. Open Questions for the Human

1. Is it acceptable that disabling or blocking `compound-v-vault` disables `superpowers-v` (F5)? If not, the alternative the platform offers is a recommendation (`relevance`) or documentation, not a dependency; that is a scoping decision.
2. Raise the documented Claude Code floor, or leave 2.1.219 and note the 2.1.287 floor for Jev only (F3)?
3. Is AC-3 allowed to use a pinned `npx @anthropic-ai/claude-code@2.1.289` in a scratch config dir when the local `claude` is older (as `tests/test-vault-mod.sh` does)?

## 9. Knowledge Base Updates

- Created `docs/superpowers/library-audit/_knowledge-base/claude-code-plugin-dependencies.md` (dated entry with sources).
- Agent memory: `.claude/agent-memory/superpowers-v-doc-validator/drift-plugin-dependencies.md` plus one index line.
