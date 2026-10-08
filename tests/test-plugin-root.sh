#!/usr/bin/env bash
# tests/test-plugin-root.sh — the plugin root comes from the harness substitution
# (ADR 0005, rules 1-3; spec docs/superpowers/specs/2026-10-08-plugin-root-run-a-design.md).
#
# Claude Code replaces the bare `${CLAUDE_PLUGIN_ROOT}` token in command, skill and agent
# bodies with the path of the copy it loaded; the `${CLAUDE_PLUGIN_ROOT:-...}` form is left
# as is, and the variable is not set in the Bash tool. The old snippet used the `:-` form,
# so its cache scan always ran and could pick a stale copy. These rows pin the replacement:
#
#   (a) every file under agents/ commands/ skills/ evals/ that sets CV= carries the three
#       canonical lines byte-for-byte, no `:-` form and no cache scan;
#   (b) the lines, run with nothing substituted: a plugin checkout as $PWD is accepted with
#       a silent stderr, a plain $PWD is reported on stderr;
#   (c) with the token replaced by a path, as the harness does, CV is that path;
#   (d) hooks/session-banner.sh never falls back to `.`: a script planted in the project
#       is not executed, and the plugin's own scripts are still found next to the hook.
#
# bash 3.2 (stock macOS): no arrays, no bash-4-only constructs. Creates nothing in the repo.

set -uo pipefail
export PYTHONDONTWRITEBYTECODE=1

REPO="$(cd "$(dirname "$0")/.." && pwd)"
pass=0; fail=0
ok()  { pass=$((pass + 1)); printf 'PASS %s\n' "$1"; }
bad() { fail=$((fail + 1)); printf 'FAIL %s\n' "$1"; }

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

CANON="$WORK/canonical.txt"
cat >"$CANON" <<'EOF'
CV="${CLAUDE_PLUGIN_ROOT}"
[ -f "$CV/scripts/compound-v-preeval.py" ] || CV="$PWD"
[ -f "$CV/scripts/compound-v-preeval.py" ] || echo "Compound V: plugin root not found (no harness substitution, and $PWD is not a Compound V checkout); set CV to the plugin directory" >&2
EOF

# --------------------------------------------------------------------------- #
# (a) byte-for-byte canonical lines in every file that sets CV=
# --------------------------------------------------------------------------- #
FILES="$WORK/files.txt"
( cd "$REPO" && grep -rlE '^CV=' agents commands skills evals 2>/dev/null | LC_ALL=C sort ) >"$FILES"
nfiles="$(wc -l <"$FILES" | tr -d ' ')"
if [ "$nfiles" -ge 38 ]; then
  ok "(a) $nfiles files set CV= (at least the 38 entry points and references)"
else
  bad "(a) only $nfiles files set CV=; expected at least 38"
fi

nbad=0
while IFS= read -r rel; do
  [ -n "$rel" ] || continue
  f="$REPO/$rel"
  nset="$(grep -cE '^CV=' "$f")"
  # Every CV= line must open a block whose three lines are the canonical ones.
  blocks="$WORK/blocks.txt"
  grep -A2 -E '^CV=' "$f" | grep -v '^--$' >"$blocks"
  expect="$WORK/expect.txt"
  : >"$expect"
  i=0
  while [ "$i" -lt "$nset" ]; do cat "$CANON" >>"$expect"; i=$((i + 1)); done
  if ! cmp -s "$blocks" "$expect"; then
    nbad=$((nbad + 1)); printf '  not canonical: %s\n' "$rel"
  fi
  if grep -qF 'CLAUDE_PLUGIN_ROOT:-' "$f"; then
    nbad=$((nbad + 1)); printf '  uses the :- form the harness does not substitute: %s\n' "$rel"
  fi
done <"$FILES"
if [ "$nbad" = "0" ]; then
  ok "(a) every CV= block is the three canonical lines, and none uses the :- form"
else
  bad "(a) $nbad defect(s) in the CV= blocks (listed above)"
fi

scan="$( cd "$REPO" && grep -rlF 'superpowers-v/*/ 2>/dev/null | sort -V' agents commands skills evals 2>/dev/null )"
if [ -z "$scan" ]; then
  ok "(a) no file under agents/ commands/ skills/ evals/ carries the old cache scan"
else
  bad "(a) the old cache scan is still in: $(printf '%s' "$scan" | tr '\n' ' ')"
fi

# --------------------------------------------------------------------------- #
# (b) the lines with nothing substituted, extracted from one real file
# --------------------------------------------------------------------------- #
SNIP="$WORK/snippet.sh"
grep -A2 -E '^CV=' "$REPO/commands/v-status.md" | head -3 >"$SNIP"
FAKEHOME="$WORK/home"; mkdir -p "$FAKEHOME"
PLAIN="$WORK/plain"; mkdir -p "$PLAIN"

# run_snip <snippet file> <cwd>: prints CV on stdout, the snippet's stderr to $WORK/err.txt
# shellcheck disable=SC2016  # $1 and $CV belong to the inner shell, not this one
run_snip() {
  (cd "$2" && env -u CLAUDE_PLUGIN_ROOT HOME="$FAKEHOME" \
     bash -c '. "$1"; printf "%s" "$CV"' _ "$1" 2>"$WORK/err.txt")
}

cv="$(run_snip "$SNIP" "$REPO")"
err="$(cat "$WORK/err.txt")"
if [ "$cv" = "$REPO" ] && [ -z "$err" ]; then
  ok "(b) unsubstituted, from a plugin checkout: CV is \$PWD and stderr is empty"
else
  bad "(b) unsubstituted, from a plugin checkout: CV='$cv' stderr='$err'"
fi

cv="$(run_snip "$SNIP" "$PLAIN")"
err="$(cat "$WORK/err.txt")"
case "$err" in
  *"Compound V: plugin root not found"*)
    ok "(b) unsubstituted, from a plain directory: stderr names the problem" ;;
  *) bad "(b) unsubstituted, from a plain directory: no message on stderr (CV='$cv' stderr='$err')" ;;
esac

# --------------------------------------------------------------------------- #
# (c) the token replaced by a path, as the harness does at load
# --------------------------------------------------------------------------- #
SUBST="$WORK/substituted.sh"
# shellcheck disable=SC2016  # the literal ${CLAUDE_PLUGIN_ROOT} is the token Python replaces
REPO="$REPO" python3 -B -c '
import os, sys
text = open(sys.argv[1], encoding="utf-8").read()
open(sys.argv[2], "w", encoding="utf-8").write(text.replace("${CLAUDE_PLUGIN_ROOT}", os.environ["REPO"]))
' "$SNIP" "$SUBST"
cv="$(run_snip "$SUBST" "$PLAIN")"
err="$(cat "$WORK/err.txt")"
if [ "$cv" = "$REPO" ] && [ -z "$err" ]; then
  ok "(c) substituted: CV is the substituted path, not \$PWD, and stderr is empty"
else
  bad "(c) substituted: CV='$cv' (expected $REPO) stderr='$err'"
fi

# --------------------------------------------------------------------------- #
# (d) hooks/session-banner.sh resolves from CLAUDE_PLUGIN_ROOT, else next to itself
# --------------------------------------------------------------------------- #
BANNER="$REPO/hooks/session-banner.sh"
if grep -qF 'CLAUDE_PLUGIN_ROOT:-.}' "$BANNER"; then
  bad "(d) session-banner.sh still falls back to the project directory (CLAUDE_PLUGIN_ROOT:-.)"
else
  ok "(d) session-banner.sh has no fallback to the project directory"
fi

# A fake `claude` keeps the version probe off the real binary.
FAKEBIN="$WORK/bin"; mkdir -p "$FAKEBIN"
printf '#!/bin/sh\necho "9.9.9 (Claude Code)"\n' >"$FAKEBIN/claude"; chmod +x "$FAKEBIN/claude"

PROJ="$WORK/project"
mkdir -p "$PROJ/scripts" "$PROJ/docs/superpowers/execution"
SENTINEL="$WORK/planted-ran"
cat >"$PROJ/scripts/compound-v-dashboard.py" <<EOF
open("$SENTINEL", "w").write("ran")
print("PLANTED-DASHBOARD-RAN")
EOF
out="$(cd "$PROJ" && env -u CLAUDE_PLUGIN_ROOT PATH="$FAKEBIN:$PATH" bash "$BANNER" 2>/dev/null)"
if [ ! -e "$SENTINEL" ] && ! printf '%s' "$out" | grep -q 'PLANTED-DASHBOARD-RAN'; then
  ok "(d) unset CLAUDE_PLUGIN_ROOT: the project's planted scripts/compound-v-dashboard.py is not executed"
else
  bad "(d) unset CLAUDE_PLUGIN_ROOT: the banner executed the project's planted dashboard script"
fi
if printf '%s' "$out" | python3 -B -c 'import json,sys; json.load(sys.stdin)["hookSpecificOutput"]["additionalContext"]' 2>/dev/null; then
  ok "(d) the banner still emits valid JSON"
else
  bad "(d) the banner output is not valid JSON: $out"
fi

# The fallback is the plugin next to the hook: an empty onboard manifest in the project is
# reported by the plugin's own compound-v-onboard.py, with CLAUDE_PLUGIN_ROOT unset.
EMP="$WORK/empty-manifest"
mkdir -p "$EMP/docs/superpowers/architecture"
printf '{"generated":"2026-07-16","docs":{}}' >"$EMP/docs/superpowers/architecture/.onboard-manifest.json"
out="$(cd "$EMP" && env -u CLAUDE_PLUGIN_ROOT PATH="$FAKEBIN:$PATH" bash "$BANNER" 2>/dev/null)"
case "$out" in
  *"registers no cited files"*)
    ok "(d) unset CLAUDE_PLUGIN_ROOT: the plugin's own scripts are found next to the hook" ;;
  *) bad "(d) unset CLAUDE_PLUGIN_ROOT: the onboard staleness probe did not reach the plugin's script" ;;
esac

echo "-------------------------------------------"
printf 'tests/test-plugin-root.sh: %d passed, %d failed\n' "$pass" "$fail"
[ "$fail" = "0" ] || exit 1
echo "OK the plugin root comes from the harness substitution"
