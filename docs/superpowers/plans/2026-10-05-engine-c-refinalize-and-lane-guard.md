# Engine C Re-finalize and Lane-Guard Boundary Implementation Plan

> **For agentic workers:** executed by Compound V on Engine C from one manifest
> (`docs/superpowers/execution/2026-10-05-engine-c-refinalize-and-lane-guard/manifest.yaml`). Each task is one job in
> its own lane. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A relaunch no longer un-integrates a wave already in HEAD, and a lane claim on the checkout no longer
captures sessions working in their own nested git worktree.

**Architecture:** Lane A adds a git-verified short-circuit at the top of `finalize-wave` and exempts the lane
guard's own record file by name. Lane B stops the lane guard's cwd-to-worktree claim at the first `.git` between
`cwd` and the claimed path. A three-pass review follows.

**Tech Stack:** Python 3.9 stdlib (the script, and the Python inside the hook), bash tests.

**Spec:** `docs/superpowers/specs/2026-10-05-engine-c-refinalize-and-lane-guard-design.md`. Its "Pre-flight
amendments" section overrides the sections above it. Audits:
`docs/superpowers/archaeology/2026-10-05-2026-10-05-engine-c-refinalize-and-lane-guard-design.md`,
`docs/superpowers/expert/2026-10-05-2026-10-05-engine-c-refinalize-and-lane-guard-design.md`,
`docs/superpowers/library-audit/2026-10-05-2026-10-05-engine-c-refinalize-and-lane-guard-design.md`.

## Global Constraints

- Python 3.9 syntax, stdlib only; no `match`; no `X | Y` annotations or `isinstance(x, A | B)`.
- The hook stays filesystem-only on its resolution path: no `git` subprocess.
- Every behavioural change ships a test row that fails when the change is reverted.
- The short-circuit merges nothing and writes nothing; it never weakens what the authority decides for a wave it runs on.
- No fabricated metrics; no timing numbers in docs; no cost or savings text.
- Docs: plain words, every claim true of HEAD, no line over 200 characters outside code/tables.
- Lane discipline: touch only your `write_allowed`; `register-lane` first, with a literal `--cwd`. Run python with `-B`.
- Not in any implementation job: version bump, CHANGELOG, `plugin.json`, `marketplace.json`.
- Commit subjects are plain sentences, no `feat:`/`fix:`; no Co-Authored-By trailer.

## Partition Map

| Task | Job id | Files (write) |
|---|---|---|
| A | `refinalize` | `scripts/compound-v-emit-workflow.py` |
| B | `lane-boundary` | `hooks/lane-guard.sh`, `tests/test-lane-guard.sh`, `TROUBLESHOOTING.md` |
| R | `spec-review` | `docs/superpowers/dogfood/2026-10-05-engine-c-refinalize-and-lane-guard-review.md`, `.claude/agent-memory/superpowers-v-spec-reviewer/**` |

No file is shared. A and B run in parallel; R depends on both.

---

### Task A: Idempotent re-finalize of an integrated wave (`refinalize`)

**Files:**
- Modify: `scripts/compound-v-emit-workflow.py` — `RUN_DIR_EXEMPT_BY_NAME` (~`:4209`), `cmd_finalize_wave` (~`:5950`,
  the check goes after the `manifest_digest_fault` block at ~`:5993` and before `# ---- 1. THE AUTHORITY` at ~`:5999`;
  the commit message at ~`:6245`), selftest beside the idempotent-commit row (~`:8770`).

**Interfaces:**
- Produces: `_wave_commit_subject(wave, run_id, merged) -> str`;
  `_already_integrated_wave(run_dir, repo_root, wave, job_ids) -> dict | None` (3.9: annotate in the docstring, not
  with `|`).

- [ ] **Step 1: Write the failing selftest rows.** Beside the "idempotent no-op — not `git commit failed`" row, reuse
  the `idem_repo` pattern: a repo with one commit made with subject `_wave_commit_subject(1, "refin", ["w1"])`.
  Build a run dir `rf_dir` with a stub integration gate written as a real file:

```python
stub = os.path.join(tmp, "refusing-gate.py")
with open(stub, "w", encoding="utf-8") as fh:
    fh.write("import json, sys\n"
             "print(json.dumps({'integration': 'refused', 'tally': {'unverifiable': 1}}))\n"
             "sys.exit(1)\n")


def _refin_run(commit):
    d = tempfile.mkdtemp(dir=tmp)
    with open(os.path.join(d, "manifest.yaml"), "w", encoding="utf-8") as fh:
        json.dump({"run_id": "refin", "jobs": [
            {"id": "w1", "isolation": "direct", "write_allowed": ["src/**"]}]}, fh)
    st = {"run_id": "refin", "phase": "MERGED",
          "jobs": {"w1": {"status": "done", "isolation": "direct",
                          "merged": {"integrated": True, "commit": commit}}},
          "waves": {"1": {"jobs": ["w1"], "merged": ["w1"], "commit": commit, "integrated": True}}}
    with open(os.path.join(d, "state.json"), "w", encoding="utf-8") as fh:
        json.dump(st, fh, indent=2)
    return d


def _refin(d, repo):
    before = open(os.path.join(d, "state.json"), "rb").read()
    with _quiet():
        rc = cmd_finalize_wave(["--run-dir", d, "--repo-root", repo, "--manifest",
                                os.path.join(d, "manifest.yaml"), "--jobs", "w1", "--wave", "1",
                                "--integration-gate", stub])
    after = open(os.path.join(d, "state.json"), "rb").read()
    phase = json.loads(after).get("phase")
    return rc, before == after, phase
```

  Rows (each named after the planted failure it catches):
  - A: `_refin(_refin_run(head), repo)` → `rc == 0`, state byte-identical, phase `MERGED`.
  - B: commit `"0" * 40` → `rc != 0`, phase `BLOCKED`.
  - C: a real commit on a side branch (`git checkout -b side`, commit, `git checkout -`) → `rc != 0`, phase `BLOCKED`.
  - D: an ancestor commit whose subject is not the wave subject (an earlier ordinary commit) → `rc != 0`, phase `BLOCKED`.
  - E: commit `"--output=/tmp/x"` → `rc != 0`, phase `BLOCKED`, and `/tmp/x`-style path not created.
  - Exempt list: `run_dir_owned_by_name(run_rel + "/lane-guard-unresolved.jsonl", run_rel, "any")` is True and
    `run_dir_owned_by_name(run_rel + "/lane-guard-unresolved.jsonl.bak", run_rel, "any")` is False (the generated
    per-entry rows also cover it once the entry exists).
  Rows B-E load the manifest through the refusal path; guard them under `have_yaml` as the neighbouring refusal row does.

- [ ] **Step 2: Run, see them fail.** `/usr/bin/python3 -B scripts/compound-v-emit-workflow.py --selftest`
  Expected: row A and the exempt row FAIL (the stub refuses and the run goes `BLOCKED`).

- [ ] **Step 3: Implement.**

```python
_SHA_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")


def _wave_commit_subject(wave, run_id, merged):
    """The finalizer's own wave-commit subject: the one place its format is spelled."""
    return "compound-v: wave %d of run %s (%s)" % (wave, run_id, ", ".join(merged) or "no jobs")


def _already_integrated_wave(run_dir, repo_root, wave, job_ids):
    """The wave's result (a dict) when state.json records it integrated at a commit git confirms is
    this run's wave commit and in HEAD; else None. Writes nothing and merges nothing.

    Accepted limit: state.json is worker-writable, so a forged wave entry plus a forged ancestor
    commit carrying the finalizer's subject would make a re-finalize skip that wave (work not
    re-merged, never ungated work landing). A later revert of the wave commit is not detected."""
    try:
        state = _load_state(run_dir)
    except Exception:  # noqa: BLE001
        return None
    rec = (state.get("waves") or {}).get(str(wave))
    if not isinstance(rec, dict) or rec.get("integrated") is not True:
        return None
    commit = rec.get("commit")
    if not isinstance(commit, str) or not _SHA_RE.match(commit):
        return None
    if sorted(rec.get("jobs") or []) != sorted(job_ids) or sorted(rec.get("merged") or []) != sorted(job_ids):
        return None
    jobs = state.get("jobs") or {}
    for jid in job_ids:
        if (((jobs.get(jid) or {}).get("merged") or {}).get("integrated")) is not True:
            return None
    try:
        rc, _o, _e = _git(repo_root, ["merge-base", "--is-ancestor", commit, "HEAD"])
        if rc != 0:
            return None
        rc, subj, _e = _git(repo_root, ["log", "-1", "--format=%s", commit])
    except Exception:  # noqa: BLE001
        return None
    run_id = state.get("run_id") or os.path.basename(run_dir)
    if rc != 0 or subj.strip() != _wave_commit_subject(wave, run_id, rec.get("merged") or []):
        return None
    return {"integrated": True, "merged": list(job_ids), "commit": commit,
            "reason": ("wave already integrated at %s, which is in HEAD and is this run's wave "
                       "commit (idempotent re-finalize; the authority was not re-run)" % commit[:12])}
```

  Note on the subject: the finalizer commits with `out["merged"]` in its own order; the check rebuilds the subject from
  the recorded `merged` list, which the finalizer wrote from the same list. If the reviewer finds the two orders can
  differ, compare against the recorded list's order exactly as written.

  In `cmd_finalize_wave`, after the `fault` block:

```python
    done = _already_integrated_wave(run_dir, repo_root, args.wave, job_ids)
    if done is not None:
        out.update(done)
        return emit(0)
```

  Replace the inline message at ~`:6245` with
  `message = _wave_commit_subject(args.wave, state.get("run_id") or os.path.basename(run_dir), out["merged"])`.
  Add to `RUN_DIR_EXEMPT_BY_NAME`:

```python
    ("lane-guard-unresolved.jsonl",
     "written by hooks/lane-guard.sh, never by a job; an append-only record of sessions the guard could not resolve"),
```

- [ ] **Step 4: Run, see them pass, prove the revert.** Rerun the selftest: all rows pass. Comment out the
  `done = …` call: row A fails. Remove the exempt entry: the exempt row fails. Restore both.

- [ ] **Step 5: AC-4 on a scratch clone.**

```bash
S=$(mktemp -d); git clone -q --no-local "$PWD" "$S/c"
R=$S/c/docs/superpowers/execution/2026-10-05-jev-classifier-foundation
cp $R/state.json $S/before.json
/usr/bin/python3 -B $S/c/scripts/compound-v-emit-workflow.py finalize-wave --run-dir $R --repo-root $S/c \
  --manifest $R/manifest.yaml --wave 1 --jobs record-t3,config-jev,jev-core,vault,corpus; echo rc=$?
cmp $R/state.json $S/before.json && echo state-unchanged
```

  Expected: `rc=0` and `state-unchanged`. Quote the output in the job summary.

- [ ] **Step 6: Commit.** `git commit -m "Let finalize-wave return early for a wave git confirms is already integrated, and exempt the lane guard's record by name" -- scripts/compound-v-emit-workflow.py`

---

### Task B: The lane guard's cwd claim stops at a working-tree boundary (`lane-boundary`)

**Files:**
- Modify: `hooks/lane-guard.sh` — `resolve_job` (~`:822-848`), plus a helper beside `_rel_under` (~`:662`)
- Modify: `tests/test-lane-guard.sh` — section 2a (~`:390`) and 2b (~`:408`)
- Modify: `TROUBLESHOOTING.md:290`

**Interfaces:**
- Produces: `_crosses_worktree_boundary(cwd, wt) -> bool` in the hook's Python.

- [ ] **Step 1: Write the failing rows.**
  In section 2a (finding 78), before the lane map is written, give the registered worktree a `.git` file, as real
  linked worktrees have: `printf 'gitdir: /nowhere\n' > "$WT/.git"`, and remove it at the end of the block. The two
  existing finding-78 rows then assert: the registered worktree still resolves to `job-under-test` and an out-of-lane
  write in it is still denied.

  In section 2b, while `$RUN_L` is DISPATCHED (the live direct job claims the checkout), add:

```bash
FOREIGN="$PROJ/.claude/worktrees/foreign-session"
mkdir -p "$FOREIGN/docs"; printf 'gitdir: /nowhere\n' > "$FOREIGN/.git"
file_case "a nested git worktree NOT in the map is not captured by the checkout's direct-job claim" allow \
  Write agent_foreign "$FOREIGN" "$FOREIGN/docs/notes.md"
check "...and the hook says the session is unresolved" \
  "$([ "$(logged 'UNRESOLVED IDENTITY')" = yes ] && echo 1 || echo 0)"
file_case "a plain subdirectory of the checkout still resolves to the direct job (out-of-lane denied)" deny \
  Write agent_sub "$PROJ/docs" "$PROJ/docs/elsewhere.md"
rm -rf "$FOREIGN"
```

- [ ] **Step 2: Run, see the nested-worktree row fail.** `bash tests/test-lane-guard.sh`
  Expected: `FAIL a nested git worktree NOT in the map is not captured … -> no deny` (today it is denied as the direct job).

- [ ] **Step 3: Implement.** Beside `_rel_under`:

```python
def _crosses_worktree_boundary(cwd, wt):
    """True when a separate git working tree (a nested worktree, a submodule, a nested repository)
    sits between `wt` and `cwd`: some directory from `cwd` up to, but excluding, `wt` holds a
    `.git` entry (a file counts). The scope gate cannot see inside such a tree, and a lane claim on
    `wt` does not reach into it. Walks in the same path form under which `cwd` is inside `wt`;
    if no form puts `cwd` inside `wt`, returns False and the claim stands as before."""
    forms = [(os.path.normpath(cwd), os.path.normpath(wt))]
    try:
        forms.append((os.path.realpath(cwd), os.path.realpath(wt)))
    except Exception:
        pass
    for p, r in forms:
        r = r.rstrip(os.sep)
        if p != r and not p.startswith(r + os.sep):
            continue
        d = p
        for _ in range(p.count(os.sep) - r.count(os.sep)):
            if d == r:
                break
            if os.path.lexists(os.path.join(d, ".git")):
                return True
            d = os.path.dirname(d)
        return False
    return False
```

  In `resolve_job`'s longest-prefix loop:

```python
        for wt, job in sorted(worktrees.items(), key=lambda kv: -len(kv[0])):
            if cwd and _rel_under(cwd, wt) is not None:
                # A claim stops at a git working-tree boundary: a nested worktree, submodule or
                # repository under `wt` is another tree, which the scope gate of this job cannot see.
                if _crosses_worktree_boundary(cwd, wt):
                    continue
                return job, manifest, wt, proj, "cwd->worktree"
```

  The comment must not contain the strings `tests/test-lane-guard.sh:1344-1373` forbids; check with
  `sed -n 1344,1373p tests/test-lane-guard.sh` before writing it.

- [ ] **Step 4: Run, see all rows pass, prove the revert.** `bash tests/test-lane-guard.sh` green;
  `shellcheck hooks/*.sh` clean. Make `_crosses_worktree_boundary` return `False` always: the nested-worktree row
  fails. Make it also check `wt` itself (loop to `range(… + 1)`): the finding-78 rows fail. Restore.

- [ ] **Step 5: TROUBLESHOOTING.md:290.** After "both via `docs/superpowers/execution/<run>/lane-map.json`." add:
  "A `cwd` claim stops at a git working-tree boundary: a session in a nested worktree, submodule or repository under a
  claimed path is not that job, and is logged as unresolved." Run `/usr/bin/python3 -B scripts/lint-frontmatter.py .`.

- [ ] **Step 6: Commit.** `git commit -m "Stop the lane guard's cwd claim at a nested git working tree" -- hooks/lane-guard.sh tests/test-lane-guard.sh TROUBLESHOOTING.md`

---

### Task R: Review Gate (`spec-review`)

Three passes against the spec (amendments first) and AC-1..AC-4, written to
`docs/superpowers/dogfood/2026-10-05-engine-c-refinalize-and-lane-guard-review.md` (`## Recall`, `## SPEC`,
`## QUALITY`, `## INTEGRATION`, `## Verdict`). Run each AC on the merged tree and quote command and output,
including AC-4 on a full-depth scratch clone, a revert proof for row A and for the nested-worktree row, and the
manifest's full test command. Verdict APPROVED or ISSUES with a numbered list.

## Self-review

- Spec coverage: Defect 1 conditions 1-5 + validation + git rc + reason prefix + limits → Task A step 3 (reason does
  not start with "nothing left to commit"); rows A-E → step 1; exemption → step 3; AC-4 → step 5. Defect 2 rule 1-5
  → Task B step 3/5; rows → step 1. AC-3 → Task B step 4 and Task R.
- Names: `_wave_commit_subject`, `_already_integrated_wave`, `_crosses_worktree_boundary` — each defined in its own
  task; no task consumes another task's code.
