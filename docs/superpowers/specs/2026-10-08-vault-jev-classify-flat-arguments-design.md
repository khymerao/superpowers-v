# jev_classify reads its argument where Claude Code puts it - design

Triage: `docs/superpowers/pre-eval/2026-10-06T134630Z-fix-the-compound-v-vault-jev-classify-tool-its-tool-call-han-74e1.json`
(FULL). Handoff: `docs/superpowers/research/2026-10-05-jev-next-stage.md`, section "FIRST".

## Problem

Every live `jev_classify` call is refused with `refused: request_file must be an absolute path`, even with an absolute
path (first live attempt, `connect-cf7-to-hubspot`, 9 of 9 request files). No Jev data can be collected until this is
fixed.

Cause: the vault's `tool.call` hook (`plugins/compound-v-vault/hooks/vault.tsx:400-402`) passes `e.input` to
`serveTool`. Claude Code spreads a tool's arguments flat on the event. The engine types of the running build (2.1.293,
`ToolCallInput`) say: "the tool, the id of this call, the tool's arguments beside them (`e.command` for Bash)", and
`$.tool.call` takes the same flat shape (`$.tool.call({ tool: "Read", file_path: "a.md" })`). So `e.input` is
`undefined` and `serveTool` refuses.

The test hid it: `plugins/compound-v-vault/.tests/vault.test.tsx` calls `$.tool.call({ tool: TOOL, input: { request_file } })`,
which puts a key named `input` flat on the event, exactly what the buggy handler reads.

## Change

1. `vault.tsx`: the `tool.call` hook passes the event's own `request_file` to `serveTool` (`serveTool($, vault, e)` with
   `serveTool` reading `request_file` from the event, or `serveTool($, vault, e.request_file)`). No fallback to
   `e.input`: the contract is flat, and a second path would keep the hidden shape alive.
2. `vault.test.tsx`: the `toolCall` helper passes the argument flat, `$.tool.call({ tool: TOOL, request_file })`. Every
   existing tool test then exercises the real shape.
3. One test row pins the regression explicitly: a valid request file passed flat is served (not refused with
   `must be an absolute path`), and an argument nested under `input` is refused. Reverting change 1 makes the suite
   fail.
4. The header comment in `vault.tsx` that documents `$.tool.register` gains one clause: arguments arrive flat on the
   `tool.call` event.

## Out of scope

Reinstalling the vault in `cv-dev` and the live smoke test (done after merge, key re-entered by the maintainer);
`/v:init` 1g (next item); any other vault behaviour.

## Acceptance Criteria

1. `tests/test-vault-mod.sh` passes, with every tool-call test passing the argument flat.
2. With change 1 reverted and the tests kept, `tests/test-vault-mod.sh` fails.
3. A call with the argument under `input` is refused; a call with it flat reaches the path checks.
4. No other vault behaviour changes: all 32 existing tests still pass, and no key-shaped literal is added.
