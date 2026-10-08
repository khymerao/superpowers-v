# Library audit - gate toolchain_artifacts and resolve-model config (2026-10-08)

Spec: `docs/superpowers/specs/2026-10-08-gate-toolchain-and-model-config-design.md`. Phase 1C. DEGRADED: WebFetch plus direct code reads. `ToolSearch` for `context7` returned no Context7 tool, and the harness reported `plugin:context7:context7` as needing OAuth (present, unauthorized), so it was not used. Bash was clamped to memory/git forms, so no script was run; every code claim below is from `Read`/`Grep` at the current tree.

V-memory: the supplied block was used. The `2026-10-05-jev-next-stage.md` hit ("Harness bugs reported by a downstream run") is the spec's origin and matches it. The 3.6.3 CHANGELOG hit is the origin of `toolchain_artifacts`. Agent memory (`drift-*.md`) held nothing on these topics and no directive.

## 1. Tools Available

- Context7: unauthorized (OAuth), not used. WebFetch: yes.
- Manifests: none relevant. The change touches two stdlib-only Python scripts (CONVENTIONS: stdlib only, 3.9 floor). No third-party dependency is introduced.

## 2. Libraries Mentioned

| Name | Spec context | Current (checked 2026-10-08) | Repo pin | Status |
|---|---|---|---|---|
| git `check-ignore` | the exemption's second condition, already in scope-check | stable, documented exit codes | n/a (system git) | OK |
| git `rev-parse --show-toplevel` | `resolve_project_root` | prints the linked worktree's own root | n/a | OK, see M2 |
| Python stdlib (`subprocess`, `importlib`, `json`) | both scripts | no drift; 3.9 floor is EOL (see `python-tooling.md`) | CI 3.9 | OK |

No npm/PyPI/crates library is named, so there is no staleness classification to make.

## 3. API Signatures Verified

| Claim in spec | Verdict |
|---|---|
| `run_scope_check` at `:742-756` passes `--preexisting` and never `--toolchain-artifact` | CONFIRMED. Called twice, `:1075` (missing receipt) and `:1176` (bound receipt); both need the globs. |
| the gate script does not mention `toolchain_artifacts` | CONFIRMED (grep: zero matches). |
| per-job gate passes the globs (`gate-receipt`, `:4436-4576`) | CONFIRMED: `_toolchain_artifacts_spec(manifest)` at `:4439`, forwarded at `:4569`. |
| `scope-check.py` accepts repeatable `--toolchain-artifact` (dest `toolchain_artifacts`) | CONFIRMED (`:734-741`). Forgiveness = glob match AND `git check-ignore` at gate time. |
| `load_config_models(args.config)` at `:553` reads nothing without the flag | CONFIRMED (`:412`: `if not config_path: return {}`). |
| `default_settings_paths(config_path, repo_dir)` at `:571` derives a project `.claude` | CONFIRMED, but its fallback is `<repo_dir or cwd>/.claude`, not the git root (see M2). |
| `resolve_project_root()` in `compound-v-project-config.py`, ADR 0005 rule 5 | CONFIRMED (`:123`). Explicit `repo` wins and must be a directory; otherwise `git rev-parse --show-toplevel`; raises `ValueError` outside a repo. |
| `git check-ignore` exit 0/1/128 | CONFIRMED live (git-scm.com/docs/git-check-ignore, 2026-10-08): 0 some ignored, 1 none, 128 fatal. Tracked files are never reported without `--no-index`. Matches scope-check `_check_ignore` (`:589`). |

## 4. Critical Findings

None.

## 5. High-Priority Findings

### H1. "The same parse the emitter uses, reused" cannot be an import of the emitter

`_toolchain_artifacts_spec` lives in `compound-v-emit-workflow.py` (`:2152`), a file of over 11,000 lines with module-level state. The integration gate deliberately avoids importing code it checks against: `run_scope_check` is a subprocess "so this script must not be able to perturb the matcher" (`:743-746`), and the gate hardens its one in-process load (`load_scope_matcher`, `:417-470`) with a private `sys.pycache_prefix` and a forged-`.pyc` selftest. Importing the emitter (or sibling modules) into the gate reopens the planted-bytecode class that `python-tooling.md` (2026-09-03) records as found-and-fixed in this exact file.

The spec's word "reused" has three possible readings and only two are safe:
- re-implement the 3-line rule in the gate and pin it with a parity selftest against the emitter's function (safe, but it is "re-implemented", contradicting the spec's wording);
- move the function to a leaf module both load through the hardened loader (safe, larger change, new lane);
- plain `importlib` of the emitter (NOT safe).

The rule to preserve exactly: list, non-empty, every entry a non-blank string, else `[]` (all-or-nothing, fails closed to "nothing declared"). A partial salvage would make the gate disagree with the validator and emitter, which is the `contradicted` failure this spec fixes.

### H2. `resolve-model` callers outside the CLI path, and the emitter, change behaviour silently

`emit-workflow.py:1861` only passes `--config` when the file exists, so with no config the emitter currently runs the resolver bare. After the change that bare call resolves the config from the resolver's own cwd's git toplevel, not from the emitter's `repo_root`. An emitter run whose cwd is another checkout (or a linked worktree) would read a different `compound-v.json` than the one it just looked for. Constraint: the emitter must pass `--repo-dir <its repo_root>` (or `--config`) explicitly. Same for `agents/parallel-dispatcher.md:150` (`[ -n "$CONFIG" ] && ...`). Also `compound-v-epic-arbiter.py:601,619` call `mod.load_config_models(config_path) if config_path else {}` in-process. They bypass `main()`, so the new default does not reach them; they keep the old bug unless the default lives inside `load_config_models` or they are changed. Decide and test which.

## 6. Medium Findings

### M1. Documentation states the old contract in four places
`compound-v-resolve-model.py:14` (docstring, "in the --config JSON, if present"), `agents/parallel-dispatcher.md:141-142` ("omit it to use built-in defaults"), `skills/compound-v/routing-policy.md:379-380` ("so the resolver works with no config file"), and the `--repo-dir` help text (`:539-545`, "default is --config's own directory ... else the current directory"). The help text will contradict the new rule.

### M2. Two roots in one resolver
`--repo-dir` today governs only the settings files (effort cap); a bare call from a subdirectory reads settings from `<cwd>/.claude`. The spec moves the models config to the git toplevel but leaves `_project_claude_dir` on cwd, so from a subdirectory the models table and the `maxEffortLevel` cap come from different directories. The spec's own test row ("from a subdirectory") would not catch it. Resolve both from one project root. `git rev-parse --show-toplevel` inside a linked worktree returns that worktree's own root (git-scm.com/docs/git-rev-parse, 2026-10-08; inferred from the definition, the page does not name worktrees), so a worktree only sees a config that is tracked or copied there. `.claude/compound-v.json` is present in this worktree today.

### M3. The new loader path adds an unhardened sibling import
`_project_config_module()` (`:379-399`) does a plain `exec_module` with no pycache protection, and the spec makes the no-flag default path (previously `{}` with no import) depend on it for `resolve_project_root`. If the module cannot load, `load_config_models` has an inline fallback but no `resolve_project_root` equivalent. Specify the fallback: git toplevel inline, or the built-in table with a stderr note. Do not silently skip.

### M4. Fixing the gate does not fix the cited downstream symptoms by itself
`.DS_Store`, `.phpunit.cache`, `.baseline` forgiveness requires the manifest to declare them in `toolchain_artifacts` AND `git check-ignore` to confirm they are ignored in the tree being gated; the validator rejects catch-alls (`validate-manifest.py:2441`). The re-derived tree at run-wide gate time (`gate_root`) is not necessarily the per-job worktree, so a path ignored there but absent here would not appear; one tracked-or-unignored in the project tree stays a violation. State this limit in the test: the "passes at run-wide" row must use a gitignored path in the gated tree.

## 7. Design Constraints for the Plan

MUST:
- pass every manifest `toolchain_artifacts` glob as a separate `--toolchain-artifact` on BOTH `run_scope_check` call sites (`:1075`, `:1176`), via the same all-or-nothing parse as `_toolchain_artifacts_spec`.
- keep `run_scope_check` a subprocess and keep `git check-ignore` as the second condition; never add a glob-only exemption in the gate.
- pin gate and emitter parse parity with a selftest row (valid list, bare string, list with blank entry, absent key).
- resolve the models config and the settings directory from one project root in `compound-v-resolve-model.py`.
- make the emitter (and any caller that omits `--config`) pass `--repo-dir` explicitly; decide and test whether `epic-arbiter`'s in-process `load_config_models` is covered.
- keep Python 3.9-safe code (no `match`, no `X | Y` at runtime), stdlib only.
- update the four documentation sites in M1 in the same change.
- justify in writing, per the spec, the outside-a-repo behaviour: fail closed per ADR 0005 unless a caller legitimately runs outside a repository.

MUST NOT:
- import `compound-v-emit-workflow.py` (or any lane-owned sibling) into the integration gate through plain `importlib`.
- treat a malformed `toolchain_artifacts` as partially valid.
- fall back to cwd as a guessed project root (ADR 0005, `resolve_project_root` docstring).

## 8. Open Questions for the Human

1. Is "reused, not re-implemented" satisfied by a duplicated 3-line function plus a parity test, or must the function move to a shared module?
2. Outside a git repository with no `--repo-dir`/`--config`: fail closed, or built-in table with a stderr note? Which callers run outside a repository (`/v:models` during init is the likely one)?
3. Should `epic-arbiter`'s in-process resolvers also honour the project config by default?

## 9. Knowledge Base Updates

Appended `## Updated 2026-10-08 - gate-toolchain-and-model-config-design` to `_knowledge-base/git-cli.md`. Agent memory: `drift-git-gate-and-resolver.md` plus a `MEMORY.md` pointer.
