# compound-v-vault as an optional plugin, offered by /v:init - design

Triage: SCOPED, flavor `scoped_plus` (it touches `.claude-plugin/marketplace.json`), record
`2026-10-05T134203Z-offer-compound-v-vault-as-an-optional-plugin-instead-of-a-de-1491`. Supersedes
`2026-10-05-vault-as-dependency-design.md`, whose pre-flight audits stand as constraints here.

## Problem

Jev needs `compound-v-vault` beside `superpowers-v`, and today nothing tells a user that it exists, where to get it or
how to set its key: it is in no marketplace, and its README sends people to `/config`, where sensitive options are
never listed (docs: plugins/manifest-reference.md § User configuration).

## Decision

The vault stays a separate, optional plugin (the key must not reach `superpowers-v`'s command hooks, which receive
every option of their own plugin as `CLAUDE_PLUGIN_OPTION_*`). Installing it becomes one guided step:

1. **Marketplace.** `.claude-plugin/marketplace.json` lists `compound-v-vault` beside `superpowers-v`:
   `"source": "./plugins/compound-v-vault"`, `name` equal to the vault's `plugin.json` `name`, `version` byte-equal
   to the vault's `plugin.json` `version` (`0.1.0`), a one-line description. `superpowers-v`'s own `plugin.json` gains
   no `dependencies` entry.
2. **`/v:init`.** A new detection step "Jev vault (optional)" in `commands/v-init.md`, beside the other optional
   capabilities in Step 1, reads `claude plugin list --json` and reports one of three states: not installed; installed
   (an entry whose `id` starts with `compound-v-vault@` and is `enabled`); and, when installed, whether
   `claude plugin configure <that id> --json` reports `openrouter_key` set. It never reads, prints or asks for the
   value. Step 2 gains one item: when the vault is missing and the user wants Jev, offer
   `/plugin install compound-v-vault@procoders`, then `/plugin configure compound-v-vault@procoders` to set the key,
   then `/egress allow` in each repository; re-probe after each. The user types the key into Claude Code's own
   masked field; `/v:init` never asks for it in chat and never passes it on a command line. Declining leaves Jev off
   and changes nothing else.
3. **Vault README § Setup.** Install with `/plugin install compound-v-vault@procoders` (or let `/v:init` offer it);
   set the key with `/plugin configure compound-v-vault@procoders` (Claude Code 2.1.285 or newer; the install dialog
   may also ask); the key is not in `/config`, by design; then `/egress allow`. The vault itself needs Claude Code
   2.1.287 or newer.
4. **Root README § Install.** One short paragraph: Jev is optional, comes as the separate `compound-v-vault` plugin
   that holds the OpenRouter key, and `/v:init` offers it.
5. **Stale text.** The comment at `hooks/jev-t3.tsx:115` names `/compound-v-vault:egress`; the command is `/egress`.

## Tests

`tests/test-vault-mod.sh` gains rows that fail when the change is reverted:

- the marketplace lists `compound-v-vault`, its `source` directory holds `.claude-plugin/plugin.json`, and that file's
  `name` and `version` equal the entry's;
- `superpowers-v`'s `plugin.json` declares no dependency on `compound-v-vault`;
- `plugins/compound-v-vault/README.md` no longer tells the reader to set the key in `/config`.

## Acceptance criteria

- AC-1 `claude plugin validate .` and `claude plugin validate plugins/compound-v-vault` pass, and the root
  validation does not load `plugins/compound-v-vault` as part of `superpowers-v` (`tests/test-jev-t3-mod.sh` stays
  green).
- AC-2 The new rows pass and fail when the marketplace entry is removed or its version changed.
- AC-3 `commands/v-init.md` passes `lint-frontmatter`, and its new step never reads, prints, requests or forwards the
  key value.
- AC-4 The manifest's full test command passes.

## Out of scope

Version bump, CHANGELOG, release, a plugin dependency, merging the plugins.
