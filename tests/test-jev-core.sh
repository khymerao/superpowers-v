#!/usr/bin/env bash
# compound-v-jev.py end to end, offline: build -> fake vault response -> parse -> pair ->
# eval prepare/report. HOME is a throwaway dir, so the per-user data dir lands there and
# nothing touches the real ~/.claude. Checks: file modes, no key-shaped strings anywhere,
# error bodies never copied, nothing written under the repository, no network imports.
set -uo pipefail
export PYTHONDONTWRITEBYTECODE=1
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPT="$ROOT/scripts/compound-v-jev.py"
PY="${PYTHON:-python3}"
T="$(cd "$(mktemp -d)" && pwd -P)"   # physical path: macOS /var is a symlink to /private/var
trap 'rm -rf "$T"' EXIT
export HOME="$T/home"
mkdir -p "$HOME" "$T/repo" "$T/work"
REPO="$T/repo"
fails=0
# Spelled in pieces so this file never carries the literals the repository-wide key grep looks for.
KP="sk-""or-"
BR="Bear""er"
UIDK="user""_id"
# The CI anti-ruflo patterns, verbatim from .github/workflows/validate.yml:194.
ANTI_RUFLO='tokens? saved|token-cost (saved|savings)|cost savings:|saved [0-9]+ tokens|baseline ?= ?1000|\$[0-9]+\.[0-9]+ saved'
pass() { echo "PASS $1"; }
fail() { echo "FAIL $1"; fails=$((fails + 1)); }

jget() { # jget <json> <python expression over d>
  printf '%s' "$1" | "$PY" -B -c 'import json,sys; d=json.load(sys.stdin); print(eval(sys.argv[1]))' "$2" 2>/dev/null
}

[ -f "$SCRIPT" ] || { echo "FAIL missing $SCRIPT"; exit 1; }

# 1. selftest via the literal flag the CI sweep greps for.
if "$PY" -B "$SCRIPT" --selftest >"$T/work/selftest.out" 2>&1; then pass "selftest"; else fail "selftest"; tail -20 "$T/work/selftest.out"; fi

# 2. no network import in the file (the vault is the only HTTP client).
if grep -nE '^[[:space:]]*(import|from)[[:space:]]+(urllib|http|socket|ssl|requests|ftplib|smtplib|asyncio|httpx|aiohttp)\b' "$SCRIPT"; then
  fail "network import present"
else
  pass "no network import"
fi

# 2b. the CI anti-ruflo gate (validate.yml:194) greps scripts/ too: the script must not match it,
# not even through a literal copy of its own patterns inside the selftest.
if grep -inE "$ANTI_RUFLO" "$SCRIPT"; then
  fail "anti-ruflo pattern matches the script itself"
else
  pass "script passes the CI anti-ruflo grep"
fi

# 3. data-dir: created 0700, outside the repository.
out="$("$PY" -B "$SCRIPT" data-dir --repo "$REPO")"
DD="$(jget "$out" 'd["data_dir"]')"
case "$DD" in
  "$HOME"/.claude/compound-v-jev/*) pass "data dir under HOME" ;;
  *) fail "data dir location: $out" ;;
esac
mode="$("$PY" -B -c 'import os,sys; print(oct(os.stat(sys.argv[1]).st_mode & 0o777))' "$DD")"
if [ "$mode" = "0o700" ]; then pass "data dir 0700"; else fail "data dir mode $mode"; fi

# 4. build t3: request file 0600, options in safety order, text redacted, not in argv.
printf '%s' '{"request": "Rename the build flag in Makefile", "paths": ["Makefile"], "hints": ["build"]}' >"$T/work/state.json"
out="$("$PY" -B "$SCRIPT" build --point t3 --state-file "$T/work/state.json" --repo "$REPO")"
if [ "$(jget "$out" 'd["status"]')" = "ok" ]; then pass "build ok"; else fail "build: $out"; fi
REQ="$(jget "$out" 'd["request_file"]')"
case "$REQ" in "$DD"/req/*.req.json) pass "request file in req/" ;; *) fail "request path $REQ" ;; esac
mode="$("$PY" -B -c 'import os,sys; print(oct(os.stat(sys.argv[1]).st_mode & 0o777))' "$REQ")"
if [ "$mode" = "0o600" ]; then pass "request file 0600"; else fail "request file mode $mode"; fi
order="$("$PY" -B -c '
import sys
t = open(sys.argv[1]).read()
idx = [t.find("\"%s\":" % k) for k in ("unknown", "user-facing-major", "user-facing-minor", "plumbing")]
print("ok" if -1 not in idx and idx == sorted(idx) else "bad %r" % idx)' "$REQ")"
if [ "$order" = "ok" ]; then pass "options kept in safety order"; else fail "option order: $order"; fi
for k in point catalogue_hash model body timeout_ms context repo; do
  v="$("$PY" -B -c 'import json,sys; print(sys.argv[2] in json.load(open(sys.argv[1])))' "$REQ" "$k")"
  [ "$v" = "True" ] || fail "request file lacks $k"
done

# 5. a key-shaped string in the state is refused (fail closed), never written.
printf '{"request": "use key %sv1-0123456789abcdef0123456789abcdef0123456789abcdef with %s auth"}' "$KP" "$BR" >"$T/work/bad.json"
out="$("$PY" -B "$SCRIPT" build --point t3 --state-file "$T/work/bad.json" --repo "$REPO")"
if [ "$(jget "$out" 'd.get("reason")')" = "redaction" ]; then pass "key-shaped state refused"; else fail "key-shaped state: $out"; fi
printf '%s' 'not json' >"$T/work/junk.json"
out="$("$PY" -B "$SCRIPT" build --point t3 --state-file "$T/work/junk.json" --repo "$REPO")"
if [ "$(jget "$out" 'd.get("reason")')" = "bad_input" ]; then pass "bad state is bad_input"; else fail "bad state: $out"; fi

# 6. parse: ok Choice keyed by label regardless of order; usage.cost dropped; telemetry line.
B="$(basename "$REQ" .req.json)"
cat >"$DD/resp/$B.resp.json" <<'EOF'
{"status": "ok", "latency_ms": 312, "body": {"id": "gen-1", "provider": "TypeSafe", "model": "typesafe/jev-1.13-20260917",
 "answers": {"category": {"type": "choice", "choice": "plumbing", "confidence": 0.97,
   "probabilities": {"plumbing": 0.97, "unknown": 0.01, "user-facing-minor": 0.01, "user-facing-major": 0.01}}},
 "usage": {"input_tokens": 400, "output_tokens": 1, "cost": 0.0000123}}}
EOF
out="$("$PY" -B "$SCRIPT" parse --response-file "$DD/resp/$B.resp.json" --repo "$REPO" --mode shadow --hook-budget-left-ms 900)"
if [ "$(jget "$out" 'd["answers"]["category"]["answer"]')" = "plumbing" ]; then pass "parse choice"; else fail "parse choice: $out"; fi
if [ "$(jget "$out" 'd["model"]')" = "typesafe/jev-1.13-20260917" ]; then pass "resolved model recorded"; else fail "model: $out"; fi
if [ "$(jget "$out" 'd["point"]')" = "t3" ]; then pass "point from sibling request"; else fail "point: $out"; fi
if grep -q 'cost' "$DD/calls.jsonl"; then fail "usage.cost reached telemetry"; else pass "usage.cost dropped"; fi
keys="$("$PY" -B -c 'import json,sys; print(",".join(sorted(json.loads(open(sys.argv[1]).readlines()[-1]))))' "$DD/calls.jsonl")"
if [ "$keys" = "answer,catalogue_hash,hook_budget_left_ms,latency_ms,mode,model,point,probs,status,ts" ]; then pass "telemetry keys exact"; else fail "telemetry keys: $keys"; fi
if grep -q 'Rename the build flag' "$DD/calls.jsonl"; then fail "state text in telemetry"; else pass "no state text in telemetry"; fi

# 7. an error body carrying the account id is never copied; 402 maps to unavailable(credits).
cat >"$T/work/err.resp.json" <<EOF
{"status": "error", "http_status": 402, "latency_ms": 80,
 "body": {"error": {"message": "Insufficient credits LEAKMARKER", "code": 402}, "$UIDK": "user_LEAKMARKER_42"}}
EOF
out="$("$PY" -B "$SCRIPT" parse --response-file "$T/work/err.resp.json" --repo "$REPO" --mode shadow)"
if [ "$(jget "$out" 'd["status"]+"/"+d["reason"]')" = "unavailable/credits" ]; then pass "402 -> unavailable(credits)"; else fail "402: $out"; fi
case "$out" in *LEAKMARKER*|*"$UIDK"*) fail "error body copied to stdout" ;; *) pass "error body not in stdout" ;; esac
if grep -rq 'LEAKMARKER' "$DD"; then fail "error body copied to data dir"; else pass "error body not in data dir"; fi

# 8. pair: one line with the exact keys; a 31-day-old line is pruned on write.
old="$("$PY" -B -c 'import time; print(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 31 * 86400)))')"
printf '{"ts": "%s", "request_file": "x", "claude_category": "plumbing", "backend": "claude", "t3_reason": "demotion"}\n' "$old" >"$DD/shadow-pairs.jsonl"
out="$("$PY" -B "$SCRIPT" pair --request-file "$REQ" --claude-category plumbing --backend claude --t3-reason demotion --repo "$REPO")"
if [ "$(jget "$out" 'd["status"]')" = "ok" ]; then pass "pair ok"; else fail "pair: $out"; fi
n="$(wc -l <"$DD/shadow-pairs.jsonl" | tr -d ' ')"
if [ "$n" = "1" ]; then pass "old pair pruned"; else fail "pairs file has $n lines"; fi
keys="$("$PY" -B -c 'import json,sys; print(",".join(sorted(json.loads(open(sys.argv[1]).readline()))))' "$DD/shadow-pairs.jsonl")"
if [ "$keys" = "backend,claude_category,request_file,t3_reason,ts" ]; then pass "pair keys exact"; else fail "pair keys: $keys"; fi

# 9. eval: prepare four requests per corpus item, fake answers, report.
cat >"$T/work/corpus.jsonl" <<'EOF'
{"id": "c1", "request": "Bump the lint rule config", "paths": [".eslintrc"], "hints": [], "t3_reason": "demotion", "label_draft": "plumbing", "label_source": "implementer-draft", "human_label": null, "claude_label": null}
{"id": "c2", "request": "Change the checkout payment flow", "paths": ["src/pay.ts"], "hints": [], "t3_reason": "sensitive", "label_draft": "user-facing-major", "label_source": "implementer-draft", "human_label": null, "claude_label": null}
EOF
out="$("$PY" -B "$SCRIPT" eval --t3 --prepare --corpus "$T/work/corpus.jsonl" --repo "$REPO")"
cnt="$(jget "$out" 'len(d["request_files"])')"
if [ "$cnt" = "8" ]; then pass "eval prepare: 4 requests per item"; else fail "eval prepare: $out"; fi
printf '%s' "$out" | "$PY" -B -c '
import json, os, sys
for f in json.load(sys.stdin)["request_files"]:
    base = os.path.basename(f)[: -len(".req.json")]
    resp = os.path.join(os.path.dirname(os.path.dirname(f)), "resp", base + ".resp.json")
    body = {"model": "typesafe/jev-1.13-20260917", "answers": {"category": {"type": "choice", "choice": "plumbing",
            "probabilities": {"plumbing": 1.0, "unknown": 0.0, "user-facing-minor": 0.0, "user-facing-major": 0.0}}}}
    json.dump({"status": "ok", "latency_ms": 300, "body": body}, open(resp, "w"))
'
out="$("$PY" -B "$SCRIPT" eval --t3 --report "$T/work/report.md" --repo "$REPO")"
if [ -s "$T/work/report.md" ]; then pass "eval report written"; else fail "eval report: $out"; fi
if grep -q 'Wilson' "$T/work/report.md"; then pass "report has intervals"; else fail "report lacks intervals"; fi
if grep -q 'typesafe/jev-1.13-20260917' "$T/work/report.md"; then pass "report names model id"; else fail "report lacks model id"; fi
if grep -q 'histogram' "$T/work/report.md"; then pass "report has histogram"; else fail "report lacks histogram"; fi
if grep -qiE "$ANTI_RUFLO" "$T/work/report.md"; then
  fail "anti-ruflo phrase in report"
else
  pass "no anti-ruflo phrase"
fi

# 10. no key-shaped string in any file written, and nothing written under the repository.
if grep -rqE "$KP|$BR " "$HOME" "$T/work/report.md"; then fail "key-shaped string written"; else pass "no key-shaped string"; fi
if [ -z "$(ls -A "$REPO")" ]; then pass "nothing written under the repository"; else fail "repo not empty: $(ls -A "$REPO")"; fi

# 11. usage errors exit 2.
"$PY" -B "$SCRIPT" build --point nope --state-file "$T/work/state.json" --repo "$REPO" >/dev/null 2>&1
rc=$?
if [ "$rc" = "2" ]; then pass "usage error exits 2"; else fail "usage error exit $rc"; fi

[ "$fails" = "0" ] || { echo "$fails failure(s)"; exit 1; }
echo "all jev-core tests pass"
