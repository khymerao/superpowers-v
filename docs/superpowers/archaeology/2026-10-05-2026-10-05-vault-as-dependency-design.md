# Vault-as-dependency Code Archaeology

Spec: `docs/superpowers/specs/2026-10-05-vault-as-dependency-design.md`. Method: repository read only. Bash was clamped to
git/memory forms in this run, so nothing was executed: no `claude plugin validate`, no test run. Context7 needs
authorization and is unavailable; no local copy of the Claude Code plugin docs was found. Every claim below about CLI
behaviour is therefore UNKNOWN, not verified (see section 4).

V-memory recall (the prompt's block): nothing in it concerns manifests, marketplaces or dependencies. The only relevant
prior art is the foundation plan, which wrote the nested-plugin guard (section 3). Foundation spec
`2026-10-05-jev-classifier-foundation-design.md:39-43` says the vault is "optional" and ships "as a separate plugin";
this change makes it non-optional at install time, so that sentence is now stale (Finding 2).

## 1. Matrix

Dimension: who installs what, and what the vault then does in their sessions.

| Installer state | Key set | `/egress` answered | Vault behaviour (read at `vault.tsx:76,236,246,274,350-365`) | Spec covers? |
|---|---|---|---|---|
| New install of `superpowers-v` via dependency | no | no | registers tool `jev_classify` + command `/egress`, status `Jev: off (no_key)`, no toast (`no_key` returns at :236 before the toast at :246) | partly: spec says "costs nothing" |
| New install, user sets key in install dialog | yes | no | status `Jev: off (egress)`, one toast per session | yes (README Setup) |
| New install, key + `/egress allow` | yes | allow | `Jev: on` | yes |
| Existing user who already installed the vault by hand | any | any | unchanged | not mentioned |
| User on Claude Code < 2.1.287 (superpowers-v floor is 2.1.219) | n/a | n/a | vault is a hooks module the old CLI does not load; whether the dependency install is refused, warned or silently inert is UNKNOWN | no |
| `superpowers-v` uninstalled / dependency removed | any | any | vault's fate (auto-removed or orphaned, with a stored key) is UNKNOWN | no |
| Marketplace consumed as a local dir / git URL | n/a | n/a | bare-name resolution of `compound-v-vault` against `procoders` is UNKNOWN for local-dir marketplaces (AC-3 is the only check) | AC-3 only |

Tested cell so far: the vault alone, `claude plugin validate plugins/compound-v-vault` (`tests/test-vault-mod.sh:33`).
No existing test exercises the pair together.

## 2. Shared State

| Value | Where set | Where read | Gap |
|---|---|---|---|
| `compound-v-vault` version | `plugins/compound-v-vault/.claude-plugin/plugin.json:3` = `0.1.0`; the spec adds a second copy in the marketplace entry | nothing compares them | The only CI lockstep (`validate.yml:43-52`) is `select(.name=="superpowers-v")`. Two copies of the vault version with no guard will drift; the spec's new test row checks `name` only. |
| `superpowers-v` version | `plugin.json:4`, `marketplace.json:12` | `validate.yml:46-47,56-79`, `release.yml:30` | Spec leaves it unbumped; lockstep still holds. `release.yml:11-12` fires on a `plugin.json` push, finds `v3.8.3` released (`:45-47`), no-ops. Benign. |
| Marketplace `plugins[]` order | `marketplace.json:8-19` | CI selects by name (`:47`); nothing indexes by position | Safe to append. |
| Key | vault's `userConfig.openrouter_key` (`sensitive: true`) | `vault.tsx:76,180,236` | Unaffected by the dependency. `hooks/hooks.json` holds only `modules` (`tests/test-vault-mod.sh:51-52` enforces this), so AC-4 of the foundation spec still holds. |

## 3. Sibling Code

**Nested plugin inside the marketplace root.** `marketplace.json:13` gives `superpowers-v` `"source": "./"`; the new vault
source `./plugins/compound-v-vault` is a plugin directory physically inside the first plugin's source tree. The foundation
plan anticipated this: `tests/test-jev-t3-mod.sh:77-82` runs `claude plugin validate .` and fails if its output mentions
`compound-v-vault` or `vault.tsx`, with the message "Task R must move the marketplace root" (plan
`2026-10-05-jev-classifier-foundation.md:436-437`). That guard is the only existing evidence the root plugin does not
absorb the vault's hooks. It was never run by me; its last result is not recorded in the dogfood review. The spec's
AC-1 (`validate .`) and the test-jev-t3 guard are the same check; the new marketplace entry makes it load-bearing
rather than incidental. Latent wording bug: the BLOCKED message tells a future reader to "move the marketplace root",
which is now the opposite of this design.

**Sibling manifest check.** `tests/test-vault-mod.sh` is the natural home (spec change 5): `cd` to repo root (`:13`),
`python3 -B -c` JSON idiom already used at `:51`, `ok`/`bad` counters at `:30-31`, PASS count tail `:86`. It sets `PLUGIN`
at `:16`. It is run by the recursive `tests/` sweep (`.claude/rules/tests.md`, Python 3.9 floor), so the new row must use
stdlib `json` only (no `jq` dependency in the tests; `jq` is installed only in the `validate.yml:16-17` job).

**Stale sibling text.** `plugins/compound-v-vault/README.md:21` says to set the key via `/config`; the spec corrects
this. `hooks/jev-t3.tsx:115` still says `/compound-v-vault:egress allow` while commit `ec3bca3` made the command `/egress`
(`vault.tsx:55,338`; README `:23,37-39`). That comment is outside the spec's change list; leave it, it is a comment.

## 4. External APIs

Claude Code plugin manifest `dependencies`, marketplace `plugins[].source` relative paths, install-time userConfig
dialog, `/plugin configure`, `claude plugin list`. UNVERIFIED: Context7 unauthorized, no local docs. The spec's cited
sections (plugins/components.md, manifest-reference.md) were not read by me. Unknowns the plan must treat as
unresolved, not assumed: exact `dependencies` element shape (string vs `{name, marketplace, version}`); whether a bare
name resolves inside the same marketplace for a plugin whose source is `./`; whether version constraints are
supported or ignored; behaviour on a dependency whose Claude Code floor is higher than the host's; whether
`claude plugin validate` checks that a dependency exists in the marketplace. AC-3 is the sole empirical check and
must therefore run, not be asserted.

## 5. Regression Surface

- `claude plugin validate .` / `claude plugin test .` (`tests/test-jev-t3-mod.sh:59-96`, `tests/test-run-band-mod.sh`): if
  the root plugin starts discovering the nested vault, jev-t3 and run-band tests run against the wrong plugin.
- `tests/test-vault-mod.sh`: a new failing row breaks an existing required sweep job.
- Every existing `superpowers-v` installer who updates: gains the vault's tool, `/egress` command, and a permanent
  `Jev: off (no_key)` status segment (`vault.tsx:274`, `:350-365`). The model's tool list in every session grows by
  one tool definition, with no key and no consent.
- Installs on Claude Code between 2.1.219 and 2.1.286: the dependency's module cannot load; failure mode UNKNOWN. This
  could make `/plugin install superpowers-v` itself fail for users on the documented supported floor (`AGENTS.md`).
- `CHANGELOG`/release lockstep (`validate.yml:56-79`): not triggered while the version stays unbumped.

## 6. DRY Findings

No duplicate logic. One duplicated fact: the vault's version and description live in `plugin.json` and, after this
change, in the marketplace entry. `marketplace.json` already duplicates `superpowers-v`'s description by hand (it
differs from `plugin.json`'s), so drift is the established pattern. Decision for the plan: guard the version with the new
test row, since CI will not.

## 7. Design constraints for the spec

1. Run `claude plugin validate .` and keep `tests/test-jev-t3-mod.sh:77-82` green after the marketplace edit; if it goes red,
   the design is invalid (nested plugin), not the test. Reword its BLOCKED message, which now contradicts the design.
2. Amend the foundation spec / README claim that the vault is "optional": it is now installed for everyone.
3. Replace "the dependency costs nothing" with what is true: every installer gets a permanent `Jev: off (no_key)`
   status segment, one extra model-visible tool (`jev_classify`) and a `/egress` command, registered whether or not a
   key exists (`vault.tsx:350-365`). Either state this in the README sentence, or accept it knowingly.
4. The new test row must compare the vault's `version` between `plugin.json` and the marketplace entry, not only
   `name`/`source`, and use stdlib Python only.
5. The new test row must also fail when `source` points at a directory with no `.claude-plugin/plugin.json`, and when
   the entry is missing (AC-2 requires both failure modes be demonstrated, not claimed).
6. AC-3 must be run for real in a scratch config dir; the manifest syntax, same-marketplace bare-name resolution and
   Claude Code floor behaviour are all UNKNOWN. Add the floor case (a CLI below 2.1.287) to the checks or record it as a
   known unknown in the README.
7. Decide and document uninstall behaviour (orphaned vault holding a stored key) once AC-3 shows what the CLI does.
8. Do not touch `hooks/hooks.json`, `vault.tsx` or the vault's `hooks/hooks.json`; the test at
   `tests/test-vault-mod.sh:51-52` and the foundation AC-4 rest on `modules` being the only key.

## 8. File Touch Map

- `.claude-plugin/plugin.json`: add `dependencies`. SHARED RESOURCE (read by `validate.yml`, `release.yml`, `emit-preflight.py:121`, evals fixture lib).
- `.claude-plugin/marketplace.json`: add vault entry. SHARED RESOURCE (CI lockstep reads it).
- `plugins/compound-v-vault/README.md`: Setup rewrite (line 21 `/config` is wrong).
- `README.md`: one sentence under Install (lines 15-19).
- `tests/test-vault-mod.sh`: new manifest-agreement row (insert before the summary at `:86`).
- `tests/test-jev-t3-mod.sh`: reword the BLOCKED message at `:78` only (optional, constraint 1).
- Read-only, must stay byte-identical: `plugins/compound-v-vault/hooks/vault.tsx`, `plugins/compound-v-vault/hooks/hooks.json`, `plugins/compound-v-vault/.claude-plugin/plugin.json`, `hooks/hooks.json`, `hooks/jev-t3.tsx`.
- Untracked files `tsconfig.json`, `plugins/compound-v-vault/tsconfig.json` and `docs/superpowers/pre-eval/*` exist in the tree; the plan must not pick them up in a job's changed set.
