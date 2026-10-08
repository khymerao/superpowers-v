# T3 measurement and eval - Code Archaeology

Spec: `docs/superpowers/specs/2026-10-08-t3-measurement-and-eval-design.md`. Checkout: branch `jev-practical`, 2026-10-08.
V-memory: the block in the prompt returned the spec 1 plan/spec and the `jev-next-stage` handoff; nothing contradicts the code
except where noted. The agent Bash was clamped to memory search and git read, so no test was executed; every claim below is from
reading the files. Context7 was not usable (server needs authorization), so nothing in section 4 is verified against provider docs.

## 1. Matrix

Dimensions the new code branches by, and whether the spec covers each cell.

| Dimension | Values | Today | Spec covers? |
|---|---|---|---|
| T3 caller | hook (`triage-prompt-nudge.sh:393`), Phase T (`commands/v-triage.md:165`), Task route (engine `parent`) | hook and Phase T run `--classify-headless`; Task route runs no script | Hook and Phase T yes. The Task route has no Claude measurement at all; `pair` must accept "no measure" (spec silent) |
| Headless backend | `claude`, `codex`, `none` | `_headless_result` fixed shape (`classify-request.py:498`) | Codex covered (`wall_ms` only). `none` and timeout carry no measure (not stated) |
| Claude attempt outcome | exit 0, timed out (returns at once, :631), non-zero fast (falls to codex, :634-643) | | A claude attempt that failed fast and then codex answered: whose `wall_ms`? Unstated (see F9) |
| Claude stdout form | JSON object (new), plain text (every current fake), truncated JSON at the 64 KB cap (`CLAUDE_STDOUT_CAP` :125) | text only | "Falls back exactly as today" is ambiguous for plain text (F3) |
| `CV_JEV_T3` | `1` / unset | descriptor only when `1` and `t3_backend` is claude or codex (`triage-prompt-nudge.sh:737`) | Yes, but the transport of the measure into the descriptor is not specified (F2) |
| Eval source | corpus rows (80), `--pairs` rows | `_corpus_items`, `_pair_items` (`jev.py:733-772`) | Corpus yes. Pair rows have no `human_label`, no repeats, no variants-by-repeat; spec says nothing about them |
| Variant x repeat | 4 variants (`VARIANTS` :716) x 3 repeats (new) | 4 per item, one request file each, uuid name (:432) | Repeat index "in the request id" - no request id exists (F6) |
| Jev response status | ok / unavailable (`timeout`, `rate_limited`, `egress`, ...) / error | report counts latency only for `ok` (:851) | Not addressed (F8) |
| Jev context | `hook` 1500 ms cap, `offline` 5000 ms cap (`TIMEOUT_MS` :59) | eval requests are built `offline` (:784) | Not addressed (F8) |
| Reference label | human / claude / draft | `inv` uses `human or claude or draft` (:869) | Spec wants human only (F11) |

## 2. Shared State

**`claude_label` / `human_label` in the corpus file (`tests/fixtures/jev-t3-corpus.jsonl`)**: written by the new `--label-claude` and `--merge-human`, read by `_corpus_items` (`jev.py:745-746`) into every manifest entry's `labels`. The same file's digest is to be frozen "before any call" and checked by `--prepare` and `--report`. Both writes change the file after the freeze. Unless the digest is computed over the immutable fields only (`id`, `request`, `paths`, `hints`), the first `--label-claude` after `--freeze` makes every later `--prepare` refuse. This is a design contradiction inside the spec (F1).

**Claude measure on its way to the pair line.** Set in `classify_via_claude` (new), carried through `classify_headless` (re-wrapped by `_headless_result` for codex, :640), printed by `main` (:764), consumed in the hook by `_classify_headless` which reduces the JSON to `category<TAB>backend` (`triage-prompt-nudge.sh:427`), split at :696-697, written into the descriptor by `_write_t3_descriptor` (:482-485), read by `asDescriptor` (`hooks/jev-t3.tsx:154-166`), passed to `pair` argv by `runShadow` (:242-254), stored in `shadow-pairs.jsonl` (`jev.py:1093`). Phase T has no descriptor: the model copies the printed JSON into the `pair` command (`commands/v-triage.md:246-249`). Each hop drops or rejects fields it does not know (F2, F5, F10).

**`t3_reason`**: still only on the first `needs_t3` result (memory `phase-t-jev-shadow-map`); re-verified, the hook keeps it in a shell local (:682). Unchanged by the spec.

**Resolved model id.** The protocol freezes a "pinned model id" for the Claude side. `classify_via_claude` returns `model` = the name it asked for, from `resolve_claude_light_model` (default alias `sonnet`, `classify-request.py:126`), not the id that answered. Nothing in the current code reads a resolved id. The only source would be the new JSON result (field name unverified, F4). The Jev side already has one (`parse_response` -> `model`, :677).

## 3. Sibling Code

**`_classify_headless` + re-entry in the hook** (`triage-prompt-nudge.sh:393-434`, :668-717). Entry gate: `needs_t3` true and `t3_prompt` non-empty. Reads `.backend .timed_out .category` with jq and ignores every other key, so adding `measure` to the printed JSON is safe by itself. It then prints `category<TAB>backend`; the caller splits with `${t3_out%%$'\t'*}` and `${t3_out#*$'\t'}` and accepts only `claude|codex` for `t3_backend`, otherwise sets it to empty (:698-701). A third tab field would land inside `t3_backend`, fail the `case`, empty it, and silently stop every descriptor (:737 requires `-n "$t3_backend"`). Latent trap, not a bug today.

**`runShadow`** (`hooks/jev-t3.tsx:204-255`). Every descriptor value that reaches argv must match `SAFE_NAME = /^[A-Za-z0-9._-]+$/` (:209-213), and `asDescriptor` requires all seven keys to be strings (:158-163). An object-valued `claude_measure` is neither a string nor SAFE_NAME-safe; a JSON string with braces and quotes fails SAFE_NAME. The module's own header says every process argument is "file paths and short tokens (never request text)". A numeric JSON blob in argv does not violate the "no request text" intent but does need a new, separate validator on both sides.

**`pair`** (`jev.py:1033-1038`, :1086-1098). `--claude-category`, `--backend`, `--t3-reason` required; the line is written with exactly five keys and the test pins that (`tests/test-jev-core.sh:151`). `_append_jsonl` refuses key-shaped text (:340).

**`eval_prepare` / `eval_report`** (`jev.py:775-982`). One request file per (item, variant), file name `uuid4().hex` (:432), manifest entry `{id, source, variant, request_file, t3_reason, labels}`. The report aggregates `by_id[id][variant] = answer` (:847): with repeats the later answer overwrites the earlier, so repeats cannot be introduced without restructuring the aggregation. `meta.setdefault(e["id"], e)` (:839) is per id, fine. `hashes` only from `variant == original` (:840). Latency list is built after the `status != ok` skip (:842-852).

Latent defects in the sibling:
- `inv` falls back `human -> claude -> draft` (:869) and `agree["human"]` is computed separately. Today, with no human labels, the inversion line silently measures against the implementer draft. The spec's decision rule (a) says "vs the human label" and would be wrong if this fallback survives.
- `usable` / `gate_line` only require one resolved model id and n > 0; no minimum n.
- `_percentile` is nearest-rank on whatever list it gets, no n shown next to the cold/warm split would hide tiny samples.
- Retention: `prune` deletes `EVAL_MANIFEST` and every req/resp file older than 30 days (`RETENTION_S`, :283-318), and `_request_meta` needs the request file to know the expected labels. An eval spread over a month loses its own inputs; `shadow-pairs.jsonl` lines also expire after 30 days. A new results file and protocol copy in the data dir are not in the prune list (survive); the manifest is.

**Vault `send`** (`plugins/compound-v-vault/hooks/vault.tsx:213-233`). Offline context: one retry after a 429 when `Retry-After` fits the deadline; `latency` then spans the wait. Timeout produces `unavailable/timeout` with the elapsed latency.

## 4. External APIs (via context7)

Not verified. The context7 server requires authorization in this session, and the agent Bash is clamped, so `claude -p --output-format json` could not be run either. Unknowns that the plan must close before coding, each by a live probe on the installed CLI:

| Item | Status |
|---|---|
| `claude -p ... --output-format json` returns ONE object, not an array of events | Unknown. Repo precedent exists only for `cursor-agent` (`skills/backend-launcher/adapter-cursor.md:84`: one object, `result`, `usage`). No script in the repo parses Claude's JSON output |
| Field names `result`, `duration_ms`, `duration_api_ms`, `usage.{input_tokens,output_tokens,cache_read_input_tokens,cache_creation_input_tokens}` | Unknown for Claude. The token field names appear in the repo only as transcript fields read by `compound-v-usage-extract.py:188` and `:753` (a different source) |
| Resolved model id in the JSON result | Unknown (a `modelUsage`-style key is possible; not checked) |
| Whether `--tools ""` plus `--output-format json` keeps the prompt-after-`-p` argv order | Unknown; the variadic-`--tools` trap is documented (`classify-request.py:426-437`) |
| Does a nested `claude -p` still load project hooks | Known and mitigated: `CV_HEADLESS_CLASSIFY=1` via `_headless_env` (:84) |
| Jev (TypeSafe) response fields | Known from the repo: the vault body carries `usage.cost` (selftest fixture `jev.py:1238`). `parse_response` does not copy `usage`; keep it that way, since the spec forbids any money figure |

## 5. Regression Surface

| Path | If the new code breaks it |
|---|---|
| `--classify-headless` category | The hook and Phase T read `.category`; a JSON parser bug turns every real classify into `unknown` = FULL for every unbanded request |
| `claude` argv | `--output-format text` is pinned by selftest (`classify-request.py:969-971`) and grep-checked (`tests/test-native-points.sh:579`); the prompt-after-`-p` order guards against an empty-prompt failure |
| Hook case 1-4 outputs (`tests/test-native-points.sh:664-666`) | The shell fake prints plain text (`:506`); with a JSON-only parser case 1 `user-facing-minor` would become `unknown` and the expected tier changes |
| Descriptor | Test asserts exactly seven keys (`:730-733`, :756). A new key without updating those fails; a descriptor value that is not a string makes `asDescriptor` return null and the shadow pair is dropped silently |
| Hook stdout | Spec says unchanged; the only coupling is the tab protocol (section 3) |
| `pair` | `tests/test-jev-core.sh:151` pins five keys; Phase T calls without a measure (Task route) must still work |
| `eval --prepare` | `tests/test-jev-core.sh:158-160` asserts 4 request files per item (8 for two); 4 x 3 changes that count, and the response-faking loop (:161-169) keys by request file |
| `eval --report` | Overwrite-by-variant aggregation (F6); the existing Wilson/histogram/model-id greps (:172-179) must keep matching |
| CI sweeps | `compound-v-jev.py` and `compound-v-classify-request.py` selftests run in CI on Python 3.9 (`validate.yml:298-312`); the anti-ruflo grep covers `scripts/` and `docs/` (`validate.yml:185-214`): a report line saying "tokens saved" or a `$` figure fails the build, so the "saving that matters" section must be worded as a share of calls, not savings |
| Corpus fixture | Only `README-jev-corpus.md` and the research docs describe it; no test reads the committed file, so a malformed write by `--label-claude` is not caught by CI |

## 6. DRY Findings

- Two readers of Claude token fields already exist (`compound-v-usage-extract.py`, `compound-v-usage-aggregate.py`), both over transcripts with `_valid_int` guards and "absent stays absent" (`usage-extract.py:17-27`, `.claude/rules/scripts.md`). The measure parser must follow the same rule (null, never 0) and should reuse `_valid_int`'s semantic, not write a third integer validator. The spec's "unmeasured, never 0" matches that convention.
- Percentile: `_percentile` in `jev.py:807` is the only nearest-rank helper in the file; reuse it for cold/warm, wall_ms and duration_api_ms.
- Wilson interval and `_rate_row` exist (:719, :814); reuse for Jev-vs-Claude agreement and inversion rows.
- `build_prompt` is imported once via `_load("cv_classify_request", ...)` (`jev.py:139`); `--label-claude` must call `classify_headless(prompt=...)` through that same loader rather than shelling out, and must build the prompt with the corpus row's own `paths` and `hints` (the hook's prompt comes from `_default_t3_prompt`, `preeval.py:888-898`, which passes the six taxonomy kinds as hints; corpus rows carry the same six). One prompt builder, one place.
- Three hand-rolled places assemble the measure shape if not centralised: the python `classify`, the hook's jq, the TSX `asDescriptor`. Decide one validator (the python `pair`) and treat the other two as pass-through.

## 7. Design constraints for the spec

1. The corpus digest in the frozen protocol must cover only `id`, `request`, `paths`, `hints` (canonical order), never `human_label`, `claude_label`, `label_draft` or `label_source`. Otherwise `--freeze` -> `--label-claude` -> `--prepare` refuses by construction (F1).
2. Define the JSON-result fallback precisely: stdout that is not a JSON object with a string `result` is parsed with `parse_category(raw)` exactly as today, with every measure field `null`. The category must never depend on the JSON parse succeeding (F3). A truncated 64 KB JSON is the same case.
3. Do not add a third tab field to `_classify_headless`'s output. Carry the measure through a separate channel (second jq-extracted variable or a temp file) so `t3_backend` still resolves to exactly `claude` or `codex` (`triage-prompt-nudge.sh:696-701`).
4. The descriptor's measure must pass `asDescriptor` and `runShadow`: either an optional key that is validated separately from the seven-string-key loop, or a file path. `JevT3Descriptor` in `types/index.d.ts` gains an optional field. A missing or malformed measure must still produce a pair (measure null), never drop the pair.
5. `pair --claude-measure-json` is optional (Task route and codex-without-measure), validated to a closed key set with non-negative ints or `null`, and written only when supplied, so the five-key pair line stays valid for old callers. Update `tests/test-jev-core.sh:151` and `tests/test-native-points.sh:730,756` in the same change; AC3 "existing hook tests stay green" cannot hold literally for those two assertions.
6. `compound-v-jev.py eval` argparse needs the mode group extended (`--freeze`, `--label-claude`, `--merge-human`, `--prepare`, `--report`); today `--prepare` and `--report` are one required mutually exclusive group and `--corpus`/`--pairs` are shared options (`jev.py:1039-1046`). The existing `--prepare` assertion of 4 files per item (`tests/test-jev-core.sh:160`) must be rewritten to 12, and the response-faking loop updated.
7. Manifest entries gain `repeat` (and a `position`/`batch` field for cold/warm). `eval_report` must aggregate per (id, variant, repeat); the current `by_id[id][variant] = ...` overwrite (`jev.py:847`) is incompatible with repeats. Report agreement on the majority of repeats, with ties resolved by `STRICTNESS` (`unknown` is the strictest, :55).
8. The inversion and agreement statistics must use the human label only. Remove the `human or claude or draft` fallback (`jev.py:869`) from the decision-rule path, and print n next to every rate. When fewer than the required human labels exist, the report states "not decidable" rather than falling back.
9. Latency honesty: count and report non-ok responses (timeout, rate_limited, upstream) next to the p50/p95 of ok ones; state the cap used (`offline` = 5000 ms vs the hook's 1500 ms) and report the share of ok responses at or under 1500 ms, since that is the budget a T3 active hook would have. Note that vault latency includes a 429 `Retry-After` wait (`vault.tsx:220-226`).
10. Cold/warm is a labelling convention applied by whoever sends the requests (a terminal model calling a tool); the spec cannot verify it. Record the position in the manifest and say in the report that the split is by position, not by an observed cache state.
11. The "pinned model id" for the Claude side needs a source. `classify_via_claude` returns the requested alias, not the answering id. Either read it from the JSON result after a live probe, or record the alias and say it is an alias.
12. Run a live probe of `claude -p <prompt> --model sonnet --output-format json --tools ""` first and paste the real object shape into the plan. Until then the field names in the spec are unverified.
13. Volume: 80 rows x 4 variants x 3 repeats = 960 `jev_classify` tool calls (the vault tool takes one `request_file` per call, `vault.tsx:359`), plus 240 headless Claude calls for `--label-claude` at up to 15 s each. The spec must say whether the sender is the model driving a loop or a script, and that the 30-day prune (`RETENTION_S`) removes request files and the manifest if the eval straddles it.
14. No money figure: `usage.cost` exists in the Jev body (`jev.py:1238`) and must stay out of `parse_response`, pair lines and the report. Report wording must avoid the CI anti-ruflo phrases ("tokens saved", "cost savings:", `$N saved`).
15. `--label-claude` and `--merge-human` rewrite a committed fixture. Write atomically (the file is the only labelled input), keep the exact key order the README documents (`id, request, paths, hints, t3_reason, label_draft, label_source, human_label, claude_label`), and update `tests/fixtures/README-jev-corpus.md` Checks, which says both fields are null until the eval fills them.
16. The labelling sheet is a markdown table with unescaped content; no row currently contains a pipe, but `--merge-human` must still refuse a row whose cell count is not 4 and any id not present in the corpus, and reject any code outside `p m M u` (case-sensitive; `m` and `M` differ).

## 8. File Touch Map (for Phase 2 partitioning)

| File | Change | Flag |
|---|---|---|
| `scripts/compound-v-classify-request.py` | JSON result parse, `measure`, `wall_ms`, codex null tokens, selftest (pins at :969-971, fakes at :992-1012) | |
| `scripts/compound-v-jev.py` | `pair` measure arg, `eval` modes, freeze, label-claude, merge-human, prepare repeats, report sections, selftest | |
| `hooks/triage-prompt-nudge.sh` | pass the measure out of `_classify_headless` (not via a third tab field), one new descriptor key | |
| `hooks/jev-t3.tsx` | optional measure through `asDescriptor`/`runShadow` to `pair` | |
| `types/index.d.ts` | `JevT3Descriptor` optional field | SHARED RESOURCE (type declaration read by `hooks/jev-t3.tsx` and the vault typings) |
| `commands/v-triage.md` | T2 prints the measure; T2b `pair` command gains the optional flag; Task route omits it | |
| `tests/test-jev-core.sh` | pair key set (:151), prepare count (:160), response faking (:161-169) | |
| `tests/test-native-points.sh` | fake claude (:498-508) to emit JSON, descriptor key assertions (:730,:756), `--output-format` grep (:579) | SHARED RESOURCE (one file covers hook cases 1-4 and the Jev shadow section; two jobs cannot both edit it) |
| `tests/fixtures/jev-t3-corpus.jsonl` | written by the eval at run time, not by the implementation | SHARED RESOURCE (fixture mutated after merge by `--label-claude` and `--merge-human`) |
| `tests/fixtures/README-jev-corpus.md` | state that the two label fields are filled by the eval; digest scope | |
| `docs/superpowers/research/2026-10-08-jev-t3-eval-protocol.json` | written by `--freeze` at eval time | |
| `docs/superpowers/research/2026-10-08-jev-t3-labelling-sheet.md` | maintainer input, read by `--merge-human` | |
| `plugins/compound-v-vault/hooks/vault.tsx` | not touched by the spec; read-only reference for latency semantics | |
