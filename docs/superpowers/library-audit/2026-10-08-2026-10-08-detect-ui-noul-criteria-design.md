# Library audit - detect_ui Noul criteria (2026-10-08)

Spec: `docs/superpowers/specs/2026-10-08-detect-ui-noul-criteria-design.md`

## 1. Tools Available

- Context7: NO. `ToolSearch context7` returned no tool; the server `plugin:context7:context7` needs OAuth (same as 2026-10-08 earlier runs). DEGRADED: WebFetch-only. Nothing below is cited to Context7.
- Fallback used: WebFetch of `https://docs.typesafe.ai/api.md` (2026-10-08). No live API call made by this audit.
- V-memory recall: the prompt carried a block; no extra search run. Used: the 2026-10-05 Jev library audit constraints.
- Manifests: none relevant. The change is stdlib Python (`scripts/compound-v-jev.py`); the only dependency is the remote System One HTTP API.
- Agent memory consulted: `drift-jev-and-mods.md` (2026-10-05 line "Noul answer is a single `noul` float", "Choice criteria is a map"). It never recorded the Noul `criteria` shape; that gap is how the string form shipped.

## 2. Libraries Mentioned

| Name | Spec context | Current | Repo pinned | Last release | Maintenance | Status |
|---|---|---|---|---|---|---|
| TypeSafe System One API (Noul type) | `detect_ui` question | `jev-latest` -> example response shows `jev-1.13.0` (docs, 2026-10-08; docs do not say it is the current version) | `jev-latest` (alias, not pinned) | unknown (no changelog in `api.md`) | docs live 2026-10-08; live smoke on the same date confirmed the 400 | OK, but spec was built on a wrong reading |
| OpenRouter `/api/v1/systemone` | transport | n/a | n/a | n/a | smoke test 2026-10-08: `onboard_layer` returned `ok` on this path | OK |

No package dependency is added or changed.

## 3. API Signatures Verified

| Item | Spec claim | Docs (`api.md`, 2026-10-08) | Verdict |
|---|---|---|---|
| Noul `criteria` | optional; when present an object with `true` and `false` | "An object with keys `true` and `false`, both optional in the content shown"; `true` = "What a yes (value near 1) means", `false` = "What a no (value near 0) means"; each accepts string, object or array | Confirmed. Spec's "exactly `true` and `false`" is stricter than the API (each key optional); acceptable as a house rule, say so. |
| Noul `instructions` | string | required; string, object or array | Confirmed (string is valid) |
| Noul required fields | `type`, `instructions` | same | Confirmed |
| Choice `criteria` | not changed | required `map<string, string\|object\|array\|null>`, max 255 options | Unchanged; `onboard_layer` passes live |
| Noul answer | `noul` float | single `noul` float (2026-10-05 KB) | Unchanged |
| Error semantics | 400 `bad_input` | docs list direct 401/422/429/529 (2026-10-05 KB); the 400 here is the OpenRouter-side shape rejection | Consistent |

Repo code facts (read 2026-10-08): `compound-v-jev.py:111-114` `NOUL_CRITERIA["detect_ui"]` is a str; `:190-191` `catalogue_entry` puts it in `entry["criteria"]`; `:216` `questions_for` sends it unchanged. `ALT_WORDINGS["detect_ui"]` (`:100-104`) vary only `instructions`; `criteria` is shared across variants.

## 4. Critical Findings

None. No dependency is abandoned or deprecated.

## 5. High-Priority Findings

None.

## 6. Medium Findings

1. Spec change item 3 ("eval wording variant gets the same shape") is already satisfied by item 1. Variants 1 and 2 differ only in `instructions`; `criteria` comes from the single `NOUL_CRITERIA` constant at `:190-191`. Fixing that constant fixes every variant. Verify, do not add a second code path. (Repo-reality, flagged because the spec implies a separate edit.)
2. The `true`/`false` keys are JSON strings on the wire. In Python use the string keys `"true"` and `"false"`, never the booleans `True`/`False`. `json.dumps` happens to serialise bool keys as `true`/`false`, but a selftest comparing `set(keys) == {"true","false"}` would fail against bool keys in the in-memory dict. Store literal strings so the in-memory and wire forms agree.
3. The spec's selftest rule requires string values. The API also accepts object or array values. The stricter rule is fine for this catalogue but should be worded as a house rule, not an API rule, so a later richer criterion is not read as a bug.
4. Silent-drift cause: `jev-latest` is an alias, not a pin. The 2026-10-05 KB already noted docs recommend pinning. A string-form `criteria` may have been accepted by an earlier model and rejected now; this audit cannot establish that (no changelog, no earlier live call). Do not claim a regression cause in the plan.
5. Unverified: the shape was read from docs only. Only the spec's live smoke (2026-10-08) shows the string form fails. Acceptance criterion 3 (live `status: ok`) is the only proof the object form is accepted through OpenRouter's `/api/v1/systemone`; the plan must keep it as a gating step, not a nice-to-have.

## 7. Design Constraints for the Plan

MUST:
- MUST send Noul `criteria` as `{"true": <str>, "false": <str>}` with literal string keys.
- MUST change `NOUL_CRITERIA` (or `catalogue_entry`) so the shape is produced once; all `variant` and `reverse` paths inherit it.
- MUST add the selftest row asserting every catalogue `noul` question has `criteria` absent or a dict whose key set is exactly `{"true","false"}` with `str` values, and prove it fails against the old string form.
- MUST update the pinned selftest catalogue hash (hash is over canonical JSON of the entry, `:200-204`) and recompute it from the code, not by hand.
- MUST keep the live acceptance step (`jev_classify` returns `ok` with a `noul` answer) as the proof that OpenRouter accepts the object form.
- MUST keep the Noul parse rows (`:1252-1255`) unchanged.

MUST NOT:
- MUST NOT touch Choice `criteria` handling (`:208-214`); it is correct and live-verified.
- MUST NOT state in docs or commit text that the string form "used to work"; no evidence exists.
- MUST NOT introduce a third-party dependency.

## 8. Open Questions for the Human

- Should `detect_ui` pin a model version (`jev-1.13.0`) instead of `jev-latest`? Out of scope for this fix; the 2026-10-05 docs recommend it once thresholds are tuned. Escalate only if you want it in this change.
- Whether the repo's eval (variants) emits `criteria` anywhere besides `questions_for`: not found by grep (`criteria` appears at `:169,191,211-216,590` only), so none expected. Plan author should re-grep after the edit.

## 9. Knowledge Base Updates

Appended to `docs/superpowers/library-audit/_knowledge-base/typesafe-jev-openrouter.md` under `## Updated 2026-10-08 - detect-ui-noul-criteria-design`.
