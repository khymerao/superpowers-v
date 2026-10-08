---
name: test-helper-shape
description: A plugin test helper that builds the event in the handler's assumed shape hides a contract bug; check helpers against the engine's delivery shape.
metadata:
  type: project
---

**Defect shape.** In `plugins/compound-v-vault`, the `jev_classify` `tool.call` hook read `e.input`. The test helper
`toolCall` in `.tests/vault.test.tsx` called `$.tool.call({ tool, input: { request_file } })`, which put a key named
`input` flat on the event. That is exactly what the buggy handler read, so 32 tests stayed green while every live call
was refused. Fixed in run 2026-10-08-vault-jev-classify-flat-arguments.

**Where it can recur.** Any `plugins/*/.tests/*.test.tsx` or `hooks/*.test.tsx` helper that constructs an event
(`$.tool.call`, `command.run`, `engine.create` and so on) for a function-hooks module.

**The check.** Compare the helper's event shape with the engine types (`ToolCallInput`: the arguments sit flat beside
`tool`). Do not compare it with what the handler reads. Then run AC-style reverts on a scratch copy: restore the old
handler with the new tests kept, and confirm that a happy-path row fails, not only a refusal row (`^refused:` matches
both outcomes). Also run the staged suite once under the pinned CLI with `npx` (`tests/test-vault-mod.sh` `PIN`),
because a local `claude` newer than the pin hides pin drift.

**Lead, not a verdict.** Re-verify against the current tree. The mock harness never proves the live delivery shape;
only a live smoke test does. Related: [[verifying-acceptance-criteria]].
