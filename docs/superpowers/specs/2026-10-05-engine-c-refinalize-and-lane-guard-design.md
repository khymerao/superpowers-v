# Engine C: idempotent re-finalize of an integrated wave, and a lane guard that stops at a working-tree boundary - design

Two pipeline defects observed while running `2026-10-05-jev-classifier-foundation` and `2026-10-05-jev-review-fixes`.
Triage: FULL, record `2026-10-05T105338Z-fix-two-engine-c-pipeline-bugs-found-in-the-jev-runs-1-scrip-6cc1`
(an override fired: `hooks/lane-guard.sh` is a security hook). Trigger 0: `kb_skip`.

Constraints: Python 3.9 stdlib in Python code; bash in the hook as it is today; every behavioural change ships a
test row that fails when the change is reverted; no fabricated metrics; plain-sentence commit subjects.

## Defect 1: re-finalizing an integrated wave resets it

**Observed.** A fresh `Workflow({scriptPath})` relaunch re-runs `finalize-wave` for every wave, including waves
`state.json` already records as integrated. After the manifest had been re-emitted (new manifest digest), wave 1's
receipts no longer bound, the integration gate re-derived from worktrees that had been pruned, returned
`{"unverifiable": 5}`, and the finalizer wrote the wave back to `integrated: false`, `commit: null` (workflow
`wf_b71ebffa-5b3`). The 3.6.x message-text fix (c52343a) covers only the "nothing to commit" variant.

**Change.** `scripts/compound-v-emit-workflow.py` gains `_already_integrated_wave(run_dir, repo_root, wave, job_ids)`.
It returns the wave's success result only when all of these hold, else `None`:

- `state.json` `waves[<wave>]` is a dict with `integrated: true` and a non-empty `commit`;
- its `jobs` and its `merged` both equal `job_ids` as sets;
- every job in `job_ids` has `merged.integrated` true in `state.json`;
- `git merge-base --is-ancestor <commit> HEAD` exits 0 (asked of git, not taken from the record).

`cmd_finalize_wave` calls it right after the manifest-digest fault check and before the integration authority. A
non-`None` result is emitted with exit 0 and a reason naming the commit; nothing is written to `state.json`.
Otherwise the finalizer runs exactly as today.

**Accepted limit.** A wave commit later reverted is still an ancestor of HEAD, so it would still short-circuit.
Comparing against the sealed post-image instead gives false negatives once later commits touch the same files.

**Tests** (`--selftest`, beside the existing idempotent-commit row): a run dir whose integration gate is a stub that
prints `{"integration": "refused", "tally": {"unverifiable": 1}}` and exits 1; one direct job `w1`; `state.json`
phase `MERGED`, wave 1 integrated at the test repo's HEAD.
- Row A: `finalize-wave --wave 1 --jobs w1` exits 0, the phase stays `MERGED`, wave 1 keeps `integrated: true` and
  its commit. Without the change the stub refuses and the run goes `BLOCKED`.
- Row B: the recorded commit is `"0" * 40` (not in HEAD): no short-circuit, the stub refuses, the run goes `BLOCKED`.

## Defect 2: a lane claim on the checkout captures every nested worktree

**Observed.** `resolve_job` in `hooks/lane-guard.sh` attributes the acting session to the run's job whose recorded
worktree is the longest path prefix of `cwd`. A `direct` job's worktree is the main checkout, a prefix of every
`.claude/worktrees/<id>` under it. So while a run with a direct job was live, an unrelated session working in its own
worktree under `.claude/worktrees/` resolved to that direct job and had its writes denied. That session renamed the
run's `lane-map.json` to get out, which then blocked the run's own gate.

**Change.** In the `cwd->worktree` branch, a claim on `wt` covers `cwd` only when no directory from `cwd` up to, but
excluding, `wt` contains a `.git` entry (file or directory). A `.git` there means `cwd` sits in a separate git working
tree, and the claim stops at that boundary: the session is unresolved, and an unresolved session is allowed and
logged exactly as today. The check is filesystem-only (no `git` subprocess) and bounded by the depth between `cwd`
and `wt`. Resolution by `agent_id`, the longest-prefix order, and every rule after resolution are unchanged, so a
worktree job registered in the lane map still resolves to itself first. The comment above the branch says why. If
`TROUBLESHOOTING.md` describes how the guard picks a job, it gains one sentence; otherwise it does not change.

**Tests** (`tests/test-lane-guard.sh`), with a live lane map whose only claim is a direct job on the checkout:
- an unregistered `<checkout>/.claude/worktrees/x` holding a `.git` file: a write there is allowed and the log says
  the job is unresolved, not DENY. Without the change it is denied as the direct job.
- a plain subdirectory of the checkout (no `.git`): still resolves to the direct job, and an out-of-lane write there
  is still denied.
- a worktree registered in the map for its own job, under `.claude/worktrees/`: still resolves to that job.

## Partition

- Lane A: `scripts/compound-v-emit-workflow.py`.
- Lane B: `hooks/lane-guard.sh`, `tests/test-lane-guard.sh`, `TROUBLESHOOTING.md` (only if it describes job
  resolution).

## Acceptance criteria

- AC-1 `scripts/compound-v-emit-workflow.py --selftest` passes with rows A and B; row A fails with the call to
  `_already_integrated_wave` removed.
- AC-2 `tests/test-lane-guard.sh` passes with the three new rows; the nested-worktree row fails with the boundary
  check removed.
- AC-3 `shellcheck hooks/*.sh` is clean, and the manifest's full test command passes on the merged tree.
- AC-4 In a scratch clone of the merged tree (never the working checkout), re-running `finalize-wave` on wave 1 of
  `docs/superpowers/execution/2026-10-05-jev-classifier-foundation` (integrated, receipts bound to an older manifest
  digest) exits 0 and leaves that clone's `state.json` byte-identical.
