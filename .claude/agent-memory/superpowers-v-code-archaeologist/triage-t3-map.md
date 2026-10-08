---
name: triage-t3-map
description: Where T3 (light classify) is called, what it can change, and the hidden couplings around the triage hook, pre-eval record and onboard detect_ui
metadata:
  type: reference
---

Map facts as of the 3.5.1 checkout (2026-10-05). Leads, not verdicts: re-verify before use.

- `scripts/compound-v-preeval.py` never calls a model. It returns `needs_t3`; callers run the classifier: `hooks/triage-prompt-nudge.sh` (`_classify_headless`), `commands/v-triage.md`, `skills/compound-v/phase-preeval.md`.
- T3 has three reasons (`unbanded`, `demotion`, `sensitive`). `plumbing`/`user-facing-minor` can lower FULL to SCOPED or SCOPED+. `NEVER_DEMOTE_GLOBS` (preeval.py:258) is the only code floor.
- Pre-eval record is write-once, digest-covered, schema closed at top level. New keys must pass through `build_record` before the digest.
- The request text is not stored in any committed artifact (only a 60-char slug and a sha256 fingerprint), so T3 replay from committed records is not possible.
- Hook marker `${TMPDIR}/compound-v-triage-nudge/nudged-*` is written BEFORE the engine; the first process wins the session.
- `CV_HEADLESS_CLASSIFY=1` early-exit is in nine hooks; `classify-request.py` passes `dict(os.environ)` to nested `claude -p`/`codex exec`, and `onboard.py design_lint` runs `npx --yes` with inherited env.
- CI runs `python3 <script> --selftest` for each `scripts/*.py` containing that literal (validate.yml:298-312), Python 3.9.
- `.claude/compound-v.json` is committed team policy only (v-init.md:439); machine-local state goes in `~/.claude/compound-v-capabilities.json`.
- `detect_ui` (onboard.py:329) uses git-tracked files only and returns bool; `draft_taxonomy` falls back to os.walk but `detect_ui` does not. `emit_taxonomy_yaml` drops row `evidence`.
- The agent Bash sandbox in pre-flight runs may be clamped to memory search + git read; use Read/Grep/Glob.
