# Git Worktree and Ancestry Knowledge Base

Maintained by Compound V Phase 1B advisor. Append at the bottom on each pass.

---

## Updated 2026-10-05: Engine C re-finalize and lane-guard working-tree boundary

### Reachability: `git merge-base --is-ancestor A B`

| Outcome | Exit | Meaning | Source |
|---|---|---|---|
| A reachable from B | 0 | ancestor | [git-merge-base](https://git-scm.com/docs/git-merge-base) |
| A not reachable from B | 1 | real negative | same |
| bad object, invalid name, missing history | other non-zero (128 in practice) | **no answer** | same: "Errors are signaled by a non-zero status that is not 1." |
| A == B | 0 | a commit is its own ancestor | isolated report, 2026-09-17, [agyloop#66](https://github.com/ajxcodes/agyloop/issues/66) |

- A shallow clone can make the check error instead of answering. Treat that as "cannot tell", not as "no".
  Isolated report, 2026-10-04: [folio-assistant #2079](https://github.com/litlfred/folio-assistant/pull/2079).
- Ancestry is topology, not content. A squash merge, rebase or filter-repo rehashes commits, so a change can be
  present while its old commit is not an ancestor. Isolated report, 2026-09-17:
  [safeguard.sh](https://safeguard.sh/resources/blog/git-ancestry-lies-after-a-history-rewrite).
- Any commit value read from a file that workers can influence must be hex-validated (40 or 64 characters) before it
  reaches argv, because a leading `-` is parsed as an option.
- In a linked worktree HEAD is per-worktree, so pass `git -C <root>` explicitly
  ([git-worktree](https://git-scm.com/docs/git-worktree)).

### Working-tree boundaries

- A `.git` may be a directory or a gitfile (`gitdir: <path>`). The gitfile is "usually managed via the git
  submodule and git worktree commands" ([gitrepository-layout](https://git-scm.com/docs/gitrepository-layout)).
  A `.git` boundary therefore also matches submodules and nested `git init` repositories, not only linked worktrees.
- A linked worktree's `.git` file sits at its top directory and points at `<main>/.git/worktrees/<name>`
  ([git-worktree](https://git-scm.com/docs/git-worktree)).
- Git discovers the repository by walking up parent directories, and by default stops at filesystem boundaries
  ([git(1)](https://git-scm.com/docs/git#Documentation/git.txt-GITCEILINGDIRECTORIES)).
- The superproject's `git ls-files --others` reports an untracked nested repository as one directory entry. Edits
  inside an existing submodule appear only as a gitlink change. A path-based scope gate cannot see inside either.

### Claude Code specifics

- Default worktree location: `.claude/worktrees/<name>/`, on branch `worktree-<name>`
  ([worktrees doc](https://code.claude.com/docs/en/worktrees)).
- A hook's JSON `cwd` follows the session into the worktree and through `cd`. `${CLAUDE_PROJECT_DIR}` stays at the
  launch root (same doc).
- The hook *process* cwd can differ from the JSON `cwd` under `--project-config-root`
  ([anthropics/claude-code#99012](https://github.com/anthropics/claude-code/issues/99012), opened 2026-10-02).
  Read the JSON field.
- Claude Code vets a worktree's `.git` by what it points at, and refuses one it cannot read (worktrees doc). A
  presence-only `.git` check is weaker than the host's own check.
