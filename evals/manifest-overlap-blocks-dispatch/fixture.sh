#!/usr/bin/env bash
# Fixture: a small project repo carrying ONE Compound V run whose manifest has a
# single, deliberate defect — task-1-exporter's "src/billing/**" swallows
# task-2-invoice-hook's "src/billing/invoice.ts".
#
# Verified locally against scripts/compound-v-validate-manifest.py: exit 1 with
# EXACTLY ONE violation (the overlap). Do not add fields without re-checking
# that the violation count is still 1 — a second violation makes the graders
# ambiguous about what Claude actually found.
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/../lib/cv-fixture-lib.sh"

RUN=docs/superpowers/execution/2026-02-03-billing-export
mkdir -p "$RUN" src/billing src/ui docs/superpowers/specs docs/superpowers/plans

cat > "$RUN/manifest.yaml" <<'YAML'
run_id: 2026-02-03-billing-export
feature: "Billing CSV export"
spec_path: docs/superpowers/specs/2026-02-03-billing-export.md
plan_path: docs/superpowers/plans/2026-02-03-billing-export.md
audits:
  archaeology: docs/superpowers/archaeology/2026-02-03-billing-export.md
  domain: docs/superpowers/expert/2026-02-03-billing-export.md
  library: docs/superpowers/library-audit/2026-02-03-billing-export.md
acceptance_criteria:
  - "Export produces a CSV of the current month's invoices"
  - "No write outside the partitioned file sets"
routing_stance: balanced
max_parallel: 3
jobs:
  - id: task-1-exporter
    title: "CSV exporter module"
    body: |
      Build the CSV exporter under src/billing. Nothing else defines the row shape.
    type: bounded_crud
    backend: claude
    tier: standard
    effort: medium
    isolation: worktree
    run: parallel
    write_allowed:
      - "src/billing/**"
    read_allowed:
      - "src/**"
    acceptance:
      - "writes a CSV of the current month's invoices"
  - id: task-2-invoice-hook
    title: "Invoice screen calls the exporter"
    body: |
      Wire the export button on the invoice screen to the exporter.
    type: bounded_crud
    backend: claude
    tier: standard
    effort: medium
    isolation: worktree
    run: parallel
    write_allowed:
      - "src/billing/invoice.ts"
    read_allowed:
      - "src/**"
    acceptance:
      - "invoice screen triggers an export"
YAML

echo "# Billing CSV export — spec" > docs/superpowers/specs/2026-02-03-billing-export.md
echo "# Billing CSV export — plan" > docs/superpowers/plans/2026-02-03-billing-export.md
echo "export function renderInvoice() { return null }" > src/billing/invoice.ts
echo "export function exportCsv() { return '' }" > src/billing/exporter.ts
echo "export const App = () => null" > src/ui/app.ts

cv_vendor_tools
cv_git_init
cv_git_commit_all "billing export run, pre-dispatch"
