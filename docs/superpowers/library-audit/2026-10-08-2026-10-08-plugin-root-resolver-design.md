# Library audit - plugin-root resolver (2026-10-08)

Spec: `docs/superpowers/specs/2026-10-08-plugin-root-resolver-design.md`. Phase 1C. DEGRADED: WebSearch/WebFetch-only. `ToolSearch` for `context7` returned no Context7 tool; the harness reported `plugin:context7:context7` as needing OAuth (present, unauthorized), so it was not used. Every doc claim below is from code.claude.com pages fetched 2026-10-08. No local probe was possible: Bash was clamped to memory/git forms, so `claude plugin list --json`, `installed_plugins.json` and the real cache were not read in this run.

V-memory: the supplied block was used. `research/2026-10-05-jev-next-stage.md` ("Plugin-root resolver bug") is the origin of the spec; it matches the spec text. The 2026-10-05 plugin-dependencies KB is unrelated to the resolver itself. Agent memory (`drift-*.md`) held nothing on plugin root; no directive found in it.

## 1. Tools Available

- Context7: unauthorized (OAuth), not absent. WebSearch/WebFetch: yes.
- Manifests: `.claude-plugin/plugin.json` (`version` 3.8.3, name `superpowers-v`), `.claude-plugin/marketplace.json` (marketplace name `procoders`, entry `source: "./"`, version 3.8.3). No package manifest relevant (no npm/pip deps in this change).

## 2. Libraries Mentioned

| Name | Spec context | Current state (checked 2026-10-08) | Repo pinned | Status |
|---|---|---|---|---|
| Claude Code `${CLAUDE_PLUGIN_ROOT}` | step 1 of resolver; spec says "not set in the Bash tool" | Documented: not in the Bash env, BUT substituted inline in skill/command/agent Markdown bodies | Floor >= 2.1.219 (AGENTS.md) | see Finding C1 |
| `claude plugin list --json` | step 2 of resolver | Named in docs; fields and min version not documented | none | see Finding H1 |
| `~/.claude/plugins/cache/<mkt>/<plugin>/<version>/` | step 3 | Documented layout; root movable via `CLAUDE_CODE_PLUGIN_CACHE_DIR` | hard-coded `$HOME/.claude/plugins/cache` | see Finding H2 |
| `python3 -c` (stdlib) | version compare, JSON parse | stdlib only; no drift | repo CI floor 3.9 (drift-system-toolchain, 2026-10-05) | OK |
| `sort -V` | current snippet; test (e) | GNU/Apple both support; spec replaces it | n/a | OK (being removed) |
| `claude plugin validate` | AC 3 context | exists, v2.1.281+ for MCP checks | n/a | OK |

## 3. API Signatures Verified

| Claim in spec | Verdict |
|---|---|
| "`CLAUDE_PLUGIN_ROOT` is not set in the Bash tool" | CONFIRMED by docs: "The variables aren't present in the environment of commands Claude runs through the Bash tool, in the main session or in a subagent." |
| `claude plugin list --json` yields `[{id, enabled, installPath, ...}]`, `version` field for tie-break | UNVERIFIED in docs. Docs name the command and the `<name>@<origin>` id form only. The shape (top-level array vs object, `installPath`, `version`, `enabled`) rests on one local observation on 2.1.294. A third-party issue says "install path, enabled flag and version" without an example. |
| Cache layout `cache/<marketplace>/superpowers-v/<version>/` | CONFIRMED (loading page). `<plugin>` is the marketplace entry name. |
| Version comparable "numerically per component" | WRONG as a general rule. Version = manifest `version`, else entry `version`, else 12-char SHA, SHA-256 prefix, or `unknown`. This repo pins 3.8.3 in both manifests, so today it is numeric, but the parser must not assume it. |

## 4. Critical Findings

### C1. The spec misses the documented mechanism: inline `${CLAUDE_PLUGIN_ROOT}` substitution in Markdown

Doc (plugins-reference, "Where each variable resolves"): row "Skill, command, and agent content - Anywhere in the Markdown body - Not applicable (exported)", followed by "In skill, command, and agent content, write the `${...}` reference in the Markdown body instead, and Claude Code substitutes the path inline when it loads the content."

Consequence for the 38 files: the root cause is not only `sort -V`. The current line writes `${CLAUDE_PLUGIN_ROOT:-$(ls ...)}`. The docs document substitution of the exact `${CLAUDE_PLUGIN_ROOT}` form; the `:-default` form is not documented as substituted, so the host-resolved path was probably never used, and the fallback always ran. This is a lead to test live, not a fact: nothing in the docs states the substitution regex.

If substitution works, the host already knows the one correct answer (the enabled, loaded copy), which makes the `claude plugin list` call, the cache scan and the version compare unnecessary for agent, command and SKILL.md bodies. That removes the whole class of bug instead of ranking copies better. Limits that keep a fallback necessary:
- Files that are read as plain files rather than loaded as skill/command/agent content (the reference files `skills/compound-v/*.md` other than each `SKILL.md`, `evals/README.md`, `skills/backend-launcher/adapter-*.md`) are not documented as substituted. Only content "loaded" as a skill, command or agent body is.
- A non-Claude harness (AGENTS.md says Codex shim, untested) leaves the literal `${CLAUDE_PLUGIN_ROOT}` in the text.
- `--plugin-dir` / `@inline` plugins: documented root is the source dir; substitution presumably gives it, but that is not stated.

The plan MUST run a live test (one command file with the literal `${CLAUDE_PLUGIN_ROOT}` written plainly in the body, observe whether the model sees an absolute path) before choosing between "substitute with a fallback" and "pure fallback resolver". The spec's order should become: (1) the substituted literal, if it expanded to an existing directory; (2) installed_plugins.json / CLI; (3) cache scan; (4) `$PWD`.

## 5. High-Priority Findings

### H1. `claude plugin list --json` is an undocumented schema and a slow subprocess; `installed_plugins.json` is documented

The spec's step 2 depends on field names seen once. Docs do document `~/.claude/plugins/installed_plugins.json` as recording "each install with its `scope`, `installPath`, and `version`", under the plugins root. It has no `enabled` field; enabled state lives in the six-source `enabledPlugins` merge, which only the CLI performs. So replacing the CLI with the file alone would lose the enabled filter, and that filter is exactly what the 2026-10-05 incident needed (the old copy was the disabled one).
- Alternative: keep the CLI as the enabled-aware source, parse defensively (accept top-level list or an object holding a list; `.get`), and add `installed_plugins.json` only as a tie-break source for `installPath`/`version` if the CLI is absent.
- Cost: the CLI starts a full Node process on every resolution. The snippet runs at the start of every command and agent. No timing was measured here; the plan should measure it and cache within the session (the sentence "resolve once per session" already exists in the prose).
- Minimum CLI version for `list --json` is undocumented. `--json` on install/uninstall/update/enable/disable needs 2.1.268; do not assume the same for `list`. The plugin floor is 2.1.219, so a CLI without `--json` on `list` is possible; the spec's "absent CLI, bad JSON falls through" covers it, provided the snippet treats a non-zero exit and the text-mode output as bad JSON.

### H2. The hard-coded cache path ignores `CLAUDE_CODE_PLUGIN_CACHE_DIR`

Env-vars page: "Override the plugins root directory ... marketplaces and the plugin cache live in subdirectories under this path. Defaults to `~/.claude/plugins`." Both the old and the proposed step 3 hard-code `$HOME/.claude/plugins/cache`. A user with the override set (CI, managed machines) gets an empty step 3 and falls to `$PWD`, which is a wrong root silently if `$PWD` is some other checkout of the project. The plan MUST use `${CLAUDE_CODE_PLUGIN_CACHE_DIR:-$HOME/.claude/plugins}/cache`. The docs do not say that `CLAUDE_CONFIG_DIR` moves the plugins root (page text for that row was not retrievable); do not assume either way.

### H3. Highest-version-segment ignores enabled state (step 3)

Step 3 picks the highest version across marketplaces regardless of which marketplace is enabled. Docs: previous versions stay on disk 14 days after an update or uninstall (`.orphaned_at` marker), and a disabled or uninstalled marketplace copy remains until swept. If a stale marketplace holds the highest version (a disabled `procoders/3.9.0` against an enabled `cv-dev/3.8.3`) step 3 picks the disabled copy: the same class of wrong answer, with the sign flipped. Step 3 is only safe when step 2 failed for lack of a CLI. Say so in the snippet's comment and in the test matrix (add a case: highest version in a non-enabled marketplace with the CLI present and failing).

### H4. Non-numeric versions

`unknown`, 12-char SHA and SHA-256-prefix versions are all documented outcomes when a manifest and entry set no `version`. This repo sets one, but a fork that drops `version` gets SHA directory names. A "numeric per component" comparator either raises (`int('a1b2c3...')`) or must define an order. Specify: parse only directory names matching `^\d+(\.\d+)*([-+].*)?$` numerically; treat any other name as lowest precedence and tie-break by mtime; never raise. A raising `python3 -c` inside `$(...)` would make `CV` empty and silently take `$PWD`.

## 6. Medium Findings

### M1. Project-root work: `${CLAUDE_PROJECT_DIR}` is documented, but only for hooks/LSP

The widened scope's "one project-root rule" should know: `${CLAUDE_PROJECT_DIR}` is documented as "The project root", exported to hook commands and LSP servers, not to the Bash tool, and the Markdown-body substitution row is stated for the plugin path variables in general ("`${...}` references resolve inline ... Skill, command, and agent content"). Whether `${CLAUDE_PROJECT_DIR}` substitutes inline in Markdown bodies is not stated for this variable specifically; verify live before using it. Python scripts that derive a project root from `__file__` are wrong inside the cache by construction: docs say the cache is the plugin's installed copy, and "Files outside the plugin directory aren't copied". Nothing in the library docs makes `__file__` a valid project root for an installed plugin.

### M2. `@inline` / `--plugin-dir` plugins never enter the cache

For a session started with `--plugin-dir` or `CLAUDE_CODE_PLUGIN_DIRS`, the plugin loads in place and has no cache dir. Steps 2-3 find nothing or find the installed copy that `--plugin-dir` silently overrides ("replaced silently"). So the resolver can pick the cached marketplace copy while the session runs the `--plugin-dir` copy, the original bug in a different form. This is the developer case (this repo's own checkout). Inline substitution (C1), if it works, is the only documented way to follow the loaded copy. Otherwise the plan must state this as a known limit.

### M3. Marketplace name "procoders" and "cv-dev" are both hard facts of this machine only

`marketplace.json` names the marketplace `procoders`; the dev marketplace is user-local. No name may be hard-coded (spec already says none). Noting for the inventory: `cache/*/superpowers-v/` globs on the plugin name, and docs say `<plugin>` is the marketplace entry name, which can differ from the manifest `name` ("Entry name and manifest name"). A marketplace entry renamed from `superpowers-v` would not match the glob.

## 7. Design Constraints for the Plan

MUST:
- Live-test the inline `${CLAUDE_PLUGIN_ROOT}` substitution (exact `${CLAUDE_PLUGIN_ROOT}`, plain Markdown body, in a command, an agent and a SKILL.md) before fixing the snippet's order; record the result in the plan. Do not assume `${CLAUDE_PLUGIN_ROOT:-...}` is substituted.
- Keep a non-substituting fallback: reference files and non-Claude harnesses leave the literal text.
- Honour `CLAUDE_CODE_PLUGIN_CACHE_DIR` in the cache scan.
- Make the version comparator total: non-numeric directory names must sort lowest and never raise.
- Parse `claude plugin list --json` defensively (array or object-with-array, missing keys, non-zero exit, non-JSON); an unknown shape falls through, never aborts.
- Verify the CLI shape and `installed_plugins.json` on a real install in the test fixtures, and write the observed Claude Code version next to the fixture, because neither shape is documented for `list`.
- Include a test where the highest cached version belongs to a non-enabled marketplace (H3) and one where the version directory is a SHA (H4).
- Treat any `__file__`-derived "project root" as plugin-root semantics, never project-root.

MUST NOT:
- Cite `claude plugin list --json` field names as documented; they are an observation on 2.1.294.
- Replace the CLI with `installed_plugins.json` alone: it has no enabled state.
- Hard-code `~/.claude/plugins` or any marketplace name.
- Fall back to `$PWD` silently on a machine where the plugin is installed and a lookup failed without emitting a diagnosable signal (stderr is allowed to stay quiet per spec, but a test must pin which step won).

## 8. Open Questions for the Human

1. If the live test shows that `${CLAUDE_PLUGIN_ROOT}` is substituted in command/agent/SKILL bodies, do you want the 38 files to use it as the primary path (with the resolver as fallback only for the reference files and non-Claude harnesses)? That changes the "byte-identical snippet in 38 files" acceptance criterion.
2. What cost is acceptable for a `claude plugin list --json` call on each resolution? It is a full CLI start; no timing exists.
3. Is the `--plugin-dir` developer case (M2) required to resolve to the checkout, or is "known limit, documented" acceptable?

## 9. Knowledge Base Updates

Created `docs/superpowers/library-audit/_knowledge-base/claude-code-plugin-root.md` with dated entries for: inline substitution vs Bash env, plugins-root override, `installed_plugins.json` fields, non-numeric versions, 14-day orphan cleanup, `@inline` loading, `list --json` documentation gap.
