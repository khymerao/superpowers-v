# Verifying a Compound V acceptance criterion

From run `2026-09-11-v3.6-wide-dispatch-r2`. Re-verify each of these against the current tree before
relying on it.

## Run the criterion, do not read the selftest that covers it

Every AC in that run was already covered by a `--selftest` row in
`scripts/compound-v-emit-workflow.py`. Running them independently still paid, twice:

- **AC-4 fails closed in a way the selftest hides.** `record --expect-verdict blocked` alone does
  **not** produce a `verdict_disagreement` on the verdict. The digest branch fires first and the
  record refuses: *"an unbound digest is not an agreeing one"*. Both `--expect-verdict` and
  `--expect-diff-digest` must be passed together. The selftest always passes both, so reading it
  would have taught the wrong CLI.
- **A worktree fixture is not a drop-in for a direct one.** `record` on a worktree job whose gate
  receipt has no observed worktree refuses with a locator failure rather than recording. Build the
  AC-4 fixture as `isolation: direct`.

## The shapes that worked

- Temporary repos in the scratchpad, never in the project. `git init` + one commit +
  `git worktree add --detach` is enough for `register-lane` / `gate-receipt` / `record` /
  `finalize-wave` to run end to end.
- `record` is **write-once** per run directory. To run a second variant, `cp -R` the run directory,
  delete `results/<id>.json`, and clear that job's `status` in `state.json`.
- The clamped Bash surface refuses compounds and substitution. Put the whole procedure in a script
  file and run `bash <path>`; that also makes command and output quotable verbatim in the review.

## The two traps in reading a dead-link or lint result from a working checkout

- **Leftover worktrees poison a repo-wide scan.** The CI dead-link rule reported 32 dead links, all
  inside gitignored `.claude/worktrees/wf_*` left behind by a halted run. CI sees zero. Always filter
  by what git tracks before calling a repo-wide scan red.
- **An over-length line may predate the diff.** Check the pre-image length
  (`git show <baseline>:<file> | awk '/pattern/ {print length($0)}'`) before attributing a
  docs-constraint violation to the change under review.

## The two findings a green run will not hand you

Run `2026-09-11-v3.6-wide-dispatch-r2` passed every gate, every AC and every suite, and still had two
real defects. Both came from reading documents the gates do not read:

- **The audits' §7 MUSTs.** Expert MUST-1 required a five-ecosystem provisioning table; what shipped
  documents `npm ci` alone. No test, lint or gate looks at an audit. Build the §1.3 table explicitly
  — `grep -n "MUST" docs/superpowers/{archaeology,expert,library-audit}/<topic>.md` — and mark what
  you did not verify as unverified rather than counting it satisfied.
- **The spec's "Out of scope" section.** It named per-job provisioning; `_provision_spec` reads the
  job dict first and the validator checks only the top level. Over-build hides there, not in the diff
  of the jobs under review. Read Out of scope before declaring over-build clean, and probe anything
  it names with a live fixture rather than reading the function.

## Deriving the per-job test obligation

At `triage.tier: FULL` with a declared, non-empty `impacted_map`, the derived default applies:
match each entry of the job's `files_changed` against the map yourself. `full_command` is owed only
for a changed path matching **no** rule. Demanding it of a job whose every path matched is a review
error. Run it at run level anyway for the integration pass.
