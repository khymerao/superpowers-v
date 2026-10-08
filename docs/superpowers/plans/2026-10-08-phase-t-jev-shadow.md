# Phase T Jev Shadow Implementation Plan

> **For agentic workers:** executed by Compound V on Engine C from one manifest
> (`docs/superpowers/execution/2026-10-08-phase-t-jev-shadow/manifest.yaml`). Steps use checkbox (`- [ ]`) syntax.

**Goal:** `/v:triage` Phase T records the `t3` block and asks Jev the same T3 question in shadow; the hook and Phase T
build the request with one Python subcommand.

**Architecture:** One implementation job (Python subcommand, hook switch, command prose, tests), then a deep three-pass
review. The pieces are coupled through one builder, so they stay in one lane.

**Tech Stack:** Python 3.9 stdlib, bash hook, Markdown command prose, bash tests.

**Spec:** `docs/superpowers/specs/2026-10-08-phase-t-jev-shadow-design.md` (read its "Pre-flight amendments"; they
override the body).
**Audits:** `docs/superpowers/archaeology/2026-10-08-2026-10-08-phase-t-jev-shadow-design.md`,
`docs/superpowers/library-audit/2026-10-08-2026-10-08-phase-t-jev-shadow-design.md` (1B skipped: internal plumbing).

## Global Constraints

- Python 3.9 stdlib only; no `match`, no `X | Y` annotations. Every fix ships a test row that fails when reverted.
- `t3-request --repo R --request-env NAME --prompt-file P --context hook|offline`: request text only through the
  environment, never argv; empty request refused; config via `resolve_jev(load_project_config(repo))`; prints
  `{"status": "off", "reason": ...}` and writes nothing unless `jev.enabled` and `t3.mode` resolves to `shadow`
  (`active` coerced to `shadow`); otherwise the same JSON `build --point t3` prints.
- Extraction byte-equivalent to the hook's jq (`hooks/triage-prompt-nudge.sh:467-482`): codepoint cap 2,000, LAST
  `RESOLVED FILE PATHS` header, blank-line terminator, `(none resolved)` dropped from paths only, 20 paths, 40 hints.
  Caps imported from `compound-v-classify-request.py` where defined.
- Hook: `_write_t3_descriptor` calls `t3-request --context hook`; descriptor keys, gating and stdout unchanged; the
  prompt temp file removed on every exit path; `_T3_STATE_MAX_CHARS` removed; existing hook rows in
  `tests/test-native-points.sh` stay green, `cv-jev-state.*` asserts repointed to the new temp file, not deleted.
- Phase T prose (`commands/v-triage.md`): carry `t3_reason` from the first `needs_t3` result (default `unbanded`);
  re-invoke with `--t3-category` and `--t3-engine <claude|codex|parent>` (never with `backend: none` or a timeout);
  on a "DIFFERENT content" refusal re-run without `--t3-engine`, say so, skip the Jev step.
- Phase T Jev step, after T2 and before T3's commit, only when T3 decided: ToolSearch for
  `mcp__compound-v-vault__jev_classify`; `t3-request --context offline`; call the tool; a result that is not an
  absolute path to an existing file ends the step; `parse --mode shadow --request-file`; `unavailable` with `no_key`,
  `egress` or `disabled` deletes the request file and writes no pair; every other status runs `pair` with the carried
  category, backend and reason. Same `--repo` throughout. One-line report; never skips T3's commit. No response body
  or key in the transcript.
- `hooks/jev-t3.tsx` and the vault are not changed.
- No version bump, CHANGELOG or release. Commit subjects are plain sentences, no Co-Authored-By trailer.

## Partition Map

| Job | Files (write) |
|---|---|
| `phase-t-shadow` | `scripts/compound-v-jev.py`, `hooks/triage-prompt-nudge.sh`, `commands/v-triage.md`, `tests/test-native-points.sh`, `tests/test-jev-core.sh` |
| `spec-review` | `docs/superpowers/dogfood/2026-10-08-phase-t-jev-shadow-review.md`, `.claude/agent-memory/superpowers-v-spec-reviewer/**` |

No shared resources; no Task 0.

## Task A — phase-t-shadow

- [ ] **A1 Tests first.** `compound-v-jev.py --selftest`: `t3-request` state equals the expected bounded state on a
  fixture prompt (cap, last header, terminator, caps, `(none resolved)`); `off` for disabled and `t3.mode: off`;
  `active` coerced; empty request refused; argv never holds the request. A test in `tests/test-native-points.sh`
  runs the hook's old jq and the new subcommand on the same fixture and compares the state. A row in
  `tests/test-jev-core.sh` checks `commands/v-triage.md` for `--t3-engine` on the re-invocation and for
  `t3-request`, `jev_classify`, `parse --mode shadow`, `pair` in the Jev step, plus a planted-failure check; and runs
  the prose's re-invocation against a fixture repo to show a record with a `t3` block.
- [ ] **A2 Watch them fail.**
- [ ] **A3 Implement** the subcommand, the hook switch and the prose.
- [ ] **A4 Green.** `compound-v-jev.py --selftest`, `compound-v-preeval.py --selftest`, `tests/test-native-points.sh`,
  `tests/test-jev-core.sh`, `tests/test-jev-t3-mod.sh`, `lint-frontmatter.py .`, `shellcheck hooks/*.sh`.
- [ ] **A5 Revert checks** for each new row; restore.
- [ ] **A6 Commit** on the job's lane.

## Review Gate — spec-review

Three passes (SPEC, QUALITY, INTEGRATION) against the spec's AC and amendments, each run on the merged tree.
