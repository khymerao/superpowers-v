# Fix Run B2 Implementation Plan

> **For agentic workers:** executed by Compound V on Engine C from one manifest
> (`docs/superpowers/execution/2026-10-08-project-root-run-b2/manifest.yaml`). Steps use checkbox (`- [ ]`) syntax.

**Goal:** close run B's review issues 1 and 3: integration-gate and update-memory take the project root from
`resolve_project_root`, and validate-manifest's no-root note is true.

**Architecture:** one fix job minted from review findings (effort medium), then a deep review.

**Spec:** `docs/superpowers/specs/2026-10-08-project-root-run-b2-design.md`. **Decision:** ADR 0005 rules 5-6.

## Global Constraints

- Python 3.9 stdlib only. Every fix ships a test row that fails when reverted.
- Use the existing `resolve_project_root(repo=None, start=None)` in `scripts/compound-v-project-config.py`; do not add a
  second helper and do not change it.
- integration-gate: no `__file__`-derived repo root; explicit `--repo-root` unchanged (Engine C passes it); outside git
  with no flag: error JSON, exit 2.
- update-memory: no `__file__`-derived outcomes path; `compound-v-triage-outcomes.py`'s sibling import keeps working.
- validate-manifest: the note is true for manifests with and without a `fast_path` block.
- Command prose is not changed (its callers run from the project root).
- No version bump, CHANGELOG or release. Commit subjects are plain sentences, no Co-Authored-By trailer.

## Partition Map

| Job | Files (write) |
|---|---|
| `b2-fix` | `scripts/compound-v-integration-gate.py`, `scripts/compound-v-update-memory.py`, `scripts/compound-v-validate-manifest.py`, `tests/test-project-root.sh` |
| `spec-review` | `docs/superpowers/dogfood/2026-10-08-project-root-run-b2-review.md`, `.claude/agent-memory/superpowers-v-spec-reviewer/**` |

## Task A — b2-fix

- [ ] **A1 Tests first** (spec Tests). **A2** watch them fail. **A3** implement items 1-3. **A4** green: the three
  scripts' selftests, `compound-v-triage-outcomes.py --selftest`, `tests/test-project-root.sh`, the full suite.
  **A5** revert checks. **A6** commit.
