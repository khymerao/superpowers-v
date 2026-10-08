# Library audit: T3 measurement and eval design (Phase 1C, 2026-10-08)

Spec: `docs/superpowers/specs/2026-10-08-t3-measurement-and-eval-design.md`

## 1. Tools Available

- Context7: DEGRADED. `ToolSearch context7` returned nothing; the harness reports `plugin:context7:context7` needs OAuth. Fallback was WebFetch of first-party docs (code.claude.com, developers.openai.com/learn.chatgpt.com, docs.typesafe.ai). Nothing below is cited to Context7.
- Bash is clamped to memory/git forms in this spawn; repo facts were read with Read/Grep.
- Manifests: none relevant. This spec adds no package dependency (scripts are stdlib-only Python per `.claude/rules/scripts.md`). The "libraries" are three CLIs/services: `claude -p`, `codex exec`, and Jev via the vault tool.
- V-memory: the prompt's recall block was used (Jev foundation plan/spec, next-stage handoff). Prior KB: `_knowledge-base/typesafe-jev-openrouter.md`, `backend-worker-clis.md`.
- Recon doc: none handed.

## 2. Libraries Mentioned

| Name | Spec context | Current (checked 2026-10-08) | Repo pin | Maintenance | Status |
|---|---|---|---|---|---|
| Claude Code CLI `claude -p --output-format json` | Part 1.1, result object parse | newest seen 2.1.294 (KB 2026-10-08); json output documented | floor 2.1.219 (AGENTS.md) | active | OK, with signature caveats in section 3 |
| Codex CLI `codex exec` | Part 1.1 "codex route wall_ms only" | `--json` emits `turn.completed` with `usage` (input_tokens, cached_input_tokens, output_tokens, reasoning_output_tokens in the docs sample) | verified 0.159.1 per AGENTS.md | active | OK |
| TypeSafe Jev `jev-1.13.0` via vault `jev_classify` | Eval 4 | `jev-1.13.0`; `jev-latest` and `jev-preview` both alias it; no newer model, no deprecation listed | `jev-latest` alias in use | active | OK, but alias moves (see MUST) |
| Published comparisons (LiteLLM, Classmethod, Wavect AnyJev option-order) | Why / Eval | Not independently verified; I did not fetch them | n/a | n/a | UNVERIFIED citations |

## 3. API Signatures Verified

| Claim in spec | Verified against | Result |
|---|---|---|
| `--output-format json` returns an object with the category in `result` | code.claude.com/docs/en/headless: "`json`: structured JSON with result, session ID, and metadata"; jq example `.result` | Confirmed (single object, not an array). |
| `duration_ms`, `duration_api_ms` | Agent SDK TS `SDKResultMessage` (docs fetched 2026-10-08) | Confirmed, number, on success and error arms. |
| `usage.input_tokens`, `output_tokens` | `Usage` = `BetaUsage`; `NonNullableUsage` on the result | Confirmed, number. |
| `usage.cache_read_input_tokens`, `cache_creation_input_tokens` | `Usage` type: both `number \| null`; the result's `NonNullableUsage` makes them non-null | Confirmed names. In the result they are numbers; a parser must still tolerate absent/null. |
| `result` is always present | SDKResultMessage error arms (`error_max_turns`, `error_during_execution`, `error_max_budget_usd`, `error_max_structured_output_retries`) have `errors: string[]` and NO `result` | DRIFT RISK: spec treats only "parse failure" as a non-answer. A well-formed JSON without `result` must be handled the same way. |
| success arm implies a real answer | `is_error: boolean` exists on the success arm too; headless docs: a failure inside the run (missing auth) "prints the failure as the result on stdout" | DRIFT RISK: `result` can carry an error message text. Gate on `is_error` and `subtype == "success"` before `parse_category`. Existing fail-closed enum parse likely rejects it, but the measurement must not be recorded as a clean sample. |
| `usage` covers the call | docs: `usage` covers the main agent loop only; `modelUsage` covers every model call incl. subagents/compaction and recommended for accounting | For `--tools ""` one-shot the main loop is the whole call, but a nested session loads the same plugins/hooks (see `_headless_env`, line 85). Prefer reading `modelUsage` too, or state that tokens are main-loop only. |
| `codex exec` token fields are `null` | `codex exec --json` stream carries `turn.completed.usage` | Spec's choice is valid but not forced: `build_codex_command` (`compound-v-classify-request.py:329-338`) omits `--json`, so the events file is not JSONL today. Adding `--json` would make codex tokens measurable. Docs sample does not promise every `turn.completed` has usage. |
| `total_cost_usd` exists | present on the result | Spec 4 forbids money figures; the field will be in the JSON and MUST NOT be stored or printed (anti-ruflo grep covers scripts/docs). |

Repo facts relevant to the swap (read 2026-10-08): argv at `compound-v-classify-request.py:480-485` has `--output-format text`, and a selftest at `:969-971` pins it to `text`; that test must change. Output sink cap `CLAUDE_STDOUT_CAP = 1 << 16` (:125) is ample for one result object; a truncated JSON would parse-fail into the `unknown` path, which is the intended fail-closed behaviour. `HEADLESS_TIMEOUT_S = 15` (:123).

## 4. Critical Findings

None. No library is deprecated, archived or stale.

## 5. High-Priority Findings

None by the staleness rubric. Two signature-level risks are listed as Medium because they do not need an alternative library.

## 6. Medium Findings

1. **Result-object states not covered (is_error / error subtypes).** See section 3. Without handling, an auth failure or `error_max_turns` could be recorded as a measured Claude sample with a `wall_ms` but no answer, biasing p50/p95 and the Claude-vs-Jev comparison.
2. **Measurement validity of `wall_ms` includes plugin/hook startup.** Docs: without `--bare`, `-p` loads hooks, plugins, MCP servers, CLAUDE.md. The repo forbids `--bare` (login is skipped, per header :439). So `duration_api_ms` and `wall_ms` differ by the host's startup cost, which is machine-specific. This is the correct thing to measure (the hook waits for the process), but the report must not present `duration_api_ms` as the saving. Docs also say `--bare` will become the default for `-p` in a future release: when that happens the login problem the header describes may change; re-verify then.
3. **Jev alias drift between repeats and between eval and shadow runs.** `jev-latest` and `jev-preview` alias `jev-1.13.0` today; the response `model` field reports the resolved id. The frozen protocol pins "model id" for Claude; it must pin and record Jev's resolved id too.
4. **Option-order bias is a documented jagged edge** (KB 2026-10-05, 9 listed edges including leaning to the first option). The spec's reversed-order variant is therefore well founded. The jaggedness page itself (docs.typesafe.ai/jaggedness.md) returned 404 this run; the edge list in the KB came from an earlier fetch and is not re-confirmed today.
5. **Rule of three and Wilson are not library issues**, but note the repo already has a Wilson implementation (`scripts/compound-v-cochange.py:333`, lower bound only, z = 97.5th percentile). The eval needs both bounds; reuse the constant, do not fork a second z.

## 7. Design Constraints for the Plan

MUST:
- Parse `claude -p --output-format json` as one object; require `type == "result"`, `subtype == "success"`, `is_error == false` and a string `result` before the category is trusted. Any other shape follows the existing non-answer path (`unknown`) and its measurement is recorded as failed, not as a latency sample.
- Read token fields defensively: absent or null becomes `null` in `measure`, never `0` (matches `.claude/rules/scripts.md` "measurement that is absent stays absent").
- Update the argv selftest that pins `--output-format text` (`:969-971`) and keep the prompt as the first positional after `-p` (variadic `--tools`).
- Keep NEVER `--bare` and NEVER Haiku.
- Record the Jev response's resolved `model` (not the alias) in every pair and in the frozen protocol.
- Document that `usage` is main-loop-only (or add `modelUsage` sums) so `tokens per call` is not misread.

MUST NOT:
- Store, print or compute from `total_cost_usd` (spec part 1.4; anti-ruflo CI grep).
- Record request text from the JSON or from `modelUsage` keys into pair/results lines.
- Treat a timeout, non-zero exit, or `is_error` run as a latency sample in the p50/p95.
- Claim that codex has no token data: say "unmeasured on this route" only (it is available with `--json`; not adopted here).

## 8. Open Questions for the Human

1. Add `--json` to the codex classify route so codex tokens are measurable, or accept `null`? Spec chooses `null`; this is a scoping call, not a currency problem.
2. Should the Claude classify keep running with the host's plugins/hooks loaded (what the hook actually pays), or should the eval also measure a stripped variant for comparison? Spec implies the former.

## 9. Knowledge Base Updates

- Created `docs/superpowers/library-audit/_knowledge-base/claude-code-headless-output.md` (result-object fields, error arms, usage scope, codex `--json` usage, Jev alias state, all dated 2026-10-08).
- Agent memory: one dated line appended to `.claude/agent-memory/superpowers-v-doc-validator/drift-jev-and-mods.md`.
