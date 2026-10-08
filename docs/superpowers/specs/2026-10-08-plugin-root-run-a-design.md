# Plugin root from the harness substitution (ADR 0005, run A) - design

Decision: [`docs/superpowers/adr/0005-one-rule-per-root.md`](../adr/0005-one-rule-per-root.md), rules 1-3.
Triage: `docs/superpowers/pre-eval/2026-10-08T100252Z-run-a-of-adr-0005-plugin-root-replace-the-cv-resolver-in-38-89dd.json`
(FULL). Supersedes the design sections of `docs/superpowers/specs/2026-10-08-plugin-root-resolver-design.md`, whose
pre-flight audits (archaeology and library audit of 2026-10-08) apply here.

## Change

1. **Canonical lines.** In each of the 38 files (`agents/*.md`, `commands/v-*.md`, `skills/compound-v/*.md`,
   `skills/backend-launcher/*.md`, `evals/README.md`) the two resolver lines become exactly:

   ```bash
   CV="${CLAUDE_PLUGIN_ROOT}"
   [ -f "$CV/scripts/compound-v-preeval.py" ] || CV="$PWD"
   [ -f "$CV/scripts/compound-v-preeval.py" ] || echo "Compound V: plugin root not found (no harness substitution, and $PWD is not a Compound V checkout); set CV to the plugin directory" >&2
   ```

   In a command, skill or agent body the harness replaces `${CLAUDE_PLUGIN_ROOT}` with the loaded copy's path. In a
   file read with the Read tool or under another harness it is not replaced, the shell expands an unset variable to
   nothing, and the `$PWD` fallback applies only to a checkout of this plugin (an eval workspace qualifies, because
   `evals/lib/cv-fixture-lib.sh` vendors `scripts/` into it).
2. **Prose.** Every paragraph that explains the resolver (for example the "Resolving the plugin root" sections and the
   note that `CLAUDE_PLUGIN_ROOT` is not set in the Bash tool) is rewritten to the new rule: the harness substitutes the
   bare token in command, skill and agent bodies; reference files reuse the `CV` their entry point printed or fall back
   as above. `evals/README.md`'s "How the fixtures reach the plugin's scripts" is rewritten likewise; it must also say
   that under `claude plugin eval` the substituted path is the plugin source, so `CV` points there and the vendored
   copy is the fallback only.
3. **`hooks/session-banner.sh:35,51`**: `${CLAUDE_PLUGIN_ROOT:-.}` becomes `CLAUDE_PLUGIN_ROOT`, else the directory
   above the hook script (as `hooks/memory-refresh.sh:75` does). Never `.`.
4. **Test** `tests/test-plugin-root.sh` (new, executable, shellcheck-clean): (a) every file under `agents/`,
   `commands/`, `skills/`, `evals/` that sets `CV=` carries the three canonical lines byte-for-byte, and none contains
   `superpowers-v/*/ 2>/dev/null | sort -V`; (b) the lines, extracted from one file and run with `CLAUDE_PLUGIN_ROOT`
   unset: in a directory holding `scripts/compound-v-preeval.py` `CV` is that directory and stderr is empty; in a plain
   directory stderr carries the message; (c) with the token replaced by a path (as the harness does) `CV` is that path;
   (d) `hooks/session-banner.sh` contains no `${CLAUDE_PLUGIN_ROOT:-.}`, and run with `CLAUDE_PLUGIN_ROOT` unset from a
   project directory that holds a planted `scripts/compound-v-dashboard.py`, it does not execute that file. Each row
   fails when its change is reverted.

## Out of scope

The project root (ADR 0005 rules 5-8: run B), `_locate_script` and the other script-relative hook locators (already
rule 3), version, CHANGELOG, release.

## Acceptance Criteria

1. `tests/test-plugin-root.sh` passes and each row fails on revert.
2. No file under `agents/`, `commands/`, `skills/`, `evals/` contains the old cache scan.
3. `lint-frontmatter.py .`, `shellcheck hooks/*.sh tests/test-plugin-root.sh`, and the full suite pass.
4. A live check after merge: in this session's cv-dev install, a command body shows `CV="<install path>"`.
