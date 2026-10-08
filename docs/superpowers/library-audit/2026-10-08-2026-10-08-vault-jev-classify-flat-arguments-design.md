# Library audit: vault jev_classify flat arguments

Spec: `docs/superpowers/specs/2026-10-08-vault-jev-classify-flat-arguments-design.md`. Audited 2026-10-08.

## 1. Tools Available

- Context7: NOT AVAILABLE. `ToolSearch "context7"` returned no tool; the harness reported `plugin:context7:context7` as needing authentication (OAuth), so it was not callable. Not a connection to the library's own docs in any case: the only "library" here is the Claude Code mods API, which Context7 may not carry.
- DEGRADED: WebFetch of the official Claude Code docs plus the engine's own generated typings. Nothing below is cited to Context7.
- Primary source used: `/Users/koristuvac/.claude/plugins/cache/cv-dev/compound-v-vault/0.1.0/.claude-plugin/types/claude-code/index.d.ts`, first line "Written by Claude Code 2.1.293". The docs call this the authority over prose.
- Dependency manifests: none relevant. The vault is a mod (`plugins/compound-v-vault/hooks/vault.tsx`), no package.json involved.
- Recon doc: none handed. V-memory recall used (handoff `2026-10-05-jev-next-stage.md`, triage record). Agent memory `drift-jev-and-mods.md` read as leads and re-verified below.

## 2. Libraries Mentioned

| Name | Spec context | Current | Repo pinned | Last release | Maintenance | Status |
|---|---|---|---|---|---|---|
| Claude Code mods API (`tool.call`, `$.tool.register`, `$.tool.call`) | The hook reads `e.input`; fix reads flat args | 2.1.294 (2026-10-08, changelog) | typings from 2.1.293; spec says running build 2.1.293 | 2026-10-08 | Weekly releases; surface marked EARLY ACCESS ("may change between releases without notice") | OK, with a stability caveat |

No other library is named by the spec.

## 3. API Signatures Verified

| Claim in spec | Verified against | Result |
|---|---|---|
| `tool.call` delivers a tool's arguments flat on the event (`e.command` for Bash) | Docs `plugins/mods/events` ("`e.tool` is the tool's name and the tool's arguments are fields of `e`, such as `e.command` for Bash"); d.ts `BuiltinToolCallInputFallback` (`tool`, `tool_use_id`, `[argument: string]: unknown`) | CONFIRMED |
| Same flat shape for MCP/plugin-registered tools | d.ts `McpToolCallInputFallback`, `McpToolCallInput`; d.ts `$.agent.register` example serves a registered tool as `on("tool.call", { tool: "mcp__lab__run" }, ... e.spec ...)` | CONFIRMED |
| `$.tool.call({ tool: "Read", file_path: "a.md" })` is flat | d.ts example at `$.tool.call` | CONFIRMED |
| `tool.call` hook may return `{ result }` | Docs reference table ("`next(e)`, `{ deny: reason }`, or `{ result }`"); d.ts `ToolCallResult` | CONFIRMED (the existing `{ result: string }` return stays valid) |
| `$.tool.register({ name, description, inputSchema })` served by a `tool.call` hook on `{ tool: "mcp__<plugin>__<name>" }` | d.ts `register` doc | CONFIRMED |

Trap found: `e.input` is the correct field for a DIFFERENT event, `tool.check` ("`e.input` holds the tool's arguments, such as `command` for Bash", docs events page). The current bug is exactly that shape mix-up. The plan must not "fix" it by copying the `tool.check` convention.

## 4. Critical Findings

None.

## 5. High-Priority Findings

None.

## 6. Medium Findings

1. Reserved event keys. `tool` and `tool_use_id` are reserved on the flat event ("a rewrite of it is ignored by core", d.ts). `request_file` does not collide. Flat delivery means any future argument named `tool` or `tool_use_id` would be shadowed; the tool's schema has only `request_file`, so no action now.
2. Schema enforcement is unverified. `inputSchema` sets `additionalProperties: false`, so in a real session a model call with `{ input: {...} }` may be rejected before reaching the hook. I found no doc statement saying whether the engine validates a registered tool's arguments against `inputSchema` before `tool.call`. Consequence for the spec: AC 3 ("a call with the argument under `input` is refused") is only guaranteed by the handler's own `typeof request_file` check, which is what the test exercises. That is sufficient, but the plan must not claim the schema backs it.
3. Surface stability. The d.ts header says the API is EARLY ACCESS and may change without notice. Changelog 2.1.292: "Fixed plugin `tool.call` hooks seeing some tool calls before misnamed parameters were repaired; a hook now sees the arguments the tool will run with". This is about built-in tools and does not change the flat shape, but it shows the shape is still moving. Typings in the cache are 2.1.293; current is 2.1.294. No `tool.call` change was listed for 2.1.294 in the portion of the changelog read (the fetch covered the first 100,000 of ~992,000 characters, i.e. the newest entries).
4. The spec's quoted wording ("the tool's arguments beside them (`e.command` for Bash)") matches the docs; the quote is accurate.

## 7. Design Constraints for the Plan

- MUST read `request_file` from the `tool.call` event itself (`e.request_file`), not from `e.input`. Keep `serveTool`'s own type check on the value (`typeof === 'string'`, absolute path), because the engine's schema enforcement is unverified.
- MUST NOT add an `e.input` fallback (the spec already says so; the docs support it: `e.input` belongs to `tool.check`, not `tool.call`).
- MUST NOT change `tool.check` handling or add `e.input` reads anywhere else; `tool.check` is the event where `e.input` is correct.
- MUST change the test helper to `$.tool.call({ tool: TOOL, request_file })`, the documented shape of `$.tool.call`. The old helper put a key named `input` flat on the event, which is why the bug was invisible.
- MUST keep the regression row's "nested under `input` is refused" case as a handler-level assertion, and not describe it as schema enforcement.
- MUST NOT put `tool` or `tool_use_id` among the tool's argument names.
- MUST record the verified-against version (typings 2.1.293) in the vault.tsx header clause, since the surface is early-access.
- MUST NOT rely on the mock harness to prove the live shape: the live smoke test after merge (already out of scope in the spec) is the only check that the real engine delivers `e.request_file`.

## 8. Open Questions for the Human

1. Does the engine reject a registered tool's call that violates `inputSchema` (`additionalProperties: false`) before the hook runs? Not answered by any source I could read. It does not block the plan; it only decides whether the nested-`input` refusal is reachable in production at all. The post-merge live smoke test can settle it by sending a nested-argument call once.
2. Context7 needs OAuth in this environment. If you want it used for future audits, authorize `plugin:context7:context7` via `/mcp`.

## 9. Knowledge Base Updates

Appended to `docs/superpowers/library-audit/_knowledge-base/claude-code-mods.md` under "Updated 2026-10-08 - vault-jev-classify-flat-arguments-design".
