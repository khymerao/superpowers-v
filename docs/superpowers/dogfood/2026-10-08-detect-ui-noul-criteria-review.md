# Review Gate — run 2026-10-08-detect-ui-noul-criteria

Reviewer: `superpowers-v:spec-reviewer`, job `spec-review`, direct isolation, 2026-10-08.
Merged tree: HEAD `3265739` (implementation commit `8df3d86`, baseline `643ba42`).
Inputs: manifest `docs/superpowers/execution/2026-10-08-detect-ui-noul-criteria/manifest.yaml`, spec
`docs/superpowers/specs/2026-10-08-detect-ui-noul-criteria-design.md` (its pre-flight amendments override the body), plan
`docs/superpowers/plans/2026-10-08-detect-ui-noul-criteria.md`, audits
`docs/superpowers/archaeology/2026-10-08-2026-10-08-detect-ui-noul-criteria-design.md` and
`docs/superpowers/library-audit/2026-10-08-2026-10-08-detect-ui-noul-criteria-design.md`, job result
`results/noul.json`, gate receipt `receipts/noul.gate.json`.

## Recall

- The prompt's V-memory block (emit-time, `--intent review`) was read. Relevant rows: the 2026-10-08 phase-T Jev shadow
  review (AC-1 recorded as a selftest row count) and the typesafe/OpenRouter knowledge-base note (WebFetch of
  docs.typesafe.ai/api.md, the source the spec cites for the Noul `criteria` object). Neither constrains this diff beyond
  what the spec amendments already say.
- `recall-check --files scripts/compound-v-jev.py`:

  ```text
  recall-check: none (0/2 match on scripts/compound-v-jev.py)
    not counted (not attributable to a job's own work): harness_fault 5, pipeline_bookkeeping 3, recall_exclude 3, test_timeout 1, unattributed 3
  ```

  No repeat failure on this file pattern; no tightening.
- Reviewer memory leads re-verified here: "Negative-assertion rows / amendment vs AC — run the AC fixture against the
  amendment's literal rule" (done below as a mutation in a scratch copy) and "a check living only in an `impacted_map`
  glob never runs" (the map here names the literal path `scripts/compound-v-jev.py`, so it matches).
- No directive was found in any memory file or recalled text.

## SPEC

Diff (`git show 8df3d86`): one file, `scripts/compound-v-jev.py`, +19 −2 — the `NOUL_CRITERIA["detect_ui"]` value
(`:111-117`) and two selftest rows (`:1164-1176`). Scope gate receipt: `verdict: pass`, changed = allowed =
`[scripts/compound-v-jev.py]`, violations `[]`. Scope lock respected.

### Spec coverage

| Requirement (spec + amendments) | Implemented in | Status |
|---|---|---|
| `detect_ui` `criteria` is `{"true": ..., "false": ...}` (Change 1, amendment 1-2) | `scripts/compound-v-jev.py:111-117` | ✅ |
| The `false` text keeps the exclusions (build scripts, documentation tooling, tests, data files) | `:114-115` "build scripts, documentation tooling, tests and data files do not count" | ✅ |
| One constant shared by every `detect_ui` variant (amendment 2, Change 3) | `catalogue_entry` `:194` reads `NOUL_CRITERIA[point]` for variants 0-2; `reverse` touches options only (`:189-192`) | ✅ (wire dump below: variants 0, 1, 2 all carry the object) |
| No hand-typed catalogue hash (amendment 3) | no hash added; `catalogue_hash` (`:203-207`) recomputes from code | ✅ |
| Shape row over `questions_for(catalogue_entry(p, v))`, every point and variant; absent or subset of `{true,false}` with non-empty string values; fails on the string form (amendment 4) | `:1164-1174` (`noul_criteria_shape_ok`, `wire` over `POINTS` × `(0,1,2)`), plus `:1175-1176` predicate self-check | ✅ |
| Row is not vacuous | `any(qq["type"] == "noul" ...)` in the same `check` (`:1174`) — the row fails if no Noul question reaches the wire | ✅ |
| Existing Noul parse rows stay | diff removes nothing in `_selftest`; only additions | ✅ |
| Choice branch of `questions_for`, `_request_meta`, `_parse_answer`, vault untouched (amendment 5) | diff hunks are `:109-117` and `:1161-1177` only | ✅ |

### Audit constraints

| Audit | Constraint | Status | Notes |
|---|---|---|---|
| Archaeology 1 | object with string keys `true`/`false`, both string values, every noul question | ✅ | wire dump below |
| Archaeology 2 | split today's text without losing the exclusions | ✅ | `:113-115` |
| Archaeology 3 | no invented pinned hash | ✅ | none added |
| Archaeology 4 | shape row in `--selftest` of `scripts/compound-v-jev.py` | ✅ | `:1164-1176` |
| Archaeology 5 | no separate variant code path | ✅ | one constant |
| Archaeology 6 | Choice branch / `_request_meta` / `_parse_answer` / vault untouched | ✅ | |
| Archaeology 7-8, Library "keep the live step" | AC-3 is the only proof the API accepts the shape; needs cv-dev refresh | pending | AC-3, orchestrator post-merge |
| Library | literal string keys `"true"`/`"false"` | ✅ | |
| Library | shape produced once, all `variant`/`reverse` paths inherit | ✅ | |
| Library | row requires key set *exactly* `{true,false}` | superseded, holds in fact | spec amendment 4 and the plan's binding global constraint say "subset"; the row follows them. The wire dump (AC-1) shows both keys on variants 0, 1 and 2, so the stricter reading is also true of what ships |
| Library | update the pinned catalogue hash | superseded | amendment 3: no pinned hash exists; none invented |
| Library | Noul parse rows unchanged | ✅ | |
| Library MUST NOT | touch Choice `criteria` handling | ✅ | |
| Library MUST NOT | say the string form "used to work" | ✅ | no such text in the diff or commit message |
| Library MUST NOT | third-party dependency | ✅ | none |

### Over-build

None. The second row (`:1175-1176`) asserts the predicate rejects the string form; it is the in-tree half of "fails on
the string form", not an extra feature.

### Job acceptance (`noul`)

"The shape row passes and fails on the string form; jev selftest, test-jev-core, test-native-points and test-jev-t3-mod
green." — met; evidence in INTEGRATION (AC-1 mutation, impacted run).

## QUALITY

- Code quality: the constant reads cleanly and the predicate is local to `_selftest`. `catalogue_entry` and
  `questions_for` now hand out a reference to the module-level dict (`:194`, `:219`) where they used to hand out an
  immutable string; nothing mutates it (`criteria` is only read at `:593`, behind `q["type"] == "choice"`) and the wire
  path only serialises it, so this is not a defect today.
- No regression: `:593` (`labels = ... if q["type"] == "choice" and isinstance(q.get("criteria"), dict)`) is gated on
  type, so a Noul dict is not misread as Choice labels. `catalogue_hash` canonicalises with `sort_keys=True`, so the
  object hashes deterministically. No test under `tests/` or the vault plugin reads Noul `criteria` (grep for `noul`
  in `plugins/`, `hooks/`, `tests/`, `evals/`: no matches).
- Test alignment: every MUST has a guard — the shape row fails when the string form is restored (mutation below).
  The live API acceptance is guarded only by AC-3, which is correct per archaeology 7.
- Fabricated metrics: none. The diff prints no number.
- Global constraint 4 (commits): `8df3d86` carries no Co-Authored-By trailer and no body. Its subject,
  `compound-v: wave 1 of run 2026-10-08-detect-ui-noul-criteria (noul)`, is the Engine C finalize template that every
  wave commit uses (the implementer's work is squashed into it), not a subject the implementer wrote. Observation, not
  an issue against this run: the template's `compound-v:` prefix sits uneasily with "plain sentences" and belongs to
  the engine, not to this job. Python 3.9 stdlib: no import added. No version bump, CHANGELOG or release in the diff.
- Reward-hacking: none. No assertion removed, no threshold loosened, no test skipped; the diff only adds rows.
- §2.6: not applicable (not a marathon blocker).

## INTEGRATION

Partition: one implementation job, one file; no seam to leak across. No cross-job contract.

Test obligation: `triage.tier: FULL`, `test_scope: impacted`, a declared non-empty `impacted_map`. The only changed path,
`scripts/compound-v-jev.py`, matches the rule `when: scripts/compound-v-jev.py`, so the derived default is floor +
that rule, no `full_command` owed for the job. The job result records exactly that:
`tests.command` = the floor and the impacted rule, `tests.exit_code: 0`, `tests.scope: impacted`,
`tests.selected_count: 2`. AC-2 additionally names the full suite, which I ran myself (below).

### AC-1 — `compound-v-jev.py --selftest` passes; the new row fails with the string form restored

```text
$ /usr/bin/python3 -B scripts/compound-v-jev.py --selftest
exit=0
selftest: 114 rows ok
```

Mutation in a scratch copy of `scripts/` (the repo is not touched): the `detect_ui` constant replaced by the exact
pre-change string; `diff` of lines 105-120 against `git show 643ba42:scripts/compound-v-jev.py` reports them identical.

```text
$ /usr/bin/python3 -B <scratch>/scripts/compound-v-jev.py --selftest
mutant exit=1
FAIL catalogue Noul criteria are a true/false object on the wire
selftest: 1 of 114 rows failed
```

Wire form, every point × variant, Noul questions only:

```text
detect_ui 0 ui {"true": "At least one file renders markup or a user interface that an end user sees.", "false": "No file renders anything an end user sees: build scripts, documentation tooling, tests and data files do not count."}
detect_ui 1 ui {"true": ..., "false": ...}   (identical)
detect_ui 2 ui {"true": ..., "false": ...}   (identical)
```

AC-1: ✅

### AC-2 — `tests/test-jev-core.sh` and the full suite pass

```text
$ bash tests/test-jev-core.sh
exit=0
PASS no Jev file under the fixture repo
PASS planted: a re-invocation without --t3-engine writes no t3 block
all jev-core tests pass

$ bash -c '/usr/bin/python3 -B scripts/compound-v-jev.py --selftest >/dev/null && bash tests/test-jev-core.sh >/dev/null && bash tests/test-native-points.sh >/dev/null && bash tests/test-jev-t3-mod.sh >/dev/null && echo jev-ok'
jev-ok
exit=0
```

Full suite (`test_contract.full_command`, run by the reviewer on the merged tree):

```text
$ bash -c 'for s in scripts/compound-v-*.py; do grep -q -- "--selftest" "$s" || continue; /usr/bin/python3 -B "$s" --selftest >/dev/null 2>&1 || { echo "FAIL $s"; exit 1; }; done; for t in tests/*.sh; do bash "$t" >/dev/null 2>&1 || { echo "FAIL $t"; exit 1; }; done; echo all-tests-ok'
Thu Oct  8 14:48:23 CEST 2026
all-tests-ok
full exit=0
Thu Oct  8 14:53:07 CEST 2026
```

`git status --porcelain` after the suite lists only this review file, the reviewer memory files, and the run
directory's own bookkeeping (`lane-map.json`, `state.json`, `jobs/spec-review.baseline`,
`jobs/spec-review.test-contract.json`, `preexisting/`), all written by lane registration. The suite left no file in
the tree.

AC-2: ✅

### AC-3 — live `detect_ui` in `~/jev_test` returns `status: ok` with a `noul` answer

Pending — post-merge, owned by the orchestrator after the cv-dev plugin cache refresh (manifest AC-3, archaeology 7-8).
Not run here and not claimed. Pre-flight amendment 1 records the same request shape returning `status: ok`
(`noul: 0.99`) from a terminal session; that is design evidence, not this AC.

## Verdict

**APPROVED**, with AC-3 pending for the orchestrator after merge. The manifest's review body says to mark it so.

- PASS 1 SPEC: ✅. All 8 requirements are met, as is every applicable audit MUST. Two library-audit MUSTs are
  superseded by spec amendments 3 and 4, and both are cited above. There is no over-build. The `noul` job's acceptance
  is met.
- PASS 2 QUALITY: ✅. The code-quality check is clean and nothing regressed. The shape row guards the change, and the
  mutation run proves it fails on the string form. No metric is fabricated and no check was weakened to pass.
- PASS 3 INTEGRATION: ✅. No partition leaked and there is no seam to check. The floor and the impacted rule ran with
  exit 0 (`tests.command` / `tests.exit_code: 0` in `results/noul.json`). The full suite also passes on the merged
  tree (`all-tests-ok`).
- Feature AC: 2 of 3 are met (AC-1 ✅, AC-2 ✅). **AC-3 is pending.** It is the live `detect_ui` call in `~/jev_test`
  after the cv-dev refresh, and the orchestrator must run it before the run is DONE. This review does not claim it.

Issues: none.

Observations that do not block:

1. The Engine C wave-commit subject template (`compound-v: wave N of run ...`) has a prefix that sits uneasily with the
   global "plain sentences" commit rule. It belongs to the engine, not to this job.
2. `catalogue_entry` and `questions_for` now return a reference to the module-level `NOUL_CRITERIA` dict. Nothing
   mutates it today. A future caller that edits a wire question in place would change the catalogue.

### AC-3 live check (orchestrator, 2026-10-08)

After the merge and a cv-dev refresh, a terminal `claude -p` in `~/jev_test` ran `jev-requests --point detect_ui`,
`jev_classify` and `detect-ui --reason --jev-responses`: the response was
`{"status":"ok","latency_ms":1771,"body":{"model":"typesafe/jev-1.13-20260917","answers":{"ui":{"type":"noul","noul":0.99}}, ...}}`
and `detect-ui` printed `ui jev:sample`. AC-3 met.

Two observations for a later change (not defects of this run): `detect-ui --jev-responses <dir>` re-parses every
response file in the shared `resp/` directory, so an old error response is re-logged to `calls.jsonl` with a new
timestamp and old answers take part in the decision; and the hook T3 path logged one `timeout` at 1,505 ms against its
1,500 ms budget while Jev answered in about 1.8 s.
