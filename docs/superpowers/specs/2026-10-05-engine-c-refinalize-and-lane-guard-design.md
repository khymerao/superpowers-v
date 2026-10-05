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

## Pre-flight amendments (2026-10-05)

Audits: `docs/superpowers/archaeology/2026-10-05-2026-10-05-engine-c-refinalize-and-lane-guard-design.md`,
`docs/superpowers/expert/2026-10-05-2026-10-05-engine-c-refinalize-and-lane-guard-design.md`,
`docs/superpowers/library-audit/2026-10-05-2026-10-05-engine-c-refinalize-and-lane-guard-design.md`. This section
overrides the sections above it. Facts the auditors could not check (their git was clamped) were checked by the
orchestrator: wave commits 03cf1e2, 873b5c2, a819047, 50f540b and 7da34bd are all ancestors of HEAD;
`lane-guard-unresolved.jsonl` is not in `RUN_DIR_EXEMPT_BY_NAME`; the job-resolution code is Python inside the hook.

**Defect 1, tightened.**

1. A fifth condition, asked of git: the recorded commit's subject (`git log -1 --format=%s <commit>`) must equal the
   finalizer's own wave-commit subject for this run and wave. The subject is built by one helper,
   `_wave_commit_subject(wave, run_id, merged)`, used both where the finalizer commits today (`cmd_finalize_wave`,
   `"compound-v: wave %d of run %s (%s)"`) and by the check, so the format is spelled once.
2. The recorded `commit` must match `^[0-9a-f]{40}$` or `^[0-9a-f]{64}$` before it reaches git's argv; anything else
   declines the short-circuit.
3. Every git call runs with `-C repo_root` and counts only `returncode == 0` as yes. Exit 1, exit 128, a missing
   binary, a timeout or an exception all decline, and the declining reason is logged. No SHA-inequality condition:
   a commit is its own ancestor, and row A records the wave at HEAD.
4. The result stays inside the existing finalize output keys; its reason must not start with
   `nothing left to commit` (that prefix is load-bearing elsewhere in the finalizer).
5. Accepted limits, stated: `state.json` is worker-writable and already exempt by name, so a worker that forges both
   a `waves` entry and an ancestor commit with the finalizer's subject can make a re-finalize skip that wave. The
   consequence is a wave not re-merged (dropped work the review's checks on the merged tree catch), never ungated
   work landing: the short-circuit merges nothing. A squash or rebase of the branch makes the wave commit a
   non-ancestor, and re-finalize falls back to today's behaviour. A run the earlier incident left `BLOCKED` stays
   `BLOCKED` (the short-circuit writes nothing); `/v:resume` is what reconciles it. A later revert of the wave commit
   is not detected.
6. Observed symptom, corrected: the observable effect asserted by tests is the refusal path's real write (phase
   `BLOCKED`), not a particular `waves` field.

**Defect 1 tests, revised.** Row A: state recorded at the test repo's HEAD with the finalizer's subject; a stub gate
(a real Python file) that refuses; `finalize-wave` exits 0 and `state.json` is byte-identical. Row B: recorded commit
`"0" * 40` (git exit 128): no short-circuit, the run goes `BLOCKED`. Row C: a real commit that is not an ancestor of
HEAD (git exit 1): the run goes `BLOCKED`. Row D: an ancestor commit whose subject is not the wave subject: the run
goes `BLOCKED`. Row E: a `commit` value starting with `-`: no git call is made with it, and the run goes `BLOCKED`.

**Defect 2, exact rule.**

1. The walk uses the same path form (lexical or realpath) under which `_rel_under` matched `cwd` against `wt`;
   `_rel_under` reports which form matched, or the walk repeats the match per form.
2. It visits `cwd` and each parent up to, but excluding, `wt`, and asks `os.path.lexists(os.path.join(d, ".git"))`
   (a `.git` file counts: worktrees and submodules write one). It is bounded by the component count between the two.
3. A `.git` found: the claim stops there, and the session takes the unresolved path. If the walk never reaches `wt`
   (a path-form mismatch), the claim stands exactly as today: the guard does not fail open on a defect in the new
   check.
4. The comment above the branch names nested worktrees, submodules and nested repositories as boundaries, and says
   the scope gate cannot see inside them. It avoids the strings `tests/test-lane-guard.sh:1344-1373` forbids and
   changes no line that test mutates.
5. `TROUBLESHOOTING.md:290` describes cwd-to-worktree resolution, so it is updated (Lane B).

**Defect 2 side effect, closed in Lane A.** After the fix, an isolated session stopped at the boundary under a live
lane map is recorded by `record_unresolved` in `<run-dir>/lane-guard-unresolved.jsonl`. That run dir sits in a direct
job's gated tree and the file is tracked, so a line appended while a direct job runs would be charged to that job.
The record must stay (a worker that wrote before `register-lane` is exactly such a session), so
`RUN_DIR_EXEMPT_BY_NAME` gains `lane-guard-unresolved.jsonl` with the reason "written by hooks/lane-guard.sh, never by
a job; an append-only record of sessions the guard could not resolve". Its selftest row comes from the list; a sibling
name beside it stays non-exempt.

**Defect 2 tests, revised.** Each row runs against an isolated project fixture with a live map whose only claim is a
direct job on the checkout.
- Nested unregistered worktree with a `.git` file: a write is allowed, and the hook log carries
  `UNRESOLVED IDENTITY`, not `DENY`. Without the change it is denied as the direct job.
- Plain subdirectory of the checkout: still resolves to the direct job; an out-of-lane write is denied.
- A worktree registered for its own job, holding a `.git` file at its root (as real linked worktrees do): resolves to
  that job, and an out-of-lane write in it is denied. Without this row a check that also inspected `wt` itself would
  disable the guard for every real worktree job while the suite stayed green.

**AC-4, clarified.** The scratch clone is full depth (`git clone --no-local`, no `--depth`).

**Out of scope, unchanged rule.** Version bump, CHANGELOG, `plugin.json` and `marketplace.json` are a release step,
not an implementation job.
