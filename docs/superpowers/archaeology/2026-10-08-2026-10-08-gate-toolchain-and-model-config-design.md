# Gate toolchain_artifacts and resolve-model config - Code Archaeology

Spec: `docs/superpowers/specs/2026-10-08-gate-toolchain-and-model-config-design.md`. Checkout read 2026-10-08 (branch `jev-practical`).
V-memory recall: the prompt block was used. Its one useful hit is the downstream report in
`docs/superpowers/research/2026-10-05-jev-next-stage.md:119-129` (items 1 and 4, "Not yet reproduced here"; the cited
`docs/superpowers/execution/2026-10-06-multi-object-closeout.md` no longer exists in the tree, so the downstream evidence cannot be read, only the
two-line summary). A second search (`toolchain_artifacts integration gate re-derivation`) added only the 3.6.3 CHANGELOG entry and
`skills/compound-v/execution-manifest.md:256-303`. Context7 is not connected (auth required): there is no third-party API in this change, see section 4.

## 1. Matrix

### 1a. Integration gate: what decides a job's verdict (`compound-v-integration-gate.py`, `evaluate_job` :828-1256)

Dimensions: mode (`worktree` | `direct`, :894-899), receipt (`missing`/partial | `present`), sealed patch (`patch_sha256` recorded in the gate doc, :590-628), per-job gate verdict, re-derived verdict.

| mode | receipt | sealed patch | receipt verdict vs re-derived | outcome today | does the spec's change fix it? |
|---|---|---|---|---|---|
| any | missing/partial (:1068) | n/a | re-derive via `run_scope_check` :1075 | derived `blocked` => `blocked` (:1090). NOT `forged`. | Yes, if the glob is forwarded. |
| any | present, binding fault (digest, head, baseline, exit code, sealed patch) (:1124-1173) | any | never re-derived | `forged` or `stale`. No `run_scope_check` call at all. | **No.** `toolchain_artifacts` cannot reach this branch. |
| any | present, bindings hold (:1176) | none (pre-3.4 receipt, or any receipt without `patch_sha256`) | receipt `pass`, derived `blocked` (toolchain file seen only by the re-derivation) | `contradicted` (:1236) | Yes. |
| `worktree` | present, bindings hold | sealed, receipt `pass`, derived `blocked`, every violation absent from the sealed patch (:1203-1221) | same | already `pass` with a note. A gitignored path is never in the sealed patch (`git add -A` honours `.gitignore`). | Already handled; the change adds nothing here. |
| `direct` | present, bindings hold | sealed or not (:1203 requires `mode == "worktree"`) | receipt `pass`, derived `blocked` | `contradicted` | Yes. This and the no-sealed-patch cells are where the bug lives. |
| any | present, receipt `blocked`, derived `pass` | n/a | :1227-1235 absent-implementation rule | `blocked` | Unchanged. |

Cells the downstream report plausibly hit: `direct` mode (reviewer jobs), or a worktree job without a sealed patch. A fixture that uses a sealed worktree job passes on the old gate and proves nothing (constraint C4).

### 1b. `toolchain_artifacts` value shapes (the three parsers)

| value in manifest | validator (`compound-v-validate-manifest.py:2387-2447`) | emitter `_toolchain_artifacts_spec` (`compound-v-emit-workflow.py:2152-2167`) | integration gate today |
|---|---|---|---|
| absent / bare key (null) | valid | `[]` | `[]` (never reads it) |
| list of non-empty strings | valid | the list | ignored (**bug**) |
| list with any empty or non-string entry | invalid | `[]` (all-or-nothing, "fails closed into nothing declared") | ignored |
| bare string, catch-all (`**`), newline entry | invalid | `[]` | ignored |

The gate re-reads the manifest after `--manifest-digest` verification (:1287-1305), so a worker cannot widen the list; without `--manifest-digest` (hand CLI, selftest) the manifest is unverified exactly as `write_allowed` is.

### 1c. resolve-model config source (`compound-v-resolve-model.py:519-575`)

| caller | passes `--config` | passes `--repo-dir` | cwd | today | after the spec |
|---|---|---|---|---|---|
| emitter `resolve_job_model` (`emit-workflow.py:1831-1875`, config path from `abs_repo_root` :2356-2358) | only when `<repo>/.claude/compound-v.json` is a file | never | whatever the emitter ran in (`_run` :275 has no `cwd`) | models honoured when the file exists; built-in table otherwise | When the file is absent the CLI now runs `resolve_project_root()` from the emitter's cwd, which may be another repository or not a repository (see C7). |
| `agents/parallel-dispatcher.md:140-152`, `skills/compound-v/phase-3-parallel-opus-dispatch.md:168-180` | `[ -n "$CONFIG" ]`; `$CONFIG` is never assigned anywhere in the snippet | no | the dispatcher's session cwd | **this is the reported bug**: models ignored unless the agent invents `CONFIG` | Fixed, and the comment "omit it to use built-in defaults" becomes false. |
| `commands/v-models.md:348` | `--config .claude/compound-v.json` (relative to cwd) | no | project root by convention | unchanged | unchanged |
| in-process importers: `compound-v-classify-request.py:301-310,454-463`, `compound-v-epic-arbiter.py:597-620`, `compound-v-dashboard.py:931-990` | call `load_config_models(path)` / `resolve()` directly | n/a | n/a | pure, explicit path | **must stay unchanged** (C6) |

## 2. Shared State

**`config_models` (resolve-model `main`)**: set at `:553` from `load_config_models(args.config)`. `load_config_models` returns `{}` when `config_path` is falsy (:412-413) and, via `load_config_file` (project-config.py:101-116), when the file is missing. Nothing else sets it. A present-but-malformed file raises `ValueError` and `main` exits 2 (:554-556). After the change, a malformed project `compound-v.json` makes every flagless CLI call exit 2, where those calls used to succeed on built-in defaults.

**`settings_paths` (effort cap)**: `default_settings_paths(config_path=args.config, repo_dir=args.repo_dir)` (:571). `_project_claude_dir` (:249-260) uses the dir of `--config` when it ends in `.claude`, else `<repo_dir or os.getcwd()>/.claude`. Gap: if the spec derives the config from the project root but only passes the derived path to `load_config_models`, then from a subdirectory with no flags the config comes from `<root>/.claude/` and the `maxEffortLevel` cap files come from `<cwd>/.claude/`. Two different "project" directories in one invocation. The derived config path, or the root as `repo_dir`, must feed both.

**`manifest_toolchain_artifacts` (emitter `gate-receipt`)**: `_toolchain_artifacts_spec(manifest)` at `emit-workflow.py:4439`, passed to `_run_scope_check(..., toolchain_artifacts=...)` at :4567-4570. This is the value the per-job receipt was produced with. The gate has no equivalent variable: `evaluate_job(job, state_job, run_dir, repo_root, scope_check)` receives one job dict and never the manifest (called at :1332 from `evaluate_run`, which holds `manifest` at :1305). Nothing in the gate can see the top-level key unless it is threaded in.

**`preexisting` (gate)**: :1061-1065, prefers `<id>.verified.txt`, falls back to `<id>.txt`. Already aligned with the per-job gate (comment :1047-1060, dogfood 19). The toolchain list is the second exemption input that must get the same treatment: "the same list the gate used".

**`out["toolchain_artifacts"]`**: the per-job gate records what it forgave (`emit-workflow.py:4576`). The re-derivation's report (`evaluate_job` result dict, :831-841) has no such key, and `_violations_of` (:1259) reads only `violations`.

## 3. Sibling Code

**Sibling 1: the per-job gate's call (`emit-workflow.py` `_run_scope_check` :4276-4300 and `gate-receipt` :4436-4576).** Entry condition: always (the list is `[]` when none declared). Inputs: manifest (parsed via `_load_yaml`), `_toolchain_artifacts_spec`. Edge cases: all-or-nothing on a malformed list; flag repeated per glob; JSON `toolchain_artifacts` key in the verdict. The scope check itself (`scope-check.py:596-632`) forgives a path only when it matches a glob AND `git check-ignore` confirms it is ignored at that moment, evaluated against the same `changed` set. Latent: `check_ignore` runs at call time, so the per-job gate and the later re-derivation can disagree if `.gitignore`/exclude changes between them; the by-design answer is that `.gitignore` is a tracked file and is gated.

**Sibling 2: the gate's own `run_scope_check` (:742-783).** Subprocess on purpose ("this script must not be able to perturb the matcher"). Entry: called at :1075 (missing receipt) and :1176 (present receipt) with the identical argument list. Both call sites need the new argument. A third call exists only in the selftest helper `_honest_receipt` (:1579, positional, must keep working). Note it parses a verdict from stdout/stderr and falls back to the exit code (:780-782), so the new flag must not change exit semantics.

**Sibling 3: emitter vs gate import direction.** `emit-workflow.py:457-462` prefers to import `compute_diff_digest` FROM the gate. The spec says to read `toolchain_artifacts` using "the same parse the emitter uses, reused, not re-implemented". The only emitter implementation is the private `_toolchain_artifacts_spec` inside an 11k-line module. Importing the emitter from the gate is a circular dependency, and the gate hardens `sys.path` and loads siblings only by explicit path (:112-150, :1416-1426) because `scripts/` is a lane a job may write. The gate already has `load_manifest` (:315) which reuses the validator's loader. Neither the "import it" nor the "copy it" reading is free; this is an open design point the plan must settle (C2).

**Sibling 4: project-root resolution.** `compound-v-project-config.py:123-150` `resolve_project_root(repo=None, start=None)` is the ADR 0005 rule 5 implementation: explicit repo wins, else `git rev-parse --show-toplevel`, else `ValueError`. The gate already uses it (`integration-gate.py:1416-1451`, loaded by path, error to exit 2). `compound-v-resolve-model.py` already loads this module by path (`_project_config_module` :379-399), but with a silent `None` fallback "stays standalone-robust"; a silent fallback is the wrong behaviour for a fail-closed root rule. `compound-v-dashboard.py:949-971` is a third, divergent copy of "find the project's `.claude/compound-v.json`" (walks up 8 levels from the run dir, no git). Not in scope, but it is the ADR 0005 rule 5 violation the change will sit next to.

**Latent bug in sibling:** `resolve-model --help` for `--repo-dir` (:538-546) and the module docstring (:11-17, :49) state the old precedence. `load_config_models` docstring (:402-411) promises "missing file / absent models -> {}". Both go stale.

## 4. External APIs (via context7)

No third-party API is touched. The two contracts the change depends on are internal and were read in code:
- `git rev-parse --show-toplevel` (via `resolve_project_root`): in a linked worktree it returns the worktree root, not the main checkout. A `.claude/compound-v.json` that is gitignored (it is committed by design per `commands/v-init.md:644`, but a project may ignore it) is absent from a linked worktree, so a resolver run with a worktree cwd falls back to built-in defaults with no message.
- `git check-ignore` semantics for `--toolchain-artifact` (scope-check.py `_check_ignore`): unchanged.
Context7 MCP was not available in this session (authentication required); not needed here.

## 5. Regression Surface

| Path | If the new code is wrong, what breaks for existing users |
|---|---|
| `integration-gate.py` clean verdicts (`CLEAN`, tally, `render_human`) | Passing the glob list to the wrong job set (or forwarding it when the manifest list is malformed) lets a job's out-of-lane ignored write read `pass`. The exemption must stay as narrow as the per-job gate's. |
| `evaluate_job` signature | `evaluate_run` is the only caller, but the selftest calls `evaluate_run` ~40 times and `run_scope_check` positionally in `_honest_receipt` (:1579); a required new parameter breaks the selftest and `tests/test-integration-gate.sh`. |
| forged/stale path (:1124-1173) | Not reachable by this change; a fix that tries to "also fix forged" by re-deriving would reverse the "MISSING is re-derived, FORGED is refused" rule (CHANGELOG 2430, `tests/test-integration-gate.sh:282-299`). |
| `/v:dispatch` / `/v:resume` / finalize-wave | They branch on this gate's exit code and `integration` field (`emit-workflow.py` `cmd_finalize_wave`, `tests/test-engine-c-contract.sh`). A new stderr line or changed report shape must not alter exit codes. |
| `tests/test-project-root.sh:164-186,228-232` | Runs the gate from a project subdirectory and greps the gate's head (above the `# selftest` marker) for `dirname(here)`, `os.pardir`, `, ".."`, `dirname(HERE)`, `__file__`-derived roots. New gate code above the selftest must not match AC2. |
| `resolve-model` flagless CLI callers | Every flagless call now depends on cwd. A cwd outside git exits non-zero (fail closed) where today it printed the built-in model. Callers: dispatcher doc snippet, phase-3 snippet, any human, and the emitter when the project has no config file (C7). |
| `resolve-model` + malformed project config | A syntactically broken `.claude/compound-v.json` now turns a working flagless call into exit 2. `load_project_config` additionally rejects non-object `pre_eval`/`brainstorm`/`jev`; reusing it instead of `load_config_file` would make a resolve-model call fail because of an unrelated key. |
| in-process importers (classify-request, epic-arbiter, dashboard, validate-manifest `:1195-1204`) | If the default is implemented inside `load_config_models`/`resolve()` rather than `main()`, these all change behaviour and `resolve()` stops being "a pure function of its arguments" (docstring :361-364). |
| `resolve-model --selftest` (CI sweep, cwd = plugin repo root) | The plugin repo's own `.claude/compound-v.json` holds only `memory` keys. A selftest row that runs the CLI from the CWD instead of a fixture would read that file. Fixtures need their own `git init` and must not depend on the runner's cwd. |
| `effort_capped` output | If the root is derived but `repo_dir` is not passed to `default_settings_paths`, the `maxEffortLevel` cap changes source depending on cwd. |
| docs that tell the model what the flag does | `agents/parallel-dispatcher.md:141-142`, `skills/compound-v/phase-3-parallel-opus-dispatch.md:168-170`, `skills/compound-v/routing-policy.md:379-380`, `skills/compound-v/execution-manifest.md:150`, resolver docstring :11-17 and `--config`/`--repo-dir` help all describe "omit --config = built-in defaults". |

## 6. DRY Findings

| Area | Existing | Decision input |
|---|---|---|
| reading the manifest's `toolchain_artifacts` | validator `_validate_toolchain_artifacts` (rules), emitter `_toolchain_artifacts_spec` (all-or-nothing read). Gate: none. | Adding the gate's copy makes three. The emitter-import route is circular (Sibling 3). Either a tiny shared reader in a module both already load by path, or a documented byte-for-byte rule copy with a selftest row that pins the two to the same answers on the shapes in 1b. Silent divergence is the failure to prevent. |
| project root | `project-config.py:resolve_project_root` | Reuse it for resolve-model; do not add a fourth walk-up. The `_project_config_module()` None fallback must not swallow a root failure. |
| config file path | `project-config.py:config_path_for_repo`, `CONFIG_RELPATH` | Use these, not another `".claude", "compound-v.json"` literal (emitter :2356, validate-manifest :1197, dashboard :955 already carry copies). |
| config load + structural check | `load_config_file` / `get_models` (project-config.py:101-191); `load_config_models` is already a wrapper | Keep the wrapper; add the default in `main()` only. |
| `--toolchain-artifact` argv expansion | emitter `_run_scope_check` :4291-4294, four worker scripts | The gate's `run_scope_check` becomes the fifth expansion site; keep it a plain loop identical to :4293-4294. |

## 7. Design constraints for the spec

C1. The gate must forward `--toolchain-artifact <glob>` at BOTH `run_scope_check` call sites (missing-receipt :1075 and present-receipt :1176). One site fixed and one missed gives different verdicts for the same tree depending on receipt presence.
C2. The reader of the manifest list must match `_toolchain_artifacts_spec` exactly: a list, non-empty, every entry a non-empty string, else `[]` (all-or-nothing). It must not import `compound-v-emit-workflow.py` (circular with `emit-workflow.py:457`, and outside the gate's explicit-path loading discipline). The spec text "the same parse the emitter uses, reused" is not achievable as written; the plan must state which of "shared reader" or "copy pinned by a test" it takes.
C3. The list must come from the digest-verified manifest `evaluate_run` already loads (:1305), threaded into `evaluate_job` as an optional keyword defaulting to `[]`, never read from a result file, receipt or `state.json`.
C4. The gate test must fail on the old gate: it needs a `direct` job, or a worktree job whose gate doc has no `patch_sha256` (the existing `honest_receipt` helper in `tests/test-integration-gate.sh:147-161` produces no sealed patch). A sealed worktree fixture already passes today via :1203-1221. The file must be gitignored in the gated tree at re-derivation time (the sandbox repo has no `.gitignore` at `BASE`; use a per-case exclude or a committed `.gitignore` in the fixture) and the "honest" receipt must itself be produced with `--toolchain-artifact`, which the helper does not do (add a parameter). The negative row (glob absent from the manifest still caught) and a tracked/not-ignored file row (never forgiven) belong with it.
C5. The "forged" half of the downstream report is not covered. A missing receipt re-derives to `blocked`/`pass` (:1068-1101), never `forged`; `forged` is only produced by duplicate results (:854) or a binding fault (:1168), and `toolchain_artifacts` is never consulted on those branches. A gitignored file also cannot change `diff_digest` (`git add -A` honours `.gitignore`), so a digest fault from `.DS_Store` means it was not ignored, and `toolchain_artifacts` requires `git check-ignore`, so it would not forgive it. The spec's Problem 1 sentence "with a missing receipt, the job reads forged" is wrong against the code and the acceptance criteria must claim only `contradicted` and `blocked`. Whether the downstream `forged` verdicts are explained by this fix is UNKNOWN: the closeout document is gone.
C6. The resolve-model default lives in `main()` only. `load_config_models`, `resolve()` and `apply_effort_cap` stay pure (importers in section 1c depend on it).
C7. Every caller of the CLI that already knows the project must pass it. The emitter (`resolve_job_model`) must add `--repo-dir <abs_repo_root>` (or always pass `--config` for the file it checked), otherwise on a project with no `.claude/compound-v.json` the CLI roots itself from the emitter's cwd: another repository's models, or exit 1 outside git, turning "no config" into an emit failure (`resolve_job_model` returns an error for any non-zero rc, :1867-1868).
C8. When the root is derived, feed the same root to `default_settings_paths` (`repo_dir=root`), so the config and the `maxEffortLevel` caps come from one directory, from any subdirectory.
C9. Outside git with neither `--repo-dir` nor `--config` there is no caller that legitimately runs without a repository: the dispatcher, `/v:models`, phase-3 and the emitter all run against a project. The only no-project callers are `--selftest` and `--explicit-model`-only calls. Recommend fail closed per ADR 0005 rule 5, but the explicit-model case needs a decision: `--explicit-model` today resolves without touching config and should not start failing outside git (it never needs a config).
C10. A missing config file is the built-in table (as today). A present file with invalid JSON or a non-object `models` exits 2 with the existing error JSON; do not route through `load_project_config` (it rejects unrelated keys).
C11. The `resolve-model` selftest rows need real subprocess runs from fixture repos (`git init` in a tmpdir, as scope-check's selftest does) for: repo root, a subdirectory, `--repo-dir`, `--config` explicit still winning, no-config built-in, outside-git failure. The current selftest is in-process only. A fixture must not read the runner's cwd (the plugin repo has a `.claude/compound-v.json`).
C12. Update every document that says "omit --config for built-in defaults" (section 5 last row) in the same change; `tests/` has no row pinning them, so nothing catches the drift automatically. CHANGELOG and version follow the repository's release convention.
C13. Note, outside the spec: the CLI `--stance` default stays `balanced`, while `.claude/compound-v.json` can carry a `stance` that the dashboard reads (`compound-v-dashboard.py:961`). After this change the CLI reads the project's `models` but not its `stance`. Decide explicitly that this stays out of scope.
C14. Reproduction claim in the spec (prints `sonnet`, flags or not) is consistent with code: `load_config_models(args.config)` at :553 with `args.config=None` returns `{}`, and `--repo-dir` only affects `settings_paths`. Not executed here (shell clamped).

## 8. File Touch Map (for Phase 2 partitioning)

| File | Change | Flag |
|---|---|---|
| `scripts/compound-v-integration-gate.py` | thread `toolchain_artifacts` into `evaluate_job` and `run_scope_check`, both call sites; selftest rows | |
| `scripts/compound-v-resolve-model.py` | `main()` default config and `repo_dir`; docstring/help; selftest rows | |
| `scripts/compound-v-emit-workflow.py` | `resolve_job_model` passes `--repo-dir` (C7); its own selftest rows at ~10305 | SHARED RESOURCE: 11k-line file, many partitions touch it |
| `tests/test-integration-gate.sh` | new `toolchain_artifacts` rows and helper parameter | |
| `agents/parallel-dispatcher.md` | rewrite the `--config` comment/snippet (:141-152) | |
| `skills/compound-v/phase-3-parallel-opus-dispatch.md` | same (:168-180) | |
| `skills/compound-v/routing-policy.md` | precedence text (:377-382) | |
| `skills/compound-v/execution-manifest.md` | `toolchain_artifacts` section (:256-303) should state the run-wide gate honours it; :150 `--config` sentence | |
| `scripts/compound-v-project-config.py` | read-only reuse (`resolve_project_root`, `config_path_for_repo`); no change expected | |
| `CHANGELOG.md` | release note | SHARED RESOURCE (release/changelog ordering) |
| `tests/test-project-root.sh` | no edit expected; its AC2 grep constrains new gate code | |
