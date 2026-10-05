# Task C — scripts/compound-v-jev.py

Compound V run `2026-10-05-jev-classifier-foundation`, job `jev-core`.

Implement Task C: of docs/superpowers/plans/2026-10-05-jev-classifier-foundation.md, every step in order.  Read the pre-flight audits named in this manifest's audits block first (their §7 MUSTs bind; 1A line numbers are from 3.5.1, use the plan's anchors). Read the spec's 'Plan-review amendments' section: it overrides the sections above it. Tests first: write the selftest/test rows, run and see them fail, then implement. Touch only your lane. Run python with -B; register your lane with a literal --cwd. You are unattended: decide and return; if you approach your turn budget, commit what is complete and return a summary that says what is not.

## You are unattended

No one reads this session while it runs and no one will answer a question:
a turn that ends by asking for confirmation, approval or a preference does
NOTHING, and the job is then recorded as an absent implementation. Decide
with the spec, the plan and this prompt; when they are silent, choose the
smallest change that meets the acceptance, do it, run the checks, and return.

## Write-allowed (your lane — anything else is a scope violation)

- `scripts/compound-v-jev.py`
- `tests/test-jev-core.sh`

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

## Interfaces (your only view of the neighbours)

You see only your own job. This block is the ONLY view you get of the
names and signatures neighbouring jobs rely on — implement exactly
these, and do not rename or re-shape them.

produces (what later jobs will call):

- - CLI (one JSON object on stdout; exit 0 unless usage error = 2; selftest via the literal `--selftest` flag so the CI sweep at `validate.yml:298-312` finds it): - `build --point {t3,detect_ui,onboard_layer} --state-file F --repo R` → writes `<data_dir>/req/<uuid>.req.json`, prints `{"status":"ok","request_file":…}` or `{"status":"error","reason":"bad_input"|"redaction"}`. - `parse --response-file F --repo R --mode M [--hook-budget-left-ms N]` → `{status, reason?, point, answers: {<name>: {type, answer, probs}}, latency_ms, model, catalogue_hash}`; appends one telemetry line. - `pair --request-file F --claude-category C --backend B --t3-reason R --repo R` → appends one shadow pair line. - `eval --t3 --prepare --corpus F [--pairs] --repo R` → `{"request_files": [...]}` (originals, a reversed-order variant and two alternate-wording variants each); `eval --t3 --report OUT --repo R` → writes the markdown report. - `data-dir --repo R` → prints the resolved data dir (creates it 0700). - `<data_dir>` = `~/.claude/compound-v-jev/<repo-digest>/`; files: `req/`, `resp/`, `calls.jsonl`, `shadow-pairs.jsonl`. Every write prunes entries older than 30 days. - Request file: `{"point", "catalogue_hash", "model", "body": {"model", "state", "questions"}, "timeout_ms", "context": "hook"|"offline", "repo"}`. Response file (written by the vault, Task D): `{"status": "ok"|"unavailable"|"error", "reason"?, "http_status"?, "latency_ms", "body"?}`.

## Read-allowed (advisory — git cannot enforce reads)

- `**`

## Acceptance (your definition of done)

- compound-v-jev.py --selftest (literal flag) and tests/test-jev-core.sh green under Python 3.9; no network import in the file; no output, file or log contains sk-or- or Bearer; nothing is written under the repository; error bodies are never copied.

Turn cap: 80 (default for tier deep; default light 30 / standard 50 / deep 80). Plan to finish inside it.

## What you must NOT report

Do not report `blocked`, `files_changed` or `violations`. Those are
enforcement fields, they are derived from git by the caller, and a
constrained party filling in its own enforcement fields is the
fabricated-evidence pattern.
