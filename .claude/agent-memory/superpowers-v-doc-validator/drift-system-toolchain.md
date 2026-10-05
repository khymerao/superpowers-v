---
name: drift-system-toolchain
description: Dated facts on Python EOL lines, git --is-ancestor exit codes and shellcheck version, checked 2026-10-05
metadata:
  type: reference
---

Leads only; re-verify before reuse. Detail in `docs/superpowers/library-audit/_knowledge-base/{git-cli,python-tooling,posix-shell-tooling}.md`.

- 2026-10-05: Python 3.9 EOL 2025-10-31, 3.10 EOL 2026-10-01, oldest supported 3.11; repo CI floor is still 3.9.
- 2026-10-05: `git merge-base --is-ancestor` exits 0 true, 1 false, other non-zero = error; gitfile `.git` is a file for worktrees/submodules.
- 2026-10-05: shellcheck latest is v0.11.0 (2025-08-04); CI apt copy is 0.9.0; no bash-version awareness.
- 2026-10-05: Context7 absent again via ToolSearch in a Workflow-spawned run (only failed tessl named); Bash clamped to memory/git forms.
