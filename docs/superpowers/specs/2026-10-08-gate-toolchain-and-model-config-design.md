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

## Pre-flight amendments (2026-10-08)

These override the sections above. Sources: the 1A and 1C audits of this spec.

1. **One reader, owned by the scope gate.** The emitter imports the gate (`emit-workflow.py:457`), so the gate cannot
   import the emitter, and copying the parse would be a second definition. The all-or-nothing reader of the manifest's
   `toolchain_artifacts` moves into `scripts/compound-v-scope-check.py` (which owns what the globs mean and which the gate
   already loads by explicit path); the emitter's `_toolchain_artifacts_spec` and the gate both call it. Its existing
   selftest cases move with it.
2. **Claims.** A missing receipt re-derives to `pass` or `blocked`, never `forged` (`integration-gate.py:1068-1101`);
   this change fixes the `contradicted` and false `blocked` verdicts only. It forgives only paths the manifest declares
   and that `git check-ignore` confirms in the gated tree: `.DS_Store` and `.phpunit.cache` stay violations unless
   declared (say so in the gate's docstring).
3. **Gate test.** A **direct** job (a sealed worktree job already passes on the old gate, `:1203-1221`), a file that is
   really gitignored, and an honest receipt produced with `--toolchain-artifact`: `pass` at the run-wide gate; with the
   glob removed from the manifest, `contradicted`/`blocked`. Fails on the old gate.
4. **resolve-model default in `main()` only.** `resolve()` and `load_config_models` are called in-process by
   classify-request, epic-arbiter and dashboard; their behaviour is unchanged. In `main()`, with no `--config`: root =
   `--repo-dir` or `resolve_project_root()`; config = `<root>/.claude/compound-v.json` (absent file = built-in table); the
   same root is passed to `default_settings_paths` so the effort-cap files and the models come from one place.
   `resolve_project_root` is loaded through the same explicit-path loader as other siblings; if it cannot be loaded or
   the directory is not in git, the command fails closed with a message, except that `--explicit-model` needs no config
   and keeps working anywhere.
5. **Callers pass the root.** `compound-v-emit-workflow.py` `resolve_job_model` passes `--repo-dir <the repo root it
   already knows>`; `agents/parallel-dispatcher.md:150` passes `--repo-dir "$PWD"` (it runs from the project root).
6. **Docs in the same change.** The resolver's docstring and `--repo-dir` help, `agents/parallel-dispatcher.md:141-142`,
   `skills/compound-v/phase-3-parallel-opus-dispatch.md`, `skills/compound-v/routing-policy.md:379-380` and
   `skills/compound-v/execution-manifest.md` say that omitting `--config` means the project's config (from `--repo-dir`
   or the git toplevel), not the built-in defaults.
7. **resolve-model test** adds: from a subdirectory, the effort cap and the models come from the same root;
   `--explicit-model` outside git still succeeds; outside git without flags it exits non-zero.
