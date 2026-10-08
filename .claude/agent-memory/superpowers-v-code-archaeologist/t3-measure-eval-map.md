---
name: t3-measure-eval-map
description: Couplings around the headless Claude classify output, hook tab protocol, descriptor keys, pair line keys and the jev.py eval aggregation (for measurement/eval changes)
metadata:
  type: reference
---

Map facts as of 2026-10-08 (branch jev-practical). Leads, not verdicts: re-verify before use.

- `hooks/triage-prompt-nudge.sh` `_classify_headless` reduces the classifier JSON to `category<TAB>backend`; the caller splits at the first tab and accepts only `claude|codex` for `t3_backend`, which gates the shadow descriptor. A third tab field would silently disable every descriptor.
- Tests pin the text format: `classify-request.py` selftest asserts `--output-format` == `text`; `tests/test-native-points.sh` fake claude (shell, ~:498) and the selftest's fakeclaude.py both print plain text, so a JSON-only parser changes their expected categories.
- Pinned key sets: `tests/test-jev-core.sh:151` (pair line = 5 keys), `tests/test-native-points.sh:730,756` (descriptor = 7 string keys). `hooks/jev-t3.tsx` `asDescriptor` requires all seven to be strings and `runShadow` SAFE_NAME-checks the argv tokens.
- `compound-v-jev.py` eval: one uuid-named request file per (item, variant); report aggregates `by_id[id][variant]` (overwrites repeats); inversion reference falls back human -> claude -> draft; `prune` drops the eval manifest and req/resp after 30 days.
- `tests/test-jev-core.sh:160` asserts 4 request files per corpus item.
- Corpus fixture `tests/fixtures/jev-t3-corpus.jsonl` (80 rows) is read by no test; only its README documents the key order.
- No repo code parses `claude -p --output-format json`; only `cursor-agent` has a documented one-object shape.
