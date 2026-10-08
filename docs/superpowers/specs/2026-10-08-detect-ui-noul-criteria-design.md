# detect_ui sends a Noul question the System One API accepts - design

Triage: `docs/superpowers/pre-eval/2026-10-08T123420Z-the-detect-ui-jev-request-is-rejected-with-http-400-bad-inpu-7276.json`
(FULL, T3 `user-facing-major`).

## Problem

Live smoke test, 2026-10-08, `~/jev_test` (an `index.html` game): the `detect_ui` request came back
`{"status":"error","reason":"bad_input","http_status":400}` while three `onboard_layer` requests on the same key were
`ok`. The request built by `scripts/compound-v-jev.py` (catalogue point `detect_ui`, `QUESTION_TYPES` at `:86`) carries:

```json
"ui": {"type": "noul", "instructions": "Does any file in `files` render user-facing markup ...",
       "criteria": "Yes when at least one file renders markup ...; no for build scripts, ..."}
```

The API reference (docs.typesafe.ai/api.md, read 2026-10-08) defines Noul `criteria` as optional and, when present, an
object with two properties: `true` (what a yes, a value near 1, means) and `false` (what a no means). A string is not
that shape. So every Jev `detect_ui` call fails and `detect_ui` falls back to its deterministic floor: an `.html`-only
UI is never detected.

## Change

1. The `detect_ui` catalogue entry sends `criteria` as `{"true": "<yes description>", "false": "<no description>"}`,
   keeping today's meaning split across the two keys. The catalogue hash changes; nothing pins the old value except the
   selftest, which is updated to the new hash.
2. `compound-v-jev.py --selftest`: a row asserts that every catalogue question of type `noul` has `criteria` either
   absent or an object whose keys are exactly `true` and `false` with string values; it fails on the string form. The
   existing parse rows for the `noul` float answer (`:1252-1255`) stay.
3. Any eval wording variant of `detect_ui` (alternate catalogue wordings, if the eval builds them) gets the same shape.

## Acceptance Criteria

1. `compound-v-jev.py --selftest` passes; the new row fails with the string form restored.
2. `tests/test-jev-core.sh` and the full suite pass.
3. Live, after the cv-dev refresh: in `~/jev_test`, `jev-requests --point detect_ui` plus `jev_classify` returns
   `status: ok` with a `noul` answer, and `detect-ui --reason --jev-responses` prints a `jev:` reason.

## Pre-flight amendments (2026-10-08)

These override the sections above. Sources: the 1A and 1C audits of this spec.

1. **Cause proven live.** The same `detect_ui` request with only `criteria` changed to
   `{"true": "At least one file renders markup or a user interface that an end user sees.", "false": "Build scripts,
   documentation tooling, tests or data files."}`, sent through `jev_classify` from a terminal session in `~/jev_test`,
   returned `{"status":"ok", ... "answers":{"ui":{"type":"noul","noul":0.99}}}` (model `typesafe/jev-1.13-20260917`,
   318 ms); the string form returned 400. The test files were removed afterwards.
2. **One constant.** The change is in `NOUL_CRITERIA` (`scripts/compound-v-jev.py:111`), which every `detect_ui`
   wording variant shares (`:190-191`); Change item 3 needs no separate code path. The `false` text keeps today's
   exclusions (build scripts, documentation tooling, tests, data files).
3. **No pinned hash.** The selftest pins no catalogue hash (Change item 1 was wrong); if a test anywhere compares a
   hash, it is recomputed from code, never typed by hand.
4. **Shape row.** The selftest row runs over the wire form `questions_for(catalogue_entry(p, v))` for every point and
   every variant, and requires a `noul` question's `criteria` to be absent or an object whose keys are a subset of
   `{"true", "false"}` with non-empty string values (the API allows either key alone; this catalogue sends both). It
   fails on the string form.
5. The Choice branch, `_request_meta`, `_parse_answer` and the vault are not touched.
