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

## Updated 2026-10-05 - jev-review-fixes-design

Method: repository read only (Context7 absent; no network call about Jev). Source: `plugins/compound-v-vault/hooks/vault.tsx`, `scripts/compound-v-jev.py`.

- Vault reason literals today: `unavailable` = auth, credits, rate_limited, upstream, timeout, disabled, no_key, egress, no_vault; `failed` (wire status `error`) = bad_input, schema. Parser tuples at `compound-v-jev.py:59-61` lack `no_key` (it degrades to `upstream`) until the review-fixes run lands.
- `parse_response` routes by `http_status` first when it is a non-2xx integer; the vault's `reason` is ignored in that case (`compound-v-jev.py:537-539`). A contract test over reasons must omit `http_status`.
- `prune` removes old non-directory entries by `lstat` mtime, which includes old symlinks (the link is unlinked, never its target). Spec wording says symlinks are never removed; mismatch recorded in the audit.
