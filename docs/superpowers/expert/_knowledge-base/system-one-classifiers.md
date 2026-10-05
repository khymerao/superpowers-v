# System One Classifiers (Jev / hosted decision models) Knowledge Base

Maintained by Compound V Phase 1B advisor. Append at the bottom on each pass.

---

## Updated 2026-10-05 - Jev classifier foundation (T3 / detect_ui / onboarding)

### Transport facts (OpenRouter route), checked 2026-10-05

| Fact | Value | Source |
|---|---|---|
| System One endpoint | `POST https://openrouter.ai/api/v1/systemone` (SDK appends `/v1/systemone` to base `https://openrouter.ai/api`) | [OpenRouter Jev](https://openrouter.ai/docs/guides/community/jev) |
| Decisions API (alpha) | `POST https://openrouter.ai/api/alpha/decisions` | same |
| Model ids | `typesafe/jev-1.13`, alias `~typesafe/jev-latest` | same |
| Context window on this route | 32,000 tokens, state plus questions (direct TypeSafe docs say 64k; budget for 32k here) | same |
| Billing | per input token; output free; `usage.cost` (USD) in every response | same |
| Status | "live in beta on OpenRouter" (2026-09-18) | [aicoder](https://aicoder.com/news/news-20260918-openrouter-jev-beta) |
| Auth | OpenRouter key only, `Authorization: Bearer` | [OpenRouter auth](https://openrouter.ai/docs/api_reference/authentication) |

### Error mapping matrix (OpenRouter)

| HTTP | Meaning | Retry? |
|---|---|---|
| 402 `limit_source=openrouter_credits` | balance too low | No |
| 402 `limit_source=openrouter_key_limit` | per-key credit cap hit | No |
| 402 `limit_source=openrouter_in_flight_budget` | transient in-flight budget; carries `Retry-After` | Yes, honour `Retry-After` |
| 429 | rate limit (OpenRouter or upstream); `X-RateLimit-*`, sometimes `Retry-After` | Only with `Retry-After` |

Source: [OpenRouter limits](https://openrouter.ai/docs/api_reference/limits). `GET /api/v1/key` returns usage and `limit_remaining`.

### Egress / processor matrix

| Party | Training on inputs | Retention | ZDR |
|---|---|---|---|
| OpenRouter | does not train | providers "have their own data retention policies" | `zdr` param "filters model inference endpoints"; coverage of `/v1/systemone` **undocumented** |
| TypeSafe | "will not train ... on your prompts" (Privacy Policy, via secondary source) | may retain for ops without ZDR (isolated report); may process telemetry incl. "classifications" "without restriction" (MCA §4.3, via secondary source) | enterprise, on request |

Sources: [OpenRouter logging](https://openrouter.ai/docs/guides/privacy/logging), [OpenRouter provider selection](https://openrouter.ai/docs/guides/routing/provider-selection), [jevwiki legal (secondary)](https://jevwiki.ai/wiki/reference/legal-and-data.md). Primary TypeSafe legal URLs (`typesafe.ai/legal/{mca,data-processing,privacy-policy}`) not yet fetched; fetch before quoting in consent text.

### Calibration rules for small labelled sets (generalizable)

- Report a binomial interval, not a point estimate. Zero observed failures in n bounds the rate below 3/n at 95% ([rule of three](https://en.wikipedia.org/wiki/Rule_of_three_(statistics))). At n = 30 that is 10%.
- Thresholds selected on one half missed their target on about half of held-out splits; instruction rewording moves accuracy by 5-15 pp; Jev ECE 0.080-0.143 across tracks ([arXiv 2610.02267](https://arxiv.org/html/2610.02267)).
- Alternative deferral rule: conformal set size ("accept when the calibrated set collapses to a single answer, defer otherwise") ([Conformal Cascade](https://arxiv.org/abs/2607.25018)).
- A pre-screen's own cost can erase most savings: 23.9% claimed vs 4.3% actual once pre-screen tokens were counted ([arXiv 2610.02267](https://arxiv.org/html/2610.02267)).
- Record the served model id with every call. An alias (`~...-latest`) can move under recorded calibration data.
- One Jev request has **one shared state**. Per-item states need per-item requests; a combined state adds irrelevant context, a known accuracy drop (TypeSafe jaggedness doc, recon F1).

### Community signal

- HN launch thread "Introducing System One Models and Jev" (about 520 comments, about 2026-09-17): recurring theme is confidently wrong answers ("Type safety is not factual correctness.") and requests for calibration benchmarks ([HN 49717558](https://news.ycombinator.com/item?id=49717558)). It is one thread, below the ≥10-thread consensus bar.
- Reddit: no relevant hits on 2026-10-05.

## Updated 2026-10-05 - Jev review fixes

### Error mapping matrix, additional rows (OpenRouter), checked 2026-10-05

| HTTP | Meaning (verbatim) | Client reason |
|---|---|---|
| 401 | "Invalid credentials (OAuth session expired, disabled/invalid API key)" | key problem (`auth`) |
| 403 | "Forbidden (insufficient permissions, guardrail block, or moderation flag)" | **not** only a key problem; guardrail blocks (content filter, prompt-injection detection) return 403 before any provider is reached |
| 408 | "Your request timed out" | timeout |
| 502 | "Your chosen model is down or we received an invalid response from it" | upstream |
| 503 | "There is no available model provider that meets your routing requirements" | upstream |

Source: [OpenRouter errors and debugging](https://openrouter.ai/docs/api_reference/errors-and-debugging).
Correction: the 2026-10-05 foundation audit (constraint 8) said ~~"map 401/403 to `unavailable(no_key)`-class
reasons"~~ → updated 2026-10-05: map 401 to a key reason; 403 needs its own reason or must be documented as
"key permission or content block". Compound V's vault today maps both to `auth` (`vault.tsx:102`).

### Client-side telemetry reasons (generalizable)

- Keep "no key configured" (`no_key`), "key rejected" (401) and "request blocked" (403 guardrail/moderation)
  apart: each has a different fix. A contract test that feeds every reason literal the transport emits through
  the parser stops a reason being silently rewritten to a catch-all.
