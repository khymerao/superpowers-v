---
name: root-resolution-map
description: Where plugin-root and project-root are resolved (snippet, hooks, python), and the couplings that bite
metadata:
  type: reference
---

Map facts as of 2026-10-08. Leads, not verdicts: re-verify.

- The `CV=` snippet is in 38 markdown files (agents 6, commands 15, backend-launcher 6, compound-v skills 10, evals/README); `evals/README.md:103` has a shorter second line than the other 37. `evals/lib/cv-fixture-lib.sh:43-49` relies on the snippet falling through to `$PWD` with a throwaway HOME.
- `scripts/compound-v-triage-outcomes.py:255` `_repo_root()` is `dirname(scripts/)`, i.e. the plugin dir; `bind`/`actual`/`precision` CLI calls in commands/agents pass no `--stream`. Patches around it: `compound-v-preeval.py:1628`, `compound-v-fastpath-materialize.py:708`. Precedent for the right rule: `compound-v-emit-workflow.py:130-138` (no default repo root, fail closed).
- `compound-v-jev.py` has no `__file__`-derived project root (`--repo` required); the research handoff's claim that it does was not reproduced.
- `hooks/session-banner.sh:35,51` uses `${CLAUDE_PLUGIN_ROOT:-.}` (falls back to project cwd). Project-root walk-up to `.git` is copied in 4 hooks (triage-prompt-nudge, postcompact-resume, epic-goal-stop, jev-t3.tsx); precompact-snapshot, run-band.tsx and brainstorm-trigger0-nudge use cwd with no walk-up.
- This agent's Bash clamp admits only memory search/recall-check and `git log/show/blame`; the global `rtk` rewrite makes the `git` forms miss the clamp, so use Grep/Read.
