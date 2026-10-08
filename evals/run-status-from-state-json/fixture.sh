#!/usr/bin/env bash
# Fixture: one run directory, halted. `phase: BLOCKED` is deliberate on two
# counts: it is the interesting status to report, and it is TERMINAL for
# hooks/lane-guard.sh (see run_is_terminal(), TERMINAL_PHASES = MERGED|BLOCKED),
# so the plugin's own PreToolUse lane guard will not claim this checkout for a
# job and start denying the agent's writes mid-run.
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/../lib/cv-fixture-lib.sh"

RUN=docs/superpowers/execution/2026-03-04-notifications-digest
mkdir -p "$RUN" src/api src/ui docs/features

cat > "$RUN/state.json" <<'JSON'
{
  "run_id": "2026-03-04-notifications-digest",
  "phase": "BLOCKED",
  "updated_at": "2026-03-04T14:22:10Z",
  "jobs": {
    "task-1-api": {
      "status": "done",
      "isolation": "worktree",
      "baseline": "3f21c0ab9d4e5f6071829304a5b6c7d8e9f01234",
      "realised_commit": "8a1b2c3d4e5f60718293a4b5c6d7e8f901234567",
      "scope": "PASS"
    },
    "task-2-ui": {
      "status": "blocked",
      "isolation": "worktree",
      "baseline": "3f21c0ab9d4e5f6071829304a5b6c7d8e9f01234",
      "realised_commit": "b7c8d9e0f1a2b3c4d5e6f708192a3b4c5d6e7f80",
      "scope": "BLOCKED",
      "scope_violations": ["src/api/digest.ts"],
      "note": "wrote into task-1-api's lane; never merged"
    },
    "task-3-docs": {
      "status": "pending",
      "isolation": "worktree",
      "depends_on": ["task-2-ui"]
    }
  },
  "waves": {
    "1": { "jobs": ["task-1-api", "task-2-ui"], "merged": ["task-1-api"], "integrated": false }
  }
}
JSON

echo "# Notifications digest — spec" > "$RUN/spec.md"
echo "export function digest() {}" > src/api/digest.ts
echo "export const DigestCard = () => null" > src/ui/digest-card.ts
echo "# Notifications digest" > docs/features/digest.md

cv_git_init
cv_git_commit_all "notifications digest run, halted at the scope gate"
