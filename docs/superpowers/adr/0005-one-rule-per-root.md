# 0005. One rule for the plugin root and one for the project root

- **Status:** Accepted
- **Date:** 2026-10-08
- **Deciders:** the maintainer, from the root-resolution inventory in
  [`docs/superpowers/archaeology/2026-10-08-2026-10-08-plugin-root-resolver-design.md`](../archaeology/2026-10-08-2026-10-08-plugin-root-resolver-design.md)
  (section 1c, 31 mechanisms) and the library audit
  [`docs/superpowers/library-audit/2026-10-08-2026-10-08-plugin-root-resolver-design.md`](../library-audit/2026-10-08-2026-10-08-plugin-root-resolver-design.md)

## Context

The code finds two roots: the **plugin root** (where Compound V's own scripts live) and the **project root** (the user's
repository Compound V works on). It did so in many ways, and several of them were workarounds.

- 38 Markdown files set `CV="${CLAUDE_PLUGIN_ROOT:-$(ls -d .../cache/*/superpowers-v/*/ | sort -V | tail -1)}"`.
  Claude Code substitutes `${CLAUDE_PLUGIN_ROOT}` in command, skill and agent bodies, but only that exact token: the
  `${CLAUDE_PLUGIN_ROOT:-...}` form is left as is, and the variable is not set in the Bash tool. So the cache scan always
  ran, and because `sort -V` sorts whole paths it could pick a stale, disabled copy (2026-10-05: `procoders` 3.7.5 over
  `cv-dev` 3.8.3). Live test, 2026-10-08, Claude Code 2.1.294, a `--plugin-dir` plugin: `A=${CLAUDE_PLUGIN_ROOT}`
  became the plugin's path in a command, a skill and an agent body; `B=${CLAUDE_PLUGIN_ROOT:-fallback}` stayed literal.
- `hooks/session-banner.sh:35,51` fall back to `${CLAUDE_PLUGIN_ROOT:-.}`, the project's directory.
- `scripts/compound-v-triage-outcomes.py:255-261` derives the project root from its own `__file__`, so run from the
  plugin cache it writes the outcome stream into the cache; two callers patch around it by passing `--stream`
  (`compound-v-preeval.py:1628`, `compound-v-fastpath-materialize.py:708`), each with its own copy of the path.
- `scripts/compound-v-validate-manifest.py:3285-3295` falls back to `os.getcwd()` when no `.git` is found;
  `hooks/precompact-snapshot.sh`, `hooks/run-band.tsx:179` and `hooks/brainstorm-trigger0-nudge.sh:73,134` use the raw
  `cwd` while their sibling hooks walk up to `.git`.

## Decision

**Plugin root.**

1. Command, skill and agent bodies set `CV="${CLAUDE_PLUGIN_ROOT}"`, which the harness replaces with the path of the
   copy it actually loaded. No cache scan, no `claude plugin list` call, no marketplace name.
2. Where no substitution happens (a reference file read with the Read tool, an eval fixture, another harness), the one
   fallback is `$PWD` when it is a checkout of this plugin (it holds `scripts/compound-v-preeval.py`); otherwise the step
   stops with a message naming the problem. Never a guess.
3. Hooks use `CLAUDE_PLUGIN_ROOT`, else the path relative to the hook script itself; never `.`.
4. TypeScript modules use `$.plugin.root`; Python scripts find their siblings from `__file__`.

**Project root.**

5. An explicit `--repo`, else the git toplevel of the current directory (real path). Outside a git repository the
   command fails closed with a message; it never falls back to the plugin directory or silently to another directory.
6. Never derived from `__file__`, except inside a selftest that builds its own fixture.
7. Each shared path under the project (the triage outcome stream) is one constant, owned by one module and imported by
   the others.
8. Hooks that need the project root walk up to `.git` the same way; none uses the raw `cwd`.

## Alternatives considered

- **Keep the cache scan, sort on the version segment only, and add `claude plugin list --json`.** Approved first, then
  replaced by this decision once the live test showed the harness already supplies the exact path. It would keep two
  undocumented contracts (the JSON fields, the cache layout), a process spawn in every bash block, and the wrong answer
  for `--plugin-dir` and orphaned copies.
- **A helper script that resolves the plugin root.** Cannot be found before the root is known.

## Consequences

- The work is split into two runs: **A** (plugin root: the 38 files, `session-banner.sh`, a test that every file carries
  the canonical lines and that the fallback refuses a non-plugin `$PWD`) and **B** (project root: `triage-outcomes.py`,
  `preeval.py`, `fastpath-materialize.py`, `validate-manifest.py`, the three hooks without a walk-up). B also closes the
  downstream-reported bug that the outcome stream lands in the plugin cache.
- Substitution is an undocumented-in-detail harness behaviour (documented as existing, not as limited to the bare
  token). A test pins the canonical line, and the live probe above is the evidence; if a future Claude Code changes it,
  the fallback stops with a message instead of picking a wrong copy.
- `evals/` keep working: their fixtures run from a source checkout, which is exactly the `$PWD` fallback.
