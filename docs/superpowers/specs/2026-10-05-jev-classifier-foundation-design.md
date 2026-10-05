# Jev classifier foundation: a System One backend for bounded decisions - design

Spec 1 of 2. Jev (TypeSafe's System One decision model) joins Compound V as a cheap, fast classifier
that assists System Two (Opus/Sonnet) at bounded decision points. Spec 1 builds the foundation
(client, key vault, fallback, shadow telemetry) and three offline/low-risk consumers: T3 triage,
`detect_ui`, and the architectural classification at onboarding. Spec 2 (out of scope here) covers
the RAG evidence filter over V-memory, advisory gates, change-request detection and skill hints.

Recon: `docs/superpowers/recon/2026-10-05-jev-system-one-classifier-via-openrouter.md` (`[F*]` ids
below refer to its SOURCES).

## Decisions (maintainer, 2026-10-05, via structured questions)

1. **Scope of the whole effort:** T3 triage, architectural classification at onboarding, a smarter
   `is_ui`, RAG evidence filter, advisory gates, change-request detector plus skill hint.
2. **Decomposition:** spec 1 = foundation + offline classifiers (T3, `detect_ui`, onboarding);
   spec 2 = the hot-path and RAG consumers, which need spec 1's calibration data.
3. **Transport:** Jev through OpenRouter (`~typesafe/jev-latest`), not `typesafe/jev-router`
   (that is a chat-model router, a different product [F3][F4]).
4. **Key handling:** a Claude Code mod is the vault and the launcher. The key never enters the
   model's Bash environment, a command line, a file or the transcript.
5. **Approach:** A + floor C. Deterministic signals always run; Jev only strengthens them, and only
   in the safe direction.

## Global constraints

- Stdlib-only Python for everything under `scripts/` (no `typesafe_sdk` dependency). The mod is
  TypeScript, as the mod API requires.
- No daemon, no MCP server, no fabricated metrics. `latency_ms` is measured; cost is never printed.
- Iron Invariant "no raw LLM magnitude" holds: Jev only picks among pre-declared labels.
- Model policy unchanged: reviewers stay Opus; Jev is not a Claude tier and never appears in `tier`.
- Every Jev failure degrades to today's behaviour with exit code 0. Nothing blocks on Jev.

## C1. `scripts/compound-v-jev.py` - the only Jev client

- Subcommands:
  - `choice --point <id> --state <json|@file> --options a,b,c [--instructions …]`
  - `noul --point <id> --state <json|@file> --question …`
  - `batch --point <id> --state <json|@file> --questions <json|@file>` (several questions, one
    shared state, one request)
  - `eval --t3` (C6) and `selftest`
- Transport: `urllib.request` POST to the TypeSafe-compatible endpoint behind
  `CV_JEV_BASE_URL` (default `https://openrouter.ai/api`), model `CV_JEV_MODEL` (default
  `~typesafe/jev-latest`). The exact path and body shape are verified in 1C against the TypeSafe
  OpenAPI spec and a live OpenRouter call.
- Key: read only from `CV_JEV_KEY` in the process environment, then deleted from `os.environ`
  before any subprocess starts.
- Output, always one JSON object on stdout:
  `{status: "ok"|"unavailable"|"error", reason?, point, answer?, probs?, latency_ms, model}`.
  `unavailable` reasons: `no_key`, `disabled`, `egress`, `timeout`, `rate_limited`, `upstream`.
  `error` reasons: `schema`, `bad_input`. Exit code is 0 in every case except a usage error.
- Telemetry: one line per call appended to `docs/superpowers/memory/jev-calls.jsonl`:
  `{ts, point, status, reason?, answer?, probs?, latency_ms, model, mode}`. Never the state, the
  request text or any header.
- Retries: none in hook context; one retry honouring `retry-after` ≤ 1 s in offline context
  (`--context offline`).

## C2. Mod `compound-v-vault` (ships inside the plugin)

- `userConfig.openrouter_key`: `sensitive: true` (stored in secure storage, delivered only through
  `register(on, options)`).
- `tool.call` on Bash: when the command is exactly an allowlisted Compound V invocation
  (`compound-v-preeval.py`, `compound-v-onboard.py`, `compound-v-classify-request.py`,
  `compound-v-jev.py`, resolved under the plugin root), the mod runs it itself with
  `$.process.run(cmd, { env: { CV_JEV_KEY } })` and answers the tool call with its stdout/stderr and
  exit status. Every other command passes through untouched (`next(e)`).
- `classic.UserPromptSubmit`: runs the triage hook the same way, so T3 in the hook has the key.
  The 1A audit confirms how the plugin's own classic hook and the mod wrapper compose without the
  hook running twice.
- `session.append`: replaces any occurrence of the key value in stored rows with `[redacted]`.
  Backstop only; the design never puts the key there.
- Without the mod (no function hooks, `claude -p` without `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS=1`,
  Codex/Cursor/Antigravity/Opencode backends) there is no key and every consumer runs its
  deterministic path. The `SessionStart` banner shows one line: `Jev: on | off (<reason>)`.

## C3. Consumer: T3 triage

- Where: `scripts/compound-v-classify-request.py` and the `preeval triage` T3 call site.
- Jev `choice` over the existing four labels, ordered safest first:
  `unknown, user-facing-major, user-facing-minor, plumbing` (Jev leans toward the first option
  [F1]). The state is the existing bounded prompt input (≤2,000 request chars, ≤20 paths, ≤40
  taxonomy hints). No file contents.
- `jev.t3.mode`:
  - `shadow` (default): Jev and the current Claude/Codex classifier both answer; the existing one
    decides; both answers are recorded.
  - `active`: Jev decides when `status: ok`, the answer is not `unknown` and
    `max(probs) ≥ confidence_min`; otherwise the existing classifier runs.
- The pre-eval record gains `t3.engine` (`jev|claude|codex|parent`), `t3.probs` and
  `t3.shadow` (the other engine's answer, when shadowing). Schema updated in
  `schemas/pre-eval-record.schema.json`.
- Layer A overrides are evaluated before and independently of T3, exactly as today. `NEVER_DEMOTE`
  and the `DEMOTION_MAX_FAN_OUT` cap are unchanged.

## C4. Consumer: `detect_ui`

- Deterministic floor (always on, no Jev): extend `UI_SIGNALS` / `UI_EXT` with `.blade.php`,
  `.twig`, `.liquid`, `.html`, `.erb`, `.hbs`, `.astro`, `.swift` files importing SwiftUI, a WP
  theme root (`style.css` with a `Theme Name:` header, `theme.json`), and `.php` files that contain
  HTML markup outside PHP tags (bounded read, existing `_read_bounded`).
- Jev (only when the deterministic result is `False`): one `batch` of Nouls ("does this file
  render user-facing markup or UI?") over at most 12 sampled tracked files, each given as path plus
  its first 20 lines. Any `yes ≥ confidence_min` turns the result `True`.
- Monotonic: Jev can turn `False` into `True`, never the reverse. `detect_ui` returns the reason
  (`deterministic:<signal>` or `jev:<path>`) so the offered taxonomy rows can cite it.

## C5. Consumer: architectural classification at onboarding

- Where: `draft_taxonomy` in `scripts/compound-v-onboard.py`.
- One `batch` request: for each top-level directory (cap 40), a Choice over
  `ui, api, domain, data, infra, tooling, tests, docs, unknown` (`unknown` first) with state = the
  directory name plus up to 30 tracked file paths inside it.
- Output: a proposed band per directory in the taxonomy draft, marked `source: jev` with the
  probability. Mapping from layer to bands lives in one table in the script. The human approval gate
  of `/v:onboard` is unchanged; nothing is written to the live taxonomy without it.

## C6. Calibration and rollout

- `compound-v-jev.py eval --t3` replays the committed pre-eval records
  (`docs/superpowers/pre-eval/`) and `triage-outcomes.jsonl` through Jev and reports:
  agreement with the recorded T3 answer, agreement with the recorded `actual` outcome where
  present, the option-permutation flip rate, and latency p50/p95. Report written to
  `docs/superpowers/research/YYYY-MM-DD-jev-t3-eval.md`.
- Switching T3 to `active` is a manual config edit, recommended only when the report shows
  ≥90% agreement on ≥30 pairs and no case where Jev chose a less strict label than the recorded
  stricter one. The spec records that 23-30 pairs is a small sample and that fixed thresholds miss
  their target on held-out data [F5]; `active` is a human decision, never automatic.
- `confidence_min` comes from the report, default 0.8 until then.
- `detect_ui` and onboarding run active from day one: both are monotonic or human-gated.

## C7. Configuration (`.claude/compound-v.json`)

```json
{
  "jev": {
    "enabled": true,
    "egress": "ask",
    "confidence_min": 0.8,
    "timeout_ms": { "hook": 1500, "offline": 5000 },
    "t3": { "mode": "shadow" },
    "detect_ui": { "mode": "active" },
    "onboard": { "mode": "active" }
  }
}
```

- `egress: ask|allow|deny` per repository. `ask` offers once on the first call that would leave
  the machine and records the answer; until answered, calls return `unavailable(egress)`.
- `/v:init` gains the `jev` block with these defaults.

## Error handling

| Situation | Behaviour |
|---|---|
| No key / mod not loaded | `unavailable(no_key)`, silent; banner line |
| Timeout | `unavailable(timeout)`; existing path |
| 429 / 5xx | hook: no retry; offline: one retry ≤1 s; then `unavailable` |
| Malformed response | `error(schema)`; existing path |
| Egress not allowed | `unavailable(egress)` |

## Security

- The key path is: secure storage, mod `options`, `$.process.run` env of one allowlisted process,
  `CV_JEV_KEY` read and removed by `compound-v-jev.py`. It never appears in a command line, a file,
  a log line or the transcript; `session.append` redaction is a backstop.
- The allowlist matches the resolved script path under the plugin root, not a substring, so a
  model-written command cannot borrow the key by naming a look-alike script.
- User prompt text inside `state` can steer Jev (adversarial content [F1]). Layer A precedence and
  monotonicity bound the damage to "SCOPED instead of FULL on a non-sensitive path", the same
  exposure the current Sonnet T3 has.
- Egress is opt-in per repository.

## Testing and evidence

- `compound-v-jev.py selftest` against a localhost fake server (`CV_JEV_BASE_URL`): Choice, Noul,
  batch parsing; `no_key`, timeout, 429, 5xx, bad schema all yield `unavailable|error` with exit 0;
  the key is absent from stdout, stderr, the log line and child environments.
- T3 selftest in `compound-v-preeval.py`: shadow and active with a fake Jev; Layer A override wins
  in every case; reversing option order never yields a less strict tier.
- `detect_ui` fixtures: WP theme, Blade, Twig, Liquid, SwiftUI, pure CLI. A deterministic hit makes
  no Jev call; Jev never flips `True` to `False`.
- Onboarding: Jev bands carry `source: jev`; the approval gate is not bypassed.
- Mod: `claude plugin test` shows an allowlisted script receives the key in env only, the key is
  absent from the command and the tool result, a non-allowlisted or look-alike command is untouched,
  and `session.append` redacts the key.
- Existing `tests/test-*.sh`, `lint-frontmatter.py` and the CI no-fabricated-metrics check stay
  green.

## Acceptance Criteria

1. Without a key or the mod, triage and onboarding behave exactly as today, except the extended
   deterministic `detect_ui`.
2. With a key and `t3.mode: shadow`, every T3 records both answers and the decision is unchanged.
3. With `t3.mode: active`, a confident Jev answer skips the nested `claude -p`, and `latency_ms` is
   recorded.
4. The key is never present in any committed or temp file, transcript row, command line or the
   model's Bash environment (mod test plus a grep test).
5. `compound-v-jev.py eval --t3` produces the report from the committed records.
6. A WordPress theme fixture is detected as UI.

## Out of scope (spec 2)

RAG evidence filter over V-memory recall and pre-flight inputs, advisory probabilities on pre-flight
skip / Sonnet eligibility / recon gate 1, change-request detection in the prompt hook, skill hints,
and any use of `typesafe/jev-router`. Zero-shot model routing by Jev is excluded outright [F5].

## Open questions for pre-flight

- 1A: how the mod's `classic.UserPromptSubmit` wrapper composes with the plugin's own
  `triage-prompt-nudge.sh` registration; where the plugin root is resolved for the allowlist.
- 1C: OpenRouter's exact System One path and body (SDK appends to `base_url`), BYOK or billing
  requirements, current mod API for `userConfig` `sensitive` and `$.process.run` env, and whether
  `typesafe/jev-1.13` vs `~typesafe/jev-latest` should be pinned.
- 1B: classifier-cascade practice for calibration with small labelled sets; egress expectations for
  a developer plugin.
