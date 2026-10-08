# detect_ui Noul criteria Code Archaeology

Spec: `docs/superpowers/specs/2026-10-08-detect-ui-noul-criteria-design.md`. Checkout: branch `jev-practical`.
V-memory: the prompt block was read (parent Jev spec, library-audit, plan). The library-audit never documented the
Noul REQUEST shape (only the answer: audit lines 35, 96-98), so the spec's API claim had no prior verification here.
Agent memory (`jev-seams-map.md`, `phase-t-jev-shadow-map.md`) used as leads and re-verified.

## 1. Matrix

| Dimension | Values | Where it branches | Touched by the change? |
|---|---|---|---|
| point | t3, detect_ui, onboard_layer | `QUESTION_TYPES` `scripts/compound-v-jev.py:86` | only detect_ui |
| question type | choice, noul | `catalogue_entry` `:168-192`, `questions_for` `:207-217` | noul branch only (`:215-216`) |
| variant | original, wording1, wording2 (+ reversed) | `VARIANTS` `:713`, `ALT_WORDINGS` `:93` | all three detect_ui variants share ONE `NOUL_CRITERIA` entry (`:111`) |
| context | hook / offline | `DEFAULT_CONTEXT` `:60` | detect_ui is offline, no change |

Cells: `catalogue_entry("detect_ui", v)` for v in 0,1,2 all emit `criteria = NOUL_CRITERIA["detect_ui"]` (a str). `reverse=True`
is ignored for noul (`options is None`). One edit to `NOUL_CRITERIA` covers every variant, so spec Change item 3 is
satisfied by item 1 and nothing more is needed. `eval_prepare` (`:772-791`) builds only `t3` requests (hard-coded `"t3"`
at `:781`) and `eval_report` reads only `answers["category"]` (`:841`), so no eval path builds a detect_ui variant today.
Item 3 describes a nonexistent code path; it should be dropped or stated as vacuous.

## 2. Shared State

`NOUL_CRITERIA` (module constant, `:111-114`): a dict point -> str. Read at exactly one place, `catalogue_entry:191`. Set nowhere
else. It is used in two derived values: the wire request (`questions_for:216`, copied verbatim) and `catalogue_hash:200-204`
(canonical JSON of the entry).

`catalogue_hash`: written into the request file (`:417`), then into the parse result and telemetry (`:705`), and aggregated
by `eval_report` (`:837`, original wording of t3 only). No pinned literal exists anywhere. The hash is not stored in the
`pending-*` descriptors either. Gap in the spec: it says "nothing pins the old value except the selftest, which is updated to the new hash".
The selftest (`:1143-1159`) contains no hash literal; it only asserts stability and sensitivity for `t3`. There is nothing to
update. Persisted `calls` telemetry lines and any request files already on disk carry the old hash; that is data, not a pin,
and `HASH_RE` only checks the shape (`:582`). Old detect_ui hashes in `compound-v-jev` telemetry simply stop matching new ones;
no reader compares them.

Request shape on disk: `_request_meta` (`:570-592`) reads `q["criteria"]` only for `type == "choice"` (`:590`); for noul it ignores
`criteria`. `_parse_answer` noul branch (`:602-607`) reads only `a["noul"]`. So parse is shape-independent of the change.

## 3. Sibling Code

Choice sibling, `questions_for:210-214`: builds `criteria` as an insertion-ordered dict label -> description, and the repo
treats that dict form as the contract (library-audit Finding 5, lines 84-87). The noul branch is the only place a str is sent.
This is the same class of defect already fixed once for choice (the audit line 32 "criteria is a map, not a list" drift).
Root cause of this bug: `questions_for` has no per-type shape check, and the selftest builds the request but never validates the
wire shape. The only noul wire-shape assertion is `:1156-1158` (name `ui`, type `noul`). No test sends or inspects `criteria` for noul.

Latent issue in the sibling vault path: `plugins/compound-v-vault/hooks/vault.tsx:141-142` validates only `req.body.model` is a string and
`req.body.questions` is a record, then forwards `req.body` verbatim (`:219`). The vault will pass any malformed question to the API; the
only guard is the Python builder. A unit row in `compound-v-jev.py` is therefore the right and only gate. The vault's test fixture
(`plugins/compound-v-vault/.tests/vault.test.tsx:58`) has only a choice question.

Downstream consumer, `scripts/compound-v-onboard.py`: `jev_requests` (`:1272-1283`) builds via `_jev_build`; `_jev_detect_ui`
(`:1345-1359`) reads `answers["ui"]`; the onboard selftest (`:2541-2565`) uses `_fake_resp` with `{"ui": {"type":"noul","noul":0.93}}`
and never inspects `criteria`. Unaffected by the change.

## 4. External APIs

Context7 was unavailable (the server needs authorization), so the spec's API claim was verified with a direct fetch of
`https://docs.typesafe.ai/api.md` on 2026-10-08. Findings:

- Noul question: `type` required; `instructions` required (string | object | array); `criteria` optional, declared as an object.
  `criteria.true` "What a yes (value near 1) means"; `criteria.false` "What a no (value near 0) means". Both typed
  `string | object | array`. This confirms the spec's claim.
- Documented example: `"criteria": {"true": "Explicitly time-sensitive", "false": "No urgency expressed"}`.
- Validation failure on the direct API is documented as 422. HTTP 400 is NOT in the direct error table. Through OpenRouter the repo
  maps both 400 and 422 to `bad_input` (selftest table `:1260`), so a 400 from the OpenRouter route is consistent with the
  schema-rejection reading. Not verifiable here: that the string `criteria` is THE cause of the 400. The page does not say a string
  `criteria` is rejected; the diagnosis rests on the live observation (3 choice requests ok, 1 noul 400). The spec's AC 3 (live
  `status: ok`) is the only real proof; a selftest cannot prove the API accepts the new shape.
- Keys are the literal strings `"true"` and `"false"` (JSON strings, not booleans). Python `{"true": ..., "false": ...}` is correct;
  `{True: ...}` would serialize as `"true"` too via `json.dumps` but must not be used as a Python key (sort/compare surprises).
- Unknown: whether the API requires BOTH keys. The doc shows both together. The spec sends both. A one-key form is unverified.
- `instructions` could also stay a string; no change needed.

## 5. Regression Surface

| Path | If the change is wrong |
|---|---|
| `detect-ui --jev-responses` / onboard UI detection (`compound-v-onboard.py:1345`) | still falls to the deterministic floor; an `.html`-only repo is never detected as UI (today's state) |
| `catalogue_hash("detect_ui")` consumers (telemetry, parse, `_request_meta`) | hash value changes; no comparison against a stored value, so no break |
| `questions_for` choice branch (`:210-214`) | any refactor that touches the shared function risks the t3 and onboard_layer shapes; t3 is on the hook path with a 1500 ms budget (`:1182`) |
| `build_request` token estimate (`:408`) | object `criteria` adds a few characters only; the 32k budget row (`:1201-1203`) is unaffected |
| `ALT_WORDINGS["detect_ui"]` | unchanged, shares the criteria |
| Vault `jev_classify` forwarding (`vault.tsx:219`) | none; body is verbatim |
| `tests/test-jev-core.sh` | runs `--selftest` (`:33`); no ui-specific expectations; request-key assertions (`:74`) are on the top-level request, not on `criteria` |

## 6. DRY Findings

`criteria` for choice is built inline in `questions_for`; the new noul shape belongs next to it. The new selftest row should
validate wire shape over `catalogue()` (every point, every variant 0,1,2), not just the default entry, using `questions_for`
output (what actually goes on the wire) rather than the catalogue entry. The spec phrases it as "every catalogue question of type
noul", which is satisfied by iterating `catalogue()`; but iterating only `catalogue()` covers variant 0 only. Because the three variants
share one constant this is moot today, but a future per-variant criteria would escape the row.
No second place defines the Noul criteria text; no duplicate found (`rg` for the phrase in `scripts/`, `hooks/`, `plugins/`).

## 7. Design constraints for the spec

1. MUST send `criteria` as a JSON object with exactly the string keys `"true"` and `"false"`, both string values, for every noul
   question on the wire (`questions_for`), covering variants 0, 1 and 2. Edit `NOUL_CRITERIA` (single source, `:111`) and the
   one read at `:191/:216`; do not fork a second constant.
2. MUST split today's text into yes and no meanings without losing the exclusions ("build scripts, documentation tooling, tests or
   data files" belongs under `false`). The wording moves accuracy (audit line 86), so state in the spec which text goes under which key.
3. MUST correct spec Change item 1: the selftest pins no catalogue hash, so there is no "new hash" to update. Do not invent a pinned hash;
   if a regression pin is wanted, that is a new row, to be said as such.
4. MUST add the shape-check row to the `--selftest` in `scripts/compound-v-jev.py` (the CI sweep globs `scripts/*.py` for `--selftest`;
   `.claude/rules/scripts.md`), not to a file under `scripts/` that is not a selftest. The row must fail when the string form is restored (AC1).
   Run it over the wire form (`questions_for(catalogue_entry(p, v))`) for all points and variants 0-2.
5. MUST drop or rewrite Change item 3: no eval code builds detect_ui variants (`eval_prepare:781` is t3 only); the variants already
   share `NOUL_CRITERIA`.
6. MUST NOT touch the choice branch of `questions_for` (`:210-214`), `_request_meta`, `_parse_answer` or the vault; the existing noul parse rows
   (`:1252-1255`) stay.
7. MUST treat AC 3 (live `status: ok` plus a `jev:` reason) as the only proof that the API accepts the shape; the selftest proves
   the shape only against the documented schema (fetched 2026-10-08). It cannot show that the string `criteria` caused the 400: the
   direct API documents 422 for validation, the 400 comes through OpenRouter, and the page does not state that a string is rejected.
   The plan should keep a fallback: if the live call is still 400 after the fix, the cause is elsewhere (candidates: the
   `files` state payload, the 20-line heads, the model id). Unknown, therefore a risk.
8. MUST note that the live check needs the cv-dev plugin cache refreshed before `~/jev_test` picks up the script (AC3 wording already says so).

## 8. File Touch Map

| File | Change | Flag |
|---|---|---|
| `scripts/compound-v-jev.py` | `NOUL_CRITERIA` (`:111-114`) to `{"true":..,"false":..}` per point; new selftest row near `:1156-1158` | none |
| `tests/test-jev-core.sh` | no change needed (invokes `--selftest` at `:33`) | none |
| `docs/superpowers/specs/2026-10-08-detect-ui-noul-criteria-design.md` | fix items 1 and 3 | none |
