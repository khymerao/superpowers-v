#!/usr/bin/env bash
# Regression self-test for the worker gate->emit path transport (both
# compound-v-run-codex-worker.sh and compound-v-run-antigravity-worker.sh).
#
# Both workers read the scope gate's `.changed` / `.violations` JSON arrays and pass them
# THROUGH as JSON (jq --argjson) into job_result — no newline round-trip. This test mirrors
# that exact transport and proves a filename containing a LITERAL NEWLINE survives as ONE
# array element (the bug was: a newline-joined round-trip split it into two phantom paths).
# The scope gate itself is NUL-correct (compound-v-scope-check.py), so the BLOCK decision was
# always right; this guards the REPORTED arrays.
#
# Case 3 covers the other half of what a worker hands the gate: the post-provisioning
# --preexisting snapshot. It drives the REAL codex worker end to end against a stub `codex`
# on PATH, with a --provision-command that installs into a gitignored node_modules/, and
# proves the job is not blocked by files the model never wrote. Revert the provisioning
# support and this case fails — either the flag is rejected outright, or the installed
# files come back as ignored writes outside write_allowed.
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")/../scripts" && pwd -P)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

REPO="$TMP/repo"
mkdir -p "$REPO"
git -C "$REPO" init -q
git -C "$REPO" config user.email t@t.co
git -C "$REPO" config user.name t
echo seed > "$REPO/seed.txt"
git -C "$REPO" add -A
git -C "$REPO" commit -qm seed >/dev/null
BASE="$(git -C "$REPO" rev-parse HEAD)"

WT="$TMP/wt"
git -C "$REPO" worktree add -q "$WT" HEAD

# A filename containing a literal newline + an ordinary file.
NL="$(printf 'foo\nbar.txt')"
printf 'x' > "$WT/$NL"
printf 'y' > "$WT/normal.txt"

fail=0

run_gate() {  # $1 = allow-glob file -> echoes GATE_JSON
  python3 "$SCRIPT_DIR/compound-v-scope-check.py" \
    --worktree "$WT" --baseline "$BASE" --allow-file "$1" 2>/dev/null || true
}

# The exact worker transport: capture the gate arrays as JSON, then re-emit via --argjson.
transport() {  # $1 = GATE_JSON ; echoes the emitted files_changed+violations object
  local gj="$1" files_json violations_json
  files_json="$(printf '%s' "$gj" | jq -c '.changed // []')"
  violations_json="$(printf '%s' "$gj" | jq -c '.violations // []')"
  jq -n --argjson files "$files_json" --argjson violations "$violations_json" \
    '{files_changed: $files, violations: $violations}'
}

# --- case 1: everything allowed -> the newline name is ONE element of files_changed ------
printf '**\n' > "$TMP/allow_all"
OUT1="$(transport "$(run_gate "$TMP/allow_all")")"
n_changed="$(printf '%s' "$OUT1" | jq '.files_changed | length')"
has_nl="$(printf '%s' "$OUT1" | jq --arg p "$NL" '(.files_changed | index($p)) != null')"
if [ "$n_changed" = "2" ] && [ "$has_nl" = "true" ]; then
  echo "  case1 changed: newline filename is ONE element (2 files total) ✅"
else
  echo "  case1 FAIL: n_changed=$n_changed has_nl=$has_nl :: $OUT1"
  fail=1
fi

# --- case 2: only normal.txt allowed -> the newline name is ONE violation ----------------
printf 'normal.txt\n' > "$TMP/allow_one"
OUT2="$(transport "$(run_gate "$TMP/allow_one")")"
n_viol="$(printf '%s' "$OUT2" | jq '.violations | length')"
viol_is_nl="$(printf '%s' "$OUT2" | jq --arg p "$NL" '(.violations | index($p)) != null')"
if [ "$n_viol" = "1" ] && [ "$viol_is_nl" = "true" ]; then
  echo "  case2 violations: newline filename is ONE violation ✅"
else
  echo "  case2 FAIL: n_viol=$n_viol viol_is_nl=$viol_is_nl :: $OUT2"
  fail=1
fi

git -C "$REPO" worktree remove -f "$WT" >/dev/null 2>&1 || true

# --- case 3: provisioning --------------------------------------------------------------
# The real worker, a stub backend, and a provision command that installs into an ignored
# path. Nothing the model did creates node_modules/, so nothing about node_modules/ may
# appear in files_changed or violations, and the job must not be blocked.
PREPO="$TMP/prepo"
mkdir -p "$PREPO/src"
git -C "$PREPO" init -q
git -C "$PREPO" config user.email t@t.co
git -C "$PREPO" config user.name t
printf 'node_modules/\n' > "$PREPO/.gitignore"
printf 'base\n' > "$PREPO/src/base.ts"
git -C "$PREPO" add -A
git -C "$PREPO" commit -qm base >/dev/null

# Stub `codex`: exits 0 having written nothing. The point of the case is the gate's input,
# not the model — a real backend here would make the test non-deterministic and networked.
STUB="$TMP/stub"
mkdir -p "$STUB"
printf '#!/bin/sh\nexit 0\n' > "$STUB/codex"
chmod +x "$STUB/codex"

printf 'do nothing\n' > "$TMP/prompt.md"

# TMPDIR puts the worker's worktree under $TMP (a sibling of the repo, which the worker
# requires) so the trap cleans it up with everything else.
set +e
PROV_JSON="$(
  TMPDIR="$TMP" PATH="$STUB:$PATH" "$SCRIPT_DIR/compound-v-run-codex-worker.sh" \
    --run-id provrun --job-id provjob --repo "$PREPO" \
    --prompt-file "$TMP/prompt.md" --model stub-model \
    --write-allowed 'src/**' --timeout-sec 120 \
    --provision-command 'mkdir -p node_modules/x && printf a > node_modules/x/a' \
    --provision-timeout-sec 120 2>"$TMP/prov.err"
)"
prov_rc=$?
set -e

prov_status="$(printf '%s' "$PROV_JSON" | jq -r '.status // "MISSING"' 2>/dev/null || echo PARSE_FAIL)"
# `.blocked | tostring`, NOT `.blocked // "MISSING"`: jq's `//` treats `false` as empty, so
# the alternative would fire on exactly the value this case is asserting.
prov_blocked="$(printf '%s' "$PROV_JSON" | jq -r 'if has("blocked") then (.blocked | tostring) else "MISSING" end' 2>/dev/null || echo PARSE_FAIL)"
prov_nm="$(printf '%s' "$PROV_JSON" \
  | jq -r '[(.files_changed // [])[], (.violations // [])[]]
           | map(startswith("node_modules")) | any' 2>/dev/null || echo PARSE_FAIL)"
# Anti-vacuity: a provision command that created NOTHING would satisfy every assertion
# above without the subtraction doing any work. Read the worker's own snapshot and require
# the installed path to be in it, so the case can only pass by the mechanism it is about.
prov_wt="$(printf '%s' "$PROV_JSON" | jq -r '.worktree // ""' 2>/dev/null || echo "")"
prov_snap="MISSING"
if [ -n "$prov_wt" ] && [ -f "$prov_wt.art/preexisting.txt" ]; then
  prov_snap="$(grep -c '^node_modules/x/a$' "$prov_wt.art/preexisting.txt" || true)"
fi

if [ "$prov_rc" = "0" ] && [ "$prov_status" = "success" ] && [ "$prov_blocked" = "false" ] \
   && [ "$prov_nm" = "false" ] && [ "$prov_snap" = "1" ]; then
  echo "  case3 provisioning: installed node_modules/ is not charged to the job ✅"
else
  echo "  case3 FAIL: rc=$prov_rc status=$prov_status blocked=$prov_blocked node_modules=$prov_nm snapshot=$prov_snap"
  echo "    stdout: $PROV_JSON"
  echo "    stderr: $(cat "$TMP/prov.err" 2>/dev/null || true)"
  fail=1
fi

# The snapshot must be bounded to what provisioning created: a provision command that FAILS
# launches nothing and reports the failure verbatim, rather than running the model blind.
set +e
FAIL_JSON="$(
  TMPDIR="$TMP" PATH="$STUB:$PATH" "$SCRIPT_DIR/compound-v-run-codex-worker.sh" \
    --run-id provrun --job-id provfail --repo "$PREPO" \
    --prompt-file "$TMP/prompt.md" --model stub-model \
    --write-allowed 'src/**' --timeout-sec 120 \
    --provision-command 'exit 7' 2>"$TMP/provfail.err"
)"
set -e
fail_status="$(printf '%s' "$FAIL_JSON" | jq -r '.status // "MISSING"' 2>/dev/null || echo PARSE_FAIL)"
fail_summary="$(printf '%s' "$FAIL_JSON" | jq -r '.summary // "MISSING"' 2>/dev/null || echo PARSE_FAIL)"
if [ "$fail_status" = "error" ] && [ "$fail_summary" = "provision failed (rc=7): exit 7" ]; then
  echo "  case4 provisioning: a failed provision is reported, not run past ✅"
else
  echo "  case4 FAIL: status=$fail_status summary=$fail_summary"
  fail=1
fi

git -C "$PREPO" worktree remove -f "$TMP/compound-v/provrun/provjob" >/dev/null 2>&1 || true
git -C "$PREPO" worktree remove -f "$TMP/compound-v/provrun/provfail" >/dev/null 2>&1 || true

if [ "$fail" = "0" ]; then
  echo "SELFTEST PASSED"
  exit 0
fi
echo "SELFTEST FAILED"
exit 1
