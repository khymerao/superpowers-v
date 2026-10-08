#!/usr/bin/env bash
# Compound V — V-memory refresh hook (SessionStart + PostToolUse:Write|Edit|MultiEdit).
#
# Non-blocking + SILENT: self-backgrounds a `refresh --quick` and returns in ~ms, so it
# never stalls SessionStart or a Write/Edit. It emits NO context output, so it composes
# cleanly with session-banner.sh / plan-saved-nudge.sh (those still fire and inject their
# own context on their own, narrower Write-only registration — see hooks.json).
#
# Matcher is `Write|Edit|MultiEdit`, not `Write` alone (new-user-install hardening pass):
# most doc upkeep in a real session is an Edit/MultiEdit on an existing file (fixing a
# stale line, appending a changelog entry), not a fresh Write, so a Write-only matcher
# missed the common case and left recall stale until the next SessionStart.
#
# It NEVER installs or downloads: `refresh` without --with-embeddings is FTS5-only and
# offline. Embeddings are bootstrapped only by the explicit `/v:memory-refresh
# --with-embeddings` / `bootstrap` path, never from a hook.
#
# The index cache lives OUTSIDE the repo (~/.cache/compound-v/memory/<repo-id>/), so a
# refresh can never write into the working tree and therefore can never dirty a dispatch
# worker's git scope gate. Concurrent fires (a Write storm during dispatch, or SessionStart
# racing a Write) are safe: the engine's flock makes every loser an instant no-op.
#
# On a python3 whose sqlite3 has no FTS5 (or any other engine failure): deliberately NO
# synchronous probe here. The engine's own failure is already silent by construction —
# stdout/stderr are redirected to /dev/null below and the refresh is detached, so a crash
# inside `compound-v-memory.py` never prints into the session either way. Adding a probe
# (spawning python3 to check `import sqlite3; ... CREATE VIRTUAL TABLE ... fts5`) would
# cost a second process launch on EVERY qualifying Write/Edit/MultiEdit just to detect a
# condition whose failure mode is already harmless — that cost buys nothing a new user
# would notice, since `/v:memory-refresh` and `doctor` already surface the real error
# on demand. Silence is achieved by redirection, not by prediction.

set -euo pipefail
if [ "${CV_HEADLESS_CLASSIFY:-}" = "1" ]; then exit 0; fi  # finding 131: never fire inside the headless classifier
# CV_DISABLED_HOOKS: comma-separated hook basenames (no .sh) to turn off. lane-guard is
# excluded on purpose — see hooks/lane-guard.sh's own header comment.
_cv_off=",$(printf '%s' "${CV_DISABLED_HOOKS:-}" | tr -d ' \t'),"
case "$_cv_off" in *",memory-refresh,"*) exit 0 ;; esac

input="$(cat 2>/dev/null || true)"
file_path=$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty' 2>/dev/null || echo "")

# PostToolUse:Write|Edit|MultiEdit carries a file_path — only react to a doc this corpus
# actually indexes: anything under docs/superpowers/, or one of the fixed root files the
# engine also indexes (CHANGELOG.md, TROUBLESHOOTING.md, README.md, AGENTS.md, CLAUDE.md,
# CONVENTIONS.md, DESIGN.md — matched by basename, any depth, since the cost of an
# occasional over-trigger on a same-named nested file is one harmless no-op `--quick`
# refresh, and a repo-root-relative path check would need a shell-out this hook is not
# worth spending). SessionStart carries no file_path — always do a quick refresh.
if [ -n "$file_path" ]; then
  case "$file_path" in
    */docs/superpowers/*) : ;;
    */CHANGELOG.md|CHANGELOG.md) : ;;
    */TROUBLESHOOTING.md|TROUBLESHOOTING.md) : ;;
    */README.md|README.md) : ;;
    */AGENTS.md|AGENTS.md) : ;;
    */CLAUDE.md|CLAUDE.md) : ;;
    */CONVENTIONS.md|CONVENTIONS.md) : ;;
    */DESIGN.md|DESIGN.md) : ;;
    *.md)
      # memory.extra_globs opt-in (set in .claude/compound-v.json): react to ANY *.md
      # write/edit under the repo once a project has declared it wants that. Cheap
      # substring check — no JSON parse, no python, so a project that never opted in
      # pays nothing beyond the case statement above.
      if [ -f .claude/compound-v.json ] && grep -q '"extra_globs"' .claude/compound-v.json 2>/dev/null; then
        : # opted in — fall through to the refresh below
      else
        exit 0
      fi
      ;;
    *) exit 0 ;;
  esac
fi

script="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}/scripts/compound-v-memory.py"
command -v python3 >/dev/null 2>&1 || exit 0
[ -f "$script" ] || exit 0

# Detach: nohup + background + redirected fds so the session returns immediately.
nohup python3 "$script" refresh --quick </dev/null >/dev/null 2>&1 &
exit 0
