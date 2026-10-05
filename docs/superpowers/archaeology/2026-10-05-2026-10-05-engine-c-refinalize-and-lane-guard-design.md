# Engine C re-finalize and lane-guard boundary: Code Archaeology

Spec: `docs/superpowers/specs/2026-10-05-engine-c-refinalize-and-lane-guard-design.md`. Checkout: branch `feat/jev-classifier-foundation`, 2026-10-05.

**Method limits, stated up front.**
- V-memory recall was in the prompt; one more search ran. Both returned only the spec itself plus CHANGELOG 3.4.x/3.6.x history. Nothing contradicted the spec.
- Git is unusable for this agent. The per-spawn Bash clamp admits `git log/show/blame`, but the user's `rtk` rewrite hook turns each into `rtk git ...`, which matches no allowed form. Every `git log`/`git show` I tried was denied. Consequence: I could **not** verify whether the three wave commits recorded in the jev run's `state.json` are ancestors of HEAD (UNKNOWN, see 5.4). `git blame` was not available for latent-bug dating either. All other findings are read from files.

## 1. Matrix

### Defect 1: `cmd_finalize_wave` (`scripts/compound-v-emit-workflow.py:5950`)

| Dimension | Values in code | New short-circuit handles? |
|---|---|---|
| `state.waves[str(wave)]` | absent / dict / non-dict; written ONLY at `:6084` (`_apply`) | spec: dict required |
| wave `integrated` | true / false / None | spec: true required |
| wave `commit` | 40-hex wave commit; HEAD at that time on an idempotent re-finalize (`:6267`); `""` (`or ""`); `None`/absent (`--no-commit`, or a refused `_apply`) | spec: non-empty required; hex form NOT required (see F2) |
| per-job `merged.integrated` | true (carries `proof: head-matches-artifact` and NO `commit` for the proven-in-HEAD path, `:6178`); true with `commit` (fresh merge, `:6264`) | spec: true for all `job_ids` |
| wave `jobs` vs `merged` vs `--jobs` | equal for a clean wave. Differ if the manifest was re-emitted with another wave partition | spec: set equality; mismatch falls through to today's behaviour |
| manifest digest | `--manifest-digest` given / absent | fault check stays BEFORE the short-circuit (`:5993`). A stale CFG digest still refuses |
| isolation of jobs | worktree (pruned worktrees, receipts bound to an old digest) / direct (`worktree: ""`) | not a dimension of the check. Short-circuit never reads receipts, patches or worktrees |
| run phase at relaunch | `DISPATCHED` / `MERGED` / `BLOCKED` (incident leaves BLOCKED) | spec: nothing written, so the phase is never healed (F9) |
| HEAD vs `commit` | ancestor / not ancestor / unknown object (`merge-base` rc 128) / history rewritten | ancestor only; any non-0 falls through |

Cell used by the spec's tests: one direct job, MERGED, commit == HEAD. Not covered by any spec row: wave of 2+ jobs, worktree job, a partition mismatch, a non-hex `commit`, a forged `waves` entry.

### Defect 2: `resolve_job` (`hooks/lane-guard.sh:822`)

| cwd location | Claim in a live map | Resolves today | After the boundary rule |
|---|---|---|---|
| checkout root | direct job on checkout | direct job | unchanged (no dirs walked) |
| plain subdir of checkout (no `.git`) | direct job on checkout | direct job | unchanged |
| `<checkout>/.claude/worktrees/<id>` registered for its own job, **has `.git` file** | own entry `wt` plus checkout | own job (longest prefix first) | unchanged. **Only if the walk excludes `wt` itself** (G1) |
| `<checkout>/.claude/worktrees/<id>` NOT registered, has `.git` file | direct job on checkout | **direct job (the bug)** | unresolved, then the `agent_worktree_root` branch (`:1584`) |
| same, no `.git` (every existing fixture: `WTX/WTY/WTZ/WT_UNREG3`, `tests/test-lane-guard.sh:192-223`) | direct job on checkout | direct job | unchanged. These fixtures cannot exercise the fix |
| subdir of a registered worktree | own entry | own job | unchanged |
| submodule / vendored repo / `node_modules/x` carrying a `.git` entry inside the checkout | direct job on checkout | direct job | unresolved, so allowed (fail-open widening, G7) |
| `agent_id` present in `agents` map | n/a | `agent_id` branch (`:832`) | unchanged. Normally empty on CC 2.1.238 (`TROUBLESHOOTING.md:294`) |
| `wrappers` (external job's wrapper cwd) | listed, never claimed (`:4004`) | not in `worktrees` | not a dimension |

## 2. Shared State

**`state.waves[<wave>]`** (key is the 1-based string wave index the JS passes, `:3716`).
- Set in: `_apply` only (`:6084`), after the authority has permitted, or after a commit failure (`:6254`, with `integrated: False`, `commit` possibly unset).
- NOT set on the refusal path (`:6050-6069`). That path writes `phase=BLOCKED`, `blocked_reason`, `blocked_at`, retires `lane-map.json` and `.run.lock`, and has already run `_maybe_append_run_actual` (`:6043`).
- Read anywhere? Nothing outside the selftest (`:8915`). There is no existing consumer to copy.
- **Gap:** the spec says the finalizer "wrote the wave back to `integrated: false`, `commit: null`". The code has no such path for an `unverifiable` verdict. A refusal leaves `waves` alone. What it does write is BLOCKED plus lane-map and lock retirement. The committed jev `state.json` agrees: all three waves read `integrated: true`, and `blocked_reason`/`blocked_at` sit beside `phase: MERGED`. Either the observed run took another path, or the spec is describing the symptom loosely. The plan must target the BLOCKED write, which is what AC-1 row A asserts anyway. UNKNOWN: workflow `wf_b71ebffa-5b3` is not in the tree.

**`state.waves[<wave>].commit`.**
- Set to `out.get("commit")`. On an idempotent re-finalize that is `_head_commit()` at that moment, not a wave commit (`:6267`).
- Evidence in the jev `state.json`: wave 1's jobs carry `proof: head-matches-artifact` and no `merged.commit`, while `waves.1.commit` is `03cf1e2e...`. That is HEAD at a re-finalize, not a commit made by the wave.
- So "commit is an ancestor of HEAD" means "HEAD once contained this". It carries no information about the wave's content.

**`state.jobs[<id>].merged.integrated`.**
- Set in: `_apply` via `job_updates` (`:6082`).
- Writable by a direct worker: `state.json` is exempt by name (`RUN_DIR_EXEMPT_BY_NAME`, `:4210`).
- The finalizer already treats it as "a CACHE line, not a proof" (`:6165-6172`), and the selftest pins that (`:9170-9191`, "forged state.json does NOT skip the merge").

**`manifest_digest` / `--manifest-digest`.** Baked at emit (`:2729`, `:3090`). Verified by `manifest_digest_fault` (`:531`) before anything else.

**`lane-map.json` `worktrees`.**
- Set by `register_lane` (`:3972`), unlocked reads excluded, merged under `_run_dir_lock`.
- Direct jobs register the checkout (`:4007`). Wrappers are listed under `wrappers`, never claimed (`:4004`).
- Deleted by `_retire_lane_map` at a terminal phase or on a refusal.

**`cwd` in the PreToolUse payload.** The only input to the `cwd->worktree` branch. UNKNOWN whether it is the real path or a symlinked one on a given machine. The code compares both forms (`_rel_under`, `:662`).

## 3. Sibling Code

**Sibling for D1.** The in-loop "ALREADY MERGED? ASK GIT" block (`:6165-6191`) is the existing answer to "is this job already landed".
- Entry: a sealed patch plus a pinned baseline, giving `image`. Then `head_matches_post_image` (`:673`) compares blobs in HEAD to the patch's post-image.
- Fallback: only when `sealed is None` (pre-3.4.0 receipt) does it trust the `merged` cache (`:6182-6191`), and it records `unproven_skips`.
- Edge cases handled: forged `merged.integrated` with no work in HEAD (selftest `:9170`), reverted worktree (`:9146`), deletions in a post-image.
- The new function proves LESS than this block. See F1.

**Also a sibling.** `cmd_integrated_jobs` (`:11338`) and the JS `alreadyIntegratedIds` (`:3772-3873`).
- They already skip Implement and Gate for integrated jobs on relaunch, from `jobs[*].merged.integrated` alone.
- `finalizeWave(w, allJobs)` is still called with the FULL wave (`:3917`), by design. That call is the one that re-runs the authority against a stale tree.
- `waveHadFailure` (`:3759`) accepts `fin.integrated === true` plus `skipped-integrated` statuses, so a short-circuit result halts nothing.

**Latent bugs in the sibling.**
- `_apply` never clears `blocked_reason`/`blocked_at` when a later pass moves the phase to MERGED. The committed jev state shows `phase: MERGED` next to `blocked_reason: "wave 2 refused: ..."`. Cosmetic, but a reader sees a contradiction (F10).
- The refusal path retires `lane-map.json` and `.run.lock` even for a wave that was previously integrated (`:6066-6068`). That is the mechanism behind "blocked the run's own gate".

**Sibling for D2.**
- Transcript watcher `scripts/compound-v-transcript-watch.py:55-63, 248, 740-760`. It hit the same prefix problem and solved it by consulting only the worktrees mapped to THIS agent's job. It carries its own `_rel_under` copy (`:248`). It is not in either lane and gets no boundary rule. Not a defect of this spec, but a second resolver with different semantics.
- The record/notice branch in `main()` (`:1578-1610`) and `record_unresolved` (`:921`). This is where an unresolved cwd under `.claude/worktrees/` ends up. See G3.
- `run_is_terminal` (`:733`): BLOCKED and MERGED runs are already skipped by `map_files`. The bug only bites a LIVE run, which matches the jev incident (`lane-guard-unresolved.jsonl` lines 1-2 in the jev run dir record exactly the two unrelated sessions).

## 4. External APIs

No third-party API. One git contract.
- `git merge-base --is-ancestor A B`: exit 0 = ancestor, 1 = not, otherwise error (128 for a bad object). Same reading the repo already uses in `scripts/compound-v-integration-gate.py:194-203` (`_is_ancestor`) and `scripts/compound-v-liveness.py:197`.
- Context7 was not needed: the parallel 1C audit (`docs/superpowers/library-audit/2026-10-05-2026-10-05-engine-c-refinalize-and-lane-guard-design.md`) already covers it. I did not re-derive it.

## 5. Regression Surface and findings

Numbered findings. F = D1, G = D2, X = cross-cutting.

### Defect 1

**F1. The short-circuit skips the authority on evidence a worker can forge.** Severity high.
- It reads `state.json` (exempt by name from the scope gate, so a direct worker can write it) and then asks git only whether some commit is an ancestor of HEAD.
- A forged `waves[N] = {integrated: true, commit: <the repo's root commit>, jobs: J, merged: J}` plus `merged.integrated: true` on each job satisfies all four spec conditions. The finalizer would then report `integrated: true` and merge nothing, with no gate run.
- Today's code refuses exactly this forgery for the per-job case (`:6165-6172`, selftest `:9170-9191`). The new check weakens that invariant at wave level. Row (3) of the existing selftest would still pass, because it forges only `jobs.w1.merged`, so it will not catch the regression.
- The spec accepts a REVERT as a false positive. It does not name a FORGERY as one.
- A cheaper proof exists and is already in the file: `head_matches_post_image` over the sealed patches (`jobs/<id>.patch`, pinned by receipts). Whether those survive a re-emit is UNKNOWN for the jev run (the committed run dir holds only `manifest.yaml`, `state.json`, `dispatch.workflow.js`, `lane-guard-unresolved.jsonl`).

**F2. `commit` is not validated before it reaches git.** `_head_commit` (`:4049`) is the repo's own shape check (`^[0-9a-f]{40}$`). A `state.json` value beginning with `-` is an option to `git merge-base`. `"0"*40` (the spec's row B) is well-formed, so row B does not cover a malformed value.

**F3. The spec's stated symptom does not match the code path.** See section 2: a refusal never rewrites `waves`. Fixing the BLOCKED write is still the right target. The plan should not assert in a comment or test that `waves` gets reset.

**F4. The short-circuit skips the bookkeeping commit.**
- The commit of `state.json` and the run dir (`:6417-6429`) runs only when `out.get("commit")` is truthy on the full path.
- A relaunch after a crash between `_apply` and that bookkeeping commit would never commit the record. The audit-trail gate reds on push for that state (finding 56, `:6412-6416`).
- The spec says "nothing is written", so this is a stated behaviour, but the consequence is not.

**F5. Output schema.** `FINALIZE_SCHEMA` (`:2810`) is `additionalProperties: false` with keys `wave, integrated, commit, merged, refused, reason, triage_actual`. The short-circuit result must stay inside it. The full path already emits undeclared keys (`worktrees_pruned`, `lane_map_retired`, `scorecard_updated`, `bookkeeping_commit`, `unproven_skips`). UNKNOWN whether the harness validates strictly. Pre-existing.

**F6. A re-emit that changes the wave partition defeats the fix silently.** The key is the positional wave number and the match is set equality of `jobs`. A different partition falls through to today's behaviour with no log line saying why.

**F7. Ancestry limits beyond the one the spec states.** A rebase, squash-merge or amended history makes a genuine wave commit a non-ancestor. The check falls through and the old bug reappears, but safely. The spec lists revert only. This branch merges upstream (`b0d410a`, `00eb6c5`), which keeps ancestry.

**F8. Idempotent-re-finalize wording.** The full path's reason string is `"nothing left to commit — this wave's work is already in HEAD (idempotent re-finalize)"`, and `:6347` keys worktree pruning on `startswith("nothing left to commit")`. A new reason string must not start with that prefix.
- It would not matter on the short-circuit path (it returns before pruning), but a shared constant or a copy-paste could re-enable the prune guard's text match. The prefix is load-bearing.

**F9. The phase is never healed.**
- A run left `BLOCKED` by the incident (`:6062`) and relaunched with every wave short-circuiting stays BLOCKED, because the only writer of `DISPATCHED`/`MERGED` is `_apply`.
- `run_is_terminal` treats BLOCKED as terminal, so the lane guard ignores the run while the workflow executes later waves.
- The spec's precondition (phase MERGED) hides this. UNKNOWN whether the operator or `/v:resume` repairs the phase by hand. `resume-prepare` (`:11332`) sets PARTITION_VERIFIED only when it unpins jobs.

**F10. Stale `blocked_reason`/`blocked_at` survive a later MERGED.** Pre-existing, cosmetic. Relevant to AC-4: byte-identical output means these stay.

**F11. AC-4 depends on facts I could not check.**
- For wave 1 to short-circuit in a scratch clone, the clone's HEAD must contain `03cf1e2e56cda89d9b1d04cd4442275c8ec42ed2`. The other two wave commits are `873b5c2ecd00547fb9707808d245da78ca3987e5` (wave 2) and `a819047711091837b509445467182dee144ab424` (wave 3).
- UNKNOWN: git was blocked, so I cannot say whether any is an ancestor of HEAD or exists in the clone.
- `--jobs` must be exactly `record-t3,config-jev,jev-core,vault,corpus`, and `--repo-root` the clone.
- The default integration gate must exist in the clone: it is checked at `:5987`, BEFORE the short-circuit.
- The jev run's `manifest.yaml` is present, so a digest check, if the scratch run passes `--manifest-digest`, must match THAT file's bytes.

### Defect 2

**G1. An inclusive walk disables the guard for every worktree job, and no existing row notices.** Severity high.
- Every real linked worktree has a `.git` file at its root. If the walk includes `wt`, then a session in a registered worktree resolves to nothing.
- Every existing fixture worktree is a plain directory without `.git` (`:59-60`, `:192-195`, `:220-223`). The suite stays green under that bug.
- Spec row 3 ("registered worktree still resolves") must therefore put a `.git` entry in the registered worktree AND assert an out-of-lane DENY, not merely "no unresolved log".
- The same applies to a SUBDIR of a registered worktree.

**G2. The walk must use the same path form `_rel_under` matched on.**
- `_rel_under` (`:662`) tries lexical, then realpath, and returns only the relative part, not which pair matched.
- A walk that climbs `cwd` by `dirname` until it string-equals `wt` can overshoot when `cwd` and `wt` are spelled differently (`/tmp` vs `/private/tmp`, the macOS case the docstring names). It then meets the checkout's own `.git` and marks every direct-job session as unresolved.
- This is silent: the hook allows and logs.
- Constraint: the walk must be bounded, and when it reaches `/` without meeting `wt` the spec must say which way that falls. "Keep today's claim" and "treat as boundary" are both wrong in some spelling case, so the choice has to be stated, not left to the implementer.

**G3. "Unresolved, exactly as today" has side effects the spec's test wording does not match.**
- A cwd under `.claude/worktrees/<id>` that resolves to nothing, while a live lane map exists, takes the `agent_worktree_root` branch (`:1584-1605`): `record_unresolved` appends a line to `<newest live run>/lane-guard-unresolved.jsonl`, the log line is `ALLOW (UNRESOLVED IDENTITY under a live lane map ...)`, and a one-time `FAILED OPEN` notice goes to that session.
- Spec row 1 says the log says "the job is unresolved". The plain-session string is `ALLOW (job unresolved)`, and `tests/test-lane-guard.sh:419` greps `'job unresolved'`. The isolated-agent string is `UNRESOLVED IDENTITY` (`:668`). The row must grep the right one.
- The unrelated session still gets a notice claiming it "wrote before register-lane", and the run dir gains a record line. That is the documented residual false positive (`:882-889`). The jev run's own `lane-guard-unresolved.jsonl` shows both cases today.
- UNKNOWN: whether the scope gate charges that untracked jsonl to a live DIRECT job. It is not in `RUN_DIR_EXEMPT_BY_NAME` (`:4209-4222`, a closed list). The jev run passed with the file present, so the evidence points to "not charged", but I did not trace the gate.

**G4. Fixture isolation.**
- `$PROJ` holds several live runs: `$RUN` claims `$WT`, the `2099-09-08-live` fixture is retired, and so on. `map_files` takes the newest 8 run dirs by mtime, and `resolve_job` tries every map until one resolves.
- "A live lane map whose only claim is a direct job on the checkout" therefore needs its own project (the `$PROJ2`/`$PROJ3` pattern, with `CV_PROJECT_DIR` overridden after `run`'s default, `:704-705`).
- `recreset` (`:248`) clears only `$PROJ` and `$PROJ3`. A new project's records are not cleared. This is harmless but must be known.
- Alternatively wake `RUN_L` as section 2b does, which depends on mtime ordering.

**G5. Source-grep assertions constrain the comment the spec asks for** (`tests/test-lane-guard.sh:1344-1373`).
- The hook source must still contain `PYTHONPYCACHEPREFIX`, `stop it READING one`, `compound-v-scope-check.py`, `hooks.json`, `task-16`, `REMAINS THE AUTHORITY`, `TMPDIR`, `LOCK_EX`, `CANNOT ENFORCE IT`.
- It must NOT contain `glob_to_regex`, `fnmatch`, `replaces the git`, or `instead of the git`, nor `SEGMENT_RE`.
- The new comment above the branch must avoid those strings.
- Mutation rows plant violations by `sed` over exact source lines (`:516`, `:769`, `:784`, `:799`). Do not change those lines' text.

**G6. Behaviour change for unregistered real workers inside a run that also has a live direct job.**
- Today they are mis-resolved to the direct job. Out-of-lane writes are denied, by accident.
- After the change they are unresolved: allowed and recorded, the same window as a run with no direct job. This is a loss of accidental coverage, not a regression of designed coverage.
- The git scope gate is unchanged.

**G7. A `.git` entry inside the checkout is now an escape hatch.** Any cwd below a directory containing a `.git` entry (submodule, vendored repo, a planted file) stops being claimed by the checkout's direct job.
- Real risk is low. Writes to the planted `.git` are themselves lane-checked, and Bash cwd resets between calls.
- The Write/Edit tools pass the payload `cwd`, which is the session root, not the target's directory. The new rule therefore cannot be steered by the file path.
- It is still a new way for a path inside the checkout to fall out of a direct job's lane. The spec's "fail-open, git gate remains the authority" covers it, but it should be recorded as accepted.

**G8. Docs the change touches.**
- `TROUBLESHOOTING.md:290` DOES describe how the guard picks a job ("It resolves `agent_id` first, then falls back to `cwd` -> worktree"). The spec's conditional ("if TROUBLESHOOTING.md describes how the guard picks a job") is therefore a YES, and that file is in Lane B.
- The hook's own header (`:196-210`, "LANE MAP CONTRACT") says the same and would become incomplete.
- `docs/superpowers/architecture/.onboard-manifest.json` hashes `hooks/lane-guard.sh`. The KB goes stale on any edit (`/v:onboard --refresh`). The architecture docs cite only `hooks/lane-guard.sh:12-65`, above the edit site.

**G9. Cost and metrics.**
- The hook source is compiled on every call (`:161-170`). A ~15-line addition is a small constant, and no number should be published for it: the anti-fabricated-metrics grep covers `docs/` and `scripts/` (`.claude/rules/docs.md`).
- The walk is stat calls only, bounded by the depth between `cwd` and `wt`, and reached only after a prefix match.

### Cross-cutting

**X1. Release lockstep.** CI requires the `CHANGELOG.md` top version to equal `plugin.json` (`.github/workflows/validate.yml:54-79`). The spec's partition lists neither, nor `marketplace.json`. UNKNOWN whether this ships as a release. If it does, those files are SHARED RESOURCES outside both lanes.

**X2. The selftest is one function, and CI runs it under Python 3.9** (`validate.yml:298-312`). The new rows must sit inside it, beside the idempotent-commit row (`:8752-8772`, inside the `fin_repo`/`_init_repo` block).
- The stub gate must be a Python script, because the call is `args.python -B <gate> ...` (`:6001`).
- It must exist on disk, because `:5987` runs before the short-circuit.
- Row A passing without the change would mean the stub was never consulted, so the stub's refusal is the discriminator.
- `manifest` loading (`:6018`) is skipped when the manifest file does not exist, so the rows need no PyYAML. Rows that DO write a manifest are guarded by `have_yaml` elsewhere in the file.

## 6. DRY Findings

- **Ancestry check.** `scripts/compound-v-integration-gate.py:194` `_is_ancestor` and `scripts/compound-v-liveness.py:197` already ask git `merge-base --is-ancestor`. The emitter imports the gate through `_import_integration_gate` (`:698`), but `--integration-gate` can be a stub in the spec's own tests, so importing from the default path would answer from a different file than the one under test. Decide deliberately: extend by import, or a third inline copy (justify). Never an unnoticed one.
- **"Already integrated" has three definitions** in this file: the in-loop git-proven block (`:6165`), `cmd_integrated_jobs` from the cache (`:11338`), and the new wave-level check. The first is the only one that proves content.
- **`_rel_under` exists twice** (`hooks/lane-guard.sh:662`, `scripts/compound-v-transcript-watch.py:248`). The hook cannot import scripts casually (bytecode-prefix defence), which is why. The boundary rule goes into the hook only; the watcher keeps its own policy.
- **Commit-hash shape check.** `_head_commit` (`:4054`) holds the 40-hex regex. A second regex for `commit` would be a duplicate.

## 7. Design constraints for the spec

1. The wave-level short-circuit must not let a `state.json` edit alone skip the integration authority. Either prove the wave's content against git (`head_matches_post_image` or equivalent), or the spec must state, as an accepted limit next to "reverted commit", that a forged `waves` entry skips the authority, and say why that is acceptable for a direct worker's reach. (F1)
2. `commit` must pass a 40-hex check, as `_head_commit` does, before it is given to git. A non-hex or option-like value falls through, never raises. Add a row for it. (F2)
3. Do not state or test "the finalizer resets `waves` to `integrated: false`". The refusal path writes `phase: BLOCKED`, `blocked_reason`, `blocked_at`, and retires `lane-map.json` and `.run.lock`. Name those. (F3)
4. The spec must say what happens to a run that an earlier mis-refusal left `BLOCKED`: the short-circuit writes nothing, so the phase stays BLOCKED, and the lane guard treats the run as terminal. (F9)
5. The short-circuit result must stay within `FINALIZE_SCHEMA` keys. Its reason string must not begin with `nothing left to commit`. (F5, F8)
6. The short-circuit goes after the authority-exists check (`:5987`) and the manifest-digest fault (`:5993`), as the spec says, and before the `_gate_argv` run (`:6000`). Row A's stub must be a real file and a Python script.
7. A partition mismatch (`jobs != job_ids`) must be recorded as the way the defect survives. At minimum the output `reason` of the full path is unchanged. Decide whether to log why the short-circuit declined. (F6)
8. AC-4 must record which commits the clone must contain (`03cf1e2e...`, `873b5c2e...`, `a8190477...`), the exact `--jobs` list, and that `--repo-root` is the clone. Re-check that the clone's HEAD contains them (UNKNOWN to me). (F11)
9. Boundary walk (D2): the walk covers directories from `cwd` up to, EXCLUDING, `wt`. It must be derived from the same path form `_rel_under` matched on, and must terminate. A walk that cannot reach `wt` must have an explicit, stated default. (G1, G2)
10. D2 tests: the registered-worktree row needs a `.git` file in that worktree and in a subdir case, and must assert an out-of-lane DENY. The nested-unregistered row needs a `.git` FILE and a live direct-job claim in an isolated project. The expected log text is `UNRESOLVED IDENTITY`, not `job unresolved`. (G1, G3, G4)
11. The new comment must avoid the forbidden source strings listed in G5, and must not alter the lines the mutation rows `sed` over.
12. The spec must acknowledge the recorded side effects of an unresolved isolated agent: a run-dir record line and a one-time notice. Say whether they are accepted for an unrelated session. (G3)
13. `TROUBLESHOOTING.md` is in scope (line 290 describes resolution). The hook header's LANE MAP CONTRACT paragraph (`:196-210`) should agree. (G8)
14. State the release/CHANGELOG decision. If a release, `CHANGELOG.md`, `.claude-plugin/plugin.json` and `marketplace.json` must be in a lane. (X1)
15. No timing or cost figure for the extra stat calls. (G9)

## 8. File Touch Map (for Phase 2 partitioning)

| File | Touch | Flag |
|---|---|---|
| `scripts/compound-v-emit-workflow.py` | add `_already_integrated_wave`; call in `cmd_finalize_wave` after `:5997`; selftest rows A and B near `:8772` | One lane (A). Very large file (11k+ lines), single selftest function |
| `hooks/lane-guard.sh` | `resolve_job` `cwd->worktree` branch (`:844-846`) plus a comment; header contract paragraph (`:196-210`) | One lane (B). Python body is inside a quoted heredoc, so shellcheck sees nothing of it. Hash recorded in `docs/superpowers/architecture/.onboard-manifest.json` |
| `tests/test-lane-guard.sh` | three new rows plus a fixture project | One lane (B). Source-grep assertions at `:1344-1373` |
| `TROUBLESHOOTING.md` | one sentence at `:290` | Lane B (conditional resolves to yes) |
| `CHANGELOG.md`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` | only if released | SHARED RESOURCE, version lockstep (`validate.yml:54-79`). In neither lane today |
| `docs/superpowers/architecture/*` | staleness only | Not edited by the plan. Refresh is `/v:onboard --refresh` |
