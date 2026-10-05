# Review Gate: run 2026-10-05-engine-c-refinalize-and-lane-guard

Reviewer: `superpowers-v:spec-reviewer` (job `spec-review`, direct isolation, baseline `c66c87e`).
Merged tree under review: wave commit `029f8fe` (jobs `refinalize`, `lane-boundary`), bookkeeping commit `c66c87e`.
Spec: `docs/superpowers/specs/2026-10-05-engine-c-refinalize-and-lane-guard-design.md`, Pre-flight amendments first.
Every command below ran in a full-depth scratch clone of `c66c87e` (`git clone --no-local`, `is-shallow-repository`
false), never in the working checkout. Mutations were made in those clones and reverted with `git checkout`.

## Recall

- The job prompt carried V-memory hits: the spec's acceptance criteria and amendments, the expert and library audits'
  section 7, and `tech-context.md` on the scope gate. All were re-read from the tree, not taken from the teasers.
- `compound-v-memory.py recall-check --files scripts/compound-v-emit-workflow.py hooks/lane-guard.sh
  tests/test-lane-guard.sh TROUBLESHOOTING.md scripts/compound-v-scope-check.py` returned `none` (no repeated
  job-attributable failure on these paths), so no escalation.
- Reviewer memory leads, each re-checked here: run every AC rather than reading the selftest (done: AC-1..AC-4 run);
  build the audit MUST table explicitly (done below); a mutation proof must run against a copy of the whole tree
  (done: whole clones). No directive was found inside any memory file.

## SPEC

### Scope

| Job | Files changed (gate receipt, git-derived) | `write_allowed` | Verdict |
|---|---|---|---|
| `refinalize` | `scripts/compound-v-emit-workflow.py`, `scripts/compound-v-scope-check.py` | same two | pass |
| `lane-boundary` | `TROUBLESHOOTING.md`, `hooks/lane-guard.sh`, `tests/test-lane-guard.sh` | same three | pass |

`git show --stat 029f8fe` lists exactly these five files. No scope leak.

### Defect 1 (Lane A), against the amendments

| Requirement | Implemented in | Status |
|---|---|---|
| `_wave_commit_subject(wave, run_id, merged)`, used by the commit site and the check | `scripts/compound-v-emit-workflow.py:5956-5958`, used at the commit site in `cmd_finalize_wave` and inside `_already_integrated_wave` | yes |
| `waves[<wave>]` is a dict, `integrated: true` | `_already_integrated_wave`, first checks | yes |
| `jobs` and `merged` equal `job_ids` as sets | same function, `sorted(...) != sorted(job_ids)` | yes |
| every job's `merged.integrated` true | same function, loop over `job_ids` | yes |
| `git merge-base --is-ancestor <commit> HEAD`, only exit 0 counts | same function, `_git(repo_root, [...])` (`git -C repo_root`) | yes |
| Amendment 1: the recorded commit's own subject (`git log -1 --format=%s <commit>`) equals the wave subject | **not as written.** The code accepts any commit reachable from the recorded commit whose subject equals the wave subject (`git log --format=%s --fixed-strings --grep=<subject> <commit>`) | deviation, see Verdict item 3 |
| Amendment 2: commit matches `^[0-9a-f]{40}$` or `^[0-9a-f]{64}$` before git's argv | `_SHA_RE`, checked before the first `_git` call | yes (but unguarded by a test, Verdict item 1) |
| Amendment 3: `-C repo_root`; non-zero, missing binary, exception decline; declining code logged | `_run` returns 127 on exception; each decline writes `rc` and stderr to stderr | yes |
| Amendment 4: reason inside existing keys, not starting `nothing left to commit` | result keys `integrated`, `merged`, `commit`, `reason`; reason starts `wave already integrated at` | yes |
| Called after the manifest-digest fault check, before the authority; exit 0; writes nothing | `cmd_finalize_wave`, block `0. ALREADY INTEGRATED? ASK GIT` | yes |
| `RUN_DIR_EXEMPT_BY_NAME` gains `lane-guard-unresolved.jsonl` with the stated reason; a sibling stays non-exempt | `scripts/compound-v-emit-workflow.py:4223-4224`; selftest rows for the name and for `.bak` | yes |
| scope-check docstring names the new entry | `scripts/compound-v-scope-check.py:47-52` (the comment at 353-354 names the list, not its entries) | yes |
| Rows A-E | selftest, re-finalize rows A-E | yes (row E does not test what it claims, Verdict item 1) |

### Defect 2 (Lane B), against the amendments

| Requirement | Implemented in | Status |
|---|---|---|
| Walk in the same path form under which `cwd` is inside `wt` | `_crosses_worktree_boundary` iterates the same two forms `_rel_under` uses (`normpath`, then `realpath`) and walks in the first that matches | yes |
| Visit `cwd` and each parent up to, excluding, `wt`; `os.path.lexists(d/.git)`; bounded by component count | `hooks/lane-guard.sh:685-708` | yes |
| `.git` found: claim stops, session unresolved; no form matches: claim stands | `continue` in `resolve_job`; helper returns False when no form matches | yes |
| Comment names nested worktrees, submodules, nested repositories, and that the scope gate cannot see inside them | comment above the call in `resolve_job` and the helper docstring | yes |
| `TROUBLESHOOTING.md:290` updated | new sentence at `TROUBLESHOOTING.md:291` | yes |
| Filesystem only, no `git` subprocess | helper uses `os.path` only | yes |
| Rows: nested unregistered worktree allowed and logged `UNRESOLVED IDENTITY`; plain subdirectory denied; registered worktree with a `.git` file at its root still denied as itself | `tests/test-lane-guard.sh` section 2a and 2b | yes |

### Audit MUSTs

| Audit | Constraint | Status |
|---|---|---|
| Expert | `--is-ancestor` has three outcomes, only 0 is yes | yes |
| Expert | row with a real non-ancestor commit | yes (row C; its mutation proof is below) |
| Expert | log which non-zero exit was seen | yes, observed (QUALITY, "Decline log") |
| Expert | rely on "a commit is its own ancestor", no SHA-inequality | yes (row A records the wave at HEAD) |
| Expert | validate the recorded commit before git's argv | yes in code; no test fails when it is removed (Verdict item 1) |
| Expert | `git -C <repo_root>` | yes (`_git`) |
| Expert | AC-4 clone full depth | yes (this review) |
| Expert | walk in the matching path spelling, exclude `wt`, `lexists`, bounded, no subprocess | yes (probe: a symlinked `.git` counts; `cwd == wt` with a `.git` file returns False) |
| Expert | settle the `lane-guard-unresolved.jsonl` side effect and pin it with a row | yes (exempt by name, two rows) |
| Expert | Lane B includes `TROUBLESHOOTING.md`; comment names submodules and nested repositories | yes |
| Library | Python 3.9 stdlib only | yes (no `match`, no `X | Y`) |
| Library | true only on `returncode == 0` | yes |
| Library | single argv element, validated | yes in code (see Verdict item 1 for the test) |
| Library | bash 3.2 walk | not applicable: the resolution code is Python inside the hook (spec amendments, orchestrator check) |
| Library | no `git` from the hook | yes |
| Library | shellcheck is not evidence of bash 3.2 | not applicable: no bash line of the hook changed |

### Over-build

- Row F (a wave recorded at a later commit whose history carries the wave commit) is beyond rows A-E. It exists
  because of the deviation in Verdict item 3, and it is what AC-4 depends on. Not counted as over-build on its own.
- The existing selftest assertion `run_dir_owned_by_name(_own, "run", "j2") == (_tmpl == "state.json")` became
  `== ("{id}" not in _tmpl)`. For every template that carries `{id}` it is unchanged (still not owned by another
  job); it only admits the new job-independent name. Not a weakening.

## QUALITY

### AC-1 and the Lane A revert proofs

```text
$ /usr/bin/python3 -B scripts/compound-v-emit-workflow.py --selftest
rc=0
634/634 checks passed
```

Row A revert proof (`done = _already_integrated_wave(...)` replaced by `done = None`):

```text
rc=1
FAIL: re-finalize row A: a wave recorded integrated at HEAD, whose commit carries this run's wave subject, exits 0
  with state.json byte-identical and the phase still MERGED, though the authority would refuse it — (1, False, 'BLOCKED')
FAIL: re-finalize row F: a wave recorded at a later commit whose history carries the wave commit exits 0 with
  state.json byte-identical — (1, False, 'BLOCKED')
632/634 checks passed
```

Exempt-row revert proof (the `lane-guard-unresolved.jsonl` entry removed):

```text
rc=1
FAIL: exempt by name: lane-guard-unresolved.jsonl, for any job
630/631 checks passed
```

Further mutations, each in a fresh revert of the clone:

| Mutation | Result | Guarded? |
|---|---|---|
| subject condition replaced by `if False:` | `FAIL: re-finalize row D ... — (0, True, 'MERGED')`, 633/634 | yes |
| ancestor `rc != 0` decline replaced by `if False:` | `FAIL: re-finalize row C ... — (0, True, 'MERGED')`, 633/634 | yes |
| `_SHA_RE.match` removed from the commit validation | `rc=0`, `634/634 checks passed` | **no** (Verdict item 1) |

### Decline log

`finalize-wave` on a scratch run dir in `clone-a`, stderr only:

```text
--- recorded commit 0000000000000000000000000000000000000000
compound-v: finalize-wave 1: no idempotent short-circuit: git merge-base --is-ancestor 000000000000 HEAD exited 128
  fatal: Not a valid commit name 0000000000000000000000000000000000000000
--- recorded commit b1be7dd775eaaaea4bad2ce64de33f7dfb63749f
compound-v: finalize-wave 1: no idempotent short-circuit: no commit reachable from b1be7dd775ea has the subject
  'compound-v: wave 1 of run p (a)'
```

### Robustness probe

A malformed wave record in a worker-writable `state.json` crashes `finalize-wave` instead of declining:

```text
waves["1"]["jobs"] = [1, "a"]:
  File ".../scripts/compound-v-emit-workflow.py", line 5997, in _already_integrated_wave
TypeError: '<' not supported between instances of 'str' and 'int'
exit=1
waves = [1]:
  File ".../scripts/compound-v-emit-workflow.py", line 5984, in _already_integrated_wave
AttributeError: 'list' object has no attribute 'get'
exit=1
```

The pre-change emitter (`git show b1be7dd:scripts/compound-v-emit-workflow.py`) given the first state reached the
authority and printed its JSON result. See Verdict item 2.

### Other checks

- Regression: the manifest's full test command passes on the merged tree (INTEGRATION). The f78 rows now carry a
  `.git` file at `$WT`, which is a plain sandbox directory (`tests/test-lane-guard.sh:59`), so the `rm -f "$WT/.git"`
  cleanup touches nothing real.
- Fabricated metrics: none. No timing, cost or savings text in the diff.
- Reward hacking: none. No assertion removed, skipped or loosened; the one edited assertion is analysed above.
- Docs: `TROUBLESHOOTING.md:291` (new) is 174 characters. Line 290 is 331 characters, but its pre-image was 423;
  the diff shortened an existing over-length line and did not create one.
- The run id used for the subject check is `state.get("run_id") or os.path.basename(os.path.normpath(run_dir))`,
  while the commit site uses `os.path.basename(run_dir)` without `normpath` (`cmd_finalize_wave`). This run's
  `state.json` has no `run_id`, so the fallback is the live path. With a trailing slash on `--run-dir` the two
  differ; the check then declines (safe direction). See Verdict item 4.

### Can the lane-guard change weaken enforcement for a registered job?

- A registered job whose session `cwd` is its own worktree root: the walk excludes `wt`, so a `.git` file there does
  not matter. Proven by the f78 rows and by the mutation that also inspects `wt`, which fails them (AC-2 below).
- A registered job's session whose `cwd` sits below its root in a directory holding `.git` (probe: `True`) becomes
  unresolved and is allowed. That needs a session cwd inside a nested repository. The spec accepts this, and the
  planted `.git` directory or file is itself an untracked path that the job's git-derived scope gate reports as a
  violation. Not a finding.
- A session in an unregistered nested worktree is now allowed for writes into the checkout that were denied before.
  The spec intends this. Such a write lands in the direct job's gated tree, and that job's scope gate catches it.

## INTEGRATION

### AC-2 and the Lane B revert proofs

```text
$ bash tests/test-lane-guard.sh
rc=0
PASS a nested git worktree NOT in the map is not captured by the checkout's direct-job claim -> no deny
PASS ...and the hook says the session is unresolved
PASS a plain subdirectory of the checkout still resolves to the direct job (out-of-lane denied) -> DENY
PASS finding 78: an out-of-lane Write at the nested worktree is denied AS that job -> DENY
PASS finding 78: the deny names job-under-test, not root-job
309 passed, 0 failed
```

Nested-worktree revert proof (the `_crosses_worktree_boundary` call removed from `resolve_job`):

```text
rc=1
FAIL a nested git worktree NOT in the map is not captured by the checkout's direct-job claim -> no deny
FAIL ...and the hook says the session is unresolved
307 passed, 2 failed
```

Finding-78 proof (the walk also inspects `wt` itself):

```text
rc=1
FAIL finding 78: an out-of-lane Write at the nested worktree is denied AS that job -> DENY
FAIL finding 78: the deny names job-under-test, not root-job
307 passed, 2 failed
```

### AC-3

```text
$ shellcheck hooks/*.sh
shellcheck rc=0
$ /usr/bin/python3 -B scripts/lint-frontmatter.py .
✅ All frontmatter clean
floor rc=0
$ bash -c 'for s in scripts/compound-v-*.py; do ... done; for t in tests/*.sh; do ... done; echo all-tests-ok'
all-tests-ok
full_command rc=0
```

The full command is the manifest's `test_contract.full_command`, verbatim, run in a fresh clone (`clone-c`), which
had no `git status` changes afterwards.

### AC-4

```text
$ /usr/bin/python3 -B scripts/compound-v-emit-workflow.py finalize-wave \
    --run-dir <clone>/docs/superpowers/execution/2026-10-05-jev-classifier-foundation --repo-root <clone> \
    --manifest <clone>/docs/superpowers/execution/2026-10-05-jev-classifier-foundation/manifest.yaml \
    --wave 1 --jobs record-t3,config-jev,jev-core,vault,corpus
{
  "commit": "03cf1e2e56cda89d9b1d04cd4442275c8ec42ed2",
  "integrated": true,
  "merged": ["record-t3", "config-jev", "jev-core", "vault", "corpus"],
  "reason": "wave already integrated at 03cf1e2e56cd, which is in HEAD and carries this run's wave commit
             (idempotent re-finalize; the authority was not re-run)",
  "refused": [],
  "wave": 1
}
exit=0
state.json sha256 before: 40d4ae3b1049fefcbbf33ee00865cf50046636f9a33e3291dc5ffc1107b50684
state.json sha256 after:  40d4ae3b1049fefcbbf33ee00865cf50046636f9a33e3291dc5ffc1107b50684  identical=yes
git status --porcelain: []
```

The same command with `--manifest-digest sha256:38226f8c…` (the digest that run's `dispatch.workflow.js` passes)
also exited 0 with `state.json` identical. Negative control, in the same clone with the short-circuit call removed:
the authority answered `integration REFUSED ... {"unverifiable": 5}` and the clone's `state.json` changed to phase
`BLOCKED`, which reproduces the reported defect. The clone was then reset.

Recorded commit `03cf1e2` has the subject `bookkeeping(2026-10-05-jev-classifier-foundation): wave 2 finalized`; the
wave subject belongs to `3a5a696`, which is reachable from it. AC-4 passes only because of the deviation in item 3.

### Seams and test evidence

- Seams: Lane A exempts `lane-guard-unresolved.jsonl`; Lane B's hook writes exactly that name
  (`UNRESOLVED_RECORD = "lane-guard-unresolved.jsonl"`, `hooks/lane-guard.sh:921`). The two lanes share no other
  symbol. No partition leak.
- Test evidence per job (from `results/<id>.json`): both `status: success`, `tests.scope: impacted`,
  `tests.exit_code: 0`, three commands each. `refinalize` ran the floor, the emit rule and the scope-check rule;
  `lane-boundary` ran the floor (also the `*.md` rule), the hook rule and the test-lane-guard rule. Every changed
  path matches an `impacted_map` rule, so at tier FULL `full_command` was not owed per job; it was run here at run
  level and passed.

## Verdict

**ISSUES.** SPEC: issues (item 3). QUALITY: issues (items 1, 2, 4). INTEGRATION: AC-1 to AC-4 pass on the merged
tree, build green, seams hold.

All four items block DONE and must be resolved before re-review. Items 1, 2 and 4 belong to the `refinalize` lane.
Item 3 is outside every implementer's lane: the orchestrator resolves it by amending the spec.

1. **TEST_GAP.** Amendment 2's commit validation is not guarded. Removing `_SHA_RE.match(commit)` from
   `_already_integrated_wave` leaves the selftest at `634/634 checks passed`. Row E asserts only that no file was
   planted and that the run goes `BLOCKED`. With the validation gone, `git merge-base --is-ancestor --output=... HEAD`
   still errors, so the row passes either way. The spec's row E says "no git call is made with it". The global
   constraint says every behavioural change ships a row that fails when it is reverted. Row E needs an assertion
   that fails when the validation is removed.
2. **QUALITY.** `_already_integrated_wave` raises on a malformed wave record instead of returning `None`:
   `TypeError` at `scripts/compound-v-emit-workflow.py:5997` (mixed-type `jobs`) and `AttributeError` at `:5984`
   (`waves` is not a dict). `finalize-wave` then dies with a traceback and no JSON. The pre-change emitter answered
   the first case with its JSON result. `state.json` is worker-writable (amendment 5), and the function's contract is
   "dict or None". It should decline, and a row should pin that.
3. **SPEC deviation (needs a spec amendment, not a code change).** Amendment 1 requires the recorded commit's own
   subject (`git log -1 --format=%s <commit>`) to equal the wave subject. The code accepts any commit reachable from
   the recorded commit with that exact subject. The literal rule would fail AC-4: the recorded commit `03cf1e2` is a
   bookkeeping commit, and the finalizer records HEAD when a re-finalize has nothing left to commit. The code's
   docstring states the reason, and row F pins it. The check stays narrow: the subject spells the run id, the wave
   and the exact job list. The spec text should be amended to describe what shipped.
4. **QUALITY.** The run id is derived in two places, and the two can differ: the check uses `os.path.normpath`
   before `basename`, and the commit site in `cmd_finalize_wave` does not. Amendment 1 asked for the subject format to
   be spelled once. The helper does that, but the run id that feeds it is still computed twice. With a trailing
   slash on `--run-dir` and no `run_id` in `state.json` (this run's case), the short-circuit declines. The
   consequence is a fallback to today's behaviour, not unsafe.

## Re-review (aeb1185, 332a331)

1. **CLOSED.** Row G guards the validation. On a scratch worktree at HEAD, after `_SHA_RE.match(commit)` was removed, the selftest gave `FAIL: re-finalize row G: a recorded commit that is not a hex SHA declines with NO git call — (('ok', None), [['merge-base', '--is-ancestor', '--output=/nowhere', 'HEAD']])` and `636/637 checks passed`.
2. **OPEN.** Row H fails when the three new type checks are removed (`FAIL: re-finalize row H ... [('raised', 'AttributeError(...)'), ('raised', 'TypeError(...)'), ...]`, 636/637). But `_already_integrated_wave` still raises on a malformed per-job entry. At `scripts/compound-v-emit-workflow.py:6017`, `(jobs.get(jid) or {}).get("merged")` assumes the entry is a dict, and `.get("integrated")` assumes `merged` is a dict too. A direct call at HEAD returned `jobs {"w1": "x"} -> RAISED AttributeError("'str' object has no attribute 'get'")` and `jobs {"w1": {"merged": [1]}} -> RAISED AttributeError("'list' object has no attribute 'get'")`. The real CLI confirms it. `finalize-wave --jobs w1 --wave 1` on that `state.json` printed `AttributeError: 'str' object has no attribute 'get'`, a traceback through `main` -> `cmd_finalize_wave:6095` -> `:6017`, and exited 1 with no JSON. Row H has no case for either shape. Its fourth case, where the state is a list, returns `None` even with the new `isinstance(state, dict)` guard removed, so that case tests `_load_state` and not the guard.
3. **CLOSED.** The spec's `## Review amendment (2026-10-05)` (spec lines 154-162) replaces amendment 1's literal own-subject rule with the rule that shipped: a reachable commit carrying the exact subject, found with `git log --fixed-strings --grep` and then an exact line match. That matches the code at `:6024-6031` and its docstring. The original text at spec line 91 stays, unchanged and superseded. There is no inline pointer from it to the amendment.
4. **CLOSED.** `_finalize_run_id` (`:5961`) is the one derivation, and both the commit site (`:6344`) and the check (`:6021`) call it. At HEAD, `_finalize_run_id({}, "/x/runs/r1/")` gives `r1`, and `({"run_id": ""}, "docs/x/run-a/")` gives `run-a`. On the scratch worktree, reverting the commit site to `os.path.basename(run_dir)` gave `FAIL: the run id feeding the wave subject is derived once, in _finalize_run_id` (636/637).
5. **New, low (QUALITY).** `_SHA_RE` (`:5953`) is anchored with `$`, so `re.match` also accepts a full SHA followed by a trailing newline. That value passes the check and reaches git's argv: the probe declined only because `git merge-base` exited 128 with "Not a valid object name". It cannot inject an option, because the value starts with hex. It is still a hole in amendment 2's "checked before it reaches git" contract, which row G claims to pin. The fix is `\Z` or `fullmatch`. The regex is older than these commits (029f8fe).

Selftest at HEAD: `/usr/bin/python3 -B scripts/compound-v-emit-workflow.py --selftest` gives `637/637 checks passed`. The scratch worktree has been removed.

**Verdict: ISSUES.** Items 1, 3 and 4 are closed. Items 2 and 5 both block DONE and must be fixed before the next re-review. Item 2: a worker-writable `state.json` with a non-dict job entry still crashes `finalize-wave`. Item 5: a SHA with a trailing newline passes the validation and reaches git.

## Findings 2 and 5 closed (orchestrator, after the re-review)

2. CLOSED. `_already_integrated_wave` is now a never-raise wrapper around `_integrated_wave_or_none`: any unexpected
   error declines the short-circuit with one stderr line. The per-job check itself also accepts only a dict entry
   whose `merged` is a dict. Row H gained the two shapes the re-review reproduced (`"jobs": {"w1": "x"}` and
   `{"w1": {"merged": [1]}}`); before the fix it printed `raised AttributeError` for them.
5. CLOSED. The SHA check uses `_SHA_RE.fullmatch`. Row G2 (a SHA with a trailing newline) asserts no git call; before
   the fix it recorded `['merge-base', '--is-ancestor', 'aaaa…\n', 'HEAD']`.

Evidence: `scripts/compound-v-emit-workflow.py --selftest` `638/638 checks passed`; the manifest full command
`all-tests-ok`; `shellcheck hooks/*.sh scripts/compound-v-*.sh` clean.

**Final verdict: APPROVED.** All findings of the review and the re-review are closed.
