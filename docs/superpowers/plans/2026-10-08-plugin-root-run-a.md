# Plugin Root Run A Implementation Plan

> **For agentic workers:** executed by Compound V on Engine C from one manifest
> (`docs/superpowers/execution/2026-10-08-plugin-root-run-a/manifest.yaml`). Steps use checkbox (`- [ ]`) syntax.

**Goal:** every Markdown entry point takes the plugin root from the harness substitution of `${CLAUDE_PLUGIN_ROOT}`,
with one guarded `$PWD` fallback; `hooks/session-banner.sh` never falls back to `.`.

**Architecture:** one implementation job (38 mechanical edits share one canonical block and one test, so they cannot
be split without the test failing in each half), then a deep three-pass review.

**Spec:** `docs/superpowers/specs/2026-10-08-plugin-root-run-a-design.md`. **Decision:** `docs/superpowers/adr/0005-one-rule-per-root.md`.
**Audits:** `docs/superpowers/archaeology/2026-10-08-2026-10-08-plugin-root-resolver-design.md`,
`docs/superpowers/library-audit/2026-10-08-2026-10-08-plugin-root-resolver-design.md`.

## Global Constraints

- The three canonical lines are exactly those in the spec, byte-for-byte, in all 38 files, replacing the old two (the
  `evals/README.md` copy had a shorter second line; it gets the same three).
- Live evidence (2026-10-08, Claude Code 2.1.294, `--plugin-dir`): the bare `${CLAUDE_PLUGIN_ROOT}` is substituted in
  command, skill and agent bodies; `${CLAUDE_PLUGIN_ROOT:-...}` is not. Do not use the `:-` form anywhere in these files.
- No cache scan, no `claude plugin list`, no marketplace name, no `~/.claude/plugins` path in the canonical lines.
- `evals/lib/cv-fixture-lib.sh` is not changed; `evals/README.md` explains the new rule and that under `claude plugin
  eval` `CV` is the substituted plugin source.
- `hooks/session-banner.sh`: `CLAUDE_PLUGIN_ROOT`, else the directory above the hook script; the banner's output is
  otherwise unchanged and it still fails silent.
- `tests/test-plugin-root.sh` is executable and shellcheck-clean; each row fails when its change is reverted.
- Project-root code (ADR 0005 rules 5-8) is not touched: that is run B.
- No version bump, CHANGELOG or release. Commit subjects are plain sentences, no Co-Authored-By trailer.

## Partition Map

| Job | Files (write) |
|---|---|
| `plugin-root` | the 38 files listed in the manifest, `hooks/session-banner.sh`, `tests/test-plugin-root.sh` |
| `spec-review` | `docs/superpowers/dogfood/2026-10-08-plugin-root-run-a-review.md`, `.claude/agent-memory/superpowers-v-spec-reviewer/**` |

No shared resources; no Task 0.

## Task A — plugin-root

- [ ] **A1 Test first.** Write `tests/test-plugin-root.sh` rows (a)-(d) from the spec.
- [ ] **A2 Watch it fail** on the current tree.
- [ ] **A3 Replace** the resolver lines in the 38 files and rewrite the surrounding prose per the spec; fix
  `hooks/session-banner.sh`.
- [ ] **A4 Green.** `bash tests/test-plugin-root.sh`, `lint-frontmatter.py .`, `shellcheck hooks/*.sh tests/test-plugin-root.sh`,
  and the tests that read these files (`tests/test-*.sh` that grep commands or agents).
- [ ] **A5 Revert checks** per row; restore.
- [ ] **A6 Commit** on the job's lane.

## Review Gate — spec-review

Three passes against the spec's AC and the ADR, each on the merged tree.
