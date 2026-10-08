---
name: review-fix-commits
description: Defects that "close the review findings" commits keep introducing in scripts/*.py, and the probes that catch them
metadata:
  type: project
---

A commit that closes review findings tends to introduce new small defects of the same class while fixing the old ones.
Seen in e222217 (2026-10-05, run jev-review-fixes). Treat these as leads and re-check them on every re-review:

- **A docstring sentence edited in place without rewrapping.** In scripts/compound-v-jev.py:21 the line grew to 155
  characters. Probe: `awk 'length>120{print FNR": "length}' <file>`, and compare the result with the paragraph's
  neighbouring lines.
- **A duplicate local import in a giant `_selftest()`.** In scripts/compound-v-onboard.py, `import time as _time`
  appears twice in one scope. Probe: `grep -n 'import ' <file>`, then check whether both hits sit in the same `def`.
- **A regex fix made without a guard.** Prove the guard by mutating the fix back on a scratch copy of the whole
  `scripts/` dir. A lone copied `compound-v-jev.py` printed `selftest: 1 of 0 rows failed`, so always copy the whole dir.

- **A malformed-shape guard that covers only the shapes listed in the finding.** In aeb1185 (2026-10-05) the fix
  guarded `waves`/`jobs`/`merged` in `_already_integrated_wave` (scripts/compound-v-emit-workflow.py) and left the
  per-job `.get` chain two lines below it unguarded, so `{"jobs": {"w1": "x"}}` still raised. Probe: walk every nested
  `.get` or index on the worker-writable record, and feed each shape to the real CLI subcommand, not only to the function.
- **A `^...$` regex used with `re.match` accepts a trailing `\n`.** `_SHA_RE` in compound-v-emit-workflow.py let a SHA
  ending in a newline reach git's argv. Probe: call the validator with the valid value plus `"\n"`.

**Why:** the reviewer marks findings like these blocking (the "no close enough" policy), so each one costs another
review round.
**How to apply:** on a re-review, diff the fix commit itself for new style or quality defects, and do not stop at
confirming that the listed findings are closed.
