#!/usr/bin/env bash
# tests/test-disabled-hooks.sh — CV_DISABLED_HOOKS (v3.7.4): turn off individual
# Compound V hooks by name, borrowed from the ECC plugin's ECC_DISABLED_HOOKS.
#
# WHAT THIS FILE DEFENDS
#   * Each of the 8 switchable hooks reads CV_DISABLED_HOOKS and, when its own
#     basename (no .sh) appears in the comma list, exits 0 with NO output —
#     before it reads stdin, before it does any work.
#   * `lane-guard` is NOT one of the 8. It is the pre-write enforcement gate, and
#     an env var that can switch enforcement off — one a project's committed
#     .claude/settings.json `env` block could set for every clone — would widen
#     an authorization rather than silence a nudge. Naming it in
#     CV_DISABLED_HOOKS must not stop it from running.
#   * Matching is exact-token, comma-delimited: a name that is only a
#     prefix/suffix of a real hook name (e.g. "nudge") disables nothing.
#   * Spaces around names are ignored.
#   * session-banner.sh reports what was named: real disables, unknown names,
#     and lane-guard reported as ignored — on ONE line, only when
#     CV_DISABLED_HOOKS is non-empty, and never at all when session-banner
#     itself is the disabled one.
#
# No hook is ever driven by spawning a real `claude` process — every case below
# feeds a synthetic hook-event payload on stdin to the shell script directly.
# bash 3.2 compatible (macOS stock). Run: bash tests/test-disabled-hooks.sh

set -uo pipefail
unset CV_DISABLED_HOOKS  # a value in the caller's shell would leak into the "unchanged" checks

REPO="$(cd "$(dirname "$0")/.." && pwd)"
HOOKS_DIR="$REPO/hooks"

pass=0
fail=0
ok()  { pass=$((pass + 1)); printf 'PASS %s\n' "$1"; }
bad() { fail=$((fail + 1)); printf 'FAIL %s\n' "$1"; }

command -v jq >/dev/null 2>&1 || { printf 'FAIL tests/test-disabled-hooks.sh: jq is required\n'; exit 1; }

# The 8 hooks this feature covers. lane-guard is deliberately absent from this
# list — see the header above.
SWITCHABLE="brainstorm-trigger0-nudge epic-goal-stop memory-refresh plan-saved-nudge postcompact-resume precompact-snapshot session-banner triage-prompt-nudge"

# A realistic stdin payload per hook — just enough shape for the hook to parse,
# since a correctly-disabled hook must never read past the guard anyway.
payload_for() {
  case "$1" in
    brainstorm-trigger0-nudge)
      printf '{"hook_event_name":"PreToolUse","tool_name":"Skill","tool_input":{"skill":"superpowers:brainstorming"}}' ;;
    epic-goal-stop)
      printf '{"hook_event_name":"Stop","session_id":"s-disabled-hooks-test"}' ;;
    memory-refresh)
      printf '{"hook_event_name":"PostToolUse","tool_name":"Write","tool_input":{"file_path":"docs/superpowers/plans/x.md"}}' ;;
    plan-saved-nudge)
      printf '{"hook_event_name":"PostToolUse","tool_name":"Write","tool_input":{"file_path":"docs/superpowers/plans/x.md"}}' ;;
    postcompact-resume)
      printf '{"hook_event_name":"PostCompact","session_id":"s-disabled-hooks-test","cwd":"/tmp"}' ;;
    precompact-snapshot)
      printf '{"hook_event_name":"PreCompact","session_id":"s-disabled-hooks-test","cwd":"/tmp"}' ;;
    session-banner)
      printf '{"hook_event_name":"SessionStart","source":"startup"}' ;;
    triage-prompt-nudge)
      printf '{"hook_event_name":"UserPromptSubmit","session_id":"s-disabled-hooks-test","cwd":"/tmp","prompt":"hello there"}' ;;
  esac
}

echo "=== 1. each switchable hook: named in CV_DISABLED_HOOKS -> silent exit 0 ==="
for h in $SWITCHABLE; do
  out=$(printf '%s' "$(payload_for "$h")" | CV_DISABLED_HOOKS="$h" bash "$HOOKS_DIR/$h.sh" 2>/dev/null)
  rc=$?
  if [ "$rc" = "0" ] && [ -z "$out" ]; then
    ok "$h: CV_DISABLED_HOOKS=$h -> exit 0, empty stdout"
  else
    bad "$h: rc=$rc out=${out:0:120}"
  fi
done

echo "=== 2. spaces around names are ignored ==="
h="plan-saved-nudge"
out=$(printf '%s' "$(payload_for "$h")" | CV_DISABLED_HOOKS=" plan-saved-nudge , x " bash "$HOOKS_DIR/$h.sh" 2>/dev/null)
rc=$?
if [ "$rc" = "0" ] && [ -z "$out" ]; then
  ok "plan-saved-nudge: ' plan-saved-nudge , x ' (spaces + a stray name) still disables it"
else
  bad "plan-saved-nudge: spaced CV_DISABLED_HOOKS did not disable it (rc=$rc out=${out:0:120})"
fi

echo "=== 3. a prefix/suffix of a real name disables nothing ==="
# triage-prompt-nudge is deliberately excluded from this pair: it has its own
# "present-only" gate (a Compound-V-enabled repo) that makes it silent for
# reasons unrelated to CV_DISABLED_HOOKS under a bare /tmp cwd, which would
# make this check meaningless either way. Section 1 above already proves an
# EXACT match disables it; that is the guard this feature adds to that hook.
for h in plan-saved-nudge brainstorm-trigger0-nudge; do
  out=$(printf '%s' "$(payload_for "$h")" | env CLAUDE_PLUGIN_ROOT="$REPO" CV_DISABLED_HOOKS="nudge" bash "$HOOKS_DIR/$h.sh" 2>/dev/null)
  rc=$?
  # "disables nothing" means the hook did NOT take the early exit-0-empty path.
  if [ "$rc" = "0" ] && [ -z "$out" ]; then
    bad "$h: CV_DISABLED_HOOKS=nudge wrongly disabled it (suffix-matched)"
  else
    ok "$h: CV_DISABLED_HOOKS=nudge (a mere suffix) leaves it running"
  fi
done

echo "=== 4. unrelated CV_DISABLED_HOOKS value -> unchanged behaviour (2 hooks) ==="
# plan-saved-nudge: normal nudge text for a plan path, byte-for-byte what it
# emits with CV_DISABLED_HOOKS unset at all (checked against the un-set case).
h="plan-saved-nudge"
baseline=$(printf '%s' "$(payload_for "$h")" | env CLAUDE_PLUGIN_ROOT="$REPO" bash "$HOOKS_DIR/$h.sh" 2>/dev/null)
withvar=$(printf '%s' "$(payload_for "$h")" | env CLAUDE_PLUGIN_ROOT="$REPO" CV_DISABLED_HOOKS="some-other-hook" bash "$HOOKS_DIR/$h.sh" 2>/dev/null)
if [ -n "$baseline" ] && [ "$baseline" = "$withvar" ] && printf '%s' "$baseline" | jq -e '.hookSpecificOutput.additionalContext | test("plan saved at")' >/dev/null 2>&1; then
  ok "plan-saved-nudge: identical output with CV_DISABLED_HOOKS unset vs. naming a different hook"
else
  bad "plan-saved-nudge: output changed when CV_DISABLED_HOOKS named a different hook"
fi

# session-banner: the base banner text is still emitted (and, since no
# disabled/unknown/lane-guard names are involved here, carries no report line).
h="session-banner"
baseline=$(printf '%s' "$(payload_for "$h")" | env -i PATH="$PATH" CLAUDE_PLUGIN_ROOT="$REPO" bash "$HOOKS_DIR/$h.sh" 2>/dev/null)
withvar=$(printf '%s' "$(payload_for "$h")" | env -i PATH="$PATH" CLAUDE_PLUGIN_ROOT="$REPO" CV_DISABLED_HOOKS="some-other-hook" bash "$HOOKS_DIR/$h.sh" 2>/dev/null)
if printf '%s' "$baseline" | grep -q "Compound V loaded" && printf '%s' "$withvar" | grep -q "Compound V loaded"; then
  ok "session-banner: still emits its banner when CV_DISABLED_HOOKS names a different hook"
else
  bad "session-banner: banner missing (baseline=${baseline:0:80} withvar=${withvar:0:80})"
fi

echo "=== 5. session-banner reports disabled/unknown/ignored names on one line ==="
h="session-banner"
report=$(printf '%s' "$(payload_for "$h")" | env -i PATH="$PATH" CLAUDE_PLUGIN_ROOT="$REPO" \
  CV_DISABLED_HOOKS=" plan-saved-nudge , bogus-hook, lane-guard " bash "$HOOKS_DIR/$h.sh" 2>/dev/null \
  | jq -r '.hookSpecificOutput.additionalContext // ""')
case "$report" in
  *"CV_DISABLED_HOOKS"*"plan-saved-nudge"*) ok "banner names the real disabled hook" ;;
  *) bad "banner did not name plan-saved-nudge (report: ${report:0:200})" ;;
esac
case "$report" in
  *"unknown"*"bogus-hook"*) ok "banner flags the unrecognised name" ;;
  *) bad "banner did not flag bogus-hook as unknown (report: ${report:0:200})" ;;
esac
case "$report" in
  *"ignored (enforcement hook)"*"lane-guard"*) ok "banner reports lane-guard as ignored, not disabled" ;;
  *) bad "banner did not report lane-guard as ignored (report: ${report:0:200})" ;;
esac

echo "=== 6. session-banner disabled by name -> nothing printed at all ==="
h="session-banner"
out=$(printf '%s' "$(payload_for "$h")" | env -i PATH="$PATH" CLAUDE_PLUGIN_ROOT="$REPO" CV_DISABLED_HOOKS="session-banner" bash "$HOOKS_DIR/$h.sh" 2>/dev/null)
rc=$?
if [ "$rc" = "0" ] && [ -z "$out" ]; then
  ok "session-banner: disabling itself prints nothing (no report line either)"
else
  bad "session-banner: disabling itself did not silence it (rc=$rc out=${out:0:120})"
fi

echo "=== 7. lane-guard ignores CV_DISABLED_HOOKS entirely (still enforces) ==="
# Minimal sandbox, same shape as tests/test-lane-guard.sh's own out-of-lane
# Write case: one job whose lane is tests/**, and a Write outside it.
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
PROJ="$WORK/proj"
RUN="$PROJ/docs/superpowers/execution/2099-01-01-disabled-hooks-sandbox"
WT="$PROJ/.claude/worktrees/wf_sandbox-1"
mkdir -p "$RUN" "$WT/tests"
: >"$WT/README.md"

cat >"$RUN/manifest.yaml" <<'YEOF'
run_id: 2099-01-01-disabled-hooks-sandbox
jobs:
  - id: job-under-test
    write_allowed:
      - "tests/**"
YEOF

cat >"$RUN/lane-map.json" <<JEOF
{"run_id": "2099-01-01-disabled-hooks-sandbox",
 "agents": {"agent_abc123": "job-under-test"},
 "worktrees": {"$WT": "job-under-test"}}
JEOF

lane_payload=$(CV_T=Write CV_A=agent_abc123 CV_C="$WT" CV_F="$WT/README.md" python3 -c '
import json, os
print(json.dumps({
    "hook_event_name": "PreToolUse",
    "tool_name": os.environ["CV_T"],
    "agent_id": os.environ["CV_A"],
    "session_id": "s-disabled-hooks-lane-guard",
    "cwd": os.environ["CV_C"],
    "tool_input": {"file_path": os.environ["CV_F"]},
}))')

lane_out=$(printf '%s' "$lane_payload" \
  | env -u CLAUDE_PROJECT_DIR -u CLAUDE_PLUGIN_ROOT \
        CV_PROJECT_DIR="$PROJ" CV_DISABLED_HOOKS="lane-guard" \
        bash "$HOOKS_DIR/lane-guard.sh" 2>/dev/null)
lane_rc=$?

is_deny_json() {
  printf '%s' "$1" | python3 -c '
import json, sys
try:
    d = json.loads(sys.stdin.read())
except Exception:
    print("no"); raise SystemExit
o = d.get("hookSpecificOutput") or {}
print("yes" if o.get("permissionDecision") == "deny" else "no")'
}

if [ "$lane_rc" = "0" ] && [ "$(is_deny_json "$lane_out")" = "yes" ]; then
  ok "lane-guard: CV_DISABLED_HOOKS=lane-guard does NOT suppress the out-of-lane deny"
else
  bad "lane-guard: naming it in CV_DISABLED_HOOKS changed enforcement (rc=$lane_rc out=${lane_out:0:200})"
fi

rm -rf "$WORK"
trap - EXIT

printf 'tests/test-disabled-hooks.sh: %d passed, %d failed\n' "$pass" "$fail"
[ "$fail" = "0" ] || exit 1
