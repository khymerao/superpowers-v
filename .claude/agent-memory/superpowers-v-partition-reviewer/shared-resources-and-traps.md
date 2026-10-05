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
