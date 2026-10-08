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

# 6b. contract: every reason the vault can send survives parse unchanged. The reason literals are
# read from vault.tsx itself, so a reason added there without a matching entry here fails. The
# `function unavailable(reason` and `function failed(reason` definitions do not match `\b<fn>\('`.
VAULT="$ROOT/plugins/compound-v-vault/hooks/vault.tsx"
reasons="$("$PY" -B - "$VAULT" <<'PYEOF'
import re, sys
src = open(sys.argv[1]).read()
for fn, status in (("unavailable", "unavailable"), ("failed", "error")):
    found = sorted(set(re.findall(r"\b%s\('([a-z_]+)'" % fn, src)))
    if not found:
        print("NONE %s" % status)
    for r in found:
        print("%s %s" % (status, r))
PYEOF
)"
if printf '%s\n' "$reasons" | grep -q '^NONE'; then fail "contract: no reason literals found in vault.tsx"; fi
n=0
while read -r st rs; do
  [ -n "$st" ] || continue
  [ "$st" = "NONE" ] && continue
  printf '{"status": "%s", "reason": "%s", "latency_ms": 1}' "$st" "$rs" >"$DD/resp/$B.resp.json"
  out="$("$PY" -B "$SCRIPT" parse --response-file "$DD/resp/$B.resp.json" --repo "$REPO" --mode shadow)"
  got="$(jget "$out" 'd["status"] + " " + d.get("reason", "")')"
  if [ "$got" = "$st $rs" ]; then n=$((n + 1)); else fail "contract: vault $st($rs) parsed as '$got'"; fi
done <<EOF
$reasons
EOF
if [ "$n" -gt 0 ]; then pass "contract: $n vault reasons survive parse unchanged"; else fail "contract: no vault reason checked"; fi

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
# 8b. pair with the headless classify's measure: one more key, the measure validated; a malformed one
# is refused and writes nothing; no request text in any pair line.
M='{"wall_ms":9900,"duration_ms":6168,"duration_api_ms":2360,"tokens":{"input_tokens":2,"output_tokens":6,"cache_read_input_tokens":0,"cache_creation_input_tokens":53136},"model":"claude-sonnet-4-5-20250929"}'
out="$("$PY" -B "$SCRIPT" pair --request-file "$REQ" --claude-category plumbing --backend claude --t3-reason demotion --repo "$REPO" --claude-measure-json "$M")"
keys="$("$PY" -B -c 'import json,sys; print(",".join(sorted(json.loads(open(sys.argv[1]).readlines()[-1]))))' "$DD/shadow-pairs.jsonl")"
wall="$("$PY" -B -c 'import json,sys; print(json.loads(open(sys.argv[1]).readlines()[-1])["claude_measure"]["duration_api_ms"])' "$DD/shadow-pairs.jsonl")"
if [ "$(jget "$out" 'd["status"]')" = "ok" ] && [ "$keys" = "backend,claude_category,claude_measure,request_file,t3_reason,ts" ] && [ "$wall" = "2360" ]; then
  pass "pair with --claude-measure-json stores the measure"
else
  fail "pair with a measure: $out keys=$keys"
fi
n_before="$(wc -l <"$DD/shadow-pairs.jsonl" | tr -d ' ')"
out="$("$PY" -B "$SCRIPT" pair --request-file "$REQ" --claude-category plumbing --backend claude --t3-reason demotion --repo "$REPO" --claude-measure-json '{"total_cost_usd": 0.1}')"
n_after="$(wc -l <"$DD/shadow-pairs.jsonl" | tr -d ' ')"
if [ "$(jget "$out" 'd["reason"]')" = "bad_input" ] && [ "$n_before" = "$n_after" ]; then pass "a malformed measure is refused and writes nothing"; else fail "malformed measure: $out ($n_before -> $n_after)"; fi
if grep -q 'Rename the build flag' "$DD/shadow-pairs.jsonl"; then fail "request text in a pair line"; else pass "no request text in any pair line"; fi

# 9. eval: prepare six requests per corpus item (the original x3, three variants x1), fake answers, report.
cat >"$T/work/corpus.jsonl" <<'EOF'
{"id": "c1", "request": "Bump the lint rule config", "paths": [".eslintrc"], "hints": [], "t3_reason": "demotion", "label_draft": "plumbing", "label_source": "implementer-draft", "human_label": null, "claude_label": null}
{"id": "c2", "request": "Change the checkout payment flow", "paths": ["src/pay.ts"], "hints": [], "t3_reason": "sensitive", "label_draft": "user-facing-major", "label_source": "implementer-draft", "human_label": null, "claude_label": null}
EOF
out="$("$PY" -B "$SCRIPT" eval --t3 --prepare --corpus "$T/work/corpus.jsonl" --repo "$REPO")"
cnt="$(jget "$out" 'len(d["request_files"])')"
if [ "$cnt" = "12" ]; then pass "eval prepare: 6 requests per item"; else fail "eval prepare: $out"; fi
MAN="$DD/eval/eval-t3.json"
shape="$("$PY" -B -c '
import json, sys
es = json.load(open(sys.argv[1]))["entries"]
ok = (sorted((e["variant"], e["repeat"]) for e in es if e["id"] == "c1")
      == [("original", 1), ("original", 2), ("original", 3), ("reversed", 1), ("wording1", 1), ("wording2", 1)]
      and [e["position"] for e in es] == list(range(1, len(es) + 1))
      and len({e["request_id"] for e in es}) == len(es))
print("ok" if ok else "bad")' "$MAN" 2>/dev/null)"
if [ "$shape" = "ok" ]; then pass "eval manifest under eval/: repeat index, request id and position per request"; else fail "eval manifest shape: $shape"; fi
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

# 12. /v:triage Phase T prose: the re-invocation passes --t3-engine, and the Jev step (T2b) names
# t3-request, jev_classify, parse --mode shadow and pair. A copy with any one removed must fail.
TRIAGE_MD="$ROOT/commands/v-triage.md"
prose_check() { # md -> "ok" or what is missing
  "$PY" -B - "$1" <<'PYEOF'
import re, sys
text = open(sys.argv[1], encoding="utf-8").read()
blocks = re.findall(r"^[ \t]*```bash\n(.*?)^[ \t]*```", text, re.S | re.M)
reinv = [b for b in blocks if 'compound-v-preeval.py" triage' in b and "--t3-category" in b]
m = re.search(r"^### T2b\..*?(?=^### )", text, re.S | re.M)
step = m.group(0) if m else ""
need = [
    ("re-invocation passes --t3-engine", bool(reinv) and all("--t3-engine" in b for b in reinv)),
    ("T2b sits between T2 and T3", bool(step) and text.find("### T2.") < text.find("### T2b.") < text.find("### T3.")),
    ("t3-request --context offline", "t3-request" in step and "--context offline" in step),
    ("jev_classify loaded with ToolSearch", "mcp__compound-v-vault__jev_classify" in step and "ToolSearch" in step),
    ("parse --mode shadow --request-file", "parse --mode shadow --request-file" in step),
    ("pair", re.search(r'compound-v-jev\.py" pair --request-file', step) is not None),
    ("pair passes the measure, dropped on the Task route",
     "--claude-measure-json '<measure_json>'" in step and "Task route" in step),
    ("T2 keeps the classify's measure", "**Keep `measure`**" in text),
    ("no_key/egress/disabled write no pair", all(r in step for r in ("no_key", "egress", "disabled"))
     and "write no pair" in step),
    ("never skips T3", "never skips T3" in step),
    ("t3_reason kept from the first result", "Keep `t3_reason`" in text),
]
missing = [n for n, ok in need if not ok]
print("ok" if not missing else "missing: " + "; ".join(missing))
PYEOF
}
got="$(prose_check "$TRIAGE_MD")"
if [ "$got" = "ok" ]; then pass "v-triage prose: --t3-engine and the Jev step"; else fail "v-triage prose: $got"; fi
for tok in '--t3-engine' 't3-request' 'jev_classify' 'parse --mode shadow' '" pair --request-file' '--claude-measure-json'; do
  "$PY" -B - "$TRIAGE_MD" "$T/work/triage-mut.md" "$tok" <<'PYEOF'
import sys
src, dst, tok = sys.argv[1:4]
open(dst, "w", encoding="utf-8").write(open(src, encoding="utf-8").read().replace(tok, "XXXX"))
PYEOF
  got="$(prose_check "$T/work/triage-mut.md")"
  if [ "$got" != "ok" ]; then pass "planted: prose without '$tok' fails the check"; else fail "planted: prose without '$tok' still passes"; fi
done

# 13. The prose's own commands, run as written (placeholders filled) against a fixture repo whose
# request reaches T3: T2 asks for T3, the re-invocation writes a record with a t3 block, and the Jev
# step's t3-request, parse and pair commands run. A copy of the prose whose re-invocation lost
# --t3-engine writes a record without one.
block() { # md selector out: the one bash block matching selector, FILL_* placeholders filled
  "$PY" -B - "$1" "$2" "$3" <<'PYEOF'
import os, re, sys
md, sel, out = sys.argv[1:4]
text = open(md, encoding="utf-8").read()
blocks = re.findall(r"^[ \t]*```bash\n(.*?)^[ \t]*```", text, re.S | re.M)
pick = {
    "t2": lambda b: 'compound-v-preeval.py" triage' in b and "--t3-category" not in b,
    "reinvoke": lambda b: 'compound-v-preeval.py" triage' in b and "--t3-category" in b,
    "t3req": lambda b: "t3-request" in b,
    "parse": lambda b: 'compound-v-jev.py" parse' in b,
    "pair": lambda b: 'compound-v-jev.py" pair' in b,
}[sel]
found = [b for b in blocks if pick(b)]
if len(found) != 1:
    sys.exit("expected one %s block, found %d" % (sel, len(found)))
b = found[0]
for ph, var in (("<the request text>", "FILL_REQUEST"), ("<category>", "FILL_CATEGORY"),
                ("<engine>", "FILL_ENGINE"), ("<t3_reason>", "FILL_REASON"),
                ("<request_file>", "FILL_REQ_FILE"), ("<response_file>", "FILL_RESP_FILE"),
                ("<measure_json>", "FILL_MEASURE")):
    if ph in b:
        b = b.replace(ph, os.environ[var])
open(out, "w", encoding="utf-8").write(b)
PYEOF
}
P="$T/proj"
mkdir -p "$P/.claude" "$P/src"
printf 'def upload(chunk):\n    return chunk\n' >"$P/src/uploader.py"
# Safety coverage, but nothing banded under src/: the shape that makes the engine ask for T3.
cat >"$P/.claude/compound-v-impact-taxonomy.yaml" <<'YAML'
version: 1

path_patterns:
  - glob: "docs/**"
    difficulty_band: low
    impact_band: low

content_patterns:
  - match: "terms of service"
    pattern_type: literal
    case: insensitive
    scan: content
    kind: legal_copy
    impact_band: high

sensitive_path_list:
  - "**/*.env"
  - "**/secrets/**"

churn:
  exclude_paths:
    - "**/*.lock"
  format_commit_patterns:
    - "^chore: format"
YAML
git -C "$P" init -q >/dev/null 2>&1
git -C "$P" add -A >/dev/null 2>&1
git -C "$P" -c user.name=t -c user.email=t@example.invalid -c commit.gpgsign=false commit -q -m fixture >/dev/null 2>&1
cp -R "$P" "$T/proj-mut"
export CV="$ROOT" CLAUDE_CODE_SESSION_ID="sess-jev-core"
export FILL_REQUEST="please add a retry loop to the uploader module at src/uploader.py"
export FILL_CATEGORY="user-facing-minor" FILL_ENGINE="parent"
record_t3() { # repo pre_eval_id -> the record's t3 block as compact JSON, or "none"
  "$PY" -B -c 'import json,sys; r=json.load(open(sys.argv[1])); print(json.dumps(r.get("t3"), sort_keys=True) if "t3" in r else "none")' \
    "$1/docs/superpowers/pre-eval/$2.json" 2>/dev/null
}
block "$TRIAGE_MD" t2 "$T/work/t2.sh" && first="$(cd "$P" && bash "$T/work/t2.sh" 2>/dev/null)"
if [ "$(jget "${first:-null}" 'd.get("needs_t3")')" = "True" ]; then pass "prose T2 on the fixture asks for T3"; else fail "prose T2: ${first:-no output}"; fi
FILL_REASON="$(jget "${first:-null}" 'd.get("t3_reason") or "unbanded"')"
export FILL_REASON
export PROMPT_FILE="$T/work/t3-prompt.txt"
jget "${first:-null}" 'd.get("t3_prompt", "")' >"$PROMPT_FILE"
block "$TRIAGE_MD" reinvoke "$T/work/reinvoke.sh" && second="$(cd "$P" && bash "$T/work/reinvoke.sh" 2>/dev/null)"
pid="$(jget "${second:-null}" 'd.get("pre_eval_id", "")')"
t3b="$(record_t3 "$P" "$pid")"
if [ "$t3b" = '{"category": "user-facing-minor", "engine": "parent"}' ]; then
  pass "prose re-invocation writes a record with a t3 block"
else
  fail "prose re-invocation t3 block: ${t3b:-no record} (${second:-no output})"
fi

# The Jev step's commands, as written, in the same repo (same --repo .).
block "$TRIAGE_MD" t3req "$T/work/t3req.sh" && jr="$(cd "$P" && bash "$T/work/t3req.sh" 2>/dev/null)"
JREQ="$(jget "${jr:-null}" 'd.get("request_file", "")')"
ctx="$("$PY" -B -c 'import json,sys; print(json.load(open(sys.argv[1]))["context"])' "$JREQ" 2>/dev/null)"
if [ "$(jget "${jr:-null}" 'd.get("status")')" = "ok" ] && [ "$ctx" = "offline" ]; then
  pass "prose t3-request builds an offline request"
else
  fail "prose t3-request: ${jr:-no output}"
fi
JRESP="$(dirname "$(dirname "$JREQ")")/resp/$(basename "$JREQ" .req.json).resp.json"
printf '%s' '{"status": "ok", "latency_ms": 900, "body": {"model": "typesafe/jev-1.13-20260917", "answers": {"category": {"type": "choice", "choice": "user-facing-minor", "probabilities": {"user-facing-minor": 0.8, "unknown": 0.1, "user-facing-major": 0.05, "plumbing": 0.05}}}}}' >"$JRESP"
export FILL_REQ_FILE="$JREQ" FILL_RESP_FILE="$JRESP"
export FILL_MEASURE='{"wall_ms":8000,"duration_ms":5000,"duration_api_ms":2100,"tokens":{"input_tokens":2,"output_tokens":6,"cache_read_input_tokens":null,"cache_creation_input_tokens":null},"model":null}'
block "$TRIAGE_MD" parse "$T/work/parse.sh" && pr="$(cd "$P" && bash "$T/work/parse.sh" 2>/dev/null)"
if [ "$(jget "${pr:-null}" 'd["answers"]["category"]["answer"]')" = "user-facing-minor" ]; then pass "prose parse reads the answer"; else fail "prose parse: ${pr:-no output}"; fi
block "$TRIAGE_MD" pair "$T/work/pair.sh" && pa="$(cd "$P" && bash "$T/work/pair.sh" 2>/dev/null)"
last="$(tail -n 1 "$(dirname "$(dirname "$JREQ")")/shadow-pairs.jsonl" 2>/dev/null)"
if [ "$(jget "${pa:-null}" 'd.get("status")')" = "ok" ] \
   && [ "$(jget "${last:-null}" 'd["backend"] + "/" + d["claude_category"] + "/" + d["t3_reason"]')" = "parent/user-facing-minor/$FILL_REASON" ] \
   && [ "$(jget "${last:-null}" 'd["claude_measure"]["duration_api_ms"]')" = "2100" ]; then
  pass "prose pair writes the carried category, engine, reason and measure"
else
  fail "prose pair: ${pa:-no output} ${last:-no line}"
fi
case "$JREQ" in "$HOME"/.claude/compound-v-jev/*/req/*.req.json) pass "prose Jev request lands in the per-user data dir" ;; *) fail "prose Jev request path: $JREQ" ;; esac
if [ -z "$(find "$P" \( -name '*.req.json' -o -name '*.resp.json' -o -name 'shadow-pairs.jsonl' \) 2>/dev/null)" ]; then
  pass "no Jev file under the fixture repo"
else
  fail "Jev file under the fixture repo"
fi

# Planted: the same re-invocation with --t3-engine removed from the prose writes no t3 block.
"$PY" -B - "$TRIAGE_MD" "$T/work/triage-noengine.md" <<'PYEOF'
import sys
src, dst = sys.argv[1:3]
open(dst, "w", encoding="utf-8").write(open(src, encoding="utf-8").read().replace(" --t3-engine <engine>", ""))
PYEOF
block "$T/work/triage-noengine.md" t2 "$T/work/t2m.sh" && (cd "$T/proj-mut" && bash "$T/work/t2m.sh" >/dev/null 2>&1)
block "$T/work/triage-noengine.md" reinvoke "$T/work/reinvokem.sh" \
  && secm="$(cd "$T/proj-mut" && bash "$T/work/reinvokem.sh" 2>/dev/null)"
pidm="$(jget "${secm:-null}" 'd.get("pre_eval_id", "")')"
if [ -n "$pidm" ] && [ "$(record_t3 "$T/proj-mut" "$pidm")" = "none" ]; then
  pass "planted: a re-invocation without --t3-engine writes no t3 block"
else
  fail "planted: the no-engine re-invocation did not show the missing block (${secm:-no output})"
fi

[ "$fails" = "0" ] || { echo "$fails failure(s)"; exit 1; }
echo "all jev-core tests pass"
