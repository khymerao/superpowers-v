# detect_ui Noul Criteria Implementation Plan

> **For agentic workers:** executed by Compound V on Engine C from one manifest
> (`docs/superpowers/execution/2026-10-08-detect-ui-noul-criteria/manifest.yaml`). Steps use checkbox (`- [ ]`) syntax.

**Goal:** the `detect_ui` Noul question sends `criteria` as `{"true": ..., "false": ...}`, the shape the System One API
accepts (proven live 2026-10-08).

**Architecture:** one implementation job, then a deep review. **Spec:** `docs/superpowers/specs/2026-10-08-detect-ui-noul-criteria-design.md` (its
amendments override the body). **Audits:** `docs/superpowers/archaeology/2026-10-08-2026-10-08-detect-ui-noul-criteria-design.md`,
`docs/superpowers/library-audit/2026-10-08-2026-10-08-detect-ui-noul-criteria-design.md`.

## Global Constraints

- Change only `NOUL_CRITERIA` (`scripts/compound-v-jev.py:111`) to an object with string keys `true` and `false`; the
  `false` text keeps the exclusions (build scripts, documentation tooling, tests, data files).
- Do not touch the Choice branch of `questions_for`, `_request_meta`, `_parse_answer` or the vault.
- Selftest row over `questions_for(catalogue_entry(p, v))` for every point and variant: a `noul` question's `criteria`
  is absent or an object whose keys are a subset of `{"true", "false"}` with non-empty string values; it fails on the
  string form. No hand-typed catalogue hash.
- Python 3.9 stdlib only. No version bump, CHANGELOG or release. Commit subjects are plain sentences, no Co-Authored-By trailer.

## Partition Map

| Job | Files (write) |
|---|---|
| `noul` | `scripts/compound-v-jev.py` |
| `spec-review` | `docs/superpowers/dogfood/2026-10-08-detect-ui-noul-criteria-review.md`, `.claude/agent-memory/superpowers-v-spec-reviewer/**` |

## Task A — noul

- [ ] **A1** selftest row first; **A2** watch it fail; **A3** change `NOUL_CRITERIA`; **A4** green:
  `compound-v-jev.py --selftest`, `tests/test-jev-core.sh`, `tests/test-native-points.sh`; **A5** revert check; **A6** commit.
