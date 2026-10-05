# Domain-Expert Audit (Phase 1B) - Jev classifier foundation

Spec: `docs/superpowers/specs/2026-10-05-jev-classifier-foundation-design.md`
Recon read first and deepened: `docs/superpowers/recon/2026-10-05-jev-system-one-classifier-via-openrouter.md`
Date: 2026-10-05. All web sources below were fetched on 2026-10-05.

## 1. Domain(s) Identified

1. **system-one-classifiers** - a hosted probabilistic decision model (TypeSafe Jev via OpenRouter) used as a cheap first stage in a classifier cascade, with confidence thresholds, calibration on a small labelled set, and data egress to two third parties.
2. **claude-code-plugin-secrets** - holding an API key in a Claude Code plugin/mod (`userConfig.sensitive`, `CLAUDE_PLUGIN_OPTION_*`, mod `tool.call` interception) without weakening the plugin's own guards.

## 2. Sources Consulted

**V-memory:** used the recall block in the prompt (recon doc, v2.9 Iron Invariants, `classify_via_codex` archaeology). One extra search, "plugin secret key egress third party", surfaced a binding precedent. `docs/superpowers/specs/2026-07-12-epic-autonomous-mode-design.md` (Sol R4) requires redaction "for token / authorization-header / private-key / URL-credential / multiline-secret forms; **fail closed** (omit the suspect evidence) when redaction can't complete, before any external-model egress". That rule is implemented as `redact`/`redact_uncapped` in `scripts/compound-v-epic-arbiter.py:687,727` (verified present). Constraint 6 below reuses it.

**Knowledge base:** `docs/superpowers/expert/_knowledge-base/` has no file for either domain (closest: `dev-workflow-triage-devex.md`, `agent-hook-context-injection.md`, which cover triage UX and hook output, not secrets or classifier calibration). Two new KB files were created (section 9).

**Agent memory:** `.claude/agent-memory/superpowers-v-domain-expert/` was empty.

**Official / primary (fetched):**
- [OpenRouter - Jev documentation](https://openrouter.ai/docs/guides/community/jev): endpoints, 32,000-token window, pricing per input token, `usage.cost`.
- [OpenRouter - API authentication](https://openrouter.ai/docs/api_reference/authentication): per-key credit limits, GitHub secret-scanning partnership.
- [OpenRouter - limits (402/429)](https://openrouter.ai/docs/api_reference/limits): `limit_source`, `Retry-After`, `GET /api/v1/key`.
- [OpenRouter - provider selection](https://openrouter.ai/docs/guides/routing/provider-selection): `data_collection`, `zdr` scope.
- [OpenRouter - logging/privacy](https://openrouter.ai/docs/guides/privacy/logging): providers keep their own retention policies.
- [Claude Code - plugin manifest reference](https://code.claude.com/docs/en/plugins-reference): `userConfig`, `sensitive`, `CLAUDE_PLUGIN_OPTION_<KEY>`.
- [Claude Code - mods overview](https://code.claude.com/docs/en/plugins/mods/overview): where mods run, trust model, version floor, `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS` ignored.
- [Claude Code - mods events](https://code.claude.com/docs/en/plugins/mods/events): `tool.call` short-circuit semantics, ordering against `PreToolUse` hooks.
- [Claude Code - mods reference](https://code.claude.com/docs/en/plugins/mods/reference): limits (`$.process.run` 30 s default, hook 10 s), `allowManagedModsOnly`, `plugin.register`.
- [Fast Models, Slow Evidence (arXiv 2610.02267)](https://arxiv.org/html/2610.02267): independent Jev evaluation (recon [F5]), re-read for thresholds and pre-screen cost.
- [Conformal Cascade (arXiv 2607.25018)](https://arxiv.org/abs/2607.25018): deferral by conformal set size instead of a tuned confidence threshold.
- [Rule of three (statistics)](https://en.wikipedia.org/wiki/Rule_of_three_(statistics)).

**Secondary (fetched, not vendor-authored, treat with care):**
- [jevwiki.ai - legal and data](https://jevwiki.ai/wiki/reference/legal-and-data.md): quotes TypeSafe MCA/DPA/Privacy Policy. The primary URLs it cites (`typesafe.ai/legal/mca`, `/data-processing`, `/privacy-policy`) were **not** fetched; verify before quoting them in user-facing consent text.
- [aicoder.com news, 2026-09-18](https://aicoder.com/news/news-20260918-openrouter-jev-beta): "Jev is live in beta on OpenRouter".
- [github.com/FrancoisChastel/jev-code](https://github.com/FrancoisChastel/jev-code): a third-party Claude Code integration of Jev (prior art).

**Issue trackers (fetched):**
- [anthropics/claude-code#62442](https://github.com/anthropics/claude-code/issues/62442): sensitive `userConfig` not persisted (2.1.150), closed as not planned.
- [anthropics/claude-code#79124](https://github.com/anthropics/claude-code/issues/79124): no way to supply plugin `userConfig` secrets to cloud sessions, closed as not planned.

**Community (Layer 2/3):**
- [HN: "Introducing System One Models and Jev"](https://news.ycombinator.com/item?id=49717558): about 520 comments, about 2026-09-17 (relative dates "18 days ago").
- `site:reddit.com` searches for Jev experience and for developer concern about plugins sending code to third parties: **no relevant hits**.
- `site:news.ycombinator.com` developer-tool telemetry opt-in: only general threads (Go toolchain, VS Code, GitHub CLI telemetry), none about LLM egress from a plugin. Not used as evidence.

Queries run: "TypeSafe Jev System One classifier OpenRouter API"; "OpenRouter data retention zero data retention policy provider logging 2026"; "LLM classifier cascade calibration small labeled set conformal threshold deferral"; "OpenRouter API key leaked GitHub automatic revocation secret scanning"; "site:news.ycombinator.com developer tool telemetry opt-in sends code to third party LLM"; "Claude Code plugin userConfig sensitive keychain secure storage"; "site:reddit.com OpenRouter API key exposed charges claude code"; "\"Fast Models, Slow Evidence\" System-1 decision models evaluation"; "TypeSafe Jev privacy policy data retention training on customer requests"; "site:reddit.com ClaudeAI plugin sends code to third-party API privacy company policy 2026"; "site:reddit.com Jev TypeSafe classifier experience accuracy"; "site:news.ycombinator.com TypeSafe Jev"; "OpenRouter API errors 402 insufficient credits 429 rate limit retry-after documentation".

## 3. Domain Constraints the Brainstorm Probably Missed

### 3.1 The vault mod as designed bypasses Compound V's own lane guard (highest severity)

- The spec's C2 has the mod run allowlisted scripts itself with `$.process.run` and "answer the tool call with its stdout/stderr". Claude Code's docs say verbatim: "`PreToolUse` hooks from every other settings file and from plugins' `hooks/hooks.json`: run after the last mod calls `next`, as part of Claude Code's own behavior. **A mod that answers `tool.call` without calling `next` keeps them from running**" ([mods events](https://code.claude.com/docs/en/plugins/mods/events)). The same page: "To answer a call yourself, return an object with a `result` field ... **no permission prompt appears and the tool doesn't run**".
- `hooks/hooks.json:33-37` registers `lane-guard.sh` as a `PreToolUse` hook on `Write|Edit|MultiEdit|NotebookEdit|Bash`, which is exactly the group that gets skipped. So every allowlisted invocation (`compound-v-preeval.py` writes and commits pre-eval records; `compound-v-onboard.py` writes taxonomy drafts) would run **without the lane guard, without permission rules, and without the user's prompt**.
- And outside the sandbox: "Mods aren't sandboxed. If you turn on sandboxing, the sandbox isolates the Bash commands Claude runs, and **a process that a mod starts runs outside it**" ([mods overview](https://code.claude.com/docs/en/plugins/mods/overview)).
- MUST NOT: answer `tool.call` for any command that can write to the repo, unless the mod reproduces the permission and lane decision first. The plan has to pick a design that keeps `next(e)` on the path, or confines the short-circuit to a read-only subcommand.

### 3.2 A `userConfig` key reaches every hook process of the plugin, not only one process

- Verbatim: "`CLAUDE_PLUGIN_OPTION_<KEY>`: **exported to hook processes for every option**, with `<KEY>` uppercased" ([plugin manifest reference](https://code.claude.com/docs/en/plugins-reference)). The `Hook commands` row of the env table lists `CLAUDE_PLUGIN_OPTION_<KEY>` as exported.
- A mod "is a plugin directory" whose `hooks/hooks.json` holds `modules` and can also hold settings hooks ([mods reference](https://code.claude.com/docs/en/plugins/mods/reference)). If `compound-v-vault` ships **inside** the `superpowers-v` plugin, the key's `userConfig` belongs to `superpowers-v`. Every settings hook it registers then gets `CLAUDE_PLUGIN_OPTION_OPENROUTER_KEY` in its env: `lane-guard.sh` (every Write/Edit/Bash), the banner, the nudges, and all their children (`python3`, `git`).
- So the spec's claim in **Security** ("`$.process.run` env of one allowlisted process") is false as written. The triage hook would get the key **without** any mod wrapper. That may make the `classic.UserPromptSubmit` wrapper unnecessary, and the exposure is wider than the spec states.
- Good news, also verbatim: these variables "aren't present in the environment of commands Claude runs through the Bash tool, in the main session or in a subagent". So the "never in the model's Bash environment" goal holds.

### 3.3 Mods run in more places than the spec assumes, and need a newer Claude Code

- "Mods require Claude Code v2.1.287 or later, and they're on by default" and "If you set `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS` during early access, remove it. Claude Code v2.1.287 and later ignores it" ([mods overview](https://code.claude.com/docs/en/plugins/mods/overview)). The spec's C2 text ("`claude -p` without `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS=1`") is stale.
- Per the "Where mods run" table, hooks **do run** in `claude -p` and the Agent SDK. So the nested `claude -p` T3 classifier (the existing fallback) also loads the vault mod and its key-bearing hook env. The "without the mod" path is now defined by the version floor, `--safe-mode`/`--bare`, `disableAllHooks`, or managed `allowManagedModsOnly`. It is no longer defined by `claude -p`.
- The plugin floor is `CV_VERSION_FLOOR=2.1.219` (`hooks/session-banner.sh:57`). Between 2.1.219 and 2.1.287 there are no mods, so the banner must report `Jev: off (claude < 2.1.287)` rather than a generic reason.
- Enterprise: under managed `allowManagedModsOnly`, "Only mods that count as your organization's ... load"; `plugin.register` lets an org guard refuse a mod after inspecting `e.uses` (env vars, calls) ([mods reference](https://code.claude.com/docs/en/plugins/mods/reference)). Expect Jev to be `off` on many Team/Enterprise machines. That must be a normal, silent state.

### 3.4 Sensitive `userConfig` storage is not reliable everywhere

- [#62442](https://github.com/anthropics/claude-code/issues/62442) (Claude Code 2.1.150, macOS): sensitive values "are **not persisted** ... lost on Claude Code restart". It was closed as not planned. Whether this still happens at ≥2.1.287 is **unverified** (1C should test it live).
- [#79124](https://github.com/anthropics/claude-code/issues/79124): cloud sessions cannot get plugin `userConfig` secrets ("neither exists in a fresh cloud VM"), also closed as not planned.
- SHOULD: the banner's `off` reason must tell "no key configured" apart from "key lost". The test plan must cover a cold restart.

### 3.5 Egress: what leaves the machine is more than the spec says

- C4 (`detect_ui`) sends **the first 20 lines of up to 12 tracked files**. That is file content, while C3 promises "No file contents" for T3. The first lines of PHP/config files are where credentials live (`wp-config.php`, `config/*.php`, `.env.example`, `settings.py`). C5 sends up to 40×30 tracked paths. C3 sends up to 2,000 chars of the user's prompt, which can contain pasted secrets.
- TypeSafe side, via a secondary source quoting the MCA: "TypeSafe may Process Telemetry **without restriction**, including to improve the Services", and telemetry "explicitly includes 'summary statistics and classifications'". Also: no training on inputs; DPA under EU SCCs Module 2, governing law Ireland ([jevwiki legal](https://jevwiki.ai/wiki/reference/legal-and-data.md); primary URLs not fetched). A secondary summary states that without enterprise ZDR "requests may be kept for some period for operations, abuse prevention or debugging" (search summary of jevaiguide.com; isolated, unverified).
- OpenRouter side: OpenRouter's `zdr` "filters model inference endpoints" and "Tool backends are not filtered by zdr" ([provider selection](https://openrouter.ai/docs/guides/routing/provider-selection)). The docs **do not say** whether `zdr` / `data_collection: deny` applies to `/api/v1/systemone`. The Jev guide page states no data-retention policy at all ([OpenRouter Jev](https://openrouter.ai/docs/guides/community/jev)).
- MUST: the `egress: ask` prompt names both processors (OpenRouter and TypeSafe) and the categories sent (prompt text, file paths, file heads), and it may not claim ZDR.

### 3.6 Calibration on 23-30 pairs cannot support a 90% claim

- With n = 30, observing 27/30 = 90% agreement has a 95% Clopper-Pearson lower bound of about 73% (standard binomial interval; not from a fetched source). Observing **zero** stricter-to-looser flips in 30 only bounds that rate below 3/30 = 10% ([rule of three](https://en.wikipedia.org/wiki/Rule_of_three_(statistics)): "the interval from 0 to 3/n is a 95% confidence interval").
- Independent evaluation: thresholds chosen on one half "exceeded [their target] in roughly half of splits". Rewording instructions "moves accuracy by 5-15 pp per track". Jev ECE ranges 0.080-0.143 across tracks, not a single 0.080 ([arXiv 2610.02267](https://arxiv.org/html/2610.02267)). The recon quoted only the 0.080 end.
- Practitioners on launch day: "if it puts a high confidence value on a wrong answer, thats still hallucinating, no?" and "Type safety is not factual correctness." ([HN 49717558](https://news.ycombinator.com/item?id=49717558), about 2026-09-17; one thread of about 520 comments, so this is a recurring theme in one thread, **not** the ≥10-thread consensus threshold).
- The literature alternative to a tuned `max(probs) ≥ 0.8` is deferral by conformal set size: "accept when the calibrated set collapses to a single answer, defer otherwise" ([Conformal Cascade](https://arxiv.org/abs/2607.25018)). It still needs a held-out labelled set; its sample-size needs were not stated in the abstract.

### 3.7 Pre-screen economics are smaller than they look

- "As a safety pre-screen with fallback, cost savings shrink dramatically once the pre-screen's token expense is included - dropping from claimed 23.9% to actual 4.3% savings" ([arXiv 2610.02267](https://arxiv.org/html/2610.02267)). In `shadow` mode Jev is pure added cost and latency on every T3. The spec forbids printing cost, so nobody will see this. That is fine for the anti-fabrication rule, but the rollout decision then has no cost input at all (see open question 5).

## 4. Common Traps in This Domain

1. **Short-circuiting a tool call to inject a secret** silently drops every downstream guard: `PreToolUse` hooks, permission prompts and the sandbox (3.1).
2. **Assuming "sensitive" means "scoped".** In Claude Code it means "stored in the keychain". It does not mean "given to one process" (3.2).
3. **Same-data threshold selection.** Picking `confidence_min` from the same 30 records you report agreement on overstates performance. Thresholds miss their target on about half of held-out splits ([F5](https://arxiv.org/html/2610.02267)).
4. **Batch with a shared state across unrelated questions.** All questions in one request share one `state` ([recon F1]). C5 describes "state = the directory name plus up to 30 tracked file paths inside it" **per directory**, and also "one `batch` request". Both cannot hold. Putting all 40 directories in one state turns 39/40 of it into irrelevant state, which recon F1 lists as a known accuracy drop.
5. **Retrying 402.** OpenRouter: 402 with `limit_source: openrouter_credits` or `openrouter_key_limit` is not transient. Only `openrouter_in_flight_budget` carries `Retry-After` ([OpenRouter limits](https://openrouter.ai/docs/api_reference/limits)). The spec's reason list has no slot for 402.
6. **Context-window mismatch.** The recon cites 64k tokens (direct TypeSafe); OpenRouter's Jev page says "32,000 tokens. That's the `state` you send plus the questions" ([OpenRouter Jev](https://openrouter.ai/docs/guides/community/jev)). Budget for 32k on this transport.
7. **Treating a beta alias as stable.** Jev is "live in beta on OpenRouter" ([aicoder, 2026-09-18](https://aicoder.com/news/news-20260918-openrouter-jev-beta)). The `~typesafe/jev-latest` alias can move under recorded calibration data.
8. **Prompt-text steering.** Adversarial content in state moves the answer ([recon F1]). Embedded-payload injection detection is much weaker than detection of standalone attacks ([F5](https://arxiv.org/html/2610.02267)). C4's file heads are attacker-writable in any repo with outside contributors.

## 5. Regulatory / Compliance Notes

- **Processor disclosure (GDPR Art. 28-style relationship):** TypeSafe offers a DPA with EU SCCs Module 2 (per secondary source). Via OpenRouter, the customer's contract is with OpenRouter, and OpenRouter states that providers "have their own data retention policies" ([OpenRouter logging](https://openrouter.ai/docs/guides/privacy/logging)). A developer using this plugin on an employer's repo is sending employer data to two sub-processors. Opt-in per repo (spec C7) is the right default. The consent text must be accurate.
- **No published ZDR for this route.** Enterprise ZDR from TypeSafe is "by contacting TypeSafe" (search summary; isolated). OpenRouter's `zdr` coverage of the System One API is undocumented. Do not claim "no retention".
- **Telemetry carve-out:** TypeSafe may use "classifications" without restriction (secondary source quoting MCA §4.3). The labels Compound V asks for (`plumbing`, `ui`, ...) are low-sensitivity, but the consent text should not say "nothing is retained or reused".
- **Credentials:** OpenRouter is a GitHub secret-scanning partner. It emails on detection rather than auto-revoking ("delete the compromised key and create a new one"), and recommends "setting a credit limit on every key" ([OpenRouter auth](https://openrouter.ai/docs/api_reference/authentication)).
- No sector regulation (HIPAA/PCI) is triggered by the feature itself. It is triggered by what is in the user's repo, which is why file-content egress (3.5) matters.

## 6. Recent Breaking Changes (last 12 months)

| Date | Change | Source |
|---|---|---|
| ≥ v2.1.287 (2026) | Mods GA, on by default; `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS` ignored; mods run in `claude -p` / Agent SDK | [mods overview](https://code.claude.com/docs/en/plugins/mods/overview) |
| 2026 (v2.1.271 / .269) | `userConfig.options` and `/config` rows; sensitive options excluded from `/config` | [manifest reference](https://code.claude.com/docs/en/plugins-reference) |
| about 2026-09-17/18 | Jev launched; OpenRouter listing in beta; `~typesafe/jev-latest` alias | [HN](https://news.ycombinator.com/item?id=49717558), [aicoder](https://aicoder.com/news/news-20260918-openrouter-jev-beta) |
| 2026 | OpenRouter 402 split into `limit_source` values with `remedy_hint`; in-flight budget is retryable | [OpenRouter limits](https://openrouter.ai/docs/api_reference/limits) |
| closed not planned | Sensitive `userConfig` persistence bug (#62442), cloud-session secrets gap (#79124) | issues linked above |

## 7. Design Constraints for the Plan (non-negotiable)

1. **MUST NOT short-circuit `tool.call` for a repo-writing command.** For any allowlisted invocation that can write files or commit (`compound-v-preeval.py`, `compound-v-onboard.py`, `compound-v-classify-request.py` when it writes), the mod must either call `next(e)`, so that `PreToolUse` `lane-guard.sh`, permission rules and the sandbox run, or prove an equivalent check runs first. Answering with `{ result }` skips plugin `PreToolUse` hooks and permission prompts and runs outside the sandbox ([mods events](https://code.claude.com/docs/en/plugins/mods/events), [mods overview](https://code.claude.com/docs/en/plugins/mods/overview)). The plan states which design it uses and adds a test showing that lane-guard still fires for an allowlisted command inside a job lane.
2. **MUST correct the key-path claim.** A `userConfig.sensitive` key on the `superpowers-v` plugin is exported as `CLAUDE_PLUGIN_OPTION_OPENROUTER_KEY` to **every** settings-hook process of that plugin ([manifest reference](https://code.claude.com/docs/en/plugins-reference)). Either (a) ship the vault as a **separate plugin** that registers no settings hooks, with `superpowers-v` reading the key only through the mod's process env, or (b) keep it in-plugin. Option (b) requires every hook script (`lane-guard.sh`, banner, nudges) to `unset CLAUDE_PLUGIN_OPTION_OPENROUTER_KEY` before spawning children, and the Security section must state the wider exposure. Acceptance criterion 4's grep test must include hook child environments.
3. **MUST gate on Claude Code ≥ 2.1.287 for the mod path** and report `Jev: off (claude <2.1.287)` below it. Drop the `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS` condition from the spec, because it is ignored ([mods overview](https://code.claude.com/docs/en/plugins/mods/overview)).
4. **MUST account for mods loading in nested `claude -p`.** The T3 fallback's nested session loads the plugin and its mod. The plan states whether the nested session should receive the key, and prevents recursion (a Jev call from inside the fallback of a Jev call).
5. **MUST treat "mod refused/absent" as a normal silent state.** This covers managed `allowManagedModsOnly`, `--safe-mode`, `disableAllHooks`, cloud sessions without `userConfig` ([#79124](https://github.com/anthropics/claude-code/issues/79124)), and a lost sensitive value ([#62442](https://github.com/anthropics/claude-code/issues/62442)). In each case the result is `unavailable(no_key)` with exit 0 and one banner line.
6. **MUST NOT send file contents from sensitive paths.** C4 sampling excludes any path matching Layer A sensitive globs and common secret-bearing names (`wp-config.php`, `.env*`, `*secret*`, `*credential*`, `config/*.php`, keys and certs). The 20-line head, and the T3 request text, pass through the repo's existing external-egress redaction (`compound-v-epic-arbiter.py` `redact`, the Sol R4 precedent) before egress. If redaction cannot complete, that evidence is omitted (fail closed); it is never sent raw. The spec's "no file contents" wording must be reconciled with C4, because C4 sends contents.
7. **MUST make egress consent name both processors and the data classes**: OpenRouter and TypeSafe; prompt text up to 2,000 chars, file paths, and file heads. It MUST NOT claim zero retention, because ZDR on `/api/v1/systemone` is undocumented ([provider selection](https://openrouter.ai/docs/guides/routing/provider-selection), [OpenRouter Jev](https://openrouter.ai/docs/guides/community/jev)). If a `zdr: true` or `data_collection: deny` body field is accepted by the System One API (1C to verify), send it.
8. **MUST map HTTP 402 to `unavailable` with no retry**, using a reason such as `credits` (or `upstream` with `limit_source` recorded). Retry only when `limit_source == openrouter_in_flight_budget` and `Retry-After` ≤ 1 s in offline context ([OpenRouter limits](https://openrouter.ai/docs/api_reference/limits)). Also map 401/403 to `unavailable(no_key)`-class reasons, not `error`.
9. **MUST budget state for 32,000 tokens** (state plus questions) on the OpenRouter transport, not 64k ([OpenRouter Jev](https://openrouter.ai/docs/guides/community/jev)). Oversize input must truncate deterministically or return `error(bad_input)`. It must never be sent and allowed to fail upstream.
10. **MUST resolve C5's batch/state contradiction.** One shared state per request ([recon F1]) means either one request per directory (≤40 requests, offline context, bounded) or one request with a combined state. The combined-state option must be justified against the "irrelevant state lowers accuracy" edge. Recommended: per-directory requests, because onboarding is offline and human-gated.
11. **MUST pin the model id in recorded telemetry.** Record the model actually served (response field or `typesafe/jev-1.13`) in `jev-calls.jsonl` and the pre-eval record. Then an alias move of `~typesafe/jev-latest` invalidates calibration visibly. The eval report states the model id it calibrated.
12. **MUST report uncertainty, not just point agreement, in `eval --t3`.** Print n, the agreement, and a 95% binomial interval (Wilson or Clopper-Pearson). For the zero-flip criterion print the 3/n bound ([rule of three](https://en.wikipedia.org/wiki/Rule_of_three_(statistics))). If `confidence_min` is derived from data, derive it on a split disjoint from the one the agreement is reported on, or say plainly that it is in-sample ([F5](https://arxiv.org/html/2610.02267): thresholds missed target on about half of held-out splits).
13. **MUST include an instruction-wording perturbation in the eval**, alongside the option-permutation flip rate. Wording moves accuracy by 5-15 pp ([F5](https://arxiv.org/html/2610.02267)). Freeze the instruction text with a hash in the record so a later wording change is a visible recalibration event.
14. **MUST keep Jev monotone toward strictness in T3 `active`.** Layer A is unchanged and first. Jev may only choose a label ≥ as strict as the deterministic floor allows, and a Jev answer of `unknown` always falls through. This restates spec C3; it is listed because the HN signal ("high confidence value on a wrong answer") makes confidence alone insufficient.
15. **SHOULD document a dedicated OpenRouter key with a per-key credit limit** in the setup text ("We recommend setting a credit limit on every key", [OpenRouter auth](https://openrouter.ai/docs/api_reference/authentication)). Then a leaked key, or a runaway loop in shadow mode, is capped.
16. **SHOULD NOT send `HTTP-Referer` / `X-OpenRouter-Title` headers containing repo names or paths.** They are optional attribution headers ([OpenRouter auth](https://openrouter.ai/docs/api_reference/authentication)) and would leak repository identity.

## 8. Open Questions for the Human

1. **Vault packaging:** a separate `compound-v-vault` plugin (clean key scope, one more install step), or in-plugin with every hook scrubbing the env var (one install, wider exposure)? Constraint 2 forces a choice.
2. **Tool-call design given 3.1:** is it acceptable that the mod lets the Bash call proceed through `next(e)` and supplies the key some other way (for example a mod-registered tool or command that calls Jev, with the scripts asking the mod), even if that changes the C2 shape? Or must the script be launched from Bash, which then forces a re-implemented permission and lane check?
3. **`detect_ui` file heads:** is sending the first 20 lines of repo files to two third parties acceptable at all under `egress: allow`, or should C4 send paths only and drop the head sample?
4. **Nested `claude -p` and the key:** should the T3 fallback session be able to call Jev (it will load the mod), or should the parent strip the key for nested sessions?
5. **Cost visibility:** OpenRouter returns a measured `usage.cost` per response ([OpenRouter Jev](https://openrouter.ai/docs/guides/community/jev)). The spec bans printing cost. Is recording the measured value in `jev-calls.jsonl` (not printing it) allowed? Without it, the `shadow`→`active` decision has no cost input, and F5 shows pre-screen savings can collapse once pre-screen cost is counted.
6. **Calibration bar:** keep "≥90% on ≥30 pairs", knowing the 95% lower bound at 27/30 is about 73%? Or set the bar on the interval's lower bound and wait for more records?

## 9. Knowledge Base Updates

- Created `docs/superpowers/expert/_knowledge-base/system-one-classifiers.md`: Jev/OpenRouter transport facts, egress/processor matrix, error mapping, calibration rules for small n.
- Created `docs/superpowers/expert/_knowledge-base/claude-code-plugin-secrets.md`: `userConfig.sensitive` exposure matrix, mod `tool.call` short-circuit effects, where mods run, known storage bugs.
