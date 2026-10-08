#!/usr/bin/env bash
# Fixture: a git repo with the typo, plus .claude/compound-v-impact-taxonomy.yaml
# (the example taxonomy shipped with the plugin).
#
# Verified locally:
#   CV_TRIAGE_REQUEST="Fix the typo 'recieve' -> 'receive' in README.md ..." \
#   python3 scripts/compound-v-preeval.py triage --request-env CV_TRIAGE_REQUEST \
#           --repo . --session-id s1 --json
#   => "tier": "DIRECT", "decision": "FASTPATH_ELIGIBLE"
# WITHOUT the taxonomy the same request scores FULL_PIPELINE (predicate 3 fails
# on "bands=unknown/unknown"), so the taxonomy is a precondition of the mechanism
# under test, not a hint about the expected answer.
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/../lib/cv-fixture-lib.sh"

mkdir -p src

cat > README.md <<'MD'
# Ledger

A small double-entry ledger.

## Webhooks

When a payment settles you recieve a `payment.settled` event on the webhook
endpoint you registered.
MD

cat > src/ledger.ts <<'TS'
export function post(amount: number) {
  return amount
}
TS

cv_copy_taxonomy
cv_vendor_tools
cv_git_init
cv_git_commit_all "ledger docs with a typo"
