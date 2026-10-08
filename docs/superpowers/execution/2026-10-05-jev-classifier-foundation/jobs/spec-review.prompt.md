# Review Gate — three passes against the spec (amendments first) and AC-1..AC-6

Compound V run `2026-10-05-jev-classifier-foundation`, job `spec-review`.

Your agent definition carries the three-pass Review Gate and a Step 0 (V-memory recall). Follow it within a HARD BUDGET of 60 tool calls; FIRST action after Step 0: create docs/superpowers/dogfood/2026-10-05-jev-classifier-foundation-review.md with the section skeleton and fill it as you verify. Review the eight implementation jobs against docs/superpowers/specs/2026-10-05-jev-classifier-foundation-design.md (its Plan-review amendments section overrides earlier sections) and the plan's Task H. Your memory directory is .claude/agent-memory/superpowers-v-spec-reviewer/. Run python with -B; register your lane with a literal --cwd. You are unattended: decide and return.

Prerequisites, already merged and COMMITTED into your base before this worktree was created: record-t3, config-jev, jev-core, vault, ui-floor-onboard-jev, corpus, t3-hook-shadow, t3-mod-shadow.

## You are unattended

No one reads this session while it runs and no one will answer a question:
a turn that ends by asking for confirmation, approval or a preference does
NOTHING, and the job is then recorded as an absent implementation. Decide
with the spec, the plan and this prompt; when they are silent, choose the
smallest change that meets the acceptance, do it, run the checks, and return.

## Write-allowed (your lane — anything else is a scope violation)

- `docs/superpowers/dogfood/2026-10-05-jev-classifier-foundation-review.md`
- `.claude/agent-memory/superpowers-v-spec-reviewer/**`

## Global constraints (binding on every job)

Project-wide, and binding on EVERY job in this run including yours.
Copied verbatim from the plan — do not reinterpret, relax or widen
them.

- Python 3.9 syntax, stdlib only; no `typesafe_sdk`; no `match`; no `X | Y` annotations.
- Never Haiku. Jev is not a Claude tier and never appears in a manifest `tier`.
- The OpenRouter key exists only in the vault plugin: secure storage, `options`, the `$.http.fetch` header. Never in a Python process, an env var, argv, a file, a log line, a tool result or the transcript.
- The vault never answers a Bash tool call; `lane-guard.sh` and permission prompts stay in force.
- Request text never in argv. Local Jev data lives in `~/.claude/compound-v-jev/<repo-digest>/` (dir 0700, files 0600; `<repo-digest>` = first 16 hex of sha256 of the repo's absolute real path); retention 30 days, pruned on write. Nothing Jev-related is written under the repository except the corpus fixture and the code.
- Error bodies from OpenRouter carry the account's `user_id`: never copy any part of an error body anywhere; record only the status class.
- `t3.mode` is `off|shadow` in spec 1. The triage decision, the record's tier and every existing hook output are byte-identical to today on every existing fixture.
- Model pinned `typesafe/jev-1.13`; record the resolved id the response returns (live: `typesafe/jev-1.13-20260917`).
- No fabricated metrics: `latency_ms` measured; `usage.cost` dropped; no cost or savings text (anti-ruflo regex, `.github/workflows/validate.yml:194`).
- Every behavioural change ships a selftest/test row that fails when the change is reverted.
- Docs: plain words, every claim true of HEAD, no line over 200 characters outside code/tables.
- Lane discipline: touch only your `write_allowed`; `register-lane` first, with a literal `--cwd`.
- Names fixed by the Interfaces below; do not rename. Commit subjects are plain sentences, no `feat:`/`fix:`.
- Not in any implementation job: version bump, CHANGELOG, marketplace entry, `.gitignore`, release (Task R).

## Read-allowed (advisory — git cannot enforce reads)

- `**`

## Acceptance (your definition of done)

- The review file exists with ## Recall, ## SPEC, ## QUALITY, ## INTEGRATION, ## Verdict; each acceptance criterion is run on the merged tree with the command and its output quoted; the Task H checks (grep for sk-or-, Bearer, openrouter_key, user_id outside plugins/compound-v-vault; no network imports in compound-v-jev.py; hook output byte-identical with and without CV_JEV_T3; no request text in any process.run argv; nothing Jev-related under the repo except code, tests, corpus) are each run and quoted; verdict APPROVED or ISSUES with a numbered list.

Turn cap: 80 (default for tier deep; default light 30 / standard 50 / deep 80). Plan to finish inside it.

## What you must NOT report

Do not report `blocked`, `files_changed` or `violations`. Those are
enforcement fields, they are derived from git by the caller, and a
constrained party filling in its own enforcement fields is the
fabricated-evidence pattern.
