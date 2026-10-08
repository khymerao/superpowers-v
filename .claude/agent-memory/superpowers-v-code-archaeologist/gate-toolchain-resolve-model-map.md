---
name: gate-toolchain-resolve-model-map
description: Where toolchain_artifacts is read, how the run-wide integration gate decides verdicts, and who calls resolve-model with which config (checked 2026-10-08)
metadata:
  type: reference
---

Map facts, 2026-10-08 checkout. Leads, not verdicts: re-verify.

- `toolchain_artifacts` has three readers: validator rules (`validate-manifest.py:~2387`), emitter `_toolchain_artifacts_spec` (`emit-workflow.py:~2152`, all-or-nothing), and none in `integration-gate.py`. The emitter imports the gate (`emit-workflow.py:~457`), so the gate cannot import the emitter.
- Gate verdict branches in `evaluate_job`: missing receipt re-derives (blocked/pass, never forged); present receipt with binding fault returns forged/stale without calling the scope check; worktree + sealed patch already forgives post-seal violations (~:1203). Test fixtures built with `tests/test-integration-gate.sh` `honest_receipt` have no sealed patch.
- `resolve-model` CLI: config only from `--config`; `--repo-dir` affects only effort-cap settings paths; `_project_claude_dir` falls back to cwd. Importers (classify-request, epic-arbiter, dashboard) call `resolve()`/`load_config_models` in-process, so a default must live in `main()`.
- Emitter calls the resolver as a subprocess with `--config` only if the file exists and no `cwd`; `$CONFIG` in dispatcher/phase-3 snippets is never assigned.
- The plugin repo's own `.claude/compound-v.json` holds only `memory` keys; CI selftests run with cwd at the plugin root.
- `tests/test-project-root.sh` greps the gate source above its `# selftest` marker for `__file__`-derived roots (AC2).
