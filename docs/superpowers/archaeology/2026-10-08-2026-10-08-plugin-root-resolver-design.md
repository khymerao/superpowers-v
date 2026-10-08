# Plugin-root resolver Code Archaeology

Spec: `docs/superpowers/specs/2026-10-08-plugin-root-resolver-design.md` (including "Widened scope").
Step 0 (V-memory): the dispatcher's `## Prior context` block was used. Its one load-bearing hit,
`docs/superpowers/research/2026-10-05-jev-next-stage.md` (section "Plugin-root resolver bug" plus "Harness bugs" item 2), was
re-checked against the code. Item 2 is confirmed for `compound-v-triage-outcomes.py` and **not** reproduced for
`compound-v-jev.py` (finding F10). I could not run a second recall phrasing: this agent's Bash clamp admits only the
`compound-v-memory.py search`/`recall-check` forms, and the `rtk` rewrite turned the one attempt into a non-matching form.
The 1C knowledge base `library-audit/_knowledge-base/claude-code-plugin-root.md` (dated 2026-10-08) is read and cited where it bears on the code.

Cross-reference key: an `F<n>` tag in sections 1, 2, 3, 5 and 8 points at constraint `<n>` in section 7, except `F8` = constraint 9,
`F10` = constraint 13 and `F12` = constraint 12.

Method note: Context7 needs OAuth in this session and was not used; Phase 4 below is limited to what the repo and the 1C KB
already record. Nothing here was run against a live `claude` CLI, so every latency or behaviour claim about it is marked unknown.

## 1. Matrix

### 1a. The snippet (plugin root, Bash-in-markdown kind)

| Dimension | Values in the code today | Handled by old snippet | Spec's new snippet |
|---|---|---|---|
| `CLAUDE_PLUGIN_ROOT` in Bash | unset (docs: absent from Bash tool env, main session and subagent) | falls to `ls` | step 1, no-op in practice |
| Marketplaces cached side by side | `cv-dev/3.8.3` + `procoders/3.7.5` on this machine | **wrong**: whole-path sort, marketplace decides | steps 2-3 |
| Enabled vs disabled copy | disabled copy still in cache | not looked at | step 2 via CLI |
| `sort -V` present | GNU yes; BSD `sort` "did not always carry it" (`hooks/session-banner.sh:67-69`) | silent empty result then `$PWD` | n/a (python3) |
| Orphaned version dirs | `.orphaned_at` marker, swept after 14 days (KB line 17) | not looked at | **not handled** (F5) |
| Version string | may be SHA / `unknown` (KB line 16) | n/a | numeric compare undefined for these (F4) |
| Inline `--plugin-dir` plugin (`@inline`) | loads in place, never in cache (KB line 18) | picks some cache copy | **not handled** (F4) |
| `claude` on PATH | desktop/other hosts: PATH `claude` can differ from the host (`.claude/agent-memory/.../v-init-1g-map.md`; `commands/v-init.md:327-339`) | n/a | step 2 trusts PATH `claude` |
| Checkout (no cache) | `$PWD` is the plugin repo | `CV:-$PWD` | step 4 |
| Eval run | throwaway `$HOME`, vendored scripts at workspace root, expects fall-through to `$PWD` (`evals/lib/cv-fixture-lib.sh:43-49`) | works | **at risk** (F3) |

### 1b. Snippet carriers (38 files, counted; matches the spec's 38)

- `agents/` 6: `code-archaeologist`, `doc-validator`, `domain-expert`, `parallel-dispatcher`, `partition-reviewer`, `spec-reviewer`.
- `commands/` 15: `v-adr`, `v-collect`, `v-dispatch`, `v-epic`, `v-init`, `v-lessons`, `v-memory-refresh`, `v-models`, `v-onboard`, `v-orchestrate`, `v-remember`, `v-resume`, `v-review-plan`, `v-status`, `v-triage`. `v-pr-review.md` and `skills/pr-review/SKILL.md` carry none (they use no `$CV`).
- `skills/backend-launcher/` 6: `SKILL.md`, `adapter-{antigravity,claude,codex,cursor,opencode}.md`.
- `skills/compound-v/` 10: `SKILL`, `adr-capture`, `cross-model-review`, `execution-manifest`, `memory`, `onboarding`, `phase-0-recon`, `phase-2-disjoint-partitioning`, `phase-3-parallel-opus-dispatch`, `routing-policy`.
- `evals/README.md` 1.
- Total `$CV/...` call sites: 183 across 37 files (the 38th, `evals/README.md`, only shows the snippet). CHANGELOG 3.6.1 says "161 call sites across 36 files" at that release.

### 1c. Root-resolution inventory (the widened scope)

Kind P = plugin root, kind R = project root. "Workaround?" is my judgement from the code, with the reason.

| # | file:line | Kind | What it does | When expected root is absent | Duplicates | Workaround? |
|---|---|---|---|---|---|---|
| 1 | 38 md files, see 1b | P | the `CV=` snippet | falls to `$PWD`, which is the user's project, so `$CV/scripts/x.py` is "No such file" | all 38 copies of each other | yes: whole-path `sort -V` picks wrong copy (the bug) |
| 2 | `evals/lib/cv-fixture-lib.sh:19-30` `cv_plugin_root` | P | `CV_EVAL_PLUGIN_ROOT`, else two levels above the case dir, else `CLAUDE_PLUGIN_ROOT` | prints error, returns 1 | a 4th ladder | justified: fixture runs from a source checkout |
| 3 | `hooks/hooks.json` (10 command strings) | P | `"${CLAUDE_PLUGIN_ROOT}/hooks/x.sh"` | n/a, harness sets it | none | no |
| 4 | `hooks/memory-refresh.sh:75` | P | `${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}` | falls back to script-relative | #5, #6 same shape | no (script-relative is exact) |
| 5 | `hooks/brainstorm-trigger0-nudge.sh:128` | P | same shape as #4 | same | #4 | no |
| 6 | `hooks/lane-guard.sh:272-273` | P | `${CLAUDE_PLUGIN_ROOT:-$HOOK_DIR/..}` | script-relative | #4 | no |
| 7 | `hooks/session-banner.sh:35`, `:51` | P | `${CLAUDE_PLUGIN_ROOT:-.}/scripts/...` | **`.` = the project's cwd**: runs the project's own `scripts/compound-v-onboard.py` / `compound-v-dashboard.py` | none | **yes, and a hazard**: the same hole `hooks/precompact-snapshot.sh:188-196` documents and closed ("any repository that merely contains ... would have its own Python executed"). Latent only because the harness always sets the var for hooks |
| 8 | `hooks/triage-prompt-nudge.sh:259-268` `_locate_script` | P | `CLAUDE_PLUGIN_ROOT/scripts/$1`, else `$(dirname $0)/../scripts/$1` | returns 1, callers fail soft | #9, #10 | no |
| 9 | `hooks/postcompact-resume.sh:119-128` `_locate_dashboard` | P | same, dashboard only | returns 1 | #8 | no |
| 10 | `hooks/precompact-snapshot.sh:197-206` | P | same, inline | returns 1 | #8, #9 | no |
| 11 | `hooks/run-band.tsx:41`, `hooks/jev-t3.tsx:92` | P | `$.plugin.root` (engine-provided) | `stat` fails, returns null | none | no; only TS mechanism, and the correct one |
| 12 | `hooks/plan-saved-nudge.sh:67`, `brainstorm-trigger0-nudge.sh:147` | n/a | `CLAUDE_PLUGIN_ROOT` used only to detect "am I Claude Code" | n/a | n/a | not a root lookup |
| 13 | ~45 `os.path.dirname(os.path.abspath(__file__))` sibling loads in `scripts/*.py` | P | script finds its own siblings | n/a | `PLUGIN_ROOT = dirname(HERE)` in `compound-v-emit-preflight.py:81`, `compound-v-emit-workflow.py:956` and inline at `:937` | no: correct by construction |
| 14 | `scripts/compound-v-validate-manifest.py:6071`, `scripts/compound-v-taxonomy.py:1010` | P used as R | `dirname(dirname(__file__))` as "this repo" | n/a | none | justified: both are inside the selftest (`_selftest` starts at validate-manifest `:5072`; taxonomy block is under `expect(...)` dogfood), dogfooding the plugin's own checkout |
| 15 | `scripts/compound-v-triage-outcomes.py:255-261` `_repo_root`, `default_stream_path` | **P used as R** | `dirname(scripts/)` becomes the project root: default stream, `load_project_config` base (`:272`, `:1136`), `_resolve_exec_dir` base (`:749`) | never absent, silently wrong | #16-#18 | **yes, the defect** (F8) |
| 16 | `scripts/compound-v-preeval.py:1620-1630` | R | `kwargs.setdefault("stream_path", join(repo or ".", "docs/superpowers/memory/triage-outcomes.jsonl"))` | uses `.` | #15, #17, #18; the relpath is hard-coded again at `compound-v-preeval.py:2532, 2584, 2826, 2884, 2906, 3039, 3096, 3220` | **yes**: a per-caller patch for #15, with its own comment saying so |
| 17 | `scripts/compound-v-fastpath-materialize.py:90`, `:708` | R | own `TRIAGE_STREAM_REL`, joins with `repo` | n/a | #15, #16 | yes, same cause |
| 18 | `scripts/compound-v-emit-workflow.py:5116` | R | `join(repo_root, module.STREAM_RELPATH)` | n/a | #15 | no: uses the module's constant; correct |
| 19 | `scripts/compound-v-emit-workflow.py:130-138` | R | **no default repo root; required; absence fails closed** (history: `REPO_DEFAULT = dirname(HERE)` wrote a patch into the plugin dir, 2026-07-13 incident) | fail closed | none | no: this is the project-root rule already written down once |
| 20 | `scripts/compound-v-memory.py:82-93` `find_repo_root` | R | `git -C start rev-parse --show-toplevel`, realpath; non-git falls back to `start` | `start` | #21-#25 | no |
| 21 | `scripts/compound-v-triage-outcomes.py:615-624` `_git_toplevel` | R | same git command; non-git returns `None` | `None`, fail closed | #20 | no |
| 22 | `scripts/compound-v-validate-manifest.py:3285-3295` `_find_repo_root` | R | walk up to `.git` (dir or file) | **`os.getcwd()`** | #20, #23, #24 | yes: silent fallback to a different root than its start |
| 23 | `scripts/compound-v-transcript-watch.py:681-690` `repo_root_for` | R | walk up from run dir to `.git` | `None` | #22 | no |
| 24 | bash walk-up copies: `hooks/triage-prompt-nudge.sh:245`, `hooks/postcompact-resume.sh:85`, `hooks/epic-goal-stop.sh:155`; TS copy `hooks/jev-t3.tsx:63` | R | walk up to `.git`, 40 levels, fall back to the start dir | start dir | each other, #20, #22, #23 | no, but `postcompact-resume.sh:81-84` states it is "duplicated rather than shared" on purpose |
| 25 | `hooks/lane-guard.sh:721-746` `project_roots` | R | `CV_PROJECT_DIR`, `CLAUDE_PROJECT_DIR`, `/.claude/worktrees/<id>` strip, then walk up to a dir holding `docs/superpowers/execution` (12 levels) | empty list | none | no: different question (where is the live lane map) |
| 26 | `hooks/precompact-snapshot.sh:169-180, 231-232` | R | uses `cwd` as the root, no walk-up | silent exit | #24 | yes: disagrees with #24 (F12) |
| 27 | `hooks/run-band.tsx:179` | R | `${session.cwd()}/docs/superpowers/execution`, no walk-up | silent return | #24 | yes: a session started in a subdirectory shows no band (F12) |
| 28 | `hooks/brainstorm-trigger0-nudge.sh:73, 134` | R | passes raw hook `cwd` as `--repo` | omits `--repo` | #24 | yes: no walk-up, unlike its sibling hooks |
| 29 | `scripts/compound-v-sandbox-checkout.sh:77` | R | `git rev-parse --show-toplevel` | script aborts (`set -e` assumed, not read) | #20 | no |
| 30 | `scripts/compound-v-preeval.py:1715, 1809`, `compound-v-codex-review.sh:63`, `compound-v-run-cursor-worker.sh:339` | R | `--repo` default `.` / required absolute | `.`; the two shell scripts require absolute | #20 | python default `.` is cwd, not toplevel: yes, mild |
| 31 | `scripts/compound-v-dashboard.py:49` | R | `DEFAULT_EXECUTION_ROOT = "docs/superpowers/execution"` (cwd-relative) | empty result | #27 | same family as #27 |

## 2. Shared State

**`CV` (shell variable in 183 call sites).** Set by the snippet once per bash block. The Bash tool does not persist shell state between calls
(tool contract: "Shell state (env vars, functions) does not persist"), while every document says "resolve the plugin root once per
session". So the snippet must be present in every bash block that uses `$CV`, and the model re-runs it each time. Gap: any cost in
the snippet (a `claude` spawn, a `python3` spawn) is paid once per block, not once per session. Not measured; no number is claimed.

**`stream_path` in `compound-v-triage-outcomes.py`.** Set in: `predicted` by `compound-v-preeval.py:1628` (patched to the project);
`bind` by `compound-v-fastpath-materialize.py:710` (explicit); `actual(merge_pending)` by `compound-v-emit-workflow.py:5116` (explicit).
NOT set in: the CLI `bind` at `commands/v-orchestrate.md:151`, the CLI `actual` at `commands/v-collect.md:128`,
`commands/v-dispatch.md:340`, `agents/parallel-dispatcher.md:365`, and `precision` at `commands/v-status.md:103` (passes `--repo .` but no
`--stream`). Fallback elsewhere: `default_stream_path()` = `<plugin dir>/docs/superpowers/memory/triage-outcomes.jsonl`. Gap: run from an
installed plugin these five commands append to, or read, the plugin cache's copy; `append_line` does `makedirs` so the write succeeds
silently. In `precision`, `stream_path` resolves to the plugin dir while `exec_dir` resolves from `--repo .` (`_resolve_exec_dir`, `:744-750`),
so the two halves of one query point at different repositories. And `_make_git_ctx` (`:627-641`) treats a non-git plugin cache as "nothing
verifies", so the terminal `actual` is excluded and Tier-2 reads as insufficient: the failure is quiet.

**`proj` / project root in the hooks.** `triage-prompt-nudge.sh:605`, `postcompact-resume.sh:192`, `epic-goal-stop.sh:660`, `jev-t3.tsx:268`:
walk-up from realpath(cwd). `precompact-snapshot.sh:175-180`, `run-band.tsx:179`, `brainstorm-trigger0-nudge.sh:134`: cwd as given. A session
whose cwd is a subdirectory of the project gets a different answer from each family.

**`claude plugin list --json` fields.** The spec relies on `id`, `enabled`, `installPath`, `version`. Observed locally once (spec), and
`commands/v-init.md:304-312` already reads `id` and `enabled`. `installPath` and `version` are read nowhere in the repo today. The 1C KB
(line 15) records that the field names and minimum version are not documented.

## 3. Sibling Code

**`commands/v-init.md:301-313` (1g, `claude plugin list --json | python3 -c`).** Entry: always, in a Bash block. Reads `id` startswith
`compound-v-vault@`, `enabled`. Edge cases handled: bad JSON (`d = []`), missing CLI (stderr dropped, empty stdin -> `[]`). Edge cases not handled: no
timeout on `claude` (the sibling at `:334-339` wraps `claude --version` in `compound-v-run-with-timeout.py --timeout 5`, which needs `$CV`, which
the resolver cannot use before `CV` exists); no `scope` use. Latent bug per `v-init-1g-map.md`: PATH `claude` can be a different
install from the host. This is the closest existing code to the spec's step 2 and it is the only reader of this JSON.

**`hooks/session-banner.sh:67-81` `_semver_lt`.** The repo's only per-component numeric version compare in bash, written because `sort -V` is not
reliable on macOS. The spec's step 3 and test (e) `3.10.0` vs `3.9.9` need the same compare in python; it is a third spelling.

**`compound-v-emit-workflow.py:130-138`.** Sibling for the project-root rule: "required everywhere it decides a destination, and its absence
FAILS CLOSED". It is the only place the project-root rule is written down, and `compound-v-triage-outcomes.py` still violates it.

**`hooks/precompact-snapshot.sh:188-196`.** Sibling for the plugin-root rule on the hook side: resolve from the plugin, never from the project's cwd.
`session-banner.sh:35, 51` (`:-.`) violates it.

**`evals/lib/cv-fixture-lib.sh:19-57` and `evals/README.md:97-113`.** Document that the snippet is expected to land on `$PWD` in an eval run.
`evals/README.md:102-103` carries a second line without the `; CV="${CV%/}"` suffix (F1).

## 4. External APIs

Context7 unavailable (OAuth). From the 1C KB `claude-code-plugin-root.md`, dated 2026-10-08 and fetched from code.claude.com:

- `${CLAUDE_PLUGIN_ROOT}` is substituted inline "anywhere in the Markdown body" of skill, command and agent content; only the exact `${NAME}` form is documented. The repo's snippet writes `${CLAUDE_PLUGIN_ROOT:-...}`, which is not that form.
- Not present in the Bash tool environment, main session or subagent. Exported to hook commands, MCP stdio and LSP servers only.
- Layout `cache/<marketplace>/<plugin>/<version>/` under `~/.claude/plugins`, or under `CLAUDE_CODE_PLUGIN_CACHE_DIR` when set. The snippet hard-codes `$HOME/.claude/plugins/cache`; with that variable set the cache is elsewhere and every cache lookup misses.
- `installed_plugins.json` (documented) holds `scope`, `installPath`, `version` per install. `enabledPlugins` in settings holds enabled state across six sources; the CLI is the only documented merger.
- `claude plugin list --json` field names: undocumented. Minimum version: undocumented (`--json` on install/uninstall/update/enable/disable needs >= 2.1.268).
- Version may be a SHA, a SHA-256 prefix or `unknown`. Replaced version dirs carry `.orphaned_at` and are removed after 14 days. `--plugin-dir` beats an installed copy silently.

## 5. Regression Surface

- Every command, agent and skill that runs `$CV/scripts/...` (183 sites): if the new snippet exits non-zero, prints to stdout, or leaves `CV` empty, each of them fails with "No such file" on a path under the user's project. This is the 3.6.1 failure again.
- `tests/test-agent-recall.sh:34-35`: greps agent files for `compound-v-memory\.py"? (search|recall-check)`. Survives a snippet change; breaks if the new snippet is moved out of the agent body such that the command line changes spelling.
- `tests/memory-queries.tsv:14, 23, 34`: three recall queries expect `phase-3-parallel-opus-dispatch.md` and `memory.md` to surface for "CLAUDE_PLUGIN_ROOT not set / hint / переменная ... не для Bash". Rewriting the explanatory prose in those two files can drop their ranking; the recall test would then fail.
- Eval suite (`evals/`, 7 cases): fixtures depend on fall-through to `$PWD` (F3). A step that finds an enabled real install makes the arms run the installed plugin instead of the vendored scripts.
- `/v:epic` (30 `$CV` uses) and `/v:dispatch` (11): long-running sessions that bind scripts at start; picking a different copy mid-session changes script behaviour between blocks.
- Triage stream readers/writers (`/v:orchestrate` bind, `/v:collect` and `/v:dispatch` actual, `/v:status` precision): wrong-copy write today; any change to `default_stream_path` changes where those five write. If it now points at the project, a previously accumulated plugin-cache stream (if any exists on a user's machine) is orphaned.
- Hooks: `precompact-snapshot.sh` and `postcompact-resume.sh` share a snapshot key built from realpath(cwd) (`:175`, `:214`); changing either to a project-root key without the other silently disables the snapshot-first path. `tests/test-native-points.sh` asserts they agree by writing with one and reading with the other.
- `hooks/triage-prompt-nudge.sh` -> `compound-v-preeval.py` -> triage stream: pinned by the `setdefault` at `:1628`; removing that line without fixing #15 puts `predicted` events back into the plugin checkout.

## 6. DRY Findings

- Plugin root, bash: **seven spellings**. The snippet (38 copies) plus `${CLAUDE_PLUGIN_ROOT:-$(cd dirname $0/..)}` in `memory-refresh.sh:75`, `brainstorm-trigger0-nudge.sh:128`; `:-$HOOK_DIR/..` in `lane-guard.sh:272`; `:-.` in `session-banner.sh:35, 51`; `_locate_script` (`triage-prompt-nudge.sh:259`), `_locate_dashboard` (`postcompact-resume.sh:119`), inline (`precompact-snapshot.sh:197`). Decision input for the plan: the hooks are all "env var, else script-relative" and are correct except #7; they need one rule, not a new mechanism.
- Project root, bash/TS walk-up to `.git`: four copies (`triage-prompt-nudge.sh:245`, `postcompact-resume.sh:85`, `epic-goal-stop.sh:155`, `jev-t3.tsx:63`), two of them commented as deliberate duplicates.
- Project root, Python: `find_repo_root` (`memory.py:82`), `_git_toplevel` (`triage-outcomes.py:615`), `_find_repo_root` (`validate-manifest.py:3285`), `repo_root_for` (`transcript-watch.py:681`). Four helpers, three different "not found" results (`start`, `None`, `cwd`) and one that does not use git at all.
- Triage stream relpath: `STREAM_RELPATH` (`triage-outcomes.py:120`), `TRIAGE_STREAM_REL` (`fastpath-materialize.py:90`), and a literal join repeated 9 times in `compound-v-preeval.py` (`:1629`, `:2532`, `:2584`, `:2826`, `:2884`, `:2906`, `:3039`, `:3096`, `:3220`).
- Version compare: bash `_semver_lt` (`session-banner.sh:70`); the spec adds a python one inside a markdown snippet.
- `claude plugin list --json` parse: `commands/v-init.md:304` and the spec's step 2. Two parsers of one JSON.
- Decision (for the plan to confirm, not mine): extend the existing helpers rather than add a ninth.

## 7. Design constraints for the spec

1. **Fix the byte-identity claim.** `evals/README.md:103` has `CV="${CV:-$PWD}"` with no `; CV="${CV%/}"`. Either that file takes the full two lines, or test (a) must say which lines it compares; as written, a byte-for-byte test over all 38 fails on the current README before any change.
2. **The snippet runs in every bash block, not once.** The Bash tool keeps no shell state. The design MUST bound the cost of a `claude` spawn plus a `python3` spawn per block and MUST bound the `claude` call with a timeout it implements itself (python `subprocess` timeout; `timeout(1)` is absent on stock macOS per `hooks/session-banner.sh:63`; `compound-v-run-with-timeout.py` is not usable before `CV` is known). The latency is unmeasured and no figure may be asserted; the plan needs a measured number or a caching decision (for example, an env var the block can reuse) recorded as such.
3. **Eval isolation.** Define what step 2 does when `HOME` is a throwaway directory and a `claude` binary is on PATH. The fixtures in `evals/lib/cv-fixture-lib.sh` need the result to be the vendored workspace `$PWD`. A resolver that returns an installed copy invalidates both arms of every eval case. Test row required.
4. **Step 2 may not assume field names.** `installPath` and `version` are observed once and undocumented (1C KB line 15). The snippet MUST tolerate a missing key, a non-string, a non-directory path and a non-numeric `version` (SHA, `unknown`) and fall through, and MUST say how it orders a non-numeric version.
5. **Step 3 MUST skip `.orphaned_at` directories**, and MUST honour `CLAUDE_CODE_PLUGIN_CACHE_DIR` if the plugins root is to be found at all. Without the first, a rollback (3.8.3 to 3.7.5) leaves the orphaned higher version winning on "highest version segment"; this machine already has a disabled older copy.
6. **`--plugin-dir` / `@inline` plugins** never appear in the cache; the spec must state what happens (the CLI listing may or may not show them: unknown) or list it as a known gap. "Out of scope" currently does not mention it.
7. **State the alternative and why it is rejected.** Skill, command and agent bodies get `${CLAUDE_PLUGIN_ROOT}` substituted by the harness at load (documented, exact form only). Whether that applies to reference files read via the Read tool (`skills/compound-v/phase-*.md`, `skills/backend-launcher/adapter-*.md`) is not documented: unknown. The architecture review must decide this explicitly; it is the one mechanism that resolves the exact enabled copy with no process spawn.
8. **Hook-side plugin root: one rule, and remove `:-.`.** `hooks/session-banner.sh:35, 51` falls back to the project's cwd. Replace with the script-relative form already used by `memory-refresh.sh:75`, or document why it stays. Collapse `_locate_script`, `_locate_dashboard` and the inline copy in `precompact-snapshot.sh:197` into one pattern.
9. **Project-root rule: no `__file__`-derived default.** `compound-v-triage-outcomes.py:255-261` MUST stop deriving a project root from the script's location; follow `compound-v-emit-workflow.py:130-138` (required, fails closed). That removes the need for `compound-v-preeval.py:1628` (`setdefault`) and the five CLI call sites (`commands/v-orchestrate.md:151`, `commands/v-collect.md:128`, `commands/v-dispatch.md:340`, `agents/parallel-dispatcher.md:365`, `commands/v-status.md:103`) MUST then pass the project explicitly. `precision --repo .` today mixes a project `exec_dir` with a plugin `stream_path`.
10. **One definition of the stream relpath.** `STREAM_RELPATH` is the constant; `fastpath-materialize.py:90` and the nine literals in `compound-v-preeval.py` MUST import or reuse it, or the plan MUST justify the copies in writing.
11. **One definition of "not found" for the project root** (Python: start dir vs `None` vs `os.getcwd()`; hooks: start dir). `validate-manifest.py:3285-3295` returns `os.getcwd()` for a start path that is elsewhere, which is a silent wrong root.
12. **Subdirectory cwd.** `precompact-snapshot.sh:169-180`, `run-band.tsx:179` and `brainstorm-trigger0-nudge.sh:134` do not walk up; `triage-prompt-nudge.sh`, `postcompact-resume.sh`, `epic-goal-stop.sh` and `jev-t3.tsx` do. The rule must pick one, and the snapshot key shared by precompact/postcompact must change in both or neither.
13. **The handoff's `compound-v-jev.py` claim is not reproduced.** `compound-v-jev.py` takes `--repo` (required, `:1014-1045`) and keys its data dir on it (`:230-238`); it has no `__file__`-derived project root (`HERE` at `:49` is used only to load siblings, `:140`). The spec's widened-scope text repeats the claim ("the same is reported for `compound-v-jev.py`"); the plan must not schedule a fix for it. Caller side: `brainstorm-trigger0-nudge.sh:134` passes an un-walked cwd to a different script.
14. **Tests.** Keep `tests/memory-queries.tsv:14, 23, 34` passing (the two target docs must still rank for those queries). Test (b) must run with a fake `HOME` AND with `CLAUDE_CODE_PLUGIN_CACHE_DIR` unset; add a row for an `.orphaned_at` directory and one for a non-numeric version directory. CI discovery is recursive under `tests/` (`.github/workflows/validate.yml:351`), so `tests/test-plugin-root.sh` is picked up with no registration; it must be executable-safe and `shellcheck`-clean (`scripts/compound-v-*.sh` and `hooks/*.sh` are linted; `tests/*.sh` is not named in the rule, unknown whether shellcheck covers it).
15. **Justify, in writing, what stays:** the ~45 `__file__`-relative sibling loads (#13), the two selftest-only repo derivations (#14), `cv-fixture-lib.sh:19-30` (#2) and `lane-guard.sh:721-746` (#25, a different question).

## 8. File Touch Map

Plugin-root snippet (38 files; each is one hunk, the same two lines):
- `agents/{code-archaeologist,doc-validator,domain-expert,parallel-dispatcher,partition-reviewer,spec-reviewer}.md`: snippet plus nearby prose (`:38-39` area). `agents/*.md` are linted by `scripts/lint-frontmatter.py`.
- `commands/v-{adr,collect,dispatch,epic,init,lessons,memory-refresh,models,onboard,orchestrate,remember,resume,review-plan,status,triage}.md`: snippet plus the "set for hooks but not Bash" paragraph. `commands/v-init.md` also needs the `claude plugin list` reader reconciled (DRY with step 1g).
- `skills/backend-launcher/{SKILL,adapter-antigravity,adapter-claude,adapter-codex,adapter-cursor,adapter-opencode}.md`.
- `skills/compound-v/{SKILL,adr-capture,cross-model-review,execution-manifest,memory,onboarding,phase-0-recon,phase-2-disjoint-partitioning,phase-3-parallel-opus-dispatch,routing-policy}.md`: `memory.md` and `phase-3-parallel-opus-dispatch.md` are recall-test targets (SHARED RESOURCE for `tests/memory-queries.tsv`).
- `evals/README.md` (second line differs, F1) and `evals/lib/cv-fixture-lib.sh:43-49` (comment that repeats the old snippet).

Project-root and hook side (if the widened scope is carried out):
- `scripts/compound-v-triage-outcomes.py`: `_repo_root`, `default_stream_path`, CLI `--stream`/`--repo` handling. SHARED RESOURCE (loaded by path from `compound-v-preeval.py:379`, `compound-v-fastpath-materialize.py:139`, `compound-v-emit-workflow.py:5068`).
- `scripts/compound-v-preeval.py`: `:1628` and nine relpath literals. SHARED RESOURCE (loads eight siblings; `evals/lib/cv-fixture-lib.sh:37-41`).
- `scripts/compound-v-fastpath-materialize.py:90, 708`; `scripts/compound-v-validate-manifest.py:3285`.
- `commands/v-orchestrate.md:151`, `commands/v-collect.md:128`, `commands/v-dispatch.md:340`, `commands/v-status.md:103`, `agents/parallel-dispatcher.md:365` (already in the snippet list; second hunk each).
- `hooks/session-banner.sh:35, 51`; `hooks/precompact-snapshot.sh`; `hooks/postcompact-resume.sh`; `hooks/run-band.tsx:179`; `hooks/brainstorm-trigger0-nudge.sh:134`; `hooks/triage-prompt-nudge.sh`; `hooks/epic-goal-stop.sh`; `hooks/jev-t3.tsx`. The bash hooks are standalone by house style; a new shared sourced file would be a SHARED RESOURCE and `postcompact-resume.sh:81-84` documents why it was avoided.
- `hooks/hooks.json`: SHARED RESOURCE (route registry; touch only if a hook's invocation changes).

New files:
- `tests/test-plugin-root.sh` (new, per spec).
- Project-root helper tests: location unknown; any new Python test goes under `tests/` (`scripts/` is swept for `--selftest` only).

SHARED RESOURCE summary: `scripts/compound-v-triage-outcomes.py`, `scripts/compound-v-preeval.py`, `hooks/hooks.json`, `tests/memory-queries.tsv`, and `skills/compound-v/memory.md` plus `skills/compound-v/phase-3-parallel-opus-dispatch.md` (recall-test targets).
