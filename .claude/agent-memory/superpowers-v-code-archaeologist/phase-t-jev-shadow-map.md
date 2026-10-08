---
name: phase-t-jev-shadow-map
description: Couplings between Phase T prose (commands/v-triage.md), the hook T3 shadow descriptor, jev.py CLI, vault tool and the pre-eval write-once record
metadata:
  type: reference
---

Map facts as of 2026-10-08 (branch jev-practical). Leads, not verdicts: re-verify before use.

- `compound-v-preeval.py triage` prints `t3_reason` only on the `needs_t3` result; the re-invocation result prints `t3` (engine, category) but not `t3_reason`. Callers must keep the first call's value (hook does, `triage-prompt-nudge.sh` ~:700).
- Pre-eval record is write-once and the `t3` block is inside the digest: re-running the same request with a different or newly added `--t3-engine` is refused ("already exists with DIFFERENT content", `write_record`).
- `compound-v-jev.py` reads no config; the only resolver is `compound-v-project-config.py` `resolve_jev` (absent config = enabled + t3 shadow). `jev-t3.tsx` consumes that resolved output; `load_project_config` raises on a malformed file.
- Hook gate for the shadow is vault `jev.status` (key + https route + egress allow) AND shadow config. The vault MCP tool `jev_classify` is registered without a key or consent and answers `unavailable(no_key|egress)`; `onboarding.md` Jev-for-UI gates on the `Jev: on` status line.
- `pair` requires the request file under `data_dir(--repo)/req`; digest is sha256 of the real repo path, so worktrees have separate data dirs.
- The T3 caps 2000/20/40 live in `compound-v-classify-request.py` (`MAX_REQUEST_CHARS`, `MAX_PATHS`, `MAX_TAXONOMY_CATEGORIES`) and again as `_T3_STATE_MAX_CHARS` in the hook.
- No test greps `commands/v-triage.md`; hook shadow tests live in `tests/test-native-points.sh` section 3d.
- Agent Bash in pre-flight is clamped to memory search + git read; use Read/Grep/Glob.
