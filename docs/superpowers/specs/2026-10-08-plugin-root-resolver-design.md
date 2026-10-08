# One plugin-root resolver that picks the installed copy - design

Triage: `docs/superpowers/pre-eval/2026-10-08T094652Z-plugin-root-resolver-38-files-agents-md-commands-v-md-skills-0c93.json`
(FULL). Handoff: `docs/superpowers/research/2026-10-05-jev-next-stage.md`, section "Plugin-root resolver bug".

## Problem

38 files (`agents/*.md`, `commands/v-*.md`, `skills/compound-v/*.md`, `skills/backend-launcher/*.md`,
`evals/README.md`) resolve the plugin root with the same line:

```bash
CV="${CLAUDE_PLUGIN_ROOT:-$(ls -d "$HOME"/.claude/plugins/cache/*/superpowers-v/*/ 2>/dev/null | sort -V | tail -1)}"
CV="${CV:-$PWD}"; CV="${CV%/}"
```

`sort -V` sorts whole paths, so the marketplace directory decides before the version. On 2026-10-05, with
`cv-dev/superpowers-v/3.8.3` and `procoders/superpowers-v/3.7.5` both cached, it chose the older, disabled `procoders`
copy, and a terminal epic session ran 3.7.5's scripts. `CLAUDE_PLUGIN_ROOT` is not set in the Bash tool, so the
fallback is what normally runs.

## Change

1. **One canonical snippet**, inline (a helper script cannot be found before the root is known). Order:
   1. `CLAUDE_PLUGIN_ROOT`, when set and a directory.
   2. The enabled `superpowers-v@*` entry from `claude plugin list --json`, its `installPath` (field observed on this
      machine, Claude Code 2.1.294: `{"id": "superpowers-v@cv-dev", "enabled": true, "installPath": ".../3.8.3", ...}`).
      With several enabled entries, the highest `version`. Absent CLI, bad JSON, no enabled entry or a path that is not
      a directory falls through.
   3. The cache copy whose **version segment** is highest (`.../cache/<marketplace>/superpowers-v/<version>/`, compared
      on `<version>` alone, numerically per component).
   4. `$PWD` (a checkout of this repository), then the trailing slash stripped, as today.
   It stays bash plus `python3 -c` (stdlib), never fails the calling step, prints nothing, and leaves only `CV` set.
2. **Every one of the 38 files** carries the snippet byte-identically in place of the old two lines. The prose that
   explains the resolver (where a file has it) is updated to the new order.
3. **Tests** (`tests/test-plugin-root.sh`, new): (a) every file that resolves `CV` carries the canonical snippet
   byte-for-byte and none still has `sort -V | tail -1` over cache paths; (b) the snippet, extracted from one file and
   run against a fake `HOME` with `cache/procoders/superpowers-v/3.7.5/` and `cache/cv-dev/superpowers-v/3.8.3/` and no
   `claude` on `PATH`, picks `3.8.3`; (c) with a stub `claude` whose `plugin list --json` marks the `procoders` copy
   enabled, it picks that `installPath`; (d) `CLAUDE_PLUGIN_ROOT` wins when set; (e) a version like `3.10.0` beats
   `3.9.9`. Each fails when the old snippet is put back.

## Out of scope

The plugin's version, the cache layout, uninstalling stale copies. (Hook locators and project-root resolution were out of
scope in the first draft; the widened scope below brings them in.)

## Acceptance Criteria

1. `tests/test-plugin-root.sh` passes; with the old snippet restored in the extracted copy, rows (b) and (e) fail.
2. No file under `agents/`, `commands/`, `skills/` or `evals/` contains `superpowers-v/*/ 2>/dev/null | sort -V`.
3. `lint-frontmatter.py .`, `shellcheck` over any new `.sh`, and the full suite pass.

## Widened scope (maintainer, 2026-10-08)

The maintainer approved the design above and asked for more: look for fragmentation and workarounds in how the code
finds its roots, remove the patches, and make it consistent; anything that works only through a workaround goes back to
architectural review and is redone. So before the plan, the pre-flight inventories **every** root-resolution mechanism
in the repository, both kinds:

- **Plugin root** (where the plugin's own scripts live): the `CV=` snippet, `_locate_script` and similar in
  `hooks/*.sh`, `$.plugin.root` in `hooks/*.tsx`, `CLAUDE_PLUGIN_ROOT` uses, `__file__`-relative script lookups in
  `scripts/*.py`, any `ls`/`find` over `~/.claude/plugins/cache`, any hard-coded marketplace name.
- **Project root** (the user's repository the plugin works on): `git rev-parse --show-toplevel`, `__file__`-derived
  repo roots (`scripts/compound-v-triage-outcomes.py:260` `default_stream_path()` -> `_repo_root()` is one, reported to
  write into the plugin cache; the same is reported for `compound-v-jev.py`), `$PWD` fallbacks, walk-up-to-`.git`
  helpers, `--repo` defaults.

For each: file:line, which kind, what it does when the expected root is absent, whether it duplicates another
mechanism, and whether it is a workaround (a fallback that silently picks a wrong root, a retry, a special case for one
caller). The plan then follows an architecture decision recorded from that inventory: one plugin-root rule and one
project-root rule, each implemented once per language (bash snippet, Python helper, TS) and tested, with every
workaround either removed or justified in writing.
