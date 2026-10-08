# Review Gate — deep, three passes against the spec, its amendments and AC-1..AC-4

Compound V run `2026-10-08-t3-measurement-and-eval`, job `spec-review`.

Your agent definition carries the three-pass Review Gate and a Step 0 (V-memory recall). HARD BUDGET of 40 tool calls; FIRST action after Step 0: create docs/superpowers/dogfood/2026-10-08-t3-measurement-and-eval-review.md with the section skeleton. Review against docs/superpowers/specs/2026-10-08-t3-measurement-and-eval-design.md (amendments override). Check: the trust rule; total_cost_usd never stored; null not 0; hook stdout and two tab fields unchanged; no request text in pairs or results; the frozen digest excludes labels; the report decides on human_label only and says not decidable when labels are missing. Revert checks only in a scratch copy. Your memory directory is .claude/agent-memory/superpowers-v-spec-reviewer/; keep memory frontmatter valid YAML. Run python with -B; register your lane with a literal --cwd. You are unattended: decide and return.

Prerequisites, already merged and COMMITTED into your base before this worktree was created: measure-eval.

## You are unattended

No one reads this session while it runs and no one will answer a question:
a turn that ends by asking for confirmation, approval or a preference does
NOTHING, and the job is then recorded as an absent implementation. Decide
with the spec, the plan and this prompt; when they are silent, choose the
smallest change that meets the acceptance, do it, run the checks, and return.

## Write-allowed (your lane — anything else is a scope violation)

- `docs/superpowers/dogfood/2026-10-08-t3-measurement-and-eval-review.md`
- `.claude/agent-memory/superpowers-v-spec-reviewer/**`

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

- The review file exists with ## Recall, ## SPEC, ## QUALITY, ## INTEGRATION, ## Verdict; each AC run on the merged tree with command and output quoted; verdict APPROVED or ISSUES with a numbered list.

Turn cap: 80 (default for tier deep; default light 30 / standard 50 / deep 80). Plan to finish inside it.

## What you must NOT report

Do not report `blocked`, `files_changed` or `violations`. Those are
enforcement fields, they are derived from git by the caller, and a
constrained party filling in its own enforcement fields is the
fabricated-evidence pattern.
