---
name: drift-plugin-dependencies
description: Dated facts on Claude Code plugin `dependencies`, userConfig prompting and /plugin configure, checked 2026-10-05
metadata:
  type: reference
---

Leads only; re-verify before reuse. Detail in `docs/superpowers/library-audit/_knowledge-base/claude-code-plugin-dependencies.md`.

- 2026-10-05: bare-name `dependencies` resolve in the declaring plugin's marketplace; disabling/blocking a dependency disables the dependent plugin; `claude plugin validate` does not check a dependency name resolves.
- 2026-10-05: docs never say an auto-installed dependency's `userConfig` is prompted at install; `/plugin configure <plugin>@<marketplace>` needs >= 2.1.285; sensitive options are not in `/config`.
- 2026-10-05: Context7 reported "needs authentication" (not absent) in this run; Bash clamped to memory/git forms, so no `claude plugin validate` could be run.
