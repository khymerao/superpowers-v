# One project-root rule (ADR 0005, run B) - design

Decision: [`docs/superpowers/adr/0005-one-rule-per-root.md`](../adr/0005-one-rule-per-root.md), rules 5-8.
Triage: `docs/superpowers/pre-eval/2026-10-08T100626Z-run-b-of-adr-0005-project-root-the-project-root-is-an-explic-544f.json`
(FULL). Audits: the archaeology and library audit of 2026-10-08 for the plugin-root resolver (inventory rows 15-28 and
constraints 9-15 apply here).

## Change

1. **One Python helper.** `scripts/compound-v-project-config.py` gains `resolve_project_root(repo=None, start=None)`:
   an explicit `repo` (real path, must be a directory) wins; otherwise the git toplevel of `start` (default the current
   directory), via `git -C <start> rev-parse --show-toplevel`, real path; outside a git repository it raises
   `ValueError` with a message naming the problem. It never consults `__file__` and never returns the current directory
   as a guess. Covered by the module's selftest.
2. **`scripts/compound-v-triage-outcomes.py`.** `_repo_root()` (`:255-257`) is removed. `default_stream_path()`,
   `resolve_min_sample_count`'s config base (`:272`), `:1136` and `_resolve_exec_dir` (`:749`) take the project root
   from `resolve_project_root(args.repo)`; the CLI gains `--repo` (optional, default per the helper). `STREAM_RELPATH`
   stays the single definition of the stream path. A command run outside a git repository with no `--repo` and no
   `--stream` exits non-zero with the helper's message instead of writing beside the script.
3. **One stream path.** `scripts/compound-v-preeval.py` (the `setdefault` at `:1628-1630` and the literals at `:2532`,
   `:2584`, `:2826`, `:2884`, `:2906`, `:3039`, `:3096`, `:3220`) and `scripts/compound-v-fastpath-materialize.py`
   (`TRIAGE_STREAM_REL` at `:90`, its use at `:708`) use triage-outcomes' `STREAM_RELPATH` (loaded the way each module
   already loads its siblings). Selftest fixtures that build their own path may keep a literal only where they assert
   the constant's value.
4. **`scripts/compound-v-validate-manifest.py:3285-3295`.** `_find_repo_root` no longer falls back to `os.getcwd()`:
   a start path with no `.git` above it returns `None`, and each caller handles `None` the way it already handles a
   missing repository (read the callers; fail closed where a root is required, report it otherwise).
5. **Hooks walk up.** `hooks/precompact-snapshot.sh` (`:169-180`, `:231-232`), `hooks/run-band.tsx:179` and
   `hooks/brainstorm-trigger0-nudge.sh` (`:73`, `:134`) find the project root by walking up from the hook `cwd` to the
   nearest `.git` (directory or file), as `hooks/postcompact-resume.sh:85` and `hooks/triage-prompt-nudge.sh:245` do,
   with the same bound and the same "not found" result. The precompact snapshot key then matches the postcompact key
   for a session started in a subdirectory.
6. **Callers.** The command prose that calls `compound-v-triage-outcomes.py` without `--stream`
   (`commands/v-orchestrate.md:151`, `commands/v-collect.md:128`, `commands/v-dispatch.md:340`,
   `agents/parallel-dispatcher.md:365`, `commands/v-status.md:103`) runs from the project root, so the new default is
   right for them; no prose change is needed unless one of them runs from elsewhere (read each and fix only those).
7. **Written justification** (in the review record, not code): what stays and why: the `__file__`-relative sibling
   loads (plugin root, ADR rule 4), the two selftest-only repo derivations, `evals/lib/cv-fixture-lib.sh`'s
   `cv_plugin_root`, `hooks/lane-guard.sh:721-746` `project_roots` (it answers which run owns a path, a different
   question), and `compound-v-memory.py`'s `find_repo_root` fallback to its start directory (out of this triage's
   scope; recorded as a follow-up).

`compound-v-jev.py` is not touched: it takes `--repo` and derives nothing from `__file__` (1A constraint 13).

## Tests

- `compound-v-project-config.py --selftest`: explicit repo, git toplevel from a subdirectory, a worktree `.git` file,
  outside git raises.
- `compound-v-triage-outcomes.py --selftest` plus a test row: a copy of the script placed outside a fixture git repo,
  run from inside the repo with no `--stream`, appends to `<repo>/docs/superpowers/memory/triage-outcomes.jsonl` and
  writes nothing beside the copy; run outside any repo with no `--repo`, it exits non-zero and writes nothing. Fails on
  the old `_repo_root`.
- A row that greps `compound-v-preeval.py` and `compound-v-fastpath-materialize.py` for a hard-coded
  `triage-outcomes.jsonl` path outside selftests and fails if one appears.
- `validate-manifest`: a start path with no `.git` above yields no root and the caller's documented behaviour.
- Hooks: precompact-snapshot and brainstorm-trigger0-nudge started in a subdirectory resolve the same root as
  postcompact-resume; `run-band` test covers a subdirectory cwd.
- Existing suites stay green.

## Acceptance Criteria

1. Every test above passes and each fails when its change is reverted.
2. No script under `scripts/` derives a project root from `__file__` outside a selftest.
3. Full suite, `lint-frontmatter.py .`, `shellcheck hooks/*.sh` green.
