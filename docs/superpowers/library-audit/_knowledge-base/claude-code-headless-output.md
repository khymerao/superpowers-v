# Claude Code Headless Output Library Knowledge Base

Maintained by Compound V Phase 1C validator. Append at the bottom.

---

## Updated 2026-10-08 - t3-measurement-and-eval-design

Method: WebFetch only (Context7 needs OAuth). Sources: code.claude.com/docs/en/headless, code.claude.com/docs/en/agent-sdk/typescript, learn.chatgpt.com/docs/non-interactive-mode, docs.typesafe.ai/models.md. No live call made.

- `claude -p --output-format json` (headless docs, 2026-10-08): single JSON object; text in `result`; also `session_id`, `total_cost_usd`, per-model cost breakdown. Headless docs say `--bare` "will become the default for `-p` in a future release"; bare skips OAuth/keychain login.
- `SDKResultMessage` success arm (SDK docs, 2026-10-08): `duration_ms`, `duration_api_ms`, `is_error`, `num_turns`, `result`, `stop_reason`, `total_cost_usd`, `usage`, `modelUsage`, `permission_denials`, optional `structured_output`, `terminal_reason`. Error arm (`error_max_turns`, `error_during_execution`, `error_max_budget_usd`, `error_max_structured_output_retries`) has `errors: string[]` and NO `result`.
- `usage` = `BetaUsage` main agent loop only: `input_tokens`, `output_tokens`, `cache_creation_input_tokens` and `cache_read_input_tokens` (nullable in `Usage`, non-null in the result's `NonNullableUsage`). `modelUsage` covers all model calls.
- `codex exec --json` (OpenAI docs, 2026-10-08): events `thread.started`, `turn.started`, `turn.completed`, `turn.failed`, `item.*`, `error`; the docs sample of `turn.completed` carries `usage` with `input_tokens`, `cached_input_tokens`, `output_tokens`, `reasoning_output_tokens`. Docs do not promise it on every event. The repo's classify route omits `--json` (`compound-v-classify-request.py:329-338`).
- Jev (docs.typesafe.ai/models.md, 2026-10-08): `jev-1.13.0` only; `jev-latest` and `jev-preview` alias it; no deprecations. docs.typesafe.ai/jaggedness.md returned 404.
