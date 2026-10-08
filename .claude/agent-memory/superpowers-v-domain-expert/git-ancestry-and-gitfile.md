---
name: git-ancestry-and-gitfile
description: git merge-base --is-ancestor exit tri-state, self-ancestry, and that a .git entry marks worktrees, submodules and nested repos alike
metadata:
  type: reference
---

- `git merge-base --is-ancestor A B`: 0 = ancestor, 1 = not, any other non-zero = error (no answer).
  Source: https://git-scm.com/docs/git-merge-base (checked 2026-10-05). A == B exits 0.
- A `.git` gitfile is "usually managed via the git submodule and git worktree commands".
  Source: https://git-scm.com/docs/gitrepository-layout (checked 2026-10-05). A `.git` boundary check
  therefore also releases submodules and nested repos.
- Claude Code hooks: read the JSON `cwd`, not the process cwd (https://code.claude.com/docs/en/worktrees;
  anthropics/claude-code#99012).

Full matrix: docs/superpowers/expert/_knowledge-base/git-worktree-ancestry.md. Related: [[secret-bearing-files]]
