# Library audit (Phase 1C): Jev classifier foundation

Spec: `docs/superpowers/specs/2026-10-05-jev-classifier-foundation-design.md`
Recon: `docs/superpowers/recon/2026-10-05-jev-system-one-classifier-via-openrouter.md`
Date: 2026-10-05. Auditor: doc-validator (Phase 1C).

## 1. Tools Available

- Context7: ❌. `ToolSearch` for `context7` and for `resolve-library-id query-docs` returned nothing; the only server it named was a failed `plugin:ios-engineering-skills:tessl` connection. Context7 is genuinely absent from this session's tool list (the session's MCP instructions mention a context7 server, but no callable tool surfaced).
- **DEGRADED: WebSearch/WebFetch-only.** Every lookup below is WebFetch/WebSearch against vendor docs; none is cited as Context7.
- Bash was clamped to V-memory/git forms, so no live HTTP call to OpenRouter was possible (and no key exists). **Nothing in this audit was verified by a live call.** Items needing a live call are marked LIVE-UNVERIFIED.
- V-memory: the pipeline's recall block was used (recon doc only; no prior library-audit on TypeSafe/Jev). No `.claude/agent-memory/superpowers-v-doc-validator/` content existed at start.
- Manifests found: none for Python or Node (no `package.json`, `pyproject.toml`, `requirements*.txt`). Only `.claude-plugin/plugin.json` (plugin 3.5.1, no `userConfig`, no `modules` yet) and `hooks/hooks.json` (settings hooks; `UserPromptSubmit` -> `triage-prompt-nudge.sh`, `timeout: 25`). The charter is stdlib-only Python under `scripts/`, so the "libraries" under audit are two hosted APIs (TypeSafe System One via OpenRouter) and the Claude Code mods runtime.
- Recon claims revalidated: F1 (limits, primitives, jagged edges), F2/F3 (OpenRouter base URL and model ids), F7 (see Finding 2 - superseded). F5 (arXiv paper) and F11 are domain evidence, out of 1C scope, not re-fetched.

## 2. Libraries Mentioned

| Name | Spec context | Current (2026-10-05) | Repo pinned | Last release / signal | Maintenance | Status |
|---|---|---|---|---|---|---|
| TypeSafe Jev (System One) | C1 transport, C3-C5 consumers | `jev-1.13.0`; `jev-latest` and `jev-preview` both alias it (docs.typesafe.ai/models.md) | none; spec floats `~typesafe/jev-latest` | OpenRouter listing 2026-09-18, TypeSafe launch 2026-09-15 (per search summary) | Under 3 weeks old. Docs recommend pinning ids once thresholds are tuned. Rate limits "dynamic" | 🟢 current; maturity risk, see Finding 8 |
| OpenRouter System One endpoint | C1 default `CV_JEV_BASE_URL` | `POST https://openrouter.ai/api/v1/systemone` (SDK appends `/v1/systemone` to `https://openrouter.ai/api`) | n/a | Listed 2026-09-18 | Vendor-run | 🟢 path corroborated by 3 pages, LIVE-UNVERIFIED |
| `typesafe_sdk` (Python) | Excluded by charter | not pinned, not used | n/a | n/a | n/a | 🟢 not a dependency; docs are the only contract |
| Claude Code mods (function hooks) | C2 vault mod | Docs reference "as of v2.1.289"; mods require **>= v2.1.287**, on by default | AGENTS.md floor is 2.1.219 | Local runtime seen earlier in KB: 2.1.238 (2026-09-02) | Anthropic-maintained; API "moves between releases" per third parties | 🟡 floor mismatch, Finding 4 |
| `urllib.request` / Python stdlib | C1 transport | system python3 3.9.6 (KB entry 2026-07-26, same machine, not rechecked today) | n/a | n/a | n/a | 🟡 3.9 syntax ceiling, Finding 10 |

## 3. API Signatures Verified

| Spec claim | Verified against | Result |
|---|---|---|
| POST to `<base>` + System One path; base `https://openrouter.ai/api`; model `~typesafe/jev-latest` | openrouter.ai/docs/guides/community/typesafe-sdk; docs.typesafe.ai/sdk/python/usage.md | ✅ matches. Direct TypeSafe is `POST https://api.typesafe.ai/v1/systemone`, model `jev-latest`. OpenRouter's own Decisions API page lists a different alpha path (`/api/alpha/decisions`; one summary rendered `/api/v1/api/alpha/decisions`). Two OpenRouter paths exist; the SDK one is `/v1/systemone`. LIVE-UNVERIFIED |
| Auth | Same pages | ✅ `Authorization: Bearer <OpenRouter key>`; no TypeSafe account or BYOK needed, usage billed to the OpenRouter account |
| Request: `choice --options a,b,c` | docs.typesafe.ai/primitives/choice.md | ❌ drift. Body is `{"state": str, "model": str, "questions": { "<name>": {"type":"choice","instructions":..., "criteria": {"<option>": "<description>", ...}} }}`. `criteria` is a **map of option to description**, not a list. Up to 255 options. Finding 5 |
| Request: `batch --questions` "several questions, one shared state" | docs.typesafe.ai/api.md | ✅ `questions` is a **named object**, not an array. Question names are the keys |
| Response: `{answer, probs}` for Choice | primitives/choice.md | ✅ with renaming: `answers.<name> = {type:"choice", choice, confidence, probabilities{option: float}}`, probabilities sum to 1, top-level `model` (resolved id, e.g. `jev-1.13.0`) and `usage{input_tokens, output_tokens}` |
| Response for Noul | api.md, OpenRouter Decisions page | ⚠️ `{type:"noul", noul: 0.95}`, a single yes-probability float; **no `probabilities` map, no `choice`, no `confidence`** in the documented example. Spec's uniform `probs` field must be derived |
| OpenRouter response extras | typesafe-sdk page | `id`, `provider`, `usage.cost` added; SDKs pass them through. Parser must tolerate unknown keys |
| Error codes (spec: `timeout, rate_limited, upstream, schema`) | api.md, OpenRouter Decisions page | ⚠️ Direct: 401, 422, 429, 529. OpenRouter: 400, 401, **402 (insufficient credits)**, 403, 429, 502/503/524/529. No mapping for auth, credits or validation. Finding 6 |
| "retry-after <= 1 s" | api.md | ❌ unverified. TypeSafe docs say only "retry with exponential backoff"; no `Retry-After` header or rate-limit headers are documented |
| Limits | models.md (direct), OpenRouter Jev page | 64k tokens per request, 32k for state plus longest question (direct); OpenRouter page says 32k state+questions combined. Rate 100K tokens/s or 80 req/s direct, "subject to dynamic adjustment"; OpenRouter limits not stated. Spec's own bounds (2,000 chars, 20 paths, 12 x 20 lines, 40 dirs x 30 paths) are far under either |
| Pricing | models.md | $42 per billion input tokens, output free (direct). OpenRouter price LIVE-UNVERIFIED (recon lead remains open) |
| `$.process.run(cmd, { env: { CV_JEV_KEY } })` | code.claude.com mods api, reference, test pages | ❌ Finding 1 |
| `userConfig.openrouter_key sensitive: true`, "delivered only through `register(on, options)`" | manifest-reference, components | ❌ Finding 2 |
| `tool.call` answers "with its stdout/stderr and exit status" | mods events page | ⚠️ `{ result }` is a free-form result; no documented exit-status field. Finding 9 |
| `session.append` rewrites stored rows | mods reference | ✅ exists: `next({ ...e, message })` rewrites a row's `content` |
| `classic.UserPromptSubmit` | mods events/reference | ✅ exists. `e` is the hook's stdin JSON; settings hooks run when the mod calls `next(e)`; a mod that answers without `next` skips them |
| "without `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS=1` ... `claude -p` has no function hooks" | mods overview | ❌ Finding 4 |

## 4. Critical Findings 🔴

### Finding 1 - `$.process.run` does not take a command string, and `env` is not in the official init

- Spec (C2): `$.process.run(cmd, { env: { CV_JEV_KEY } })`.
- Official docs (code.claude.com/docs/en/plugins/mods/api): "`$.process.run`: takes an argument list and uses no shell. It resolves to `{ exitCode, stdout, stderr }` ... rejects if the program can't start or is still running at the timeout, 30 seconds by default, 10 minutes at most". Examples are `$.process.run(['git','status'])`.
- Official test page (mods/test): for a `process.run` stub, "`e.argv` is the argument list and `e.init` holds `cwd` and `timeoutMs`". No `env`, no `stdin` listed in any official page I could read.
- A third-party gist and a search summary state `{ cwd, env, stdin, timeoutMs }`. The official docs do not corroborate that. The authoritative source is the `.d.ts` that Claude Code writes into `.claude-plugin/types/` for the installed build (mods/create "get the types for your build"); `mods/types/claude-code.d.ts` on GitHub could not be read through the fetcher.
- Consequence: the entire key path in C2 and the Security section depends on a parameter the official docs do not show. If `env` is absent, the only ways to hand the key to a child are argv (visible to `ps`, violates "never in a command line") or a mod-side `$.env.set` (scope and leakage to the Bash tool unverified) or stdin (also unconfirmed). A mod-side `$.http.fetch` (documented, returns `{status, ok, headers, text}`) removes the child process from the key path entirely but moves the HTTP client into TypeScript, which conflicts with "`compound-v-jev.py` is the only Jev client".
- The command string `cmd` must also become an argv array. A Bash tool command is a shell string; the mod would have to parse it into an argv or re-run it through an explicit `['bash','-c', ...]`, which reintroduces a shell.
- Alternative: none to recommend as a library swap. This is a design blocker for Section 8 Q1.

### Finding 2 - A sensitive `userConfig` value is exported to every plugin hook process as `CLAUDE_PLUGIN_OPTION_<KEY>`

- Spec (C2, Security): the key is "delivered only through `register(on, options)`" and "never appears in ... a log line".
- Official docs (manifest-reference, "Reference a saved value"): "`CLAUDE_PLUGIN_OPTION_<KEY>`: exported to hook processes **for every option**, with `<KEY>` uppercased". Components doc: "every hook process receives `CLAUDE_PLUGIN_ROOT` and `CLAUDE_PLUGIN_DATA` in its environment, plus `CLAUDE_PLUGIN_OPTION_<KEY>` for each user configuration value". Sensitive options are stored in secure storage but nothing exempts them from this export; the docs exempt only skill/agent content ("a sensitive value there becomes a placeholder").
- This plugin's `hooks/hooks.json` registers settings hooks on `Stop`, `UserPromptSubmit` and others. Each would receive `CLAUDE_PLUGIN_OPTION_OPENROUTER_KEY` once `userConfig.openrouter_key` exists. Their children (`claude -p`, `codex exec`, any Python script) inherit it unless scrubbed. The spec scrubs `CV_JEV_KEY`, a different variable name.
- The same fact also resolves recon lead "does `CLAUDE_ENV_FILE` reach hook processes" differently: no `SessionStart` env-file write is needed, because the UserPromptSubmit settings hook already receives the key through `CLAUDE_PLUGIN_OPTION_*` with no mod at all. That makes the mod unnecessary for the hook path and widens the key's exposure to all hooks of the plugin.
- Not exported: to commands run through the Bash tool (docs: path variables "aren't present in the environment of commands Claude runs through the Bash tool"; that sentence names the path variables, and I found no explicit statement for `CLAUDE_PLUGIN_OPTION_*`, so treat as probable, not verified), and to monitors.
- Alternative: name the option so the export is intended (`CLAUDE_PLUGIN_OPTION_OPENROUTER_KEY`), have `compound-v-jev.py` read and delete it, and scrub it in every subprocess env; or keep the key outside `userConfig` entirely (macOS Keychain read by the mod).

## 5. High-Priority Findings 🟠

### Finding 3 - Earlier mods in the chain can observe the key-bearing `process.run` call

- Docs (mods/events, "The order mods run in"): every mods API call is itself an event; "a mod earlier in the chain can observe, rewrite, or refuse your call". `sec-default@builtin`, organisation `prependPlugins`, then user-installed mods run first. "A later mod can't stop an earlier one from seeing an event." Mods are unsandboxed and can "read your secrets: environment variables and settings files", and a process a mod starts runs outside the Bash sandbox.
- A key in `init.env` (if supported) or argv is therefore visible to any user mod loaded before `compound-v-vault`, in-process. The Security section's "never appears in ... the transcript" is true only for the model's view, not for other mods. Mod order among user-installed mods is not controllable by this plugin.
- Third-party corroboration: dash.security "Claude Mods: the new attack surface built in".

### Finding 4 - The function-hook gate described in the spec is stale; the version floor is 2.1.287, not 2.1.219

- Spec (C2): "`claude -p` without `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS=1`" has no function hooks.
- Docs (mods/overview): "Mods require Claude Code v2.1.287 or later, and they're on by default ... If you set `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS` during early access, remove it. Claude Code v2.1.287 and later ignores it, so setting it to `0` doesn't keep mods off." Table "Where mods run": `claude -p` and the Agent SDK: hooks run **Yes**; cloud sessions: yes for a plugin that reaches the cloud session; WSL Desktop sessions: no.
- Local AGENTS.md states a Claude Code floor of 2.1.219 for the plugin overall. A mod needs 2.1.287. On 2.1.219-2.1.286 the module is not loaded, so the "without the mod" path must be the default degrade (it is, by design), but the banner reason and acceptance criterion 1 should not say "function hooks off"; say "Claude Code < 2.1.287 or mods disabled (`disableAllHooks`, `--safe-mode`, managed `allowManagedModsOnly`)".
- Other disable paths the spec lacks: `disableAllHooks: true`, `--safe-mode`, `allowManagedModsOnly`, and `claude plugin test` reports "hooks modules are turned off" with a reason.

### Finding 5 - Request shape: options need descriptions, questions are a named map, Noul has a different answer shape

- See Section 3. `--options a,b,c` cannot be sent as-is; every option needs a description string (docs: descriptions should "separate the options from each other"). The label set for T3 (`unknown, user-facing-major, user-facing-minor, plumbing`) and onboarding layers (`ui, api, domain, ...`) need authored descriptions, and **description wording moves accuracy**: the cited evaluation (recon F5) reports ±5-15 pp from wording changes. The descriptions are part of the calibrated artefact and must be versioned with it.
- "Unknown first" depends on JSON object key order. Python dicts and `json.dumps` preserve insertion order; any intermediate sort (`sort_keys=True`) silently reorders options and, per the jaggedness page, "the model leans toward the option that comes first".
- Documented jagged edges (docs.typesafe.ai/model-jaggedness/jev-1.13.md, 9 items): literal reading, math/counting, numeric representations, date/time comparison, indirection, irrelevant context, adversarial content ("State is data, and `jev-1.13` does not treat it as hostile by default"), contradictory criteria, generation. Spec C3-C5 pass raw user prompt text and file heads in `state`; that is the adversarial-content case. The Security section already accepts it.

## 6. Medium Findings 🟡

### Finding 6 - Error taxonomy has no home for auth, credits and validation failures

- 401, 402, 403 (OpenRouter), 400/422 (schema rejected by the server) are not in the spec's reason lists. A 402 or 401 mapped to `upstream` hides a configuration fault from the banner. Add distinct reasons (for example `auth`, `credits`) or document the mapping. 524/529 are provider timeouts/overload and map to `upstream`.

### Finding 7 - Noul has no probability map; spec's `probs` for batch Nouls must be defined

- C4's "`yes >= confidence_min`" is consistent with the single `noul` float. C1's output contract (`probs?`) needs a stated shape for Noul (`{yes: p}`), else eval tooling and the telemetry line diverge between Choice and Noul.

### Finding 8 - Floating alias `~typesafe/jev-latest` versus the calibrated threshold

- `jev-latest` -> `jev-1.13.0` today (models.md, 2026-10-05); `jev-preview` is currently identical. Docs: pin version ids "if you've tuned thresholds against particular versions". Spec records `model` per call, which is good (the response's resolved `model` field gives `jev-1.13.0`), but `confidence_min` "comes from the report" and `active` mode is a human decision on that report: an alias move silently invalidates both. On OpenRouter the pinned id is `typesafe/jev-1.13`.
- Also the cited evaluation (recon F5) says fixed thresholds missed their target on 47% of held-out splits: the spec already notes this.

### Finding 9 - `tool.call` `{ result }` carries a result, not an exit status

- Docs: "return an object with a `result` field, such as `{ result: 'Skipped by my-mod' }`, without calling `next`. ... no permission prompt appears and the tool doesn't run, so the result you return is all Claude learns". Results from `next` carry `deny` and `isError`. Replacing a Bash call therefore means synthesising text for stdout, stderr and exit code; Claude no longer sees the real Bash tool result shape, and "answers the tool call with its stdout/stderr and exit status" is a formatting convention the mod invents. Permission prompts and sandbox rules for that command are also skipped, because the mod bypasses `next`.
- Hook timing: a mod hook has a 10 s own-time limit, excluding time inside mods API calls (so `process.run` is not counted), but `process.run` itself defaults to 30 s. The `UserPromptSubmit` settings hook budget is 25 s (hooks.json). The spec's `timeout_ms.hook: 1500` is far inside both.

### Finding 10 - Python 3.9 on the maintainer's machine; `Retry-After` unverified

- KB (2026-07-26): macOS system `python3` is 3.9.6. `urllib.request` is fine; avoid 3.10+ syntax in the new script (`match`, `X | Y` annotations without `from __future__ import annotations`). Not rechecked today (no Bash).
- TypeSafe documents no `Retry-After` header; the "retry once honouring `retry-after` <= 1 s" rule needs a fallback when the header is absent.

## 7. Design Constraints for the Plan

MUST:
- MUST treat the key-delivery mechanism as unresolved until the build's own `.claude-plugin/types/` declarations (or a `claude plugin test` stub of `process.run`) show whether `init` accepts `env`. Do not write C2 task text that assumes `env`.
- MUST write every `$.process.run` call as an argv array, never a command string.
- MUST decide explicitly whether `CLAUDE_PLUGIN_OPTION_<KEY>` reaching all plugin hook processes is acceptable. If a `userConfig` key is used, `compound-v-jev.py` and every script that spawns a child (`claude -p`, `codex exec`) MUST scrub both `CV_JEV_KEY` and the `CLAUDE_PLUGIN_OPTION_*` key variable from child environments, and the selftest MUST assert both.
- MUST NOT claim the key is invisible to other mods; scope the claim to "not in the model's Bash environment, command line, files or transcript".
- MUST send Choice questions as `criteria` maps with a description per option, preserve insertion order (no `sort_keys`), and version the descriptions with the calibration report.
- MUST send questions as a named object, and parse `answers.<name>` with `type`-specific shapes (`choice`: `choice`, `probabilities`, `confidence`; `noul`: `noul` float). Parsers MUST ignore unknown keys (OpenRouter adds `id`, `provider`, `usage.cost`).
- MUST define distinct handling for 401/402/403/400/422, and map 429/502/503/524/529 to `unavailable`.
- MUST record the response's resolved `model` (`jev-1.13.0`) in every telemetry line and in the eval report; `active` mode MUST be gated on a report produced against the same resolved model.
- MUST pin `typesafe/jev-1.13` for `active` mode and for the calibration run; floating `~typesafe/jev-latest` is acceptable only for `shadow` and for `detect_ui`/onboarding if the monotonic/human-gated argument is kept.
- MUST gate mod behaviour on Claude Code >= 2.1.287 and describe the off-reasons correctly (Finding 4); the plugin's overall floor stays 2.1.219 and the mod is optional.
- MUST confirm the System One path with one live OpenRouter call (or the TypeSafe OpenAPI document at api.typesafe.ai/docs) before the plan locks `CV_JEV_BASE_URL` + path, because Section 3 is doc-derived only.
- MUST keep `compound-v-jev.py` free of Python >= 3.10 syntax while `python3` 3.9 is the macOS system interpreter.

MUST NOT:
- MUST NOT add `typesafe_sdk`; the wire format is small and documented (charter holds).
- MUST NOT print `usage.cost` or compute spend; it is measured by OpenRouter, but the spec's no-cost-output rule and the CI no-fabricated-metrics check stand.
- MUST NOT rely on `Retry-After` being present.
- MUST NOT assume `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS` has any effect on 2.1.287+.
- MUST NOT use Jev for model routing or RAG skip gating (recon F5; already out of scope in the spec).

## 8. Open Questions for the Human

1. Key transport. Given Findings 1-3, which is acceptable: (a) `userConfig` key arriving to hooks as `CLAUDE_PLUGIN_OPTION_*` with scrubbing and no mod at all for the hook path; (b) a mod that calls `$.http.fetch` itself (key never leaves the Claude Code process; HTTP client duplicated in TypeScript); (c) a mod that spawns the script only if `process.run` env is confirmed; (d) macOS Keychain read by the script?
2. If the key is exposed to all plugin hooks (Finding 2), is that acceptable for a key that spends the maintainer's OpenRouter credits, given that the plugin's other hooks (including third-party-pluggable ones through `claude -p`) run with it?
3. Pin or float: should T3 `shadow` use `typesafe/jev-1.13` from day one so the calibration set is one model version?
4. Is a live OpenRouter call with a throwaway key allowed during planning to settle the path, Noul shape and the actual `Retry-After`/rate-limit headers?
5. OpenRouter `provider` request preferences include data-collection controls (per the Decisions API page). Should the spec's egress block set them, since request text and file paths leave the machine?

## 9. Knowledge Base Updates

- Created `docs/superpowers/library-audit/_knowledge-base/typesafe-jev-openrouter.md` (Jev models, wire shape, errors, limits, OpenRouter paths, all dated 2026-10-05).
- Created `docs/superpowers/library-audit/_knowledge-base/claude-code-mods.md` (mods gate and version, `process.run`, `userConfig` export, chain visibility, `tool.call` result, dated 2026-10-05).
- Agent memory: dated drift facts written under `.claude/agent-memory/superpowers-v-doc-validator/`.

## Sources (all accessed 2026-10-05)

- https://docs.typesafe.ai/models.md, /api.md, /primitives/choice.md, /model-jaggedness/jev-1.13.md, /sdk/python/usage.md, /llms.txt
- https://openrouter.ai/docs/guides/community/jev, /typesafe-sdk; https://openrouter.ai/docs/api/api-reference/alphadecisions/submit-a-decisions-questions-and-answers-request; https://openrouter.ai/typesafe
- https://code.claude.com/docs/en/plugins/mods/{overview,api,events,reference,test}; /plugins/manifest-reference; /plugins/components
- https://dash.security/blog/claude-mods-the-new-attack-surface-built-in; https://gist.github.com/ruvnet/a485e930b148185197fc53fd38b429ea (third-party, used only to flag the `env`/`stdin` claim as uncorroborated)
