---
name: finalize-and-laneguard-map
description: Where Engine C finalize-wave, state.waves and the lane-guard cwd->worktree resolution live, and the couplings no import graph shows (checked 2026-10-05)
metadata:
  type: reference
---

Map facts, 2026-10-05 checkout. Leads, not verdicts: re-verify before use.

- `cmd_finalize_wave` is `scripts/compound-v-emit-workflow.py:~5950`. Order: authority-exists check, `manifest_digest_fault`, the integration-gate subprocess, `_maybe_append_run_actual`, then refusal (writes `phase: BLOCKED` and retires `lane-map.json` and `.run.lock`) or merge, commit and `_apply`.
- `state.waves[str(wave)]` is written ONLY by `_apply` and read nowhere outside the selftest. A refusal never rewrites it.
- `state.json` is exempt by name from the scope gate (`RUN_DIR_EXEMPT_BY_NAME`), so a direct worker can forge `merged.integrated`. The finalizer's per-job check asks git (`head_matches_post_image`); any wave-level trust in `state.json` weakens that.
- On an idempotent re-finalize `waves[N].commit` is HEAD at that time, not a wave commit.
- `hooks/lane-guard.sh` `resolve_job` (~:822): longest-prefix over `lane-map.json` `worktrees`; a direct job registers the checkout, which prefixes every `.claude/worktrees/<id>`. Wrappers are listed, never claimed.
- An unresolved cwd under `.claude/worktrees/` with a live map still writes a `lane-guard-unresolved.jsonl` line and emits a one-time notice (`record_unresolved`). The log string is `UNRESOLVED IDENTITY`, not `job unresolved`.
- Every existing `tests/test-lane-guard.sh` fixture worktree is a plain directory with no `.git`, so no existing row can see a `.git`-boundary bug.
- `tests/test-lane-guard.sh:1344-1373` greps the hook source for required and forbidden strings (`fnmatch`, `glob_to_regex`, `replaces the git`, `instead of the git`); mutation rows `sed` exact lines.
- Agent Bash can be clamped to git read forms, and the user's `rtk` hook rewrites `git ...` to `rtk git ...`, which then matches no clamp form. Use Read/Grep; git may be unavailable.
