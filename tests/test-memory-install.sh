#!/usr/bin/env bash
# tests/test-memory-install.sh — the NEW-USER V-memory smoke test. No network, no
# bootstrap: only the always-on FTS5 lane + the memory-refresh hook's filter, exactly
# what a fresh checkout gets with zero setup.
#
# Run explicitly under /bin/bash (bash 3.2 on macOS) — no arrays, no bash-4-only
# constructs, matching tests/test-hook-recursion-guard.sh / test-dogfood-index.sh.
set -u

REPO="$(cd "$(dirname "$0")/.." && pwd)"
ENGINE="$REPO/scripts/compound-v-memory.py"
HOOK="$REPO/hooks/memory-refresh.sh"

[ -f "$ENGINE" ] || { echo "FATAL: $ENGINE missing"; exit 1; }
[ -f "$HOOK" ]   || { echo "FATAL: $HOOK missing"; exit 1; }
command -v git >/dev/null 2>&1 || { echo "FATAL: git required"; exit 1; }

pass=0; fail=0
ok()  { pass=$((pass + 1)); printf 'PASS %s\n' "$1"; }
bad() { fail=$((fail + 1)); printf 'FAIL %s\n' "$1"; }

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# --------------------------------------------------------------------------- #
# Fixture repo: a few docs/superpowers/**/*.md + a root CHANGELOG.md, committed.
# Every engine/hook invocation below points COMPOUND_V_MEMORY_HOME at a scratch
# directory under $WORK — the real ~/.cache/compound-v is never touched.
# --------------------------------------------------------------------------- #
FIXTURE="$WORK/fixture-repo"
mkdir -p "$FIXTURE/docs/superpowers/specs" "$FIXTURE/docs/superpowers/plans"

git -C "$FIXTURE" init -q
git -C "$FIXTURE" config user.email "test@example.invalid"
git -C "$FIXTURE" config user.name  "memory-install-test"
git -C "$FIXTURE" config commit.gpgsign false

cat >"$FIXTURE/docs/superpowers/specs/2026-09-01-widget-spec.md" <<'EOF'
# Widget spec

The frobnicator widget needs a left-handed calibration mode.
EOF

cat >"$FIXTURE/docs/superpowers/plans/2026-09-01-widget-plan.md" <<'EOF'
# Widget plan

Implement left-handed calibration for the frobnicator.
EOF

cat >"$FIXTURE/CHANGELOG.md" <<'EOF'
# Changelog

## v0.1.0
Initial frobnicator release.
EOF

git -C "$FIXTURE" add -A
git -C "$FIXTURE" commit -q -m seed

# --------------------------------------------------------------------------- #
# (a) + (b): search with no index builds one and returns a hit; doctor reports
# an FTS5 mode line. Run once per interpreter (default `python3`, then a PATH
# trick so `python3` resolves to /usr/bin/python3 if that binary exists) — both
# runs go through the SAME hard-coded-`python3` code paths (engine invoked
# directly here, hook invoked via PATH below), so this also doubles as the
# cross-interpreter check task item (d) asks for.
# --------------------------------------------------------------------------- #
run_search_and_doctor() {
  label="$1"; cache="$WORK/cache-$label"
  mkdir -p "$cache"

  out=$(cd "$FIXTURE" && COMPOUND_V_MEMORY_HOME="$cache" python3 "$ENGINE" \
        search "frobnicator calibration" --top 5 2>&1)
  rc=$?
  if [ "$rc" = "0" ] && printf '%s' "$out" | grep -q "frobnicator"; then
    ok "$label: search with no index builds one and returns a hit"
  else
    bad "$label: search failed or found no hit (rc=$rc): $(printf '%s' "$out" | head -3 | tr '\n' ' ')"
  fi

  dout=$(cd "$FIXTURE" && COMPOUND_V_MEMORY_HOME="$cache" python3 "$ENGINE" doctor 2>&1)
  if printf '%s' "$dout" | grep -qi "FTS5"; then
    ok "$label: doctor prints a mode line containing FTS5"
  else
    bad "$label: doctor did not mention FTS5: $(printf '%s' "$dout" | head -5 | tr '\n' ' ')"
  fi
}

# Default PATH — whatever `python3` this shell already resolves.
run_search_and_doctor "default-python3"

# --------------------------------------------------------------------------- #
# (d) — also run under /usr/bin/python3 if present, via the PATH trick (never
# call the alternate binary by path directly: the hook below hard-codes plain
# `python3`, so exercising it under the second interpreter needs PATH to be
# what actually changes).
# --------------------------------------------------------------------------- #
if [ -x /usr/bin/python3 ]; then
  OLD_PATH="$PATH"
  PATH="/usr/bin:$PATH"
  export PATH
  resolved="$(command -v python3)"
  if [ "$resolved" = "/usr/bin/python3" ]; then
    run_search_and_doctor "usr-bin-python3"
  else
    bad "usr-bin-python3: PATH trick did not resolve python3 to /usr/bin/python3 (got $resolved)"
  fi
  PATH="$OLD_PATH"
  export PATH
else
  echo "SKIP usr-bin-python3: /usr/bin/python3 not present on this machine"
fi

# --------------------------------------------------------------------------- #
# (c) hook filter, positive case: an Edit under docs/superpowers/ must trigger
# the background refresh (asserted by the cache directory's index.sqlite
# appearing — the hook self-backgrounds, so poll briefly).
# --------------------------------------------------------------------------- #
hook_payload() {
  # $1 = file_path as the tool would report it (repo-relative, matching real usage)
  printf '{"hook_event_name":"PostToolUse","tool_name":"Edit","session_id":"s-mem-install","cwd":"%s","tool_input":{"file_path":"%s"}}' "$FIXTURE" "$1"
}

wait_for_index() {
  # $1 = cache dir to poll under; succeeds (rc 0) once an index.sqlite appears,
  # or times out after ~3s (rc 1).
  i=0
  while [ "$i" -lt 10 ]; do
    if find "$1" -name index.sqlite 2>/dev/null | grep -q .; then
      return 0
    fi
    i=$((i + 1))
    sleep 0.3
  done
  return 1
}

HIT_CACHE="$WORK/hook-cache-hit"
mkdir -p "$HIT_CACHE"
hout=$(cd "$FIXTURE" && hook_payload "$FIXTURE/docs/superpowers/specs/2026-09-01-widget-spec.md" \
       | CLAUDE_PLUGIN_ROOT="$REPO" COMPOUND_V_MEMORY_HOME="$HIT_CACHE" bash "$HOOK")
hrc=$?
if [ "$hrc" = "0" ] && [ -z "$hout" ]; then
  ok "hook: docs/superpowers Edit exits 0 and prints nothing"
else
  bad "hook: docs/superpowers Edit rc=$hrc out=$(printf '%s' "$hout" | head -c 80)"
fi
if wait_for_index "$HIT_CACHE"; then
  ok "hook: docs/superpowers Edit spawned a refresh (index.sqlite appeared)"
else
  bad "hook: docs/superpowers Edit never produced an index.sqlite under its cache dir"
fi

# --------------------------------------------------------------------------- #
# (c) hook filter, negative case: an Edit of an unrelated source file must NOT
# spawn a refresh. Uses a fresh, never-touched cache dir so "did it fire" is
# unambiguous, and waits the SAME duration as the positive case above so a
# false pass can't hide behind "didn't wait long enough."
# --------------------------------------------------------------------------- #
MISS_CACHE="$WORK/hook-cache-miss"
mkdir -p "$MISS_CACHE"
mout=$(cd "$FIXTURE" && hook_payload "$FIXTURE/src/app.ts" \
       | CLAUDE_PLUGIN_ROOT="$REPO" COMPOUND_V_MEMORY_HOME="$MISS_CACHE" bash "$HOOK")
mrc=$?
if [ "$mrc" = "0" ] && [ -z "$mout" ]; then
  ok "hook: unrelated src/app.ts Edit exits 0 and prints nothing"
else
  bad "hook: unrelated src/app.ts Edit rc=$mrc out=$(printf '%s' "$mout" | head -c 80)"
fi
if wait_for_index "$MISS_CACHE"; then
  bad "hook: unrelated src/app.ts Edit spawned a refresh (it must not have)"
else
  ok "hook: unrelated src/app.ts Edit did not spawn a refresh"
fi

printf 'tests/test-memory-install.sh: %d passed, %d failed\n' "$pass" "$fail"
[ "$fail" = "0" ] || exit 1
