---
description: Classify one change request before any work starts — resolve, score, and write plus COMMIT the pre-eval triage record, then print the tier (DIRECT | SCOPED | FULL) with the predicates that decided it. DIRECT means the human implements in place, runs the test floor, and commits the change together with its record.
---

You are running **`/v:triage`** — the **entry point** to Compound V's sizing engine.

`scripts/compound-v-preeval.py` and its five siblings are ~10,400 lines of deterministic scoring
that, until this command existed, **nothing ever called**: `docs/superpowers/pre-eval/` had never
appeared in this repository's git history and no run had ever been bound to a record. Every other
v3.0 mechanism — the validator's `triage` block, the Stop-hook coverage gate, the outcome stream,
the circuit breaker — consumes a record that only Phase T produces.

The argument is `{{args}}`.

## Resolving the plugin root

The `scripts/` this command calls ship with the plugin — they are not files in your own
repository. Resolve the plugin root once per session before calling any of them:

```bash
CV="${CLAUDE_PLUGIN_ROOT}"
[ -f "$CV/scripts/compound-v-preeval.py" ] || CV="$PWD"
[ -f "$CV/scripts/compound-v-preeval.py" ] || echo "Compound V: plugin root not found (no harness substitution, and $PWD is not a Compound V checkout); set CV to the plugin directory" >&2
```

`CLAUDE_PLUGIN_ROOT` is set for hooks but is not set in this Bash environment. Claude Code
substitutes the plugin's path for the braced reference in the first line when it loads this
file, so that line already holds the path of the copy it loaded. Where nothing substituted it
(another harness, or this file read with the Read tool), the shell expands the unset variable to
an empty string; the second line then accepts `$PWD` only when it is a checkout of this plugin,
and the third says so on stderr instead of guessing.

## You are not the only producer any more (v3.4)

`hooks/triage-prompt-nudge.sh` fires on `UserPromptSubmit` and runs **the same subcommand Phase T
runs below**, so a change request that arrives as an ordinary prompt is usually already sized and
already has a record — written, bound to the session, and **uncommitted**, because a hook must not
run git. Before scoring, check whether that record exists and covers this work:

```bash
ls -t docs/superpowers/pre-eval/*.json 2>/dev/null | head -5
```

If one carries this session's id, **do not mint a second**: commit it (step T3) and go. A record per
prompt is how the outcome stream the circuit breaker reads stops meaning anything. Run Phase T when
the hook did not fire — a slash-command invocation, a second request in the same session, or any
session the hook was not registered in.

As of **v3.4.1 a request needing T3 is no longer one of those cases**: the hook finishes the classify
itself with the headless one-shot (see T2) and records a real tier. It falls back to its reminder
only when no classifier could be RUN at all — no `claude`/`codex` CLI on the machine, or one that
hung past the cap — and that reminder is the signal to run Phase T here.

## One phase

`/v:triage <request>` is **Phase T** — resolve localization, classify, score, write **and commit**
the record, then print the tier and predicates 1-6. Run it before any work starts, when no record
already covers the request.

### A DIRECT change is an ordinary commit

DIRECT means "implement in place, run the floor, commit on the branch". That commit is an
**ordinary `git commit`**: make the edit, run the test floor, commit it together with the triage
record, and let review and the human be the enforcement they already are. There is no separate
landing gate — the triage record and the Stop-hook coverage gate are what bind the change to its
decision.

SCOPED and FULL are unchanged: they still require a human offer and acceptance, then
`/v:orchestrate` and `/v:dispatch`.

## The vocabulary rule

**Never re-spell a decision string or a tier token.** `DECISION_FASTPATH` / `DECISION_SCOPED` /
`DECISION_FULL` and the `DECISION_TO_TIER` map live in `scripts/compound-v-preeval.py`; Phase T
reads them by calling the engine's own `triage` subcommand. A
duplicated wire vocabulary is how the two halves of this release drift apart, and the one ratified
exception (a sibling analyser consuming the value as JSON off a record, with a selftest asserting
equality) does not apply here.

The same rule governs the `sensitive` set: it comes from the taxonomy via
`compound-v-taxonomy.match_auto_route()`, **never** from a list written here. `MANDATORY_SENSITIVE`
in that module is the code-level floor that keeps a taxonomy which forgets the two policy files from
re-opening the self-widening hole; this command adds nothing to it.

---

## The six auto-route predicates (spec §A4), and where each is evaluated

| # | Predicate | Evaluated |
|---|---|---|
| 1 | Tier is `DIRECT` and **no override fired** | Phase T, from the record's `decision` + `override_fired` |
| 2 | Exactly one resolved path, and it is a **literal** | Phase T, via the engine's own `_is_single_literal_path` |
| 3 | Taxonomy present and **digest-matched**; never a fail-closed `unknown` band | Phase T, against the record's pinned snapshot |
| 4 | Path matches the taxonomy's `auto_route_allow` | Phase T, via `match_auto_route` |
| 5 | Path matches **no** entry in the `sensitive` set | Phase T, via `match_auto_route` (taxonomy + mandatory floor) |
| 6 | **No test file touched** | Phase T, on the resolved path |

Predicates 1-6 decide *membership*, and Phase T reports them for every record — a DIRECT change
gets the six as evidence, and then commits ordinarily.

---

## Phase T — decide

### T1. Preconditions

```bash
git rev-parse --show-toplevel
```

```bash
printf '%s\n' "${CLAUDE_CODE_SESSION_ID:-}"
```

Read what that prints before running T2 — it is what the record binds, and its consequences are
under "On the session id" below.

### T2. Score, bind, write the record — one call

The whole of Phase T is a subcommand of the engine. Put the request text in
`V_TRIAGE_REQUEST` (never on argv: a request is arbitrary text, it has to survive shell
quoting, and argv is visible to every process on the machine) and run this from the repo root:

```bash
V_TRIAGE_REQUEST='<the request text>' python3 "$CV/scripts/compound-v-preeval.py" triage \
  --request-env V_TRIAGE_REQUEST --repo . \
  --session-id "${CLAUDE_CODE_SESSION_ID:-}" --base-commit "$(git rev-parse HEAD)" --json
```

It prints one JSON object: `pre_eval_id`, `tier`, `decision`, `needs_t3`, `record_ref`,
`predicates` (spec §A4's 1-6, each with a `pass` and a `why`), `declared_paths`, plus `member`
(all six hold), `refused_paths`, `disabled` and the binding echoed back.

**This is the same call `hooks/triage-prompt-nudge.sh` makes** — see `triage_request`'s docstring
in the engine, which names both callers. That is the point of it being a subcommand rather than
prose: the scoring, the binding, the declared-path vocabulary and the six predicates have one
implementation, it is covered by `compound-v-preeval.py --selftest`, and a second producer is one
line rather than a copy.

After a `needs_t3` result the re-invocation adds `--t3-category` and `--t3-engine` (see the
`needs_t3` bullet below for both values). Add `--taxonomy PATH` only to point at a non-default
taxonomy.

**Two results are not a tier, and each has one right response:**

- `"disabled": true` — `pre_eval.enabled` is false. The stage is a no-op, **nothing was written**,
  and this change is FULL by the operator's own configuration. Say so; do not hand-write a record.
- `"needs_t3": true` — the deterministic layers cannot band the request without a light classify.
  Answer the returned `t3_prompt` with one of the returned `t3_categories` and re-invoke with
  `--t3-category <enum>`. The re-invocation resumes the same `pre_eval_id` (discovered by request
  fingerprint) rather than minting a second. Any error, timeout, or non-enum reply is `unknown`,
  which is FULL.

  **Keep `t3_reason` from this first result** (`unbanded`, `demotion` or `sensitive`; `unbanded`
  when the field is absent). The re-invocation's output does not carry it, and the Jev step (T2b)
  needs it. Never invent one.

  **Write the returned `t3_prompt` to a temp file first**, with
  `PROMPT_FILE="$(mktemp "${TMPDIR:-/tmp}/cv-t3-prompt.XXXXXX")"`, whichever route answers. It
  holds the request text: keep it only until T2b ends, then `rm -f` it.

  **The headless one-shot is the default route** (v3.4.1, finding 50). Run it on that file:

  ```bash
  python3 "$CV/scripts/compound-v-classify-request.py" --classify-headless \
    --prompt-file "$PROMPT_FILE" --cwd . --timeout 15
  ```

  It prints `{"category", "backend", "timed_out", "exit_code", "model"}`: one nested
  `claude -p --tools ""` on the resolved `claude`/`light` model (never Haiku), falling back to the
  read-only `codex` route, both under `compound-v-run-with-timeout.py` with stdin closed. Pass the
  `category` straight back as `--t3-category`. Prefer it because it is the same route
  `hooks/triage-prompt-nudge.sh` takes, so an attended `/v:triage` and the hook that fires without
  anyone asking reach the same answer by the same path.

  **`backend: "none"` is not an answer.** It means no classifier CLI was available on this machine
  — as does `timed_out: true`. Neither is a classification, and neither may be recorded as
  `--t3-category unknown`: that would put a made-up band on a real record. Fall back to the Task
  route below. A model that RAN and replied `unknown` is different and *is* an answer: re-invoke
  with it and take the FULL that follows.

  **The Task route is the fallback**, and the only route on a harness with no `claude`/`codex` CLI:
  run **one** `light`-tier Task (Sonnet, never Haiku) with the `t3_prompt`, then
  `--parse` its reply into the enum:

  ```bash
  python3 "$CV/scripts/compound-v-classify-request.py" --parse --reply '<the Task reply>'
  ```

  **The re-invocation** names the category and who answered it, so the record carries a `t3`
  block (`engine`, `category`). Run it from the repo root with the same request text:

  ```bash
  V_TRIAGE_REQUEST='<the request text>' python3 "$CV/scripts/compound-v-preeval.py" triage \
    --request-env V_TRIAGE_REQUEST --repo . \
    --session-id "${CLAUDE_CODE_SESSION_ID:-}" --base-commit "$(git rev-parse HEAD)" --json \
    --t3-category <category> --t3-engine <engine>
  ```

  `<category>` is the enum the classify answered. `<engine>` is the `backend` the headless
  classify printed (`claude` or `codex`), or `parent` when the Task route answered. A
  `backend: "none"` or `timed_out: true` result is still not an answer: it never reaches
  `--t3-category` or `--t3-engine`, and the Task route answers instead (engine `parent`). The engine
  is evidence only: it never changes the tier.

  **If the re-invocation is refused** with `triage failed: ... already exists with DIFFERENT
  content`, a record for this request already exists without this `t3` block. Do not edit that
  record. Re-run the same command without `--t3-engine`, say in the report that the record keeps no
  `t3` block, and skip T2b.

### T2b. Ask Jev the same question, in shadow

Run this step only when T3 decided the tier: T2 returned `needs_t3: true` and the re-invocation with
`--t3-engine` wrote the record. Skip it in every other case. It is a shadow: it never changes the
record, the tier or the next step, and **it never skips T3** — whatever happens here, including a
failure of any command below, go on to commit the record. Use the same `--repo .` for every command,
from the repo root. Never print or `cat` the response file, and never print a key.

1. **Find the tool.** `mcp__compound-v-vault__jev_classify` is a deferred tool: load it with
   ToolSearch (`select:mcp__compound-v-vault__jev_classify`) before you treat it as absent. Absent
   means the vault is not installed or is disabled here; the step ends.
2. **Build the request** with the same request text and the prompt file from T2:

   ```bash
   V_TRIAGE_REQUEST='<the request text>' python3 "$CV/scripts/compound-v-jev.py" t3-request \
     --repo . --request-env V_TRIAGE_REQUEST --prompt-file "$PROMPT_FILE" --context offline
   ```

   It prints `{"status": "ok", "request_file": ...}`. Any other status ends the step: `off` means
   the committed config has Jev disabled or `jev.t3.mode: off`, and nothing was written.
3. **Call `jev_classify`** with `{"request_file": "<request_file>"}`. It returns the response file's
   path, or a string such as `refused: disabled`. A result that is not an absolute path to an
   existing file ends the step.
4. **Parse the answer** (it writes one metadata-only `calls.jsonl` line, whatever the status):

   ```bash
   python3 "$CV/scripts/compound-v-jev.py" parse --mode shadow --request-file "<request_file>" \
     --response-file "<response_file>" --repo .
   ```

5. **Keep the pair, or drop the request.** When `parse` printed `"status": "unavailable"` with
   `"reason"` `no_key`, `egress` or `disabled`, Jev is not switched on for this user (no key, or no
   egress consent for this repository): delete the request file with `rm -f "<request_file>"` and
   write no pair. Every other status (`ok`, `timeout`, `upstream`, `auth`, ...) is paired:

   ```bash
   python3 "$CV/scripts/compound-v-jev.py" pair --request-file "<request_file>" \
     --claude-category <category> --backend <engine> --t3-reason <t3_reason> --repo .
   ```

   `<category>` and `<engine>` are the values the re-invocation passed; `<t3_reason>` is the value
   kept from the first `needs_t3` result.

However the step ends, and also when it is skipped, `rm -f "$PROMPT_FILE"`. Report the step in
**one line**: what Jev answered (from `parse`'s `status` and `answers`) or why the step ended, and
whether a pair was written. Then T3.

**On the session id.** `CLAUDE_CODE_SESSION_ID` is the harness session id as a Bash call in this
session sees it, and it is what the record binds. **If it is empty, say so and continue** — the
record is still written and still classifies, but with `session_id: null` it covers nothing for the
Stop-hook triage gate (`hooks/epic-goal-stop.sh` compares it exactly, and an empty value can never
match). That is the fail-closed direction; do not substitute a pid or an invented uuid. The engine
binds what it is given and refuses to invent, so passing an empty value is safe.

**On `refused_paths`.** A non-empty list means the localizer resolved a path the triage gate cannot
read back (a leading `/`, a `..` segment, a control character). Those are dropped from
`declared_paths` — report them, because coverage the record claims and does not have is worse than
coverage it never claimed.

### T3. Commit the record

The engine deliberately **never runs git**, and neither does the UserPromptSubmit hook; committing
is this command's job, and it is not optional. An uncommitted record is invisible to the Stop-hook
triage gate (which reads committed files back with `jq`) and is lost to `git clean`, a fresh clone or a removed worktree
the moment a branch is merged or discarded — the v2.6.4 data-loss shape.

**This step also applies to a record the hook wrote.** If you skipped T2 because
`hooks/triage-prompt-nudge.sh` had already sized this session's request, its record is sitting
uncommitted; commit it here with the same two commands.

```bash
git add docs/superpowers/pre-eval/<pre_eval_id>.json docs/superpowers/pre-eval/<pre_eval_id>.intent.json docs/superpowers/pre-eval/<pre_eval_id>.localization.json docs/superpowers/pre-eval/<pre_eval_id>.taxonomy-snapshot.yaml docs/superpowers/memory/triage-outcomes.jsonl
```

```bash
git commit -m "triage(<TIER>): <short request> [<pre_eval_id>]"
```

Some of those artifacts are absent by design — there is no snapshot when the repository has no
taxonomy, and no localization artifact when localization failed. `git add` the ones that exist.

### T4. Report

Print the tier, the predicate list exactly as T2 emitted it, and the next step:

- **DIRECT** → implement it, run the test floor, and commit it as an **ordinary commit** together
  with its record. A human and a review are downstream of you, which is the enforcement that class
  is trading on.
- **SCOPED** → offer it; on acceptance `/v:orchestrate` (manifest, run dir, scope gate, floor, one combined SPEC+QUALITY review; recon and the three pre-flights are skipped).
- **SCOPED+** (`"tier": "SCOPED"` with `"flavor": "scoped_plus"`) → a small edit on a **sensitive**
  path. Offer it; on acceptance `/v:orchestrate` with `triage.flavor: scoped_plus`, where a deep
  review and a cross-model second opinion are **mandatory**, not offered. SCOPED+ is not a fourth
  tier token — it is SCOPED plus a flavor, and the size being small is exactly why the review does
  not shrink with it.
- **FULL** → offer it; on acceptance the unchanged pipeline.

---

## Safety

- **Never widen the class.** `auto_route_allow`, the `sensitive` set and the line budget come from
  the taxonomy through `match_auto_route`; do not add a special case here.
- **Never hand-write or re-score a record that already exists.** The UserPromptSubmit hook and
  Phase T are the two producers and they call the same subcommand; a third copy of the scoring is
  the drift v3.4 removed.
- **Never edit the taxonomy to widen a class.** The two policy files are sensitive in code
  (`compound-v-taxonomy.MANDATORY_SENSITIVE`) as well as in this repo's taxonomy, so a taxonomy that
  forgets them still cannot be self-widened.
- **Never invent a session id.** An empty `CLAUDE_CODE_SESSION_ID` means the record covers nothing;
  say so.
- **No fabricated metrics.** Print the engine's real output, nothing derived or estimated.

## Selftests

Phase T is no longer prose, so its proofs are no longer here: the scoring, the binding, the
declared-path vocabulary and predicates 1-6 are covered by the engine's own suite, which CI runs.

```bash
python3 "$CV/scripts/compound-v-preeval.py" --selftest
```
