#!/usr/bin/env bash
# One project-root rule (ADR 0005, rules 5-8; run B). The project root is an explicit
# --repo, else the git toplevel of the current directory -- never a script's own location
# (that is the PLUGIN root) and never the current directory as a guess. Each row below
# fails when its change is reverted:
#   - project-config resolve_project_root (its selftest)
#   - triage-outcomes writes the PROJECT's stream, not one beside the script, and refuses
#     outside git with no --repo / --stream
#   - preeval and fastpath-materialize carry no second copy of the stream path
#   - validate-manifest's _find_repo_root returns None instead of the cwd, and its CLI
#     caller handles that explicitly
#   - precompact-snapshot and brainstorm-trigger0-nudge walk up to the nearest .git
set -uo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
PY=/usr/bin/python3
export PYTHONDONTWRITEBYTECODE=1

pass=0; fail=0
check() {
  if [ "$2" = 1 ]; then echo "PASS $1"; pass=$((pass + 1)); else echo "FAIL $1"; fail=$((fail + 1)); fi
}

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
# Keep git from finding any repository ABOVE the sandbox: "outside git" means outside git.
export GIT_CEILING_DIRECTORIES="$TMP"
gitq() { git -c user.email=t@t -c user.name=t -c commit.gpgsign=false "$@"; }

# --- 1. the helper ------------------------------------------------------------------
"$PY" -B "$REPO/scripts/compound-v-project-config.py" --selftest >"$TMP/pc.log" 2>&1
rc=$?
check "HELPER: project-config selftest (explicit repo, subdir toplevel, worktree, outside git)" \
  "$([ "$rc" = 0 ] && echo 1 || echo 0)"
check "HELPER: resolve_project_root exists in project-config" \
  "$(grep -q '^def resolve_project_root(repo=None, start=None):' "$REPO/scripts/compound-v-project-config.py" && echo 1 || echo 0)"

# --- 2. triage-outcomes: the stream is the project's ---------------------------------
# A COPY of the scripts, placed outside the fixture repository: an installed plugin.
mkdir -p "$TMP/plugin"
cp -R "$REPO/scripts" "$TMP/plugin/scripts"
TO="$TMP/plugin/scripts/compound-v-triage-outcomes.py"
PROJ="$TMP/proj"
mkdir -p "$PROJ/sub/deeper"
gitq init -q "$PROJ"
STREAM="$PROJ/docs/superpowers/memory/triage-outcomes.jsonl"

(cd "$PROJ/sub/deeper" && "$PY" -B "$TO" predicted --pre-eval-id PID-SUB >/dev/null 2>"$TMP/to1.err")
rc=$?
check "TRIAGE: run from a project subdirectory with no --stream succeeds" "$([ "$rc" = 0 ] && echo 1 || echo 0)"
check "TRIAGE: the event lands in <project>/docs/superpowers/memory/triage-outcomes.jsonl" \
  "$(grep -q 'PID-SUB' "$STREAM" 2>/dev/null && echo 1 || echo 0)"
check "TRIAGE: nothing is written beside the plugin copy" \
  "$([ ! -e "$TMP/plugin/docs" ] && echo 1 || echo 0)"

NOGIT="$TMP/nogit"
mkdir -p "$NOGIT"
(cd "$NOGIT" && "$PY" -B "$TO" predicted --pre-eval-id PID-NOGIT >/dev/null 2>"$TMP/to2.err")
rc=$?
check "TRIAGE: outside git with no --repo and no --stream exits non-zero" \
  "$([ "$rc" != 0 ] && echo 1 || echo 0)"
check "TRIAGE: ... and says why" \
  "$(grep -q 'not inside a git repository' "$TMP/to2.err" && echo 1 || echo 0)"
check "TRIAGE: ... and writes nothing (not in the cwd, not beside the copy)" \
  "$([ -z "$(ls -A "$NOGIT")" ] && [ ! -e "$TMP/plugin/docs" ] && echo 1 || echo 0)"

(cd "$NOGIT" && "$PY" -B "$TO" predicted --pre-eval-id PID-REPO --repo "$PROJ" >/dev/null 2>&1)
rc=$?
check "TRIAGE: an explicit --repo wins from outside git" \
  "$([ "$rc" = 0 ] && grep -q 'PID-REPO' "$STREAM" 2>/dev/null && echo 1 || echo 0)"
check "TRIAGE: _repo_root() is gone" \
  "$(grep -qE '^def _repo_root|_repo_root\(\)' "$REPO/scripts/compound-v-triage-outcomes.py" && echo 0 || echo 1)"

# --- 3. one stream path ---------------------------------------------------------------
# Outside selftests (above `def _selftest`), neither script may spell the stream path.
# (Written to a file first: `grep -q` closing a pipe early would trip pipefail.)
for f in compound-v-preeval.py compound-v-fastpath-materialize.py; do
  awk '/^def _selftest/ { exit } { print }' "$REPO/scripts/$f" >"$TMP/head-$f"
  check "ONE STREAM PATH: $f has no hard-coded triage-outcomes.jsonl outside its selftest" \
    "$(grep -qE "[\"']triage-outcomes\.jsonl[\"']|\"memory\", *\"triage" "$TMP/head-$f" && echo 0 || echo 1)"
  check "ONE STREAM PATH: $f uses triage-outcomes' STREAM_RELPATH" \
    "$(grep -q 'STREAM_RELPATH' "$TMP/head-$f" && echo 1 || echo 0)"
done
check "ONE STREAM PATH: no second constant for it in fastpath-materialize" \
  "$(grep -q 'TRIAGE_STREAM_REL *=' "$REPO/scripts/compound-v-fastpath-materialize.py" && echo 0 || echo 1)"

# --- 4. validate-manifest: no cwd fallback --------------------------------------------
VM="$REPO/scripts/compound-v-validate-manifest.py"
got="$("$PY" -B - "$VM" "$NOGIT" <<'PYX'
import importlib.util, sys
spec = importlib.util.spec_from_file_location("cv_vm_root", sys.argv[1])
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
print(repr(m._find_repo_root(sys.argv[2])))
fp = m._validate_fast_path({}, {"eligible": True}, "pre-dispatch", None, None, None)
print("FP-NOROOT" if any("needs a repository root" in p for p in fp) else "FP-GUESSED")
PYX
)"
check "VALIDATE: a start path with no .git above yields no root (None, not the cwd)" \
  "$([ "$(printf '%s\n' "$got" | head -1)" = None ] && echo 1 || echo 0)"
check "VALIDATE: fast-path validation with no root fails closed instead of using the cwd" \
  "$(printf '%s' "$got" | grep -q 'FP-NOROOT' && echo 1 || echo 0)"
printf 'run_id: x\njobs: []\n' >"$NOGIT/manifest.yaml"
(cd "$REPO" && "$PY" -B "$VM" --require-triage "$NOGIT/manifest.yaml" >/dev/null 2>"$TMP/vm1.err")
rc=$?
check "VALIDATE: --require-triage with no root fails closed (exit 2, says why)" \
  "$([ "$rc" = 2 ] && grep -q 'no git repository above' "$TMP/vm1.err" && echo 1 || echo 0)"
(cd "$REPO" && "$PY" -B "$VM" "$NOGIT/manifest.yaml" >/dev/null 2>"$TMP/vm2.err")
check "VALIDATE: with no flag needing a root it reports the missing root and goes on" \
  "$(grep -q 'checks that need a repository root are skipped' "$TMP/vm2.err" && echo 1 || echo 0)"

# --- 5. hooks walk up -----------------------------------------------------------------
if ! command -v jq >/dev/null 2>&1; then
  check "HOOKS: jq is required for the hook rows" 0
else
  # precompact writes in a subdirectory; postcompact, in the same subdirectory, reads the
  # snapshot back. The disk is changed in between, so only a snapshot explains the line.
  HP="$TMP/hookproj"
  RUNDIR="$HP/docs/superpowers/execution/2026-01-01-x"
  mkdir -p "$RUNDIR" "$HP/sub/deeper" "$TMP/store"
  gitq init -q "$HP"
  now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  jq -n --arg ts "$now" '{run_id:"2026-01-01-x", phase:"DISPATCHED", updated_at:$ts,
      jobs:{"a":{status:"pending"},"b":{status:"done"}}}' >"$RUNDIR/state.json"
  printf 'run_id: 2026-01-01-x\n' >"$RUNDIR/manifest.yaml"
  ev() { jq -n --arg cwd "$1" --arg ev "$2" \
    '{hook_event_name:$ev,session_id:"pr-1",cwd:$cwd,trigger:"auto",compact_summary:"x"}'; }
  ev "$HP/sub/deeper" PreCompact | TMPDIR="$TMP/store" CLAUDE_PLUGIN_ROOT="$REPO" \
    bash "$REPO/hooks/precompact-snapshot.sh" >/dev/null 2>&1
  check "PRECOMPACT: a subdirectory session takes a snapshot of the project" \
    "$([ -n "$(find "$TMP/store" -name 'snap-*' 2>/dev/null)" ] && echo 1 || echo 0)"
  jq '.phase="MERGED" | .jobs |= map_values(.status="done")' "$RUNDIR/state.json" >"$TMP/st.json" \
    && mv "$TMP/st.json" "$RUNDIR/state.json"
  out="$(ev "$HP/sub/deeper" PostCompact | TMPDIR="$TMP/store" CLAUDE_PLUGIN_ROOT="$REPO" \
    bash "$REPO/hooks/postcompact-resume.sh" 2>/dev/null)"
  check "PRECOMPACT/POSTCOMPACT: same key from a subdirectory (postcompact reports the snapshot)" \
    "$(printf '%s' "$out" | grep -q 'UNFINISHED COMPOUND V WORK' && echo 1 || echo 0)"

  # trigger0 nudge: the recall helper is handed the PROJECT root, not the subdirectory.
  FAKE="$TMP/fakeplug"
  mkdir -p "$FAKE/scripts"
  cat >"$FAKE/scripts/compound-v-emit-preflight.py" <<'PYF'
import sys
a = sys.argv[1:]
print("FAKE_REPO=[%s]" % (a[a.index("--repo") + 1] if "--repo" in a else ""))
PYF
  payload="$(jq -n --arg cwd "$HP/sub/deeper" \
    '{tool_name:"Skill",session_id:"pr-2",cwd:$cwd,tool_input:{skill:"superpowers:brainstorming",args:"a topic"}}')"
  out="$(printf '%s' "$payload" | TMPDIR="$TMP/store" CLAUDE_PLUGIN_ROOT="$FAKE" \
    bash "$REPO/hooks/brainstorm-trigger0-nudge.sh" 2>/dev/null)"
  check "TRIGGER0 NUDGE: a subdirectory session passes the project root as --repo" \
    "$(printf '%s' "$out" | grep -qF "FAKE_REPO=[$HP]" && echo 1 || echo 0)"
fi

echo "test-project-root: $pass passed, $fail failed"
[ "$fail" = 0 ]
