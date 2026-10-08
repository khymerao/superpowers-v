# Integration gate honours toolchain_artifacts; resolve-model reads the project config - design

Triage: `docs/superpowers/pre-eval/2026-10-08T123419Z-item-5-harness-bugs-reproduced-1-scripts-compound-v-integrat-5605.json`
(FULL). Handoff: `docs/superpowers/research/2026-10-05-jev-next-stage.md`, "Harness bugs reported by a downstream run",
items 1 and 4. Decision context: ADR 0005 (project root).

## Problem

1. **The run-wide re-derivation ignores `toolchain_artifacts`.** The per-job gate (`compound-v-emit-workflow.py`
   `gate-receipt`, `:4436-4576`) passes the manifest's `toolchain_artifacts` globs to `compound-v-scope-check.py` as
   `--toolchain-artifact`. `compound-v-integration-gate.py` re-derives every job with `run_scope_check` (`:742-756`),
   which passes `--preexisting` but never `--toolchain-artifact`; the script does not mention `toolchain_artifacts`
   at all. A job whose gitignored build artifact was forgiven at its own gate is therefore re-derived as a violation,
   and the receipt reads `contradicted` (or, with a missing receipt, the job reads `forged`). Downstream report
   (2026-10-06, `connect-cf7-to-hubspot`): review jobs that changed nothing read `contradicted` or `forged` because
   `.DS_Store`, `.phpunit.cache` and a job's `.baseline` changed during the run. Confirmed in code 2026-10-08.
2. **`resolve-model` without `--config` ignores the project's `models` table.** Reproduced 2026-10-08 in a fixture repo
   whose `.claude/compound-v.json` maps `claude.standard` to `opus`: `--backend claude --tier standard` prints `sonnet`
   without `--config` (also with `--repo-dir .`), and `opus` with `--config .claude/compound-v.json`.
   `load_config_models(args.config)` (`:553`) reads nothing when the flag is absent, although
   `default_settings_paths(config_path, repo_dir)` (`:571`) already derives a project `.claude` directory.

## Change

1. `compound-v-integration-gate.py`: read the manifest's top-level `toolchain_artifacts` once (the same parse the
   emitter uses, reused, not re-implemented) and pass each glob as `--toolchain-artifact` in `run_scope_check`, so the
   re-derivation applies the same exemption the per-job gate did. The gate's other verdict rules are unchanged.
2. `compound-v-resolve-model.py`: when `--config` is absent, the config is `<project root>/.claude/compound-v.json`,
   where the project root is `--repo-dir` when given, else `resolve_project_root()` from
   `scripts/compound-v-project-config.py` (ADR 0005 rule 5). A missing file means the built-in defaults, as today.
   Outside a git repository with no `--repo-dir` and no `--config`, the behaviour is decided by the pre-flight after
   reading the callers (`agents/parallel-dispatcher.md:152`, `commands/v-models.md:348`, `skills/compound-v/routing-policy.md:372`,
   the emitter): fail closed per ADR 0005, unless a caller legitimately runs outside a repository, in which case the
   built-in table with a one-line stderr note, justified in writing.

## Tests

- `tests/test-integration-gate.sh` (or the gate's selftest): a run whose job created a gitignored file matching a
  manifest `toolchain_artifacts` glob, with a passing per-job receipt, is `pass` at the run-wide gate, not
  `contradicted`; with the glob removed from the manifest it is still caught. Fails on the old gate.
- `compound-v-resolve-model.py --selftest` or a test row: a fixture repo whose config maps `claude.standard` to `opus`
  resolves `opus` with no `--config`, from the repo root, from a subdirectory, and with `--repo-dir`. Fails on the old
  default.

## Acceptance Criteria

1. Both rows pass and each fails when its change is reverted.
2. Full suite, `lint-frontmatter.py .` and `shellcheck` green.
