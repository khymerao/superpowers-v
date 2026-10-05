---
name: shared-resources-and-traps
description: Overlap traps and hidden shared resources in superpowers-v manifests (mod test discovery, CI test discovery, interface materialization, standard-tier Sonnet)
metadata:
  type: project
---

Leads only - re-verify each against the current tree before citing it as a finding.

- **`claude plugin test <dir>` recurses** into every `*.test.ts(x)` under dir, including a nested
  `plugins/<other>/hooks/*.test.tsx` (verified empirically on Claude Code 2.1.289, 2026-10-05).
  `claude plugin validate .` does NOT load a nested plugin's hooks.json. So a job that adds a nested
  plugin under the marketplace source `./` silently feeds tests into `tests/test-run-band-mod.sh`
  (`claude plugin test .`, requires 0 fail) - check that job's impacted_map runs that test.
  **Why:** the nested job's own impacted tests never run the root mod test.
  **How to apply:** whenever a manifest writes `plugins/**`, look for root-level `claude plugin test .` callers.
- **CI test discovery is dynamic** (`.github/workflows/validate.yml` `tests` job: recursive `find tests`
  for `*.sh`/`*.py`; selftest sweep greps `scripts/*.py` for `--selftest`). A new test file needs no
  CI edit, so validate.yml is not a shared resource for "adds a test" jobs.
- **Interface materialization drops the header line.** `/v:orchestrate` copied each plan task's
  `**Interfaces (produced):** <text>` block without the text on the header line itself (seen
  2026-10-05: lost `resolve_jev(...)` signature, `detect_ui_reason` signature, half a JSONL schema,
  a whole "consumes" line). Compare each job's `interfaces` first line against the plan line.
  Step 8's grep `^\*\*Interfaces:\*\*` misses the `(produced)` variant entirely.
- **`standard` tier resolves to Sonnet under `balanced`** (`scripts/compound-v-resolve-model.py`
  `_CLAUDE_BALANCED`). Planners here tend to leave two-file or text-composition jobs (corpus writing,
  config + command doc) on `standard` with no justification - check them against the 8-box taxonomy.
- **Undeclared consumers hide behind the wave barrier** (`topo_waves` makes each wave a barrier). A
  wave-2 job reading a wave-1 job's API without `depends_on` works by accident; it breaks on a failed
  or resumed prerequisite. Cross-check "consumes" lines against `depends_on`.
- **`hooks/hooks.json` `modules` takes ONE module per plugin** (Claude Code 2.1.289 refuses a second
  entry, seen 2026-10-05). A job adding a new mod must make it the single module and import the
  existing `hooks/run-band.tsx` `register`, so `tests/test-run-band-mod.sh` (its grep of the
  validator's per-module hooks line) becomes a shared resource of any new-mod job - that job must own it.
- **Cross-script tests outside a job's impacted_map.** `tests/test-onboard-rules.sh` drives
  `scripts/compound-v-onboard.py` via CLI, and `tests/test-native-points.sh` stubs `scripts/compound-v-jev.py`
  (seen 2026-10-05). An impacted_map that runs only the script's `--selftest` misses them; only the
  full_command at merge catches a break. Grep `tests/*.sh` for the script name before trusting impacted scope.
- **Lane-guard self-interference on dogfood runs.** The guard that enforces a run is the INSTALLED plugin
  copy (`~/.claude/plugins/cache/.../hooks/lane-guard.sh`), not the checkout, so a lane editing
  `hooks/lane-guard.sh` changes nothing mid-run. `resolve_job` walks maps newest-mtime first and, per map,
  tries agent_id then the cwd->worktree claim, so a direct job's checkout claim in one live map can
  capture a worker of another live run (or any session in `.claude/worktrees/*`) before its own map's
  agent_id entry is reached (seen 2026-10-05). Check which runs are non-terminal (MERGED/BLOCKED = terminal).
- **Out-of-lane drivers of `hooks/lane-guard.sh`:** `tests/test-disabled-hooks.sh` executes it,
  `tests/test-native-points.sh` greps its literal tool tuple `"Write", "Edit", "MultiEdit", "NotebookEdit", "Bash"`.
  `tests/test-transcript-watch.sh` / `test-usage-workflow.sh` only use the emit-workflow path as a string.
- **`RUN_DIR_EXEMPT_BY_NAME` is enumerated in prose** in `scripts/compound-v-scope-check.py`'s docstring
  (~:47 and ~:353). A job adding an entry to the list in emit-workflow leaves that docstring stale unless it owns it.
- **`claude plugin validate .` also validates `.claude-plugin/marketplace.json`** (first line of its output,
  seen 2026-10-05 on 2.1.289), so `tests/test-run-band-mod.sh` and `tests/test-jev-t3-mod.sh` (both require rc 0)
  are drivers of marketplace.json. An impacted_map entry for marketplace.json that runs only `jq` + one test
  misses them unless another changed file (e.g. `hooks/*.tsx`) pulls them in.
- **Co-change marketplace.json -> plugin.json / CHANGELOG.md (~100% / ~97%)** is release-driven (release
  commits dominate support). For a "no version bump" run it is an expected WARN, not an omission.
