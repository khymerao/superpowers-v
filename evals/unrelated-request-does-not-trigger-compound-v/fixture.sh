#!/usr/bin/env bash
# Fixture: one ordinary source file and nothing Compound V-shaped — no run
# directory, no manifest, no taxonomy. A plugin that fires here is firing on a
# read-only question.
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/../lib/cv-fixture-lib.sh"

mkdir -p src

cat > src/retry.ts <<'TS'
const BASE_MS = 200
const MAX_ATTEMPTS = 5

export class RetriesExhausted extends Error {}

export async function withRetry<T>(fn: () => Promise<T>): Promise<T> {
  let lastError: unknown
  for (let attempt = 0; attempt < MAX_ATTEMPTS; attempt++) {
    try {
      return await fn()
    } catch (err) {
      lastError = err
      const jitter = Math.random() * BASE_MS
      await new Promise((r) => setTimeout(r, BASE_MS * 2 ** attempt + jitter))
    }
  }
  throw new RetriesExhausted(String(lastError))
}
TS

cv_git_init
cv_git_commit_all "retry helper"
