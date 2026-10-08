# T3 Measurement and Eval Implementation Plan

> **For agentic workers:** executed by Compound V on Engine C from one manifest
> (`docs/superpowers/execution/2026-10-08-t3-measurement-and-eval/manifest.yaml`). Steps use checkbox (`- [ ]`) syntax.

**Goal:** measure the headless Claude T3 classify beside Jev in every shadow pair, and extend `eval --t3` so a frozen,
human-labelled eval can decide spec 1.5.

**Architecture:** one implementation job (the measure flows classify -> hook/descriptor -> module -> pair, and the eval
lives in the same script), then a deep review. **Spec:** `docs/superpowers/specs/2026-10-08-t3-measurement-and-eval-design.md` (amendments override).
**Audits:** `docs/superpowers/archaeology/2026-10-08-2026-10-08-t3-measurement-and-eval-design.md`, `docs/superpowers/library-audit/2026-10-08-2026-10-08-t3-measurement-and-eval-design.md`.

## Global Constraints

- Python 3.9 stdlib only. Every change ships a test row that fails when reverted.
- Trust the JSON result only when `type == "result"`, `subtype == "success"`, `is_error` is false and `result` is a
  string; otherwise today's `parse_category(raw)` with null measure fields. Never store or print `total_cost_usd`.
  Token fields from `usage` (main loop), absent -> `null`. Prompt stays the first positional after `-p`; no `--bare`;
  never Haiku.
- `_classify_headless` keeps two tab fields; the measure travels separately; descriptor gains one string key
  `claude_measure`; pinned key-set tests updated; `pair --claude-measure-json` optional; no request text in any pair or
  results line.
- Frozen protocol digest over `id`, `request`, `paths`, `hints` only; records both resolved model ids.
- 6 Jev calls per row (base x3 + 3 variants x1); report keyed by `(id, variant, repeat)`.
- Agreement and inversions vs `human_label` only; "not decidable" below 80 human labels.
- Eval files under the Jev data dir's `eval/` subdirectory, skipped by the prune.
- `--merge-human` reads `docs/superpowers/research/2026-10-08-jev-t3-labelling-sheet.md` (codes `p m M u`), refusing
  unknown codes or missing rows; it does not run in this job (no labels yet).
- Hook stdout unchanged. No version bump, CHANGELOG or release. Commit subjects are plain sentences, no Co-Authored-By trailer.

## Partition Map

| Job | Files (write) |
|---|---|
| `measure-eval` | `scripts/compound-v-classify-request.py`, `scripts/compound-v-jev.py`, `hooks/triage-prompt-nudge.sh`, `hooks/jev-t3.tsx`, `hooks/jev-t3.test.tsx`, `types/index.d.ts`, `commands/v-triage.md`, `tests/test-native-points.sh`, `tests/test-jev-core.sh`, `tests/fixtures/jev-t3-corpus.jsonl` |
| `spec-review` | `docs/superpowers/dogfood/2026-10-08-t3-measurement-and-eval-review.md`, `.claude/agent-memory/superpowers-v-spec-reviewer/**` |

## Task A — measure-eval

- [ ] **A1** tests first (spec AC 1-3 with the amendments); **A2** watch them fail; **A3** implement measurement
  (classify, hook, module, Phase T prose, pair) then the eval (`--freeze`, `--label-claude`, `--merge-human`,
  `--prepare`, report sections); **A4** green: selftests of classify-request, jev, preeval;
  `tests/test-native-points.sh`, `tests/test-jev-core.sh`, `tests/test-jev-t3-mod.sh`, `lint-frontmatter.py .`,
  `shellcheck hooks/*.sh`; **A5** revert checks; **A6** commit. Do not run `--label-claude` or any live call.
