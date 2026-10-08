#!/usr/bin/env bash
# Fixture: a disjoint partition with ONE defect — a `backend: codex` job at
# `isolation: direct`. Verified locally: the validator exits 1 with EXACTLY ONE
# violation ("codex requires worktree"). task-1 is `run: serial` on purpose; a
# parallel+direct job would raise a SECOND violation and blur the signal.
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/../lib/cv-fixture-lib.sh"

RUN=docs/superpowers/execution/2026-02-10-search-reindex
mkdir -p "$RUN" src/search docs/runbooks docs/superpowers/specs docs/superpowers/plans

cat > "$RUN/manifest.yaml" <<'YAML'
run_id: 2026-02-10-search-reindex
feature: "Search reindex worker"
spec_path: docs/superpowers/specs/2026-02-10-search-reindex.md
plan_path: docs/superpowers/plans/2026-02-10-search-reindex.md
audits:
  archaeology: docs/superpowers/archaeology/2026-02-10-search-reindex.md
  domain: docs/superpowers/expert/2026-02-10-search-reindex.md
  library: docs/superpowers/library-audit/2026-02-10-search-reindex.md
acceptance_criteria:
  - "Reindex completes without dropping documents"
routing_stance: balanced
max_parallel: 3
jobs:
  - id: task-1-reindex-worker
    title: "Reindex worker"
    body: |
      Build the reindex worker that streams documents into the search index.
    type: large_isolated
    backend: codex
    model: gpt-5.6-terra
    effort: medium
    isolation: direct
    run: serial
    write_allowed:
      - "src/search/**"
    read_allowed:
      - "src/**"
    acceptance:
      - "reindexes without dropping documents"
  - id: task-2-docs
    title: "Reindex runbook"
    body: |
      Document how an operator triggers and monitors a reindex.
    type: docs
    backend: claude
    tier: light
    effort: low
    isolation: worktree
    run: parallel
    write_allowed:
      - "docs/runbooks/reindex.md"
    read_allowed:
      - "src/search/**"
    acceptance:
      - "runbook documents the reindex"
YAML

echo "# Search reindex — spec" > docs/superpowers/specs/2026-02-10-search-reindex.md
echo "# Search reindex — plan" > docs/superpowers/plans/2026-02-10-search-reindex.md
echo "export function reindex() {}" > src/search/reindex.ts
echo "# Reindex runbook" > docs/runbooks/reindex.md

cv_vendor_tools
cv_git_init
cv_git_commit_all "search reindex run, pre-dispatch"
