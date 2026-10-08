# Task A — Claude classify measure in shadow pairs; frozen human-labelled T3 eval

Compound V run `2026-10-08-t3-measurement-and-eval`, job `measure-eval`.

Implement Task A of docs/superpowers/plans/2026-10-08-t3-measurement-and-eval.md (A1..A6). Read the spec docs/superpowers/specs/2026-10-08-t3-measurement-and-eval-design.md and its Pre-flight amendments, and both audits (section 7) first. Tests first. Make no live Claude or Jev call. Touch only your lane. Run python with -B; register your lane with a literal --cwd. You are unattended: decide and return.

## You are unattended

No one reads this session while it runs and no one will answer a question:
a turn that ends by asking for confirmation, approval or a preference does
NOTHING, and the job is then recorded as an absent implementation. Decide
with the spec, the plan and this prompt; when they are silent, choose the
smallest change that meets the acceptance, do it, run the checks, and return.

## Write-allowed (your lane — anything else is a scope violation)

- `scripts/compound-v-classify-request.py`
- `scripts/compound-v-jev.py`
- `hooks/triage-prompt-nudge.sh`
- `hooks/jev-t3.tsx`
- `hooks/jev-t3.test.tsx`
- `types/index.d.ts`
- `commands/v-triage.md`
- `tests/test-native-points.sh`
- `tests/test-jev-core.sh`
- `tests/fixtures/jev-t3-corpus.jsonl`

## Global constraints (binding on every job)

Project-wide, and binding on EVERY job in this run including yours.
Copied verbatim from the plan — do not reinterpret, relax or widen
them.

- Python 3.9 stdlib only. Every change ships a test row that fails when reverted.
- Trust the JSON result only when `type == "result"`, `subtype == "success"`, `is_error` is false and `result` is a string; otherwise today's `parse_category(raw)` with null measure fields. Never store or print `total_cost_usd`. Token fields from `usage` (main loop), absent -> `null`. Prompt stays the first positional after `-p`; no `--bare`; never Haiku.
- `_classify_headless` keeps two tab fields; the measure travels separately; descriptor gains one string key `claude_measure`; pinned key-set tests updated; `pair --claude-measure-json` optional; no request text in any pair or results line.
- Frozen protocol digest over `id`, `request`, `paths`, `hints` only; records both resolved model ids.
- 6 Jev calls per row (base x3 + 3 variants x1); report keyed by `(id, variant, repeat)`.
- Agreement and inversions vs `human_label` only; "not decidable" below 80 human labels.
- Eval files under the Jev data dir's `eval/` subdirectory, skipped by the prune.
- `--merge-human` reads `docs/superpowers/research/2026-10-08-jev-t3-labelling-sheet.md` (codes `p m M u`), refusing unknown codes or missing rows; it does not run in this job (no labels yet).
- Hook stdout unchanged. No version bump, CHANGELOG or release. Commit subjects are plain sentences, no Co-Authored-By trailer.

## Read-allowed (advisory — git cannot enforce reads)

- `**`

## Acceptance (your definition of done)

- AC-1..AC-3 rows pass and each fails on revert; the selftests, hook tests, test-jev-core, test-jev-t3-mod, lint and shellcheck green; no live call made.

Turn cap: 80 (default for tier deep; default light 30 / standard 50 / deep 80). Plan to finish inside it.

## What you must NOT report

Do not report `blocked`, `files_changed` or `violations`. Those are
enforcement fields, they are derived from git by the caller, and a
constrained party filling in its own enforcement fields is the
fabricated-evidence pattern.
