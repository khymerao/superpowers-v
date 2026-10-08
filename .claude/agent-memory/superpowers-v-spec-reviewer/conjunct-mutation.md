---
name: conjunct-mutation
description: "Guard rows for a multi-clause rule often test only one clause; mutate each conjunct alone, and check fixtures are not all-agree"
metadata:
  type: reference
---

A lead, observed in run 2026-10-08-t3-measurement-and-eval. Re-verify before relying on it.

- **The shape.** A rule that has several conjuncts, such as the JSON trust rule in
  `scripts/compound-v-classify-request.py` `parse_claude_json` (type, subtype, is_error, result-is-str), ships with
  negative fixtures that break two fields at once. The `json_error_subtype` fixture also deleted `result`, so the
  `result is str` clause caught it and the subtype clause was never tested alone. Removing `subtype` or `type` from the
  rule left the selftest green.
- **A sibling shape: a fixture where every row agrees.** In the `compound-v-jev.py` `_eval_rows` fixture every variant
  answer equals the base label. A report row that asserts `0/4 flips` therefore passes for any `flips()` at all.
- **The check that catches it.** Copy the tree with `git archive HEAD | tar -x` into the scratchpad. Mutate one clause
  at a time with an anchor that must match exactly once (python `str.count == 1`), run the selftest, restore. About
  5 s per mutation for these scripts. Survivors are TEST_GAPs under the "fails when reverted" constraint.
- **A related trap.** A label/eval command that accepts any `backend in (claude, codex)` run as a "Claude" vote or a
  "Claude" latency sample mixes fallbacks into a measurement. Check what the `ran` filter admits against the report's
  labels.
