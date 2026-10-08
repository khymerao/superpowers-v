# Task A — t3-request builder, hook switch, Phase T t3 block and Jev shadow step

Compound V run `2026-10-08-phase-t-jev-shadow`, job `phase-t-shadow`.

Implement Task A of docs/superpowers/plans/2026-10-08-phase-t-jev-shadow.md, every step in order (A1..A6). Read the spec docs/superpowers/specs/2026-10-08-phase-t-jev-shadow-design.md, especially its Pre-flight amendments, and both audits (section 7) first; they and the plan Global Constraints bind. Tests first. Touch only your lane. Run python with -B; register your lane with a literal --cwd. You are unattended: decide and return.

## You are unattended

No one reads this session while it runs and no one will answer a question:
a turn that ends by asking for confirmation, approval or a preference does
NOTHING, and the job is then recorded as an absent implementation. Decide
with the spec, the plan and this prompt; when they are silent, choose the
smallest change that meets the acceptance, do it, run the checks, and return.

## Write-allowed (your lane — anything else is a scope violation)

- `scripts/compound-v-jev.py`
- `hooks/triage-prompt-nudge.sh`
- `commands/v-triage.md`
- `tests/test-native-points.sh`
- `tests/test-jev-core.sh`

## Global constraints (binding on every job)

Project-wide, and binding on EVERY job in this run including yours.
Copied verbatim from the plan — do not reinterpret, relax or widen
them.

- Python 3.9 stdlib only; no `match`, no `X | Y` annotations. Every fix ships a test row that fails when reverted.
- `t3-request --repo R --request-env NAME --prompt-file P --context hook|offline`: request text only through the environment, never argv; empty request refused; config via `resolve_jev(load_project_config(repo))`; prints `{"status": "off", "reason": ...}` and writes nothing unless `jev.enabled` and `t3.mode` resolves to `shadow` (`active` coerced to `shadow`); otherwise the same JSON `build --point t3` prints.
- Extraction byte-equivalent to the hook's jq (`hooks/triage-prompt-nudge.sh:467-482`): codepoint cap 2,000, LAST `RESOLVED FILE PATHS` header, blank-line terminator, `(none resolved)` dropped from paths only, 20 paths, 40 hints. Caps imported from `compound-v-classify-request.py` where defined.
- Hook: `_write_t3_descriptor` calls `t3-request --context hook`; descriptor keys, gating and stdout unchanged; the prompt temp file removed on every exit path; `_T3_STATE_MAX_CHARS` removed; existing hook rows in `tests/test-native-points.sh` stay green, `cv-jev-state.*` asserts repointed to the new temp file, not deleted.
- Phase T prose (`commands/v-triage.md`): carry `t3_reason` from the first `needs_t3` result (default `unbanded`); re-invoke with `--t3-category` and `--t3-engine <claude|codex|parent>` (never with `backend: none` or a timeout); on a "DIFFERENT content" refusal re-run without `--t3-engine`, say so, skip the Jev step.
- Phase T Jev step, after T2 and before T3's commit, only when T3 decided: ToolSearch for `mcp__compound-v-vault__jev_classify`; `t3-request --context offline`; call the tool; a result that is not an absolute path to an existing file ends the step; `parse --mode shadow --request-file`; `unavailable` with `no_key`, `egress` or `disabled` deletes the request file and writes no pair; every other status runs `pair` with the carried category, backend and reason. Same `--repo` throughout. One-line report; never skips T3's commit. No response body or key in the transcript.
- `hooks/jev-t3.tsx` and the vault are not changed.
- No version bump, CHANGELOG or release. Commit subjects are plain sentences, no Co-Authored-By trailer.

## Read-allowed (advisory — git cannot enforce reads)

- `**`

## Acceptance (your definition of done)

- All new rows pass and each fails when its change is reverted; compound-v-jev.py and compound-v-preeval.py selftests, test-native-points.sh, test-jev-core.sh, test-jev-t3-mod.sh, lint-frontmatter and shellcheck green.

Turn cap: 80 (default for tier deep; default light 30 / standard 50 / deep 80). Plan to finish inside it.

## What you must NOT report

Do not report `blocked`, `files_changed` or `violations`. Those are
enforcement fields, they are derived from git by the caller, and a
constrained party filling in its own enforcement fields is the
fabricated-evidence pattern.
