#!/usr/bin/env bash
# tests/test-resolve-model.sh — compound-v-resolve-model.py driven through its CLI.
#
# WHAT IT PINS
#   Omitting --config means the PROJECT's .claude/compound-v.json, found from
#   --repo-dir or the git toplevel of the current directory — not the built-in
#   table. Until this row existed, a project whose config mapped claude.standard
#   to opus still got `sonnet` from every caller that left --config off.
#
#   The models and the maxEffortLevel cap come from the SAME root, so a call from
#   a subdirectory reads both from the toplevel's .claude/.
#
#   Outside a git repository with neither --config nor --repo-dir the resolver
#   fails closed (ADR 0005), except that --explicit-model needs no config and
#   keeps working anywhere.
#
# The --selftest covers resolve() and load_config_models in-process; their
# behaviour is unchanged. This file covers what only main() decides.

set -uo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd -P)"
RESOLVER="${RESOLVE_MODEL_SRC:-$REPO/scripts/compound-v-resolve-model.py}"
PY="${PY:-python3}"
export PYTHONDONTWRITEBYTECODE=1

pass=0
fail=0
ok()  { pass=$((pass + 1)); printf 'PASS %s\n' "$1"; }
bad() { fail=$((fail + 1)); printf 'FAIL %s\n' "$1"; }
check(){ if [ "$2" = "1" ]; then ok "$1"; else bad "$1"; fi; }

[ -f "$RESOLVER" ] || { echo "FATAL: $RESOLVER missing"; exit 1; }
command -v "$PY" >/dev/null 2>&1 || { echo "FATAL: $PY required"; exit 1; }
command -v git   >/dev/null 2>&1 || { echo "FATAL: git required"; exit 1; }

WORK="$(cd "$(mktemp -d)" && pwd -P)"
trap 'rm -rf "$WORK"' EXIT

# The user's own ~/.claude/settings.json must not decide a row here.
mkdir -p "$WORK/userhome"
export CLAUDE_CONFIG_DIR="$WORK/userhome"
# Nothing above $WORK may be mistaken for the fixture's repository.
export GIT_CEILING_DIRECTORIES="$WORK"

# Fixture project: claude.standard -> opus, and a project effort cap of `low`.
FIX="$WORK/project"
mkdir -p "$FIX/.claude" "$FIX/sub/deeper"
git -C "$FIX" init -q
git -C "$FIX" config user.email "test@example.invalid"
git -C "$FIX" config user.name  "resolve-model-test"
git -C "$FIX" config commit.gpgsign false
printf '{"models": {"claude": {"standard": "opus"}}}\n' >"$FIX/.claude/compound-v.json"
printf '{"maxEffortLevel": "low"}\n' >"$FIX/.claude/settings.json"
printf 'seed\n' >"$FIX/README.md"
git -C "$FIX" add -A
git -C "$FIX" commit -q -m seed

OUTSIDE="$WORK/not-a-repo"
mkdir -p "$OUTSIDE"

field() { # <json> <key>
  printf '%s' "$1" | "$PY" -c \
    "import json,sys
try:
    v = json.load(sys.stdin).get('$2')
except ValueError:
    v = None
print(json.dumps(v) if isinstance(v, (dict, list)) else v)"
}
cap_source() { # <json>
  printf '%s' "$1" | "$PY" -c \
    'import json,sys
try:
    c = json.load(sys.stdin).get("effort_capped") or {}
except ValueError:
    c = {}
print(c.get("source") or "")'
}

# 1. From the project root, no --config: the project's map wins.
OUT="$(cd "$FIX" && "$PY" "$RESOLVER" --backend claude --tier standard)"
check "no --config, from the root ⇒ the project's models (opus), not the built-in sonnet" \
      "$([ "$(field "$OUT" model)" = opus ] && echo 1 || echo 0)"

# 2. From a subdirectory: the git toplevel, not the current directory.
OUT="$(cd "$FIX/sub/deeper" && "$PY" "$RESOLVER" --backend claude --tier standard)"
check "no --config, from a subdirectory ⇒ still the toplevel's models (opus)" \
      "$([ "$(field "$OUT" model)" = opus ] && echo 1 || echo 0)"

# 3. --repo-dir from somewhere else entirely.
OUT="$(cd "$OUTSIDE" && "$PY" "$RESOLVER" --backend claude --tier standard --repo-dir "$FIX")"
check "no --config, --repo-dir names the project ⇒ its models (opus)" \
      "$([ "$(field "$OUT" model)" = opus ] && echo 1 || echo 0)"

# 4. One root for the models AND the effort cap, from a subdirectory.
OUT="$(cd "$FIX/sub" && "$PY" "$RESOLVER" --backend claude --tier deep)"
check "from a subdirectory the effort cap comes from the same root as the models" \
      "$([ "$(field "$OUT" effort)" = low ] \
         && [ "$(cap_source "$OUT")" = "$FIX/.claude/settings.json" ] && echo 1 || echo 0)"

# 5. An explicit --config still wins, unchanged.
printf '{"models": {"claude": {"standard": "explicit-cfg-model"}}}\n' >"$WORK/other.json"
OUT="$(cd "$FIX" && "$PY" "$RESOLVER" --backend claude --tier standard --config "$WORK/other.json")"
check "an explicit --config is still the config read" \
      "$([ "$(field "$OUT" model)" = explicit-cfg-model ] && echo 1 || echo 0)"

# 6. A project with no config file: the built-in table, as before.
NOCFG="$WORK/nocfg"
mkdir -p "$NOCFG"
git -C "$NOCFG" init -q
OUT="$(cd "$NOCFG" && "$PY" "$RESOLVER" --backend claude --tier standard)"
check "a project with no .claude/compound-v.json ⇒ the built-in table (sonnet)" \
      "$([ "$(field "$OUT" model)" = sonnet ] && echo 1 || echo 0)"

# 7. --explicit-model needs no config and works outside git.
OUT="$(cd "$OUTSIDE" && "$PY" "$RESOLVER" --backend claude --tier deep --explicit-model opus)"
RC=$?
check "--explicit-model outside git ⇒ succeeds" \
      "$([ "$RC" = 0 ] && [ "$(field "$OUT" model)" = opus ] && echo 1 || echo 0)"

# 8. Outside git with no flags: fail closed, with a message.
OUT="$(cd "$OUTSIDE" && "$PY" "$RESOLVER" --backend claude --tier standard 2>&1)"
RC=$?
check "outside git with neither --config nor --repo-dir ⇒ exits non-zero" \
      "$([ "$RC" != 0 ] && printf '%s' "$OUT" | grep -q 'git' && echo 1 || echo 0)"

printf '\n%d passed, %d failed\n' "$pass" "$fail"
[ "$fail" = "0" ] || exit 1
exit 0
