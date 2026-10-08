#!/usr/bin/env bash
# Shared helpers for Compound V eval scaffold scripts.
#
# A scaffold_script runs AS YOU (outside the agent sandbox) in the run's empty
# workspace, and only when `claude plugin eval` is given --scaffold. Source this
# from a case's fixture.sh:
#
#   . "$(dirname "${BASH_SOURCE[0]}")/../lib/cv-fixture-lib.sh"
#
# Everything here writes into $PWD (the throwaway workspace) and never touches
# the plugin checkout or your git config.

set -euo pipefail

# --- Where is the plugin? ----------------------------------------------------
# A case dir is <plugin>/evals/<case>/, so the plugin root is two levels above
# the *case* dir and three above this lib. Resolve from the caller's path first
# (BASH_SOURCE[1] = the fixture.sh that sourced us), then fall back.
cv_plugin_root() {
  local here root
  if [ -n "${CV_EVAL_PLUGIN_ROOT:-}" ]; then printf '%s' "${CV_EVAL_PLUGIN_ROOT%/}"; return 0; fi
  here="$(cd "$(dirname "${BASH_SOURCE[1]:-${BASH_SOURCE[0]}}")" && pwd)"   # the case dir
  root="$(cd "$here/../.." && pwd)"                                         # <plugin>
  if [ -f "$root/.claude-plugin/plugin.json" ]; then printf '%s' "$root"; return 0; fi
  if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -f "${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json" ]; then
    printf '%s' "${CLAUDE_PLUGIN_ROOT%/}"; return 0
  fi
  echo "cv-fixture-lib: cannot locate the superpowers-v plugin root (tried $root)" >&2
  return 1
}

# cv_vendor_tools
#
# Copy the plugin's scripts/ and schemas/ into the workspace, preserving the
# plugin's own layout at the workspace ROOT.
#
# The WHOLE scripts/ directory, not a hand-picked subset: compound-v-preeval.py
# alone loads eight siblings lazily (taxonomy, localize, classify-request,
# project-config, triage-outcomes, churn, validate-taxonomy, update-memory), and
# a subset that is right today silently breaks the day one of them gains a
# dependency. It is ~3 MB of .py and it goes into a throwaway workspace.
#
# Why the workspace root: every Compound V command resolves its tooling as
#   CV="${CLAUDE_PLUGIN_ROOT:-$(ls -d "$HOME"/.claude/plugins/cache/*/superpowers-v/*/ ...)}"; CV="${CV:-$PWD}"
# In an eval run CLAUDE_PLUGIN_ROOT is unset for Bash and $HOME is a throwaway
# directory, so that chain lands on $PWD. Vendoring here is what makes the
# documented fallback resolve, and it is deliberately visible to BOTH arms: the
# baseline can `ls` and find the same scripts, so the delta measures whether the
# plugin steers Claude to USE the gate, not whether the gate was reachable.
cv_vendor_tools() {
  local root; root="$(cv_plugin_root)"
  mkdir -p scripts schemas
  cp "$root"/scripts/*.py scripts/
  cp "$root"/scripts/*.sh scripts/ 2>/dev/null || true
  chmod +x scripts/* 2>/dev/null || true
  cp "$root"/schemas/*.json schemas/ 2>/dev/null || true
}

# cv_copy_taxonomy — the impact taxonomy the pre-eval engine needs to reach a
# real tier. Without it every request scores FULL_PIPELINE (verified locally).
cv_copy_taxonomy() {
  local root; root="$(cv_plugin_root)"
  mkdir -p .claude
  cp "$root/.claude/compound-v-impact-taxonomy.example.yaml" .claude/compound-v-impact-taxonomy.yaml
}

# cv_git_init — a repo-local git identity. Never touches your global config.
cv_git_init() {
  git init -q .
  git config user.email "eval@example.invalid"
  git config user.name "Compound V Eval Fixture"
  git config commit.gpgsign false
}

cv_git_commit_all() {
  git add -A
  git -c core.hooksPath=/dev/null commit -q -m "${1:-fixture baseline}"
}
