---
name: impacted-map-globs
description: "An impacted_map `when: '*.md'` rule matches only root-level files, so a check that lives only in that rule silently never runs for nested Markdown"
metadata:
  type: project
---

Lead (re-verify before citing): `impacted_map` `when` globs are matched by the scope gate's
`glob_to_regex` (`scripts/compound-v-fastpath-run.py` `_scope_check()` docstring: `*` does not
cross `/`, `**` does). A rule written `when: '*.md'` therefore matches `README.md` but never
`agents/x.md` or `skills/compound-v/y.md`.

Seen in run 2026-10-08-plugin-root-run-a: the `*.md` rule carried the only `lint-frontmatter.py .`
invocation; all 38 changed Markdown files resolved as "unmapped" to `full_command`, which does not
lint. The job's `tests.command` had no lint run at all, and the gate receipt still read green.

Recurred in run 2026-10-08-gate-toolchain-and-model-config: 4 nested `.md` paths "matched no `when`
glob" (receipt `contract_notes`), so lint again ran only in the reviewer's AC-2 probe.

Revert technique that kept the checkout untouched: tests that read a `*_SRC` override
(`INTEGRATION_GATE_SRC` in `tests/test-integration-gate.sh`, `RESOLVE_MODEL_SRC` in
`tests/test-resolve-model.sh`) take a pre-change script copied into the scratchpad beside a copy of
`scripts/*.py` (siblings load by path), so the revert check needs no worktree.

**Why:** a check placed only in a rule that never fires is a check that never runs, with no red
signal anywhere.

**How to apply:** for every review, read the gate receipt's `contract_notes` "unmapped:" line and
ask which commands live ONLY in a rule whose `when` matched nothing. Run those yourself on the
merged tree and report the glob (suggest `**/*.md`) as a non-blocking INTEGRATION finding.
Related: [[verifying-acceptance-criteria]].
