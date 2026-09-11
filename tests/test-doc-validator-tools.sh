#!/usr/bin/env bash
# tests/test-doc-validator-tools.sh — the library auditor must be told how to FIND
# its own tools, and must not be told a falsehood about them.
#
# WHY THIS FILE EXISTS
#   Until 3.6.2 three documents told the doc-validator that an agent launched
#   inside a native Workflow "does not inherit the session's MCP tools", and
#   cited 12 of 16 audits reporting DEGRADED as the evidence. The claim had never
#   been verified. A live probe on 2026-09-12 spawned an agent inside a native
#   Workflow, ran ToolSearch for `context7`, got BOTH tools back, and called
#   `resolve-library-id` successfully.
#
#   The claim was self-fulfilling: MCP tools are DEFERRED, so they are absent
#   from a tool list until ToolSearch loads their schemas. An auditor told to
#   "check your own tool list" and to expect nothing did exactly that, found
#   nothing, and wrote DEGRADED — which was then read back as proof. Thirteen
#   Workflow-spawned doc-validator transcripts in this repository contain no
#   Context7 call at all.
#
#   So these rows guard two things a reader cannot verify by looking at prose:
#   that the auditor is told to RUN THE SEARCH, and that the refuted claim has
#   not crept back in.

set -uo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd -P)"

pass=0
fail=0
ok()  { pass=$((pass + 1)); printf 'PASS %s\n' "$1"; }
bad() { fail=$((fail + 1)); printf 'FAIL %s\n' "$1"; }
check(){ if [ "$2" = "1" ]; then ok "$1"; else bad "$1"; fi; }

# The three documents that carry the auditor's tool guidance: the agent
# definition it is spawned as, the inlined prompt used when that definition is
# not loaded, and the phase reference a human reads.
DOCS="
$REPO/agents/doc-validator.md
$REPO/skills/compound-v/doc-validator-prompt.md
$REPO/skills/compound-v/phase-1c-documentation-validation.md
"

for f in $DOCS; do
  n="$(basename "$f")"
  check "$n exists" "$([ -f "$f" ] && echo 1 || echo 0)"

  # The instruction that actually finds a deferred tool.
  check "$n tells the auditor to run ToolSearch" \
    "$(grep -q 'ToolSearch' "$f" && echo 1 || echo 0)"

  # The reason it must, stated so a reader does not "simplify" it away.
  check "$n says the Context7 tools are DEFERRED" \
    "$(grep -qi 'deferred' "$f" && echo 1 || echo 0)"

  # The refuted claim, in any of the spellings the three files used.
  check "$n does NOT repeat the refuted 'a Workflow agent has no MCP' claim" \
    "$(grep -qiE 'do(es)? not inherit the session.s MCP|not inherit.{0,20}MCP tools' "$f" \
       && echo 0 || echo 1)"

  # DEGRADED must stay reachable — the fix is not "assume Context7 is there".
  check "$n still defines the DEGRADED fallback" \
    "$(grep -q 'DEGRADED' "$f" && echo 1 || echo 0)"
done

# An empty search is the ONLY evidence of absence. If a document drops this, an
# auditor is free to go back to reading its tool list and concluding from silence.
check "the phase reference says only an EMPTY search proves absence" \
  "$(grep -qiE 'only an empty|empty result is evidence|empty.{0,30}evidence of absence' \
      "$REPO/skills/compound-v/phase-1c-documentation-validation.md" && echo 1 || echo 0)"

printf '\n%d passed, %d failed\n' "$pass" "$fail"
[ "$fail" = "0" ] || exit 1
echo "OK the library auditor is told how to find its tools, and no refuted claim remains"
exit 0
