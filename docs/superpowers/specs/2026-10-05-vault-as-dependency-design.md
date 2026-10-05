# compound-v-vault as a declared dependency of superpowers-v - design

Triage: FULL, record `2026-10-05T132519Z-make-compound-v-vault-a-declared-dependency-of-superpowers-v-19ae`
(T3 `user-facing-major`: it changes how the plugin is installed). Trigger 0: `kb_skip`.

## Problem

Jev needs two plugins today: `superpowers-v` and `compound-v-vault`, installed and configured separately. The
maintainer finds that inconvenient. They cannot simply be merged: Claude Code exports every `userConfig` value of a
plugin, sensitive ones included, as `CLAUDE_PLUGIN_OPTION_<KEY>` to every command hook of that plugin, with no
per-option opt-out (docs: plugins/components.md § Hooks; plugins/manifest-reference.md § Reference a saved value).
`superpowers-v` has about a dozen command hooks, some of which start `claude -p`, `codex` and Python; a key there
would sit in all of their environments, which the foundation spec forbids (`2026-10-05-jev-classifier-foundation-
design.md:38-40`, AC-4).

## Decision

Keep the key in its own plugin, and make installing `superpowers-v` bring the vault with it.

- `.claude-plugin/plugin.json` gains `"dependencies": ["compound-v-vault"]` (docs: manifest-reference.md
  § dependencies; a bare name resolves against the plugin's own marketplace).
- `.claude-plugin/marketplace.json` lists `compound-v-vault` with `"source": "./plugins/compound-v-vault"` and the
  vault's own version and description, so the bare name resolves in the `procoders` marketplace.
- The vault stays inert without a key (`unavailable(no_key)`, status line `Jev: off (no_key)`), so the dependency
  costs nothing for anyone who does not use Jev, and every consumer keeps its deterministic or Claude path.
- The key is entered in the install dialog Claude Code opens for unset options, or later with
  `/plugin configure compound-v-vault@procoders`. Sensitive options are not listed in `/config` by design
  (manifest-reference.md § User configuration), and the docs say so.

## Changes

1. `plugin.json`: the `dependencies` entry. Its `version` is not bumped (no release in this change).
2. `marketplace.json`: the vault entry beside `superpowers-v`.
3. `plugins/compound-v-vault/README.md` § Setup: the vault arrives with `superpowers-v`; set the key in the install
   dialog or with `/plugin configure`; it is not in `/config`; then `/egress allow` per repository.
4. Root `README.md` § Install: one sentence that installing `superpowers-v` also installs `compound-v-vault`, which
   holds the OpenRouter key for Jev, is inert without one, and is configured with `/plugin configure`.
5. A test row (in the existing `tests/test-vault-mod.sh`) that fails when the two manifests disagree: every name in
   `plugin.json` `dependencies` is a plugin in `marketplace.json`, and that entry's `source` directory holds a
   `.claude-plugin/plugin.json` whose `name` matches.

## Out of scope

Version bump, CHANGELOG, the CI version-lockstep step (`.github/workflows/validate.yml:43-49` already compares only
`superpowers-v`'s two versions), merging the plugins, and moving the key anywhere else.

## Acceptance criteria

- AC-1 `claude plugin validate .` passes, and `claude plugin validate plugins/compound-v-vault` passes.
- AC-2 The new test row passes, and fails when the `dependencies` entry or the marketplace entry is removed.
- AC-3 Installing `superpowers-v` from a local marketplace built from this tree also installs `compound-v-vault`
  (checked with `claude plugin list` in a scratch config directory, never the maintainer's own).
- AC-4 The manifest's full test command passes.

## Superseded (2026-10-05)

Not built. The pre-flights (`docs/superpowers/{archaeology,expert,library-audit}/2026-10-05-2026-10-05-vault-as-
dependency-design.md`) showed that a dependency makes the vault load-critical (a disabled, blocked or failing vault
disables `superpowers-v`), that the key is still set with `/plugin configure` (the install dialog is documented only
for the plugin being installed, not its dependencies), and that the vault would show `Jev: off (no_key)`, a command and
a tool to everyone who never uses Jev. The maintainer chose the optional route instead:
`docs/superpowers/specs/2026-10-05-vault-optional-via-init-design.md`.
