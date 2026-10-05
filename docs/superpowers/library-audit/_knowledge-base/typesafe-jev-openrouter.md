# TypeSafe Jev / OpenRouter Library Knowledge Base

Maintained by Compound V Phase 1C validator. Append at the bottom.

---

## Updated 2026-10-05 - jev-classifier-foundation-design

Method: WebFetch/WebSearch only (Context7 absent). No live call made; LIVE-UNVERIFIED items are marked.

- Models (docs.typesafe.ai/models.md, 2026-10-05): current `jev-1.13.0`; `jev-latest` and `jev-preview` both alias it. Pricing direct: $42 per billion input tokens, output free. Limits: 64k tokens per request, 32k for state plus longest question; 100K tokens/s or 80 req/s, dynamic. Docs recommend pinning version ids once thresholds are tuned.
- OpenRouter ids (openrouter.ai/typesafe): `typesafe/jev-1.13`, `~typesafe/jev-latest`, `typesafe/jev-router` (chat router, different product). OpenRouter listing date 2026-09-18 per search summary; no BYOK, billed to the OpenRouter account.
- Paths: OpenRouter System One `POST https://openrouter.ai/api/v1/systemone` (SDK appends `/v1/systemone` to base `https://openrouter.ai/api`); direct `POST https://api.typesafe.ai/v1/systemone`. OpenRouter's Decisions API page documents a separate `/api/alpha/decisions` path. LIVE-UNVERIFIED.
- Auth: `Authorization: Bearer <key>`.
- Request: `{state, model, questions: {<name>: {type: "choice"|"noul"|"score", instructions, criteria}}}`. Choice `criteria` is a map option -> description, up to 255 options. `questions` is a named object.
- Response: `{model (resolved), answers: {<name>: ...}, usage{input_tokens, output_tokens}}`. Choice: `choice`, `confidence`, `probabilities` (sum 1). Noul: `noul` float only. OpenRouter adds `id`, `provider`, `usage.cost`.
- Errors: direct 401, 422, 429, 529. OpenRouter 400, 401, 402, 403, 429, 502/503/524/529. No documented `Retry-After`; docs say exponential backoff.
- Jagged edges (jev-1.13): 9 listed, including option-order bias (leans to first option), adversarial state, no arithmetic/dates.
- Open: OpenRouter price, OpenRouter rate limits, the Decisions-path vs systemone-path relationship.
