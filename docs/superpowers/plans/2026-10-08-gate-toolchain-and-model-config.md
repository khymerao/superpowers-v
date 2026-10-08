# Gate toolchain_artifacts and resolve-model config Implementation Plan

> **For agentic workers:** executed by Compound V on Engine C from one manifest
> (`docs/superpowers/execution/2026-10-08-gate-toolchain-and-model-config/manifest.yaml`). Steps use checkbox (`- [ ]`) syntax.

**Goal:** the run-wide integration gate applies the manifest's `toolchain_artifacts` exactly as the per-job gate does,
and `resolve-model` without `--config` reads the project's config.

**Architecture:** one implementation job (both fixes touch `compound-v-emit-workflow.py`, so they share a lane), then a
deep review. **Spec:** `docs/superpowers/specs/2026-10-08-gate-toolchain-and-model-config-design.md` (amendments override the body). **Audits:**
`docs/superpowers/archaeology/2026-10-08-2026-10-08-gate-toolchain-and-model-config-design.md`, `docs/superpowers/library-audit/2026-10-08-2026-10-08-gate-toolchain-and-model-config-design.md`.

## Global Constraints

- Python 3.9 stdlib only. Every fix ships a test row that fails when reverted.
- The `toolchain_artifacts` reader lives once, in `scripts/compound-v-scope-check.py`; the emitter and the gate call
  it; no copy. The gate passes each glob as `--toolchain-artifact` in `run_scope_check`.
- Claims are limited to `contradicted` and false `blocked`; `.DS_Store`-style files stay violations unless declared.
- The gate test uses a direct job, a really gitignored file and a receipt made with `--toolchain-artifact`.
- resolve-model: the new default lives in `main()` only; one root for models and the effort cap; fail closed outside
  git, except `--explicit-model`. `resolve()` and `load_config_models` are unchanged for in-process callers.
- `resolve_job_model` in the emitter and `agents/parallel-dispatcher.md:150` pass `--repo-dir`.
- The five docs named in spec amendment 6 are updated in the same change.
- No version bump, CHANGELOG or release. Commit subjects are plain sentences, no Co-Authored-By trailer.

## Partition Map

| Job | Files (write) |
|---|---|
| `gate-model` | `scripts/compound-v-scope-check.py`, `scripts/compound-v-integration-gate.py`, `scripts/compound-v-emit-workflow.py`, `scripts/compound-v-resolve-model.py`, `tests/test-integration-gate.sh`, `tests/test-resolve-model.sh`, `agents/parallel-dispatcher.md`, `skills/compound-v/phase-3-parallel-opus-dispatch.md`, `skills/compound-v/routing-policy.md`, `skills/compound-v/execution-manifest.md` |
| `spec-review` | `docs/superpowers/dogfood/2026-10-08-gate-toolchain-and-model-config-review.md`, `.claude/agent-memory/superpowers-v-spec-reviewer/**` |

## Task A — gate-model

- [ ] **A1** tests first (spec Tests plus amendments 3 and 7; `tests/test-resolve-model.sh` is new if the resolver has
  no shell test); **A2** watch them fail; **A3** implement amendments 1, 4, 5, 6; **A4** green: selftests of
  scope-check, integration-gate, emit-workflow, resolve-model; `tests/test-integration-gate.sh`,
  `tests/test-engine-c-contract.sh`, `tests/test-resolve-model.sh`, `lint-frontmatter.py .`; **A5** revert checks;
  **A6** commit.
