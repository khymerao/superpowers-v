# Fix run B2: the last two __file__ project roots (ADR 0005) - design

Decision: [`docs/superpowers/adr/0005-one-rule-per-root.md`](../adr/0005-one-rule-per-root.md), rules 5-6.
Source: the review of run `2026-10-08-project-root-run-b`
(`docs/superpowers/dogfood/2026-10-08-project-root-run-b-review.md`, `## Verdict` issues 1 and 3).
Triage: `docs/superpowers/pre-eval/2026-10-08T112548Z-fix-run-b2-for-adr-0005-review-findings-of-run-2026-10-08-pr-72d6.json` (FULL).

## Change

1. **`scripts/compound-v-integration-gate.py:1423-1424`.** Without `--repo-root` the gate took the plugin directory
   (`dirname(__file__)/..`) as the repository it verifies. `/v:dispatch`, `/v:collect` and `/v:resume` call it without
   `--repo-root` from the project root, so an installed plugin checked its own cache tree. The default becomes
   `resolve_project_root(args.repo_root)` from `scripts/compound-v-project-config.py` (explicit flag, else the git
   toplevel of the current directory); outside git with no flag it prints the gate's usual error JSON and exits 2.
   Engine C already passes `--repo-root` explicitly; that path is unchanged.
2. **`scripts/compound-v-update-memory.py:67-74`.** `_default_outcomes_path()` defaulted `task-outcomes.jsonl` into the
   plugin directory. It takes the project root from `resolve_project_root` (with a `--repo` flag if the CLI lacks one);
   outside git with no explicit path it fails closed with a message. Its importer `compound-v-triage-outcomes.py`
   loads it as a sibling; that use must keep working.
3. **`scripts/compound-v-validate-manifest.py:3376-3378`.** The no-root note ("checks that need a repository root are
   skipped") is false for a manifest with a `fast_path` block, whose validation fails closed without a root. Reword it
   so it is true in both cases (or print it only when the manifest has no `fast_path` block).

## Tests (`tests/test-project-root.sh`)

- integration-gate: from a copy of the script outside a fixture repo, run inside the repo with no `--repo-root`, the
  resolved root is the fixture repo (observable through the report or an error naming the path), never the copy's
  parent; outside git with no flag it exits 2. Fails on the old default.
- update-memory: same shape for the outcomes path; writes into `<repo>/docs/superpowers/memory/`, nothing beside the
  copy.
- validate-manifest: a `fast_path` manifest with no repository root does not print the false note.
- The AC-2 grep: no script under `scripts/` derives a project root from `__file__` outside a selftest.

## Acceptance Criteria

1. The new rows pass and each fails when its change is reverted.
2. No script under `scripts/` derives a project root from `__file__` outside a selftest (run B's AC-2, now met).
3. Full suite, `lint-frontmatter.py .` and `shellcheck` green.
