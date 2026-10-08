# Jev classifier foundation: a System One backend for bounded decisions - design

Spec 1 of 2. Jev (TypeSafe's System One decision model) joins Compound V as a cheap, fast classifier
that assists System Two (Opus/Sonnet) at bounded decision points. Spec 1 builds the foundation
(a vault mod that is the only Jev HTTP client, a Python request/response layer, fallback, shadow
telemetry) and three consumers: T3 triage, `detect_ui`, and the architectural classification at
onboarding. Spec 2 (out of scope) covers the RAG evidence filter over V-memory, advisory gates,
change-request detection and skill hints.

Recon: `docs/superpowers/recon/2026-10-05-jev-system-one-classifier-via-openrouter.md` (`[F*]` ids).
Pre-flight: `docs/superpowers/archaeology/2026-10-05-2026-10-05-jev-classifier-foundation-design.md`
(1A), `docs/superpowers/expert/2026-10-05-2026-10-05-jev-classifier-foundation-design.md` (1B),
`docs/superpowers/library-audit/2026-10-05-2026-10-05-jev-classifier-foundation-design.md` (1C).
This revision supersedes the first draft (commit b2d3165); see "Pre-flight amendments".

## Decisions (maintainer, 2026-10-05, via structured questions)

1. **Scope of the whole effort:** T3 triage, architectural classification at onboarding, a smarter
   `is_ui`, RAG evidence filter, advisory gates, change-request detector plus skill hint.
2. **Decomposition:** spec 1 = foundation + T3 + `detect_ui` + onboarding; spec 2 = the rest.
3. **Transport:** Jev through OpenRouter's System One route, model pinned to `typesafe/jev-1.13`;
   not `typesafe/jev-router` (a chat-model router, a different product [F3][F4]).
4. **Key handling (revised after pre-flight):** a mod is the vault **and the only HTTP client**.
   It calls Jev with `$.http.fetch`; the key never leaves the Claude Code process. Python never
   holds the key. The mod never answers a Bash tool call on the model's behalf.
5. **Approach:** A + floor C. Deterministic signals always run; Jev only strengthens them.
6. **T3 active policy: deferred to spec 1.5 (plan review, 2026-10-05).** Spec 1 ships T3 in
   `off|shadow` only; the policy below is the candidate for spec 1.5 and is decided on the first eval
   report. See "Plan-review amendments". Candidate policy, asymmetric. A stricter Jev answer decides
   at once. A demoting Jev answer at `p ≥ θ_demote` gives a *provisional* tier at once and is
   confirmed by the existing Claude classifier at `/v:orchestrate` bind, before the manifest
   freezes; the stricter answer wins on disagreement. A demoting answer below `θ_demote` falls
   back to today's Claude classifier inside the hook.

## Global constraints

- Python under `scripts/` stays stdlib-only and Python 3.9 compatible (no `match`, no `X | Y`
  annotations without `from __future__ import annotations`). No `typesafe_sdk`.
- The mod is TypeScript (the mod API requires it) and ships as a **separate plugin** in the
  `procoders` marketplace, `compound-v-vault`, with no settings (classic) hooks, so its sensitive
  `userConfig` value is not exported as `CLAUDE_PLUGIN_OPTION_*` to any Compound V hook process.
- Mods need Claude Code ≥ 2.1.287. The `superpowers-v` floor stays 2.1.219; the vault is optional.
  Without it every consumer runs its deterministic or Claude path, exactly as today.
- No daemon, no MCP server, no fabricated metrics. `latency_ms` is measured; cost is never printed
  (`usage.cost` from OpenRouter is dropped, not logged).
- Iron Invariant "no raw LLM magnitude" holds: Jev only picks among pre-declared labels.
- Reviewers stay Opus. Jev is not a Claude tier and never appears in a manifest `tier`.
- Every Jev failure degrades to today's behaviour; no Compound V script exits non-zero because of Jev.

## C1. `scripts/compound-v-jev.py` - request builder, parser, telemetry, eval (no network)

- Owns the versioned question catalogue: for each decision point (`t3`, `detect_ui`,
  `onboard_layer`) the instruction text, the ordered options and **one description per option**.
  The catalogue carries a content hash; every request and telemetry line records it, because
  wording moves accuracy by 5-15 pp [F5].
- `build --point <id> --state @file` writes a request file
  `$TMPDIR/compound-v/jev/<uuid>.req.json`:
  `{point, catalogue_hash, model: "typesafe/jev-1.13", state, questions}` where `questions` is a
  named map, Choice options are a `criteria` map in insertion order (safest option first, never
  `sort_keys`). Input text passes through the existing external-egress redaction
  (`compound-v-epic-arbiter.py` `redact`) and fails closed if redaction fails. State plus questions
  are budgeted to 32,000 tokens (0.25 tokens/char estimate); over budget is `error(bad_input)`.
- `parse --resp @file` validates a response file written by the vault and prints the normalized
  result: `{status, reason?, point, answers: {<name>: {type, answer, probs}}, latency_ms, model,
  catalogue_hash}`. Choice `probs` = the returned probability map; Noul `probs` = `{yes: p}`.
  Unknown keys are ignored (OpenRouter adds `id`, `provider`, `usage`).
- Status reasons:
  - `unavailable`: `no_vault`, `disabled`, `no_key` (no key in the vault), `egress`, `timeout`, `rate_limited` (429),
    `upstream` (5xx, 502/503/524/529), `credits` (402), `auth` (HTTP 401: rejected or disabled key; HTTP 403: insufficient permissions, guardrail block or moderation flag);
  - `error`: `schema`, `bad_input` (400/422 or local budget).
- Telemetry: one line per call to `docs/superpowers/memory/jev-calls.jsonl`:
  `{ts, point, status, reason?, answer?, probs?, latency_ms, model, catalogue_hash, mode}`. Never
  the state, the request text or any header.
- `eval --t3`: see C6.
- `selftest`: catalogue order and hashing, redaction fail-closed, budget, parse of Choice/Noul and
  every error class, no key-shaped strings anywhere in outputs.

## C2. Plugin `compound-v-vault` (mod)

- `userConfig.openrouter_key`: `sensitive: true`. `userConfig.egress`: `ask|allow|deny`, default
  `ask` (non-sensitive). Consent is per user, recorded per repository in
  `$CLAUDE_PLUGIN_DATA/egress.json` keyed by repo root; never committed.
- The only Jev HTTP client: `$.http.fetch` POST to the OpenRouter System One route with the key as
  the bearer header. Timeouts: hook path 1,500 ms, offline 5,000 ms. One retry only offline, only on
  429 with `Retry-After ≤ 1 s` (absent header = no retry). 402/401/403 never retried.
- **Hook path.** `on('classic.UserPromptSubmit', …)`: `await next(e)` first (the Compound V triage
  hook runs unchanged and, when T3 is needed, leaves a request file and a pending marker). The mod
  then fetches, writes `<uuid>.resp.json`, and re-runs the triage re-entry with
  `$.process.run(['python3', <plugin root>/scripts/compound-v-preeval.py, 'triage', '--t3-response',
  <file>, …])`. The argv carries file paths only; no key, no env injection.
- **Offline path.** The mod registers one model-callable tool, `jev_classify(request_file)`: it
  reads a request file under `$TMPDIR/compound-v/jev/` (any other path is refused), fetches, writes
  the response file beside it and returns its path. The tool writes nothing in the repository.
  Onboarding and `eval` use it through their documented command flow (C5, C6).
- **Recursion guard.** When `CV_HEADLESS_CLASSIFY` is set (the nested `claude -p` T3 fallback),
  the mod does nothing: no fetch, no tool.
- **Egress.** With `egress: ask` and no recorded answer for this repo, the hook path returns
  `unavailable(egress)` and the mod shows one toast offering `/compound-v-vault:egress allow|deny`;
  the offline tool asks the same question before its first fetch. The consent text names OpenRouter
  and TypeSafe and the data classes sent (request text, file paths, taxonomy hints, file heads for
  `detect_ui`), and makes no zero-retention claim.
- **Redaction backstop.** `session.append` replaces any occurrence of the key value with
  `[redacted]`.
- Banner: the mod sets a status line `Jev: on | off (<reason>)`.
- Out of reach, stated plainly: another mod earlier in the chain can observe the vault's API calls
  (mods are unsandboxed). The guarantee is "never in the model's environment, a command line, a
  file or the transcript", not "invisible to other mods".

## C3. Consumer: T3 triage

- The engine still returns `needs_t3`. `hooks/triage-prompt-nudge.sh` writes the request through
  `compound-v-jev.py build --point t3` (state = today's bounded classify input: ≤2,000 request
  chars, ≤20 paths, ≤40 taxonomy hints; no file contents) and exits as today. The vault mod
  re-enters with the response. The hook contract accepts `backend: jev` as classified.
- Options, safest first, each with a description: `unknown`, `user-facing-major`,
  `user-facing-minor`, `plumbing`.
- `t3.mode: shadow` (default): Jev answers, the existing Claude/Codex classifier also answers and
  decides; both are recorded.
- `t3.mode: active`, the asymmetric policy (decision 6), applied per answer:
  1. Jev `unknown` → existing classifier.
  2. Jev's answer yields a tier **no less strict** than the T1/Layer-A outcome without T3 (no
     demotion, no SCOPED+) → Jev decides; the existing classifier is not called.
  3. Jev's answer **demotes** (`t3_reason` `demotion` or `sensitive`, answer `plumbing` or
     `user-facing-minor`) and `max(probs) ≥ θ_demote` → the record carries the tier with
     `t3.provisional: true`. `/v:orchestrate` runs the existing Claude classifier before freezing
     the manifest. Agreement clears `provisional`; disagreement re-triages with the stricter
     answer and writes a successor record (records stay write-once; the successor names its
     predecessor).
  4. Jev demotes below `θ_demote` → existing classifier in the hook, as today.
- Layer A overrides, `NEVER_DEMOTE`, `DEMOTION_MAX_FAN_OUT` and the difficulty floor are unchanged
  and evaluated before T3.
- Record: `t3.engine` (`jev|claude|codex|parent`), `t3.probs`, `t3.catalogue_hash`, `t3.model`,
  `t3.provisional`, `t3.shadow` (the other engine's answer). Added to
  `schemas/pre-eval-record.schema.json` and passed into `build_record` before the digest.
- Shadow pairs with the request text are kept **locally** (not committed) in
  `$TMPDIR/compound-v/jev/shadow-pairs.jsonl` or the plugin data dir, so C6 can replay them.

## C4. Consumer: `detect_ui`

- `detect_ui(repo) -> bool` keeps its signature and behaviour contract for every caller. A new
  `detect_ui_reason(repo) -> (bool, reason)` carries `deterministic:<signal>` or `jev:<path>`.
- Deterministic floor (always on): add `.blade.php`, `.twig`, `.liquid`, `.erb`, `.hbs`, `.astro`,
  `.swift` importing SwiftUI, a WordPress theme root (`style.css` with a `Theme Name:` header, or
  `theme.json`), and `.php` with HTML markup outside PHP tags (bounded read). `.html` is not a
  deterministic signal (docs sites and fixtures would flip); Jev covers it.
- Jev, only when the floor says `False` and the vault is available: one request of Nouls over at
  most 12 sampled tracked files (path + first 20 lines each), excluding Layer A sensitive globs and
  secret-bearing names, passed through `scan_secrets` and redaction. Any `yes ≥ confidence_min`
  turns the result `True`.
- Monotonic: Jev never turns `True` into `False`. A repo newly detected as UI gets the shared-token
  and a11y rows offered, which is the intended effect.

## C5. Consumer: architectural classification at onboarding

- `draft_taxonomy` writes one request **per top-level directory** (cap 40; each its own state, so
  no irrelevant-state dilution): a Choice over `unknown, ui, api, domain, data, infra, tooling,
  tests, docs`, state = directory name + up to 30 tracked paths.
- The `/v:onboard` command flow calls `jev_classify` for each request file and passes the
  response files back to `compound-v-onboard.py` (`--jev-responses <dir>`). No vault: the step is
  skipped and the draft is today's.
- The proposed band per directory is marked `source: jev` with its probability, and
  `emit_taxonomy_yaml` keeps that evidence through WRITE. The human approval gate is unchanged.

## C6. Calibration and rollout

- Committed pre-eval records cannot be replayed (they store no request text) and only 6 used T3,
  so calibration is **prospective**: shadow mode collects local pairs (C3).
- `compound-v-jev.py eval --t3 --pairs <file>` writes request files for every pair (the model or
  maintainer runs `jev_classify` over them) and then reports, against the pinned model id:
  n; agreement with the recorded classifier and with recorded `actual` outcomes, each with a 95%
  binomial interval; strictness inversions (Jev less strict than the recorded answer), with the
  `3/n` upper bound when zero are observed; option-order flip rate (options reversed);
  instruction-wording perturbation (two alternate catalogue wordings); latency p50/p95.
  Report: `docs/superpowers/research/YYYY-MM-DD-jev-t3-eval.md`.
- `θ_demote` and `confidence_min` are derived on a split disjoint from the reported agreement, or
  labelled in-sample. Defaults until a report exists: `θ_demote = 0.95`, `confidence_min = 0.8`.
- Switching T3 to `active` is a manual config edit, recommended only on a report for the same
  resolved model id with n ≥ 30 and zero strictness inversions. A change of the resolved model id
  invalidates the report and drops `active` back to `shadow` (logged).
- `detect_ui` and onboarding run active from day one: monotonic or human-gated.

## C7. Configuration (`.claude/compound-v.json`, committed team policy)

```json
{
  "jev": {
    "enabled": true,
    "model": "typesafe/jev-1.13",
    "confidence_min": 0.8,
    "t3": { "mode": "shadow", "theta_demote": 0.95 },
    "detect_ui": { "mode": "active" },
    "onboard": { "mode": "active" }
  }
}
```

Egress consent is not here (it is per user, C2). `/v:init` gains the `jev` block.

## Security

- Key path: secure storage, vault `options`, `$.http.fetch` bearer header. It is never in a Python
  process, an env var, a command line, a file, a log line or the transcript.
- The vault never answers a Bash tool call, so `lane-guard.sh`, permission prompts and sandbox
  rules apply to every command exactly as today. Its own `$.process.run` re-entry runs a fixed argv
  (the plugin's `compound-v-preeval.py` with file arguments) outside the Bash sandbox, as every mod
  process does; the argv is not model-controlled.
- `jev_classify` reads only request files under `$TMPDIR/compound-v/jev/` and writes only beside
  them.
- Prompt text in `state` can steer Jev [F1]. In active mode a demotion is never final without the
  Claude confirmation at bind; the post-diff re-classifier and SCOPED+ review remain.
- Egress is opt-in per user and repository; outbound text is redacted and size-capped.
- A dedicated OpenRouter key with a credit limit is recommended in the vault's setup text.

## Error handling

| Situation | Behaviour |
|---|---|
| No vault (CC < 2.1.287, mods off, safe mode, `allowManagedModsOnly`, cloud, WSL Desktop) | `unavailable(no_vault)`; today's path |
| Key missing or lost from secure storage | `unavailable(no_key)`; status line says so |
| Timeout | `unavailable(timeout)`; today's path |
| 429 | hook: none; offline: one retry if `Retry-After ≤ 1 s`; then `unavailable(rate_limited)` |
| 402 / 401 / 403 | `unavailable(credits)` / `unavailable(auth)`, no retry |
| 5xx, 524, 529 | `unavailable(upstream)` |
| 400 / 422, bad response | `error(bad_input)` / `error(schema)` |
| Egress not allowed | `unavailable(egress)` |

## Testing and evidence

- `compound-v-jev.py selftest` (offline, no network).
- `compound-v-preeval.py` selftest: shadow; active rules 1-4 with fake responses; Layer A override
  wins in every case; option reversal never yields a less strict tier; provisional record and bind
  confirmation (agree and disagree, successor record); digest covers the new fields.
- Hook test: `backend: jev` accepted; no double run; `CV_HEADLESS_CLASSIFY` respected.
- `detect_ui` fixtures: WordPress theme, Blade, Twig, Liquid, SwiftUI, pure CLI, a docs site with
  `.html` (stays `False` without Jev). Every existing `detect_ui` caller and selftest unchanged.
- Onboarding: per-directory requests; `source: jev` survives `emit_taxonomy_yaml`; gate intact.
- Vault: `claude plugin test` with a stubbed `http.fetch` and `process.run`: the key appears only
  in the fetch auth header; never in argv, files written, tool results or appended rows; the tool
  refuses paths outside `$TMPDIR/compound-v/jev/`; recursion guard; egress `ask` path; every error
  class mapping.
- Existing `tests/test-*.sh`, `lint-frontmatter.py` and the CI no-fabricated-metrics check stay
  green.
- Before the plan locks the route: one live OpenRouter call (maintainer-run, throwaway limited key)
  confirms the System One path, the response shape and rate-limit headers.

## Acceptance Criteria

1. Without the vault, triage, `detect_ui` (beyond the extended floor) and onboarding behave exactly
   as today.
2. With the vault and `t3.mode: shadow`, every T3 records both answers; the decision is unchanged.
3. (Moved to spec 1.5.) Spec 1: `t3.mode` accepts only `off|shadow`; `active` is coerced to `shadow`
   with a warning.
4. The key appears in no file, transcript row, command line, Python process or env var
   (vault test + grep test).
5. `eval --t3` produces the report with intervals and the pinned model id.
6. A WordPress theme fixture is detected as UI deterministically.

## Pre-flight amendments (2026-10-05)

Draft 1 (b2d3165) had the mod run allowlisted scripts itself with the key in their env and answer
the Bash call. Pre-flight showed that this bypasses `lane-guard.sh` and permission prompts (1B),
that a sensitive `userConfig` value is exported to every hook process of its plugin (1B, 1C),
that the key leaks to `claude -p`/`codex`/`npx` children (1A), that `$.process.run` takes argv
(1C), and that T3 can demote (1A). Revisions: vault as a separate plugin and the only HTTP client;
Python key-free; asymmetric T3 with bind confirmation; per-option descriptions and catalogue hash;
pinned model; full error taxonomy; 32k budget; per-directory onboarding requests; `detect_ui` bool
contract kept and `.html` dropped from the floor; outbound redaction; prospective calibration with
intervals; egress consent per user.

## Plan-review amendments (2026-10-05, Fable review, maintainer accepted)

These override the sections above where they differ.

1. **Scope cut.** In the committed records every T3 consultation was a demotion (`demotion`/`sensitive`
   answered `plumbing`). Under the candidate policy every such case is provisional and Claude still runs at bind,
   so `active` saves no Claude call on the observed distribution. Spec 1 therefore ships: vault, key-free Python
   layer, record `t3` block, T3 **shadow**, the eval, the deterministic `detect_ui` floor, and Jev for `detect_ui`
   and onboarding. Deferred to spec 1.5: `active`, `provisional`, `t3-decide`, `confirm`, successor records
   (`supersedes`), the model-drift gate, the bind step in `/v:orchestrate`.
2. **Eval on a committed corpus.** `tests/fixtures/jev-t3-corpus.jsonl`: 60-100 T3-shaped requests (synthetic
   or consented, no secrets), each labelled by the Claude classifier and by a human. `eval --t3` runs over it
   offline through `jev_classify`; shadow pairs are a second, growing source. The report adds a probability
   histogram and the share of hard 0/1 answers; if most answers are 0/1, spec 1.5 gates on agreement plus zero
   strictness inversions, not on a threshold.
3. **Durable local data.** Shadow pairs and any stored request text live in `~/.claude/compound-v-jev/<repo-digest>/`
   (dir 0700, files 0600), not `$TMPDIR`; retention 30 days, pruned by `compound-v-jev.py` on each write.
   `jev-calls.jsonl` moves to the same directory (not tracked, not indexed by V-memory).
4. **Record `t3` block** gains `category` and drops `provisional` (spec 1.5 re-adds it).
5. **Config:** `confidence_min` per point (`t3`, `detect_ui`, `onboard`); `t3.calibrated_model` (unused until 1.5,
   recorded in reports).
6. **`detect_ui` Jev:** one Noul over the whole sample ("does any of these files render user-facing UI?"), not one
   Noul per file by index.
7. **Hook safety:** the hook never stops before today's Claude path; the mod never replaces another hook's
   `additionalContext`; shadow returns the classic result untouched.

## Out of scope (spec 2)

RAG evidence filter over V-memory recall and pre-flight inputs, advisory probabilities on pre-flight
skip / Sonnet eligibility / recon gate 1, change-request detection, skill hints, `typesafe/jev-router`,
and zero-shot model routing by Jev [F5].
