---
name: jev-tool-refusals
description: Jev prose that cleans up on a parse status misses the vault tool's `refused:` strings, which skip parse entirely
metadata:
  type: project
---

Pattern (seen 2026-10-08, Phase T Jev step in `commands/v-triage.md`): a cleanup branch keyed on `parse`'s
`unavailable` reason (`no_key` / `egress` / `disabled`) never sees the case where `jev_classify` returns a
`refused: <reason>` string instead of a response path. `serveTool` checks `isDisabled` before `classify`
(`plugins/compound-v-vault/hooks/vault.tsx`, the `refused: disabled` line), so `disabled` arrives as a refusal
string, not as an `unavailable` response, and the request file written by `t3-request` stays behind unpaired.

**Why:** the vault returns refusals and paths through the same channel; specs written from the `parse` side keep
assuming every outcome reaches `parse`.

**How to apply:** when a review covers any new caller of `jev_classify` (prose or code), check what happens to the
request file on every `refused:` return, not only on `parse` statuses. Re-verify against the current `serveTool`
first; this is a lead, not a finding.
