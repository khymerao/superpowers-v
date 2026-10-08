#!/bin/bash
# test-lessons.sh — CLI-level test of scripts/compound-v-lessons.py (the /v:lessons drafter).
#
# Builds the script's own selftest fixture in a temp repo, then drives the real CLI:
#   draft --json      -> a candidate with the expected prefer-action appears
#   record rejected   -> the next draft no longer proposes it
#   routing-lessons.md is byte-identical before and after both commands (no script writes it)
# Ubuntu- and macOS-safe: no `sed -i`, no `stat -f`; bytes compared with `cmp`.
set -eu

repo_root=$(cd "$(dirname "$0")/.." && pwd)
script="$repo_root/scripts/compound-v-lessons.py"
export PYTHONDONTWRITEBYTECODE=1

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
fx="$tmp/repo"
mkdir -p "$fx"

pass=0
fail() { echo "FAIL: $1" >&2; exit 1; }
ok() { pass=$((pass + 1)); echo "ok - $1"; }

# --- fixture: the same one the --selftest uses ------------------------------------
python3 - "$script" "$fx" <<'PY'
import importlib.util, sys
spec = importlib.util.spec_from_file_location("cv_lessons", sys.argv[1])
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
mod.build_fixture(sys.argv[2])
PY
lessons="$fx/docs/superpowers/memory/routing-lessons.md"
reviews="$fx/docs/superpowers/memory/lesson-reviews.jsonl"
[ -f "$lessons" ] || fail "fixture did not write routing-lessons.md"
cp "$lessons" "$tmp/lessons.before"

# --- 1. draft --json: the docs-on-light test-floor candidate, tier_up light -> standard
python3 "$script" draft --repo "$fx" --json >"$tmp/d1.json" || fail "draft exited non-zero"
fp=$(python3 - "$tmp/d1.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
key = ["type_model", "test_failure", "docs", "claude", "light"]
hit = [c for c in d["candidates"] if c["key"] == key]
if len(hit) != 1:
    sys.exit("no single candidate for %r" % key)
c = hit[0]
if c["action"] != "tier_up" or "`light` → `standard`" not in c["prefer"]:
    sys.exit("wrong prefer-action: %s / %s" % (c["action"], c["prefer"]))
if not c["bullet"].startswith("- **YYYY-MM-DD** — `docs` on **claude·light**"):
    sys.exit("bullet not in routing-lessons format: %s" % c["bullet"])
if sorted(c["runs"]) != ["2026-01-03-tf-a", "2026-01-04-tf-b"]:
    sys.exit("wrong evidence runs: %r" % c["runs"])
print(c["fingerprint"])
PY
) || fail "draft did not produce the expected tier_up candidate"
ok "draft --json proposes tier_up (light → standard) for docs, citing both runs ($fp)"

python3 - "$tmp/d1.json" <<'PY' || fail "shared-file / below-threshold expectations"
import json, sys
d = json.load(open(sys.argv[1]))
keys = [c["key"] for c in d["candidates"]]
assert ["shared_file", "src/shared/index.ts"] in keys, keys
assert ["type_model", "test_failure", "mechanical_refactor", "claude", "light"] not in keys
assert d["scanned"]["excluded_by_scan_failures"]["recall_exclude"] == 1
PY
ok "shared file becomes a Task 0 candidate; the 1-run / excluded / harness-fault group does not"

[ ! -e "$reviews" ] || fail "draft created lesson-reviews.jsonl — draft must be read-only"
ok "draft wrote nothing"

# --- 2. record rejected, then draft again -> gone ------------------------------------
python3 "$script" record --repo "$fx" --fingerprint "$fp" --decision rejected \
  --note "fixture: docs floor failures are the fixture's own" >"$tmp/r.json" || fail "record exited non-zero"
[ "$(wc -l <"$reviews" | tr -d ' ')" = "1" ] || fail "record did not append exactly one line"
grep -q "\"fingerprint\": \"$fp\"" "$reviews" || fail "recorded line lacks the fingerprint"
ok "record appended one line to lesson-reviews.jsonl"

python3 "$script" draft --repo "$fx" --json >"$tmp/d2.json" || fail "second draft exited non-zero"
python3 - "$tmp/d2.json" "$fp" <<'PY' || fail "rejected fingerprint was proposed again"
import json, sys
d = json.load(open(sys.argv[1]))
fp = sys.argv[2]
assert fp not in [c["fingerprint"] for c in d["candidates"]]
assert fp in [s["fingerprint"] for s in d["skipped_reviewed"]]
PY
ok "rejected candidate is gone from the next draft (listed under skipped_reviewed)"

# --- 3. bad input is refused, and writes nothing -------------------------------------
if python3 "$script" record --repo "$fx" --fingerprint "NOT-HEX" --decision rejected 2>/dev/null; then
  fail "a malformed fingerprint was accepted"
fi
[ "$(wc -l <"$reviews" | tr -d ' ')" = "1" ] || fail "a refused record still wrote"
ok "malformed fingerprint refused without writing"

# --- 4. routing-lessons.md byte-identical -----------------------------------------------
cmp -s "$lessons" "$tmp/lessons.before" || fail "routing-lessons.md changed — no script may write it"
ok "routing-lessons.md byte-identical after draft + record + draft"

echo "PASS: $pass checks"
