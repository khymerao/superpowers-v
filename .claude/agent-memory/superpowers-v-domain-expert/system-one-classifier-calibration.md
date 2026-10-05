---
name: system-one-classifier-calibration
description: Jev/OpenRouter facts (32k window, 402 no-retry, ZDR undocumented for systemone) and small-n calibration rules for classifier cascades
metadata:
  type: reference
---

Checked 2026-10-05:
- OpenRouter Jev route: `/api/v1/systemone`, 32,000-token window (not 64k), `usage.cost` in each response, beta
  (https://openrouter.ai/docs/guides/community/jev).
- 402 is not retryable unless `limit_source=openrouter_in_flight_budget` (https://openrouter.ai/docs/api_reference/limits).
- `zdr` covers "model inference endpoints"; coverage of systemone undocumented.
- Small n: zero failures in n bounds the rate below 3/n (rule of three); thresholds missed held-out targets on about half
  of splits (arXiv 2610.02267).

**How to apply:** leads for any Jev/System One spec; re-verify before citing. Detail:
docs/superpowers/expert/_knowledge-base/system-one-classifiers.md. Related: [[claude-code-mod-secret-scope]]
