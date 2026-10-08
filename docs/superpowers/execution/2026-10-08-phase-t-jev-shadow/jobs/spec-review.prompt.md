# Review Gate — deep, three passes against the spec, its amendments and AC-1..AC-5

Compound V run `2026-10-08-phase-t-jev-shadow`, job `spec-review`.

Your agent definition carries the three-pass Review Gate and a Step 0 (V-memory recall). HARD BUDGET of 40 tool calls; FIRST action after Step 0: create docs/superpowers/dogfood/2026-10-08-phase-t-jev-shadow-review.md with the section skeleton. Review the job against docs/superpowers/specs/2026-10-08-phase-t-jev-shadow-design.md (its amendments override the body) and the plan. Check in particular: the hook output and descriptor are unchanged; the request text never reaches argv; the no_key/egress/disabled branch writes no pair; a Jev-step failure cannot skip the record commit. Revert checks only in a scratch copy. Your memory directory is .claude/agent-memory/superpowers-v-spec-reviewer/. Run python with -B; register your lane with a literal --cwd. You are unattended: decide and return.

Prerequisites, already merged and COMMITTED into your base before this worktree was created: phase-t-shadow.

## You are unattended

No one reads this session while it runs and no one will answer a question:
a turn that ends by asking for confirmation, approval or a preference does
NOTHING, and the job is then recorded as an absent implementation. Decide
with the spec, the plan and this prompt; when they are silent, choose the
smallest change that meets the acceptance, do it, run the checks, and return.

## Write-allowed (your lane — anything else is a scope violation)

- `docs/superpowers/dogfood/2026-10-08-phase-t-jev-shadow-review.md`
- `.claude/agent-memory/superpowers-v-spec-reviewer/**`

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

- The review file exists with ## Recall, ## SPEC, ## QUALITY, ## INTEGRATION, ## Verdict; each AC run on the merged tree with command and output quoted; verdict APPROVED or ISSUES with a numbered list.

Turn cap: 80 (default for tier deep; default light 30 / standard 50 / deep 80). Plan to finish inside it.

## What you must NOT report

Do not report `blocked`, `files_changed` or `violations`. Those are
enforcement fields, they are derived from git by the caller, and a
constrained party filling in its own enforcement fields is the
fabricated-evidence pattern.
