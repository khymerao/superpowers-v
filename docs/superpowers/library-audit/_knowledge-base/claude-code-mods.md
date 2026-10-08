# Claude Code Mods (function hooks) Knowledge Base

Maintained by Compound V Phase 1C validator. Append at the bottom.

---

## Updated 2026-10-05 - jev-classifier-foundation-design

Sources: https://code.claude.com/docs/en/plugins/mods/{overview,api,events,reference,test}, /plugins/manifest-reference, /plugins/components (fetched 2026-10-05). Reference states "as of v2.1.289".

- Gate: mods require Claude Code >= 2.1.287 and are on by default. `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS` is ignored from 2.1.287. Hooks run in `claude -p` and the Agent SDK (no drawing there). Off switches: `disableAllHooks`, `--safe-mode`, managed `allowManagedModsOnly`/`allowManagedHooksOnly`, WSL Desktop sessions.
- Layout: `hooks/hooks.json` carries `"modules": ["./register.js"]` and may also carry settings `hooks`. Module exports `register(on, options)`; `options` holds `userConfig` values.
- `$.process.run(argv, init)`: argument list, no shell, resolves `{exitCode, stdout, stderr}`, timeout 30 s default / 10 min max. Official test docs list `init` as `cwd` and `timeoutMs`; a third-party gist claims `env` and `stdin` too (uncorroborated officially). Authoritative: the `.d.ts` written to `.claude-plugin/types/`.
- `tool.call` can return `{ deny }`, `{ result }` (skips the tool and the permission prompt), or `next(e)`. Results from `next` carry `deny`/`isError`.
- Chain: `sec-default` and org `prependPlugins` first, then user mods, then `appendPlugins`, then builtin. Every mods API call is an event an earlier mod can observe or rewrite. Managed-settings `PreToolUse` hooks run before any mod; other settings hooks run after the last mod's `next`.
- `classic.<Event>` hooks wrap settings hook events (`e` = stdin JSON). Answering without `next` skips the settings hooks.
- Limits: hook own-time 10 s (excl. mods API calls), `$.fs` 4 MiB, `$.store` 4 MiB.
- `userConfig` `sensitive: true`: masked, stored in secure credential store, not shown in `/config`. `CLAUDE_PLUGIN_OPTION_<KEY>` is exported to **hook processes for every option**; not substituted into skill/agent content for sensitive values; monitors do not receive it.

## Updated 2026-10-08 - vault-jev-classify-flat-arguments-design

Sources: https://code.claude.com/docs/en/plugins/mods/events and /reference (reference says "as of v2.1.290"), https://code.claude.com/docs/en/changelog (newest 2.1.294, 2026-10-08), engine typings `.claude-plugin/types/claude-code/index.d.ts` "Written by Claude Code 2.1.293" (all read 2026-10-08). Context7 unavailable (needs OAuth).

- `tool.call`: the tool's arguments are FLAT fields of `e` (`e.command` for Bash; a registered tool's `e.spec` in the d.ts example). `tool` and `tool_use_id` are reserved; core ignores a rewrite of them. `$.tool.call({ tool, ...args })` takes the same flat shape.
- `tool.check` is the opposite: `e.input` holds the arguments. Mixing the two is the jev_classify bug.
- `tool.call` returns `next(e)`, `{ deny }` or `{ result }`.
- Not found in any source: whether a registered tool's `inputSchema` (`additionalProperties: false`) is validated before the `tool.call` hook. Unverified.
- 2.1.292: "a hook now sees the arguments the tool will run with" (misnamed-parameter repair, built-in tools). 2.1.293 added `isDeferred` to `$.tool.register`. Typings header: EARLY ACCESS, may change without notice.

## Updated 2026-10-08 - phase-t-jev-shadow-design

Sources: https://code.claude.com/docs/en/changelog (newest 2.1.294, 2026-10-08; only the first 100k chars read), `plugins/compound-v-vault/hooks/vault.tsx` at this checkout. Context7 needed OAuth.

- 2.1.293 `isDeferred` on `$.tool.register`: `false` lists the schema in the prompt from the start "instead of behind tool search", so a registered tool defaults to deferred. `vault.tsx:354` registers `jev_classify` without it; a caller must find it through `ToolSearch`.
- `vault.tsx:214-215`: network cap comes from the request file's `context` (`hook` 1,500 ms, `offline` 5,000 ms). A caller outside a hook that builds a `hook` request gets 1.5 s.
- `serveTool` returns `refused: ...` strings in the same channel as a response-file path.
- Still unverified (no changelog entry found): whether a registered tool's `inputSchema` is enforced before `tool.call`.
