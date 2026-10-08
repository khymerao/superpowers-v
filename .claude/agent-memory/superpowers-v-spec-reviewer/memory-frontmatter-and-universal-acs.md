---
name: memory-frontmatter-and-universal-acs
description: "Two recurring review traps: a memory file whose description has an unquoted colon-space breaks lint and test-agent-memory; a repo-wide AC can be broken by files the audit never inventoried"
metadata:
  type: project
---

Leads (re-verify before citing).

1. **Reviewer memory can turn the whole tree red.** A memory file's `description:` value that contains
   `: ` (for example a quoted `when: '*.md'`) is a YAML parse error. `scripts/lint-frontmatter.py .`
   and `tests/test-agent-memory.sh` ("the repo's own frontmatter passes the linter") both scan
   `.claude/agent-memory/**`. In run 2026-10-08-project-root-run-b the file came from run A's review
   commit, and HEAD stayed red, unseen, because no job's impacted set ran lint on that path.
   **How to apply:** quote every memory `description:`. After any memory write, run
   `lint-frontmatter.py .` on the checkout before returning.

2. **A universal AC ("no script under scripts/ does X") is wider than the lane.** The archaeology
   matrix that fed the spec can miss sites: here `compound-v-integration-gate.py` `main` and
   `compound-v-update-memory.py` `_default_outcomes_path` both derived a project root from `__file__`
   and were not inventoried. **How to apply:** grep the whole of `scripts/` yourself
   (`dirname(here)`, `dirname(HERE)`, `dirname(_x())`, `dirname(dirname(abspath(__file__)))`,
   `os.pardir`, `"..")`), classify every hit as plugin resource, selftest or project root, and report
   misses as ACCEPTANCE_GAP with a follow-up lane. Do not stop at the job's diff.

Related: [[impacted-map-globs]], [[verifying-acceptance-criteria]].
