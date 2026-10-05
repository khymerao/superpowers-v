# Library audit - Engine C re-finalize and lane guard (2026-10-05)

Spec: `docs/superpowers/specs/2026-10-05-engine-c-refinalize-and-lane-guard-design.md`

## 1. Tools Available

- Context7: ❌ DEGRADED: WebSearch/WebFetch only. `ToolSearch` for `context7` and for `resolve-library-id query-docs` both returned "No matching deferred tools"; the only server it named was a failed `tessl` connection. Context7 is genuinely absent from this run. No lookup below is attributed to Context7.
- WebFetch: ✅ (git-scm.com, devguide.python.org, github.com/koalaman/shellcheck).
- Bash: clamped to V-memory search and `git log|show|blame`; code was inspected with Read only.
- V-memory: the prompt carried a recall block (dogfood records, CHANGELOG, tech-context). None of it concerns library versions, so it is not used as evidence here.
- Dependency manifests: none. The repo has no package.json, pyproject.toml, requirements.txt, go.mod or Cargo.toml (consistent with every prior audit in this directory). The "dependencies" are the system toolchain.
- Trigger 0 recon: spec says `kb_skip`, so none exists.
- Memory consulted: `drift-jev-and-mods.md` (Jev/mods leads, not relevant to this spec). Existing KB files `git-cli.md`, `python-tooling.md`, `posix-shell-tooling.md` read first.

## 2. Libraries Mentioned

The spec adds no third-party library. Everything it names is a language runtime, a CLI, or a filesystem convention.

| Name | Spec context | Current | Repo pinned | Last release | Maintenance | Status |
|---|---|---|---|---|---|---|
| Python (stdlib only) | "Python 3.9 stdlib in Python code"; `subprocess` for `git merge-base`, `json` for `state.json` | 3.14 line (3.14.7, 2026-08-05; KB 2026-09-03). 3.11 is the oldest supported line | CI floor `python-version: '3.9'` (`.github/workflows/validate.yml`, per KB) | 3.9.25 final, EOL 2025-10-31 | 3.9 and, as of 2026-10-01, 3.10 are both EOL (devguide.python.org/versions, fetched 2026-10-05) | 🟡 MEDIUM, a known and deliberate floor, no new exposure |
| git `merge-base --is-ancestor` | `_already_integrated_wave` asks git whether the recorded commit is in HEAD | git 2.55.0 (2026-06-29, KB) | none declared | n/a | active | 🟢 OK |
| gitfile (`.git` as a file) | lane-guard boundary test: `.git` entry, "file or directory" | stable git layout | n/a | n/a | n/a | 🟢 OK |
| bash (hook, "as it is today") | boundary loop in `resolve_job` | macOS ships 3.2.57 (KB 2026-09-03) | n/a | n/a | frozen GPLv2 | 🟡 MEDIUM, see constraint |
| shellcheck | AC-3 `shellcheck hooks/*.sh` | v0.11.0, 2025-08-04 (fetched 2026-10-05, unchanged from KB) | CI apt copy is 0.9.0 on Ubuntu 24.04 (KB) | 2025-08-04 | active | 🟢 OK |

## 3. API Signatures Verified

| API | Spec use | Verified against | Result |
|---|---|---|---|
| `git merge-base --is-ancestor <commit> <commit>` | exit 0 means the recorded wave commit is an ancestor of HEAD | git-scm.com/docs/git-merge-base, fetched 2026-10-05: exit 0 true, exit 1 false, any other non-zero is an error (invalid object) | Signature current. Spec says "exits 0" and treats the rest as `None`; that is correct only if exit 1 AND error codes (128 for an unknown object) both fall through. See constraint 2. |
| Gitfile format | `.git` entry "file or directory" marks a separate working tree | git-scm.com/docs/gitrepository-layout, fetched 2026-10-05: gitfile is a plain-text `.git` holding `gitdir: <path>`, written by `git worktree` and `git submodule` | Current. Both worktrees and submodules produce a `.git` FILE, so the "file or directory" test covers both, and also treats a nested submodule as a boundary. |
| `subprocess.run` (3.9) | git call from `cmd_finalize_wave` | stdlib, long-stable; `capture_output=`, `check=`, `timeout=` all exist in 3.7+ | OK. `match`/`case` and `X \| Y` in `isinstance` remain 3.10+ and unprotected by `from __future__ import annotations` (KB 2026-09-03, still valid). |

No call in the spec has drifted.

## 4. Critical Findings 🔴

None.

## 5. High-Priority Findings 🟠

None.

## 6. Medium Findings 🟡

**M1. Python 3.9 floor is now two EOL lines behind.** 3.9 EOL 2025-10-31; 3.10 EOL 2026-10-01 per the devguide fetched today; oldest supported is 3.11. Not introduced by this spec, and the spec states the 3.9 constraint explicitly. Recorded because a locally newer interpreter will pass a 3.10+-only construct that CI's 3.9 job then rejects. Alternative if the floor is ever raised: 3.11 (supported to October 2027). Not a decision for this spec.

**M2. bash 3.2 floor for the hook, and shellcheck does not check it.** The spec says "bash in the hook as it is today", which is the right call. The directory-walk loop must not use bash 4+ features (`mapfile`, `declare -A`, `${var,,}`, namerefs). Shellcheck v0.11.0 has no bash-minor-version mode (koalaman/shellcheck#2850, KB 2026-09-03), so AC-3 "shellcheck clean" does not prove it. CI installs shellcheck 0.9.0 via apt, so local and CI results can differ.

**M3. `git merge-base --is-ancestor` has three outcomes, the spec describes two.** Exit 0 true, exit 1 false, other non-zero is an error. The spec's "else None" is safe only if the implementation treats every non-zero (and a subprocess failure or timeout) the same way. A truthiness shortcut such as `returncode != 1` would turn a git error into "ancestor". Row B (`"0"*40`) exercises the error path (exit 128), not the exit-1 path; row B therefore does not distinguish "not an ancestor" from "git failed". Neither is wrong for the spec, but the test claim "not in HEAD" is slightly off for a nonexistent object.

## 7. Design Constraints for the Plan

- MUST keep `_already_integrated_wave` to Python 3.9 stdlib: no `match`/`case`, no `isinstance(x, A | B)`, and `subprocess.run` keyword args only from the 3.7+ set.
- MUST treat the result as true only on `returncode == 0` exactly. Exit 1 (not ancestor), 128 (unknown object), a missing git binary (`OSError`/`FileNotFoundError`), and a timeout all return `None`.
- MUST run the git call against the run's repo explicitly (`git -C <repo_root>`, or `cwd=repo_root`), not the process cwd, because `finalize-wave` runs from a workflow transport whose cwd is not guaranteed to be the repo root.
- MUST pass the recorded commit as a single argv element and MUST validate it as a 40-hex (or at least non-empty, non-dash-prefixed) string before use, so a hand-edited `state.json` cannot inject an option. Validate rather than rely on a `--` separator, which this subcommand's documented synopsis does not show.
- MUST NOT use a shallow or `--depth` clone for AC-4's scratch clone. A shallow clone may not contain the wave commit, in which case git exits non-zero and the short-circuit correctly does not fire, which would fail AC-4 for the wrong reason.
- MUST write the lane-guard boundary walk in bash 3.2-compatible syntax (plain `while` and `[ -e "$d/.git" ]`; `-e`, not `-d`, so a gitfile counts). No `mapfile`, `declare -A`, namerefs or `[[ =~ ]]` with PCRE shorthands.
- MUST test `.git` with `-e` (or `-e` and `-L`), never `-d` alone: git worktrees and submodules write a `.git` FILE.
- MUST normalize `cwd` and `wt` the same way before the walk (same trailing-slash and symlink treatment the existing longest-prefix comparison uses), and terminate the loop on reaching `wt` or `/` so a `cwd` outside `wt` cannot loop forever.
- MUST NOT call `git` from the hook (the spec already says filesystem-only); that also keeps the hook inside its existing per-call latency and timeout bounds.
- MUST NOT treat "shellcheck clean" as evidence of bash 3.2 compatibility; AC-3 needs the plan to name a separate check or accept the gap.
- MUST NOT add 3.10+ syntax to `compound-v-emit-workflow.py`; its `--selftest` rows run under CI's 3.9 pin.

## 8. Open Questions for the Human

1. Row B uses a nonexistent commit (git exit 128). Do you also want a row where the commit exists but is not an ancestor of HEAD (exit 1)? Without it the `returncode == 0` strictness in constraint 2 is not pinned against an `!= 1` regression, and the repo rule says every behavioural change needs a row that fails when reverted.
2. Is a submodule checkout under a direct job's worktree meant to be a boundary too? The spec's "`.git` file or directory" rule makes it one. Say so explicitly if intended.

## 9. Knowledge Base Updates

- Appended `## Updated 2026-10-05 - engine-c-refinalize-and-lane-guard` to `docs/superpowers/library-audit/_knowledge-base/git-cli.md` (`--is-ancestor` exit codes, gitfile format).
- Appended a dated entry to `docs/superpowers/library-audit/_knowledge-base/python-tooling.md` (3.10 EOL 2026-10-01, oldest supported 3.11).
- Appended a dated entry to `docs/superpowers/library-audit/_knowledge-base/posix-shell-tooling.md` (shellcheck v0.11.0 re-confirmed 2026-10-05).
