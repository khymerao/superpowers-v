# Recon — Jev (System One) classifier via OpenRouter for Compound V (2026-10-05)

*This recon is evidence to widen the brainstorm's questions, not a conclusion to converge on. VERIFIED FACTS / CONSTRAINTS are provisionally binding (1B/1C revalidate); UNVERIFIED LEADS are questions until validated; SUGGESTED DIRECTIONS are read last (directions-late) and are some of several possibilities — generate alternatives that ignore them.*

## QUESTIONS TO ASK
- Don't assume "Jev on OpenRouter" means one thing: `typesafe/jev-router` (a chat-completions model router) and `~typesafe/jev-latest` / `typesafe/jev-1.13` (the System One classifier) are different products with different APIs [F2][F3][F4]. Ask which one is meant before designing.
- Don't put Jev on zero-shot model routing or a RAG "skip retrieval" gate without labelled data: an independent evaluation found Jev near chance on model routing and called RAG skip gates unsafe [F5]. Ask which decision points have labelled outcomes to calibrate on.
- Don't let a classifier answer override a deterministic fail-closed gate (Layer A overrides, sensitive paths). Ask whether Jev may only *demote inside an already-bounded slot* (T3) or also *escalate*.
- Don't design key handling before asking where the key lives today (keychain, 1Password, `.env`, shell profile) and whether the plugin may write to `CLAUDE_ENV_FILE` [F7].
- Don't skip the egress question: request text, file paths and taxonomy hints leave the machine to OpenRouter and TypeSafe. Ask if that is acceptable for every repo the plugin runs in, or opt-in per repo.
- Don't forget the stdlib-only, no-daemon charter: the official client is `typesafe_sdk`; ask whether a pip dependency is acceptable or a raw HTTP call is required.
- Don't assume latency: TypeSafe docs publish none; one paper measured a range [F5]. Ask what budget the `UserPromptSubmit` hook (25 s timeout today) should give Jev.
- Ask what the fallback chain is when the key is absent, OpenRouter returns 429, or confidence is low (current Sonnet `claude -p` T3? deterministic FULL?).

## VERIFIED FACTS / CONSTRAINTS
- Jev evaluates a `state` against typed questions: Choice (one of N), Score (levels), Noul (yes/no); returns probabilities, not text [F1].
- Text input only; 64k tokens per request, 32k for state plus longest question; all questions in one request share the state and run in parallel [F1].
- Rate limits are published but "can change without notice" [F1].
- Known jagged edges in jev-1.13: literal reading, no counting/arithmetic, date comparison, multi-hop indirection, accuracy drops with irrelevant state, adversarial content in state can move the answer, leans toward the first Choice option, not a generator [F1].
- The Python SDK supports OpenRouter by setting `api_key=OPENROUTER_API_KEY`, `base_url="https://openrouter.ai/api"`, `model="~typesafe/jev-latest"`; also env vars `TYPESAFE_API_KEY` / `TYPESAFE_BASE_URL` [F2].
- OpenRouter lists `typesafe/jev-1.13`, `typesafe/jev-router`, `~typesafe/jev-latest`; only `jev-router` appears in the public `/api/v1/models` chat-model list [F3][F9].
- `typesafe/jev-router` picks a generative model and reasoning effort per request through OpenAI-compatible chat completions; it is cache-aware and prefers not to switch models [F4][F9].
- Independent paired evaluation (13,923 cases, jev-1.13 vs Laya) [F5]:
  - Jev strong on tool selection (99.5%), large label sets (81% at 60+ labels), injection screening (98%), groundedness;
  - option-order flips 1.8% (vs 30.3% Laya); ECE 0.080;
  - model routing near chance (~50%) for both; RAG relevance gating ~61%; "RAG skip gates" listed as unsafe;
  - wording variations move accuracy ±5-15 pp; fixed thresholds missed their target on 47% of held-out splits;
  - measured latency 83-325 ms.
- TypeSafe's RAG cookbook pattern: per retrieved passage, one request with four Nouls (relevant? usable evidence? contradicts the query premise? instructs the model?); thresholds in code route each passage to evidence / conflict / drop; evidence and conflicts reach the generator in separate blocks [F6].
- TypeSafe's skill-suggestion cookbook: two requests per turn (rank whole roster + "needs a skill at all?", then verify top 3 with full text); injects one hint line, never removes the roster [F8].
- Claude Code `SessionStart` hooks can persist env vars for later Bash commands by writing `export` lines to `$CLAUDE_ENV_FILE` [F7].
- The aitmpl secrets article uses a `PreToolUse` hook on `Edit|Write` that regex-scans content and exits 2 to block secret writes; it recommends env vars over hardcoding [F10].

## UNVERIFIED LEADS
- Whether `~typesafe/jev-latest` through OpenRouter charges the same as direct TypeSafe, and whether BYOK is required [F2] - verify in 1C.
- Whether OpenRouter's System One proxy path is `/api/v1/systemone` (SDK appends to base_url) - verify with a live call in 1C.
- Whether `CLAUDE_ENV_FILE` exports reach hook processes (not only the Bash tool) - the triage hook needs the key; verify in 1A/1C.
- gut-check (Laya-based) uses `confidence_threshold=0.55, min_margin=0.15` to escalate to System 2 [F11] - a pattern, not a Jev number.
- `jev-router` pricing shows `-1` (variable / pass-through) in the models API [F9]; real charging unclear.

## SUGGESTED DIRECTIONS
*Non-exhaustive — these are N of many possible framings; the brainstorm generates alternatives that ignore them.*
1. **Narrow slot swap:** Jev replaces only the T3 Choice (plumbing / minor / major / unknown) behind a confidence gate, falling back to the existing Sonnet `claude -p`; key from a `SessionStart` hook; shadow mode first against committed pre-eval records.
2. **System One as an evidence filter for System Two:** apply the RAG-passage pattern to V-memory recall and pre-flight inputs (relevance / usable / contradicts / injection Nouls per chunk) so Opus reads fewer, cleaner chunks; Jev never makes routing calls.
3. **Advisory layer everywhere, deciding nowhere:** Jev scores the judgement points (pre-flight skip, Sonnet-eligibility boxes, change-request detection, skill hint) and writes probabilities into records; Opus still decides; calibration data accumulates before any gate is allowed to act on it.

## SOURCES
- [F1] https://docs.typesafe.ai/models.md and https://docs.typesafe.ai/model-jaggedness/jev-1.13.md - accessed 2026-10-05 - model limits, primitives, failure modes
- [F2] https://docs.typesafe.ai/sdk/python/usage.md - accessed 2026-10-05 - "Use an OpenRouter API key and an OpenRouter model ID", base_url `https://openrouter.ai/api`, model `~typesafe/jev-latest`
- [F3] https://openrouter.ai/typesafe - accessed 2026-10-05 - lists jev-1.13, jev-router, ~jev-latest
- [F4] https://jev101.dev/compare/jev-vs-jev-router/ - accessed 2026-10-05 - "related listings, not the same API"
- [F5] https://arxiv.org/html/2610.02267 - accessed 2026-10-05 - "Fast Models, Slow Evidence", paired evaluation of System-1 decision models
- [F6] https://docs.typesafe.ai/cookbooks/classifying_rag_passages.md - accessed 2026-10-05 - four-Noul passage routing
- [F7] https://code.claude.com/docs/en/hooks - accessed 2026-10-05 (via search summary) - `CLAUDE_ENV_FILE` in SessionStart
- [F8] https://docs.typesafe.ai/cookbooks/skill_suggestion.md - accessed 2026-10-05 - two-request skill suggestion
- [F9] verified manually on 2026-10-05 against `curl https://openrouter.ai/api/v1/models` output: only `typesafe/jev-router` matched "jev"/"typesafe"
- [F10] https://aitmpl.com/blog/security-hooks-secrets/ - accessed 2026-10-05 - PreToolUse secret-detection hook, exit 2 blocks
- [F11] https://github.com/rfi-irfos/gut-check - accessed 2026-10-05 - EscalationPolicy thresholds
