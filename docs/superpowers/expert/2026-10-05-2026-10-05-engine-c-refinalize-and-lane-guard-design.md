# Domain audit (Phase 1B): Engine C idempotent re-finalize and lane-guard working-tree boundary

Spec: `docs/superpowers/specs/2026-10-05-engine-c-refinalize-and-lane-guard-design.md`. Audited 2026-10-05.

**Limits of this audit.** This agent's Bash was clamped to `git log/show/blame` and the V-memory engine, so nothing
below was executed: no `git merge-base` probe, no `shellcheck`, no hook run. Every claim about git or Claude Code
behaviour cites a fetched primary source. Every claim about this repository's code cites a file and line I read. The
one induced-regression finding (F7) comes from reading the code and is marked PLAUSIBLE until Phase 1A or the plan
reproduces it.

## 1. Domain(s) Identified

- **git-worktree-ancestry**: git working-tree discovery (`.git` dir vs gitfile, linked worktrees, submodules) and
  commit reachability (`git merge-base --is-ancestor` semantics, history rewrites, shallow clones).
- **claude-code-hooks / worktrees**: what a `PreToolUse` hook gets as `cwd`, and how Claude Code lays out and vets
  its own worktrees under `.claude/worktrees/`.
- **autonomous-agent-orchestration** (existing KB): resumed workflows re-run completed stages, so state-writing
  stages must be idempotent.

## 2. Sources Consulted

**KB reused.** `docs/superpowers/expert/_knowledge-base/autonomous-agent-orchestration.md:202-205` says *"Resume
re-runs completed work … Any stage that writes/commits state or appends to an outcomes stream **must be
idempotent**."* That is the domain rule Defect 1 breaks. No KB file covered git ancestry or gitfile semantics, so I
created one (section 9).

**V-memory** (prompt block, plus two searches of my own: "lane guard direct job checkout prefix nested worktree" and
"finalize-wave integrated wave reset idempotent relaunch"):
- `docs/superpowers/archaeology/2026-09-03-v3-4-3-codex-sandbox-checkout.md` §9 reproduced this same defect class
  live on 2026-09-03. A stale run's lane map recorded the bare project root as a direct job's worktree, and an
  unregistered session was captured by it through the `cwd->worktree` branch.
- `docs/superpowers/archaeology/2026-09-03-v3-4-2-transcript-watch.md` §7 constraint 0 says the cwd-to-prefix map
  must not be used for attribution, because a direct job's entry "is the bare repo root, which matches every" path.
- `CHANGELOG.md` [3.4.2] (finding 68: a finished run's map claimed the checkout forever) and [3.4.3] (finding 78:
  longest-prefix ordering) are the earlier partial fixes. Both left the nested-worktree case open.
- `CHANGELOG.md` [3.6.1] records a self-contradictory `state.json`: `status: blocked` beside
  `merged.integrated: true` on the same job.

**Official sources fetched**
- [git-merge-base docs](https://git-scm.com/docs/git-merge-base): `--is-ancestor` *"exit with status 0 if true, or
  with status 1 if not. Errors are signaled by a non-zero status that is not 1."*
- [gitrepository-layout](https://git-scm.com/docs/gitrepository-layout): a `.git` *"plain text file … containing
  `gitdir:` <path> … is called a gitfile and is usually managed via the git submodule and git worktree commands."*
- [git-worktree](https://git-scm.com/docs/git-worktree): the linked worktree's `$GIT_DIR` and `$GIT_COMMON_DIR`
  *"settings are made in a `.git` file located at the top directory of the linked worktree."*
- [git(1) environment](https://git-scm.com/docs/git#Documentation/git.txt-GITCEILINGDIRECTORIES): git discovers the
  repository by walking up parent directories, and by default *"does not cross filesystem boundaries."*
- [Claude Code: worktrees](https://code.claude.com/docs/en/worktrees): worktrees default to
  `.claude/worktrees/<name>/`. The doc also says *"`cwd` follows Claude: the `cwd` field in the hook's input JSON is
  the worktree root, and it moves again when Claude runs `cd`."* Claude Code refuses a worktree whose *".git file
  points at the main repository's own .git directory"*, and *"also refuses when the directory has a .git entry it
  can't read."*
- [anthropics/claude-code#99012](https://github.com/anthropics/claude-code/issues/99012), opened 2026-10-02, open.
  With `--project-config-root` the hook *process* cwd is the config root, while the JSON `cwd` field still holds the
  session directory.

**Community and isolated reports.** Each is a single source. None meets the 10-post consensus threshold.
- Isolated report, 2026-09-17: [ajxcodes/agyloop#66](https://github.com/ajxcodes/agyloop/issues/66). Quote:
  *"In Git, every commit is considered an ancestor of itself (`git merge-base --is-ancestor X X` exits with code
  `0`)."* This matches git's documented "ancestor" definition. Row A depends on it.
- Isolated report, 2026-10-04: [litlfred/folio-assistant PR #2079](https://github.com/litlfred/folio-assistant/pull/2079)
  is titled "cannot tell is not no". It separates exit 1 (a real negative) from exit 128 on a shallow clone ("this
  repository cannot see enough history to say").
- Isolated report, 2026-09-17: [safeguard.sh blog](https://safeguard.sh/resources/blog/git-ancestry-lies-after-a-history-rewrite).
  Squash merges, rebases and filter-repo all rebuild hashes, so `--is-ancestor` answers about graph topology and not
  about whether the code is present.
- Search results with no cited claim taken from them:
  [GitLens #5067](https://github.com/gitkraken/vscode-gitlens/issues/5067) and
  [worktree-mgr PR #44](https://github.com/JohnXu22786/worktree-mgr/pull/44), "fail closed on merge-base errors".

**Not searched.** Layer 3 (persona forums) was skipped on purpose. The end users of this feature are this plugin's
own operators, and their record is this repository's dogfood and archaeology docs, which V-memory covered.

## 3. Domain Constraints the Brainstorm Probably Missed

**Defect 1 (ancestry short-circuit)**
- **MUST** treat `--is-ancestor` as having three outcomes: 0 = ancestor, 1 = not an ancestor, anything else = error
  ([git docs](https://git-scm.com/docs/git-merge-base)). The spec's "exits 0" predicate is correct. But **Row B as
  written (`"0" * 40`) tests the error path (an invalid object name, exit 128), not the not-an-ancestor path (exit 1).**
- **MUST** add a row where the recorded commit is a real commit that is not an ancestor of HEAD, for example a commit
  on a sibling branch of the test repo. Without it, nothing tests the exit-1 branch.
- **MUST** log which non-zero exit was seen when the short-circuit declines, so a history error (shallow clone,
  missing object) can be told apart from "not merged" in the run log
  ([folio-assistant #2079](https://github.com/litlfred/folio-assistant/pull/2079), isolated report).
- **MUST** rely on "a commit is its own ancestor" and nothing stricter. Row A records the wave at HEAD itself. A
  plan author who "fixes" this with a SHA-inequality check, as agyloop#66 proposes, would break Row A.
- **MUST** validate the recorded `commit` before it reaches git's argv. `state.json` is written by pipeline stages
  that workers drive, and a value starting with `-` is parsed as an option. Use the regex
  `^[0-9a-f]{40}$|^[0-9a-f]{64}$` (SHA-1 or SHA-256), and/or pass `--end-of-options`.
- **MUST** run git as `git -C <repo_root>`. HEAD is per-worktree in a linked worktree
  ([git-worktree](https://git-scm.com/docs/git-worktree)), so an implicit process cwd can ask the wrong HEAD.
- **MUST** keep AC-4's scratch clone at full depth. A shallow clone can make `--is-ancestor` error (exit 128), the
  short-circuit then declines, and AC-4 fails for a reason that has nothing to do with the fix.

**Defect 2 (`.git` boundary)**
- **MUST** walk upward using the same path spelling (lexical or realpath) under which `_rel_under` matched `cwd` to
  `wt`. `_rel_under` (`hooks/lane-guard.sh:662-682`) matches on either one, because macOS `/tmp` is really
  `/private/tmp`. A walk in the other spelling either never reaches `wt` or overshoots it.
- **MUST** count a `.git` that is a file, a directory, or a dangling symlink: use `os.path.lexists`, not `exists`.
  Claude Code itself treats an unreadable `.git` entry as a reason to refuse
  ([worktrees doc](https://code.claude.com/docs/en/worktrees)), not as a reason to ignore it.
- **MUST** use the hook input's JSON `cwd` (it already does). Never use the process cwd
  ([#99012](https://github.com/anthropics/claude-code/issues/99012)).
- **SHOULD** say in the code comment that a `.git` entry is also what submodules and nested independent repositories
  leave behind ([gitrepository-layout](https://git-scm.com/docs/gitrepository-layout)), not only linked worktrees.
  The boundary therefore releases those too.

## 4. Common Traps in This Domain

1. **Treating "not 0" as "not merged".** Exit 1 and exit 128 mean different things (see section 3).
2. **Ancestry is topology, not content.** A rebase, a squash merge or a filter-repo of the integration branch
   rehashes the wave commit, so it is no longer an ancestor even though its changes are present
   ([safeguard.sh](https://safeguard.sh/resources/blog/git-ancestry-lies-after-a-history-rewrite), isolated report).
   The spec accepts the revert case (a false positive). It does not mention the rewrite case, which is a false
   negative. **A false negative falls back to today's path, which is the defect itself.**
3. **The gitfile is not exclusive to worktrees.** Submodules use it as well. A nested `git init` (a vendored clone,
   a test fixture) leaves a `.git` directory. This repository has no `.gitmodules` today (glob returned none).
4. **Presence vs content of `.git`.** Claude Code checks what a `.git` file points at. The spec checks only that one
   exists. Inside a direct job, a worker that creates `sub/.git` and works from `sub/` would go unresolved, and so
   unchecked by the guard. That creating write is visible to the guard (if it is a tool write) and always to the
   scope gate (a new untracked path). This is a bounded evasion with the git gate as the backstop. It matches the
   guard's stated floor-not-enforcement contract (`.claude/rules/hooks.md`, citing `hooks/lane-guard.sh:24-30`).
5. **The superproject's git cannot see inside a nested repo.** `git ls-files --others` lists an untracked nested
   repository as a single directory entry and does not recurse into it. Edits inside an existing submodule show up
   only as a gitlink change. So in direct mode, writes inside a nested repo can slip past both the guard (after this
   change) and the scope gate. No such repo exists here today.

## 5. Regulatory / Compliance Notes

None. No regulation applies. The relevant "authority" is the repository's own security contract: the triage record
fired an override because `hooks/lane-guard.sh` is a security hook, and the guard is fail-open by design
(`TROUBLESHOOTING.md:290`).

## 6. Recent Breaking Changes (last 12 months)

- **Claude Code ≥ 2.1.206.** `EnterWorktree` asks for approval before entering a path outside `.claude/worktrees/`
  ([worktrees doc](https://code.claude.com/docs/en/worktrees)). Inside `.claude/worktrees/`, sessions move freely,
  which is exactly the population Defect 2 captures.
- **Claude Code worktree isolation checks.** Claude Code already blocks Edit/Write into the main checkout from an
  isolated worktree session (same doc, "How Claude Code enforces isolation"). This is the host's own guard. It does
  not make the lane guard's mis-attribution harmless: the guard denies first.
- **#99012 (open, 2026-10-02).** The hook process cwd can differ from the session cwd under
  `--project-config-root`.
- No change to `git merge-base --is-ancestor` semantics was found. The exit-code contract above is current on
  git-scm.com.

## 7. Design Constraints for the Plan

1. `_already_integrated_wave` MUST short-circuit only on exit **0** of
   `git -C <repo_root> merge-base --is-ancestor <commit> HEAD`. Exit 1, any other code, a timeout or an exception
   MUST all decline the short-circuit. The declining code MUST appear in the emitted reason or the log.
2. The recorded `commit` MUST match `^[0-9a-f]{40}$|^[0-9a-f]{64}$` before it is passed to git. Otherwise: no
   short-circuit.
3. The selftest MUST add a row C: the recorded commit is a real, existing commit that is not an ancestor of HEAD
   (exit 1). Expected: no short-circuit, the stub refuses, the run goes `BLOCKED`. Row B (`"0" * 40`) stays, as the
   error-path row.
4. The plan MUST NOT add a SHA-inequality condition. A wave recorded at HEAD must short-circuit (Row A).
5. AC-4's scratch clone MUST be a full-depth clone (no `--depth`, no `--shallow-*`), and the AC text MUST say so.
6. The upward `.git` walk MUST use the path spelling that matched in `_rel_under`, MUST exclude `wt` itself, MUST
   test `os.path.lexists(dir/.git)`, and MUST stay bounded by the depth between `cwd` and `wt` with no subprocess.
7. **(F7, PLAUSIBLE, verify before planning.)** After the fix, an unrelated session in `.claude/worktrees/x` is
   unresolved, and it then meets the recording gates. Gate 3 holds because `agent_worktree_root(cwd)` matches. Gate 2
   holds because the direct job's "worktree" is the checkout, which exists. So `record_unresolved`
   (`hooks/lane-guard.sh:1584-1594`) appends `lane-guard-unresolved.jsonl` into the live run directory in the main
   checkout, and that checkout is the direct job's gated tree. The `SKIP-RECORD` guard (`hooks/lane-guard.sh:945-951`)
   checks only the acting agent's worktree. `lane-guard-unresolved.jsonl` is not in `RUN_DIR_EXEMPT_BY_NAME`
   (`scripts/compound-v-emit-workflow.py:4209-4222`). In direct mode, any run-dir file that is not exempt and was not
   in the register-time snapshot is charged to the job (`scripts/compound-v-emit-workflow.py:4190-4194, 4245-4258`).
   Before the fix these sessions were denied, so nothing was recorded. **The plan MUST settle this explicitly.**
   Either a session stopped at a `.git` boundary does not record (it is a separate working tree, not this run's
   worker), or the record is exempt by name with a stated reason. A test row MUST then pin whichever choice it makes.
   Note: suppressing the record also hides an Engine C worker that writes before `register-lane` in its own
   worktree. That trade-off is the human's (see section 8).
8. Lane B MUST include `TROUBLESHOOTING.md`. Line 290 describes resolution ("falls back to `cwd` → worktree"), so the
   spec's conditional fires.
9. The comment above the `cwd->worktree` branch MUST name submodules and nested repositories as boundaries too, and
   MUST say that the scope gate cannot see inside them.

## 8. Open Questions for the Human

1. **History rewrite.** If the integration branch is rebased or squash-merged after a wave integrates, the wave
   commit stops being an ancestor and re-finalize falls back to the resetting behaviour. Accept that as a second
   limit beside the revert case, or require a content check (a sealed post-image or patch-id) as a fallback?
2. **F7 trade-off.** For a session stopped at a `.git` boundary, should the guard (a) stay silent, (b) record into
   the run directory with the jsonl made exempt by name, or (c) record somewhere outside the gated tree, such as the
   `$TMPDIR` log only?
3. **Contradictory job state** (CHANGELOG 3.6.1). A job with `status: blocked` beside `merged.integrated: true`: should
   the short-circuit honour `merged.integrated` alone, as the spec says, or also require a non-blocked status?
4. **Spoofable boundary.** Is the presence-only `.git` test acceptable, given the scope gate as backstop, or should
   the guard require a gitfile whose `gitdir:` points under this repository's `.git/worktrees/`, as Claude Code's own
   check does?

## 9. Knowledge Base Updates

- Created `docs/superpowers/expert/_knowledge-base/git-worktree-ancestry.md`. It covers the `--is-ancestor`
  three-outcome exit contract, self-ancestry, shallow-clone and history-rewrite failure modes, gitfile scope
  (worktree and submodule), upward discovery, and the Claude Code hook `cwd` rule. Every entry is cited.
