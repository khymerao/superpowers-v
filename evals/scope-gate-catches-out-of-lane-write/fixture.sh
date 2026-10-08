#!/usr/bin/env bash
# Fixture: a repo at a known baseline commit, plus the uncommitted working-tree
# state a job left behind. docs/** is the declared lane; the job also modified a
# tracked file outside it AND created an untracked one, so both of the gate's
# probes (baseline diff + ls-files --others) have something to find.
#
# Verified locally: `compound-v-scope-check.py --repo . --baseline <sha>
# --allow 'docs/**'` exits 1 with
#   BLOCKED: 2 file(s) written outside write_allowed:
#     - src/server/auth.ts
#     - src/server/session.ts
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/../lib/cv-fixture-lib.sh"

mkdir -p docs src/server

cat > docs/reindex.md <<'MD'
# Reindex runbook
MD
cat > src/server/auth.ts <<'TS'
export function verifySession(token: string) {
  return token.length > 0
}
TS

cv_vendor_tools
cv_git_init
cv_git_commit_all "baseline before task-3-docs"
# The baseline is a TAG, not a file: a file written after the commit would be
# untracked, and the gate unions untracked paths into the changed set, so the
# fixture itself would show up as a third violation.
git tag cv-baseline HEAD

# --- what the job actually did, after the baseline ---------------------------
cat >> docs/reindex.md <<'MD'

Trigger a reindex with `npm run reindex`. Watch the worker log until it idles.
MD
# in lane, fine. Out of lane, twice:
cat >> src/server/auth.ts <<'TS'

// widened while wiring the docs example
export function verifySessionLoose(token: string) {
  return true
}
TS
cat > src/server/session.ts <<'TS'
export const SESSION_TTL_S = 3600
TS
