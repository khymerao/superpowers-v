---
name: drift-git-gate-and-resolver
description: Dated facts on git check-ignore exit codes, rev-parse --show-toplevel in worktrees, and where the toolchain_artifacts parse and resolve-model config read live, checked 2026-10-08
metadata:
  type: reference
---

Leads only; re-verify before reuse. Detail in `docs/superpowers/library-audit/_knowledge-base/git-cli.md`.

- 2026-10-08: `git check-ignore` exits 0 (some ignored), 1 (none), 128 (fatal); tracked files not reported without `--no-index`.
- 2026-10-08: `git rev-parse --show-toplevel` in a linked worktree prints that worktree's root (inferred from the definition).
- 2026-10-08: `_toolchain_artifacts_spec` is in `scripts/compound-v-emit-workflow.py` (~:2152), all-or-nothing; the integration gate must not import that file (pycache hardening, `load_scope_matcher`).
- 2026-10-08: Context7 was OAuth-pending (not absent) via ToolSearch; Bash clamped to memory/git forms.
