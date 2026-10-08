#!/usr/bin/env bash
# tests/test-memory-recall-bench.sh — tests the `bench` SUBCOMMAND itself (idea 5 of
# /v:remember's read-time quality work): does hit@top actually distinguish a query that
# should hit from one that should miss, does it split totals by group, and does it degrade
# sanely on a malformed query file? This is a harness test, NOT a numbers test: it runs
# against a small built-in FIXTURE repo, never the real superpowers-v checkout (CI has no
# real index, and the real repo's hit/miss numbers belong in release notes, produced by hand
# with `bench --queries tests/memory-queries.tsv`, never invented here).
#
# Run explicitly under /bin/bash (bash 3.2 on macOS) — no arrays, no bash-4-only constructs,
# matching tests/test-memory-install.sh / test-dogfood-index.sh.
set -u

REPO="$(cd "$(dirname "$0")/.." && pwd)"
ENGINE="$REPO/scripts/compound-v-memory.py"

[ -f "$ENGINE" ] || { echo "FATAL: $ENGINE missing"; exit 1; }
command -v git >/dev/null 2>&1 || { echo "FATAL: git required"; exit 1; }

pass=0; fail=0
ok()  { pass=$((pass + 1)); printf 'PASS %s\n' "$1"; }
bad() { fail=$((fail + 1)); printf 'FAIL %s\n' "$1"; }

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# --------------------------------------------------------------------------- #
# Fixture repo: two docs/superpowers/specs/*.md, one about "frobnicator calibration", one
# about "widget packaging" — distinct vocabularies so a query built from one's words has no
# lexical overlap with the other (FTS5 is lexical; that is exactly what makes a miss real).
# --------------------------------------------------------------------------- #
FIXTURE="$WORK/fixture-repo"
mkdir -p "$FIXTURE/docs/superpowers/specs"

git -C "$FIXTURE" init -q
git -C "$FIXTURE" config user.email "test@example.invalid"
git -C "$FIXTURE" config user.name  "memory-recall-bench-test"
git -C "$FIXTURE" config commit.gpgsign false

cat >"$FIXTURE/docs/superpowers/specs/2026-09-01-frobnicator-spec.md" <<'EOF'
# Frobnicator spec

The frobnicator widget needs a left-handed calibration mode, tracked as quokka-calibration.
EOF

cat >"$FIXTURE/docs/superpowers/specs/2026-09-02-packaging-spec.md" <<'EOF'
# Packaging spec

Shipping crates must be palletized before the loading dock accepts them, tracked as zeltar-pallet.
EOF

# A third doc with vocabulary that shares NOTHING (not even a stemmed root) with either doc
# above, so a query drawn only from ITS meaning (a true paraphrase, no shared words) is a
# clean, deterministic FTS5-lexical miss against either target — not an accident of which
# doc happens to share a token with the query.
cat >"$FIXTURE/docs/superpowers/specs/2026-09-03-unrelated-spec.md" <<'EOF'
# Unrelated spec

This document exists only so the corpus has a third entry; it discusses nothing relevant.
EOF

git -C "$FIXTURE" add -A
git -C "$FIXTURE" commit -q -m seed

CACHE="$WORK/cache"
mkdir -p "$CACHE"

run_bench() {
  # $1 = queries file, remaining args passed through to `bench`. Combined stdout+stderr —
  # for the text-output and "no traceback" checks, never for JSON (stderr's staleness/refresh
  # lines would corrupt the JSON parse; use run_bench_json for that).
  qfile="$1"; shift
  (cd "$FIXTURE" && COMPOUND_V_MEMORY_HOME="$CACHE" python3 "$ENGINE" \
    bench --queries "$qfile" "$@" 2>&1)
}

run_bench_json() {
  # Same, but ALWAYS passes --json and captures stdout ONLY — the output must be valid JSON
  # on its own, and the inline refresh / staleness lines this engine always writes to stderr
  # must never land in it.
  qfile="$1"; shift
  (cd "$FIXTURE" && COMPOUND_V_MEMORY_HOME="$CACHE" python3 "$ENGINE" \
    bench --queries "$qfile" "$@" --json 2>/dev/null)
}

run_bench_stderr() {
  # stderr ONLY (the classic 2>&1 1>/dev/null swap) — used to check the per-row warning a
  # malformed line prints, without that warning polluting a JSON capture.
  qfile="$1"; shift
  (cd "$FIXTURE" && COMPOUND_V_MEMORY_HOME="$CACHE" python3 "$ENGINE" \
    bench --queries "$qfile" "$@" 2>&1 1>/dev/null)
}

# --------------------------------------------------------------------------- #
# (1) a query that MUST hit, one that MUST miss, plus a paraphrase-labelled row that also
# must miss (no lexical overlap by construction) — the exact three-row shape the docstring
# for `bench` promises to grade correctly.
# --------------------------------------------------------------------------- #
QF1="$WORK/queries-1.tsv"
printf 'frobnicator calibration quokka\tfrobnicator-spec.md\ten\n' >"$QF1"
printf 'zeltar pallet nonexistent-marker-nothing-here\tfrobnicator-spec.md\ten\n' >>"$QF1"
printf 'large parcels get moved onto wooden platforms so warehouse gates permit entry for these goods\tpackaging-spec.md\tparaphrase\n' >>"$QF1"

json1=$(run_bench_json "$QF1" --top 4 --no-embed)
py_check() {
  # $1 = python snippet reading JSON from stdin, printing "True"/"False"
  printf '%s' "$json1" | python3 -c "
import json, sys
d = json.load(sys.stdin)
$1
"
}

if [ "$(py_check 'print(d["rows"][0]["hit"])')" = "True" ]; then
  ok "bench: the frobnicator query HITS (lexical overlap with frobnicator-spec.md)"
else
  bad "bench: the frobnicator query should have hit and did not: $json1"
fi

if [ "$(py_check 'print(d["rows"][1]["hit"])')" = "False" ]; then
  ok "bench: the zeltar/pallet query MISSES (no lexical overlap with frobnicator-spec.md)"
else
  bad "bench: the zeltar/pallet query should have missed and did not: $json1"
fi

if [ "$(py_check 'print(d["rows"][2]["hit"])')" = "False" ]; then
  ok "bench: the paraphrase row MISSES (no lexical overlap with packaging-spec.md by design)"
else
  bad "bench: the paraphrase row should have missed and did not: $json1"
fi

# --------------------------------------------------------------------------- #
# (2) group totals: "all" always counts every row; a named group counts only its own rows.
# --------------------------------------------------------------------------- #
if [ "$(py_check 'print(d["totals"]["all"]["n"] == 3 and d["totals"]["all"]["hits"] == 1)')" = "True" ]; then
  ok "bench: totals.all counts every row (3 rows, 1 hit)"
else
  bad "bench: totals.all wrong: $(py_check 'print(d["totals"]["all"])')"
fi
if [ "$(py_check 'print(d["totals"]["en"]["n"] == 2 and d["totals"]["en"]["hits"] == 1)')" = "True" ]; then
  ok "bench: totals.en counts only the two en-labelled rows"
else
  bad "bench: totals.en wrong: $(py_check 'print(d["totals"].get("en"))')"
fi
if [ "$(py_check 'print(d["totals"]["paraphrase"]["n"] == 1 and d["totals"]["paraphrase"]["hits"] == 0)')" = "True" ]; then
  ok "bench: totals.paraphrase counts only the one paraphrase row, and it is the miss"
else
  bad "bench: totals.paraphrase wrong: $(py_check 'print(d["totals"].get("paraphrase"))')"
fi

# --------------------------------------------------------------------------- #
# (3) text output: hit/MISS markers and the per-group hit@top summary line are present.
# --------------------------------------------------------------------------- #
text1=$(run_bench "$QF1" --top 4 --no-embed)
if printf '%s' "$text1" | grep -q "hit  \[en" && printf '%s' "$text1" | grep -q "MISS \[en"; then
  ok "bench text: hit and MISS markers both appear, tagged with their group"
else
  bad "bench text: markers missing or wrong: $(printf '%s' "$text1" | head -8)"
fi
if printf '%s' "$text1" | grep -Eq "all[[:space:]]+hit@4: 1/3"; then
  ok "bench text: the all-group summary line reports 1/3"
else
  bad "bench text: no correct 'all ... hit@4: 1/3' summary line: $(printf '%s' "$text1" | tail -6)"
fi

# --------------------------------------------------------------------------- #
# (4) a malformed row (wrong column count) is skipped with a warning, not fatal — one good
# row alongside it still runs and reports.
# --------------------------------------------------------------------------- #
QF2="$WORK/queries-2.tsv"
{
  printf '# a comment line, and a blank line below are both skipped\n'
  printf '\n'
  printf 'this line has only one column with no tabs at all\n'
  printf 'frobnicator calibration quokka\tfrobnicator-spec.md\ten\n'
} >"$QF2"
out2=$(run_bench_json "$QF2" --top 4 --no-embed)
rc2=$?
warn2=$(run_bench_stderr "$QF2" --top 4 --no-embed --json)
if [ "$rc2" = "0" ] && printf '%s' "$out2" | python3 -c "
import json, sys
d = json.load(sys.stdin)
assert len(d['rows']) == 1 and d['rows'][0]['hit'] is True
" 2>/dev/null; then
  ok "bench: a malformed row is skipped (warning only); the one good row still runs and hits"
else
  bad "bench: malformed-row handling broke the run (rc=$rc2): $(printf '%s' "$out2" | head -3)"
fi
if printf '%s' "$warn2" | grep -q "expected 3 tab-separated columns"; then
  ok "bench: the skipped malformed row is warned about on stderr, by line number"
else
  bad "bench: no warning printed for the malformed row: $(printf '%s' "$warn2" | head -3)"
fi

# --------------------------------------------------------------------------- #
# (5) an empty/all-malformed query file is a clean exit 1, never a traceback.
# --------------------------------------------------------------------------- #
QF3="$WORK/queries-empty.tsv"
printf '# nothing usable here\n' >"$QF3"
out3=$(run_bench "$QF3" --top 4 --no-embed --json)
rc3=$?
if [ "$rc3" = "1" ] && ! printf '%s' "$out3" | grep -qi "traceback"; then
  ok "bench: an all-comment query file exits 1 with a message, never a traceback"
else
  bad "bench: empty-file handling wrong (rc=$rc3): $(printf '%s' "$out3" | head -3)"
fi

# --------------------------------------------------------------------------- #
# (6) a missing queries file is a clean exit 1, never a traceback.
# --------------------------------------------------------------------------- #
out4=$(run_bench "$WORK/does-not-exist.tsv" --top 4 --no-embed --json)
rc4=$?
if [ "$rc4" = "1" ] && ! printf '%s' "$out4" | grep -qi "traceback"; then
  ok "bench: a missing queries file exits 1 with a message, never a traceback"
else
  bad "bench: missing-file handling wrong (rc=$rc4): $(printf '%s' "$out4" | head -3)"
fi

printf 'tests/test-memory-recall-bench.sh: %d passed, %d failed\n' "$pass" "$fail"
[ "$fail" = "0" ] || exit 1
