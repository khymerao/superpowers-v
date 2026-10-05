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
