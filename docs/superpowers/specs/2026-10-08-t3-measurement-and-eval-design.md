# Measure the Claude T3 classifier beside Jev, and an eval that can decide spec 1.5 - design

Triage: `docs/superpowers/pre-eval/2026-10-08T161225Z-measure-the-claude-t3-classifier-next-to-jev-and-extend-the-517a.json`
(FULL). Handoff: `docs/superpowers/research/2026-10-05-jev-next-stage.md` (Update 2026-10-08, "Next").

## Why

Spec 1.5 (T3 active) can only save the headless Claude classify that Jev would replace. Today nothing measures that
classify: `compound-v-classify-request.py --classify-headless` runs `claude -p ... --output-format text` and keeps the
category only. Shadow pairs record Jev's `latency_ms` and nothing for Claude. And the eval (`compound-v-jev.py eval
--t3`) has no human labels, no repeats and no cold/warm split. Published comparisons
(LiteLLM's Jev-vs-Haiku tier routing, Classmethod's Jev routing test, Wavect's option-order study of AnyJev) used
author labels, warm calls and a single ordering; their method points we adopt are listed under "Eval".

## Measurement (part 1)

1. `--classify-headless` runs `claude -p` with `--output-format json` and parses the result object: the category from
   `result`, plus `duration_ms`, `duration_api_ms` and `usage` (`input_tokens`, `output_tokens`,
   `cache_read_input_tokens`, `cache_creation_input_tokens`). It also measures the wall time around the whole process
   (`time.monotonic`), because the hook waits for the process, not the API. The printed JSON gains
   `measure: {wall_ms, duration_ms, duration_api_ms, tokens: {...}}`. The codex route records `wall_ms` only; its token
   fields are `null` (unmeasured, never `0`). A parse failure of the JSON result is the same as today's non-answer
   (category `unknown` path unchanged).
2. `compound-v-jev.py pair` accepts the Claude-side measurement (one `--claude-measure-json` argument, validated) and
   stores it in the pair line beside the Jev side, which keeps its `latency_ms`. The pair line never holds request text.
3. The hook (`hooks/triage-prompt-nudge.sh` -> descriptor -> `hooks/jev-t3.tsx` -> `pair`) and Phase T
   (`commands/v-triage.md`) pass that measurement through. The hook's stdout and the descriptor's existing keys stay
   unchanged (one new key for the measurement).
4. No money figure anywhere (spec 1: cost is never printed). Milliseconds and tokens only.

## Eval (part 2)

1. **Frozen protocol.** `eval --t3 --freeze` writes `docs/superpowers/research/2026-10-08-jev-t3-eval-protocol.json`
   (corpus digest, catalogue hash, pinned model id, variants, repeats, split seed, thresholds to report) before any
   call; `--prepare` and `--report` refuse to run against a corpus or catalogue that no longer matches it.
2. **`--label-claude`.** Runs the same headless classifier (same `build_prompt` T3 prompt as the hook) over each
   corpus row, 3 times, and writes `claude_label` (the majority; ties go to the stricter label) plus every run's
   measurement to a results file under the eval data directory (not the repo), and `claude_label` into the corpus.
3. **Human labels.** `--merge-human <sheet>` reads the maintainer's blind sheet
   (`docs/superpowers/research/2026-10-08-jev-t3-labelling-sheet.md`, codes `p m M u`) into `human_label`, refusing an
   unknown code or a missing row.
4. **Jev requests.** `--prepare` writes, per row: the base request, the reversed option order and the two alternate
   wordings, each **3 times** (repeat index in the request id). The model sends them with `jev_classify` from a terminal
   `claude`; the first call of a batch is tagged cold, the rest warm (the vault records `latency_ms`; the request file
   records its position).
5. **Report** (`docs/superpowers/research/YYYY-MM-DD-jev-t3-eval.md`):
   - agreement with `human_label` for Jev (base, majority of repeats) and for Claude, each with a 95% Wilson interval;
     Jev vs Claude agreement;
   - **strictness inversions** vs the human label (Jev less strict), with the rule-of-three bound when zero;
   - self-consistency over the 3 repeats; order flips and wording flips compared **by label**, not index;
   - probability histogram and the share of hard 0/1 answers;
   - a **risk-coverage** curve: for a threshold on Jev's top probability, the share of rows Jev would decide and its
     error rate vs the human label; the threshold is fitted on one half (fixed seed) and reported on the other;
   - the **saving that matters**: the share of rows where Jev's answer would not demote (no Claude confirmation needed
     under the spec 1.5 candidate policy), i.e. the calls spec 1.5 could actually skip;
   - latency: Jev p50/p95 cold and warm separately; Claude wall_ms and duration_api_ms p50/p95; Claude tokens per call.
6. **Decision rule** (stated in the report, fixed now): spec 1.5 is worth building only if (a) zero strictness
   inversions vs the human label, (b) Jev's agreement with the human is not worse than Claude's (intervals overlap or
   Jev higher), and (c) the skippable share in 5 is material. Otherwise spec 1.5 is not built and the next step is
   spec 2.

## Out of scope

Running the eval itself (done after merge, with the maintainer's labels); T3 active; spec 2.

## Acceptance Criteria

1. `compound-v-classify-request.py --selftest`: the JSON parse (category, measure fields), a non-JSON or partial result
   falls back exactly as today, codex tokens are `null`.
2. `compound-v-jev.py --selftest`: `pair` stores and validates the Claude measurement; `--freeze` and the refusal on a
   changed corpus; `--merge-human` (codes, missing row); `--prepare` emits 4 variants x 3 repeats with cold/warm
   position; the report's new sections on fixture responses, including the split and the skippable share; no request
   text in any pair or results line.
3. The hook and Phase T pass the measurement; existing hook tests and `tests/test-jev-core.sh` stay green; hook stdout
   unchanged.
4. Full suite, `lint-frontmatter.py .`, `shellcheck hooks/*.sh` green.

## Pre-flight amendments (2026-10-08)

These override the sections above. Sources: the 1A and 1C audits of this spec, and a live probe.

1. **Live probe of the result shape** (Claude Code 2.1.294, `claude -p "<one word>" --model sonnet --output-format json
   --tools ""`): one JSON object with `type: "result"`, `subtype: "success"`, `is_error: false`, `result` (string),
   `duration_ms` 6168, `duration_api_ms` 2360, `num_turns` 1, `usage` {`input_tokens` 2, `output_tokens` 6,
   `cache_creation_input_tokens` 53136, `cache_read_input_tokens` 0, ...}, `modelUsage` keyed by model id, and
   `total_cost_usd`. Wall time 9.9 s. The headless classify loads the whole Claude Code context (about 53k tokens) to
   answer one word.
2. **Trust rule.** The category is taken only when `type == "result"`, `subtype == "success"`, `is_error` is false and
   `result` is a string. Anything else (an error subtype, `is_error`, non-JSON or truncated stdout) falls back to
   today's `parse_category(raw)` on the raw text, with measure fields `null`, and is not a latency sample.
   `total_cost_usd` is never read into any stored or printed field. Token fields come from `usage` (main loop only,
   stated in the report); absent fields are `null`, never `0`. The resolved Claude model id comes from the
   `modelUsage` key.
3. **Hook interface.** `_classify_headless` keeps its two tab-separated fields (`category`, `backend`); the measure is
   read separately from the same JSON (jq), never as a third tab field. The descriptor gains one string-valued key
   `claude_measure` holding compact JSON (so `asDescriptor`'s string checks still apply); tests that pin the key set
   (`tests/test-native-points.sh:730,756`, descriptor 7 -> 8 keys; `tests/test-jev-core.sh:151`, pair keys) are
   updated, not deleted. `pair --claude-measure-json` is optional (the Task route has none).
4. **Frozen protocol digest** covers only `id`, `request`, `paths`, `hints` of each corpus row, so `--label-claude` and
   `--merge-human` (which rewrite labels) do not invalidate it. The protocol also records Jev's resolved model id and
   Claude's.
5. **Volume.** Per row: the base request 3 times plus each of the 3 variants once (6 calls; 480 in all), not 12.
   `eval_report` keys responses by `(id, variant, repeat)` (it overwrote by `(id, variant)`); the test that asserts 4
   files per item becomes 6. `--label-claude`: 3 runs per row (240 headless calls).
6. **Cold latency** comes from live shadow pairs (the hook path is always cold); the eval batch measures warm calls and
   reports the first call of the batch separately. The report shows non-ok counts, the share of Jev calls under the
   1,500 ms hook budget, and notes that the offline cap is 5,000 ms and a 429 retry inflates latency.
7. **Inversions and agreement use `human_label` only.** A row without a human label is excluded and counted; with fewer
   than 80 human labels the report says "not decidable" for the decision rule.
8. **Retention.** Eval request, response and results files live in an `eval/` subdirectory of the Jev data directory
   that the 30-day prune skips; the frozen protocol and report are committed.
9. The codex route keeps `wall_ms` only (`--json` for codex is out of scope). Reuse the existing Wilson implementation.
