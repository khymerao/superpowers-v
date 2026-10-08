# Claude Code Host Detection Library Knowledge Base

Maintained by Compound V Phase 1C validator. Append at the bottom.

---

## Updated 2026-10-08 - v-init-vault-host-and-desktop-design

Sources (fetched 2026-10-08): https://code.claude.com/docs/en/env-vars, /cli-reference, /desktop, /changelog; community gists
https://gist.github.com/mculp/e6a573f2a45ef7dbbf30f6a8574c7351 (v2.1.104) and https://gist.github.com/unkn0wncode/f87295d055dd0f0e8082358a0b5cc467. Context7 needed OAuth; not used.

- `CLAUDE_CODE_EXECPATH`: NOT in the official env-vars page (checked both halves). Third-party gist: "Binary path (auto-injected)". Maintainer saw it in a desktop session 2026-10-05. Unconfirmed in terminal Bash-tool env.
- `CLAUDE_CODE_ENTRYPOINT`: NOT in the official env-vars page. Third-party gist lists `cli`, `sdk-ts/sdk-py/sdk-cli`, `mcp`, `claude-vscode`, `claude-desktop`, `remote_*`, `local-agent`, `claude-code-github-action`; the v2.1.104 mculp gist lists only `local-agent, remote...`. The Agent SDK is reported to overwrite it with `sdk-py`.
- Documented host markers: `CLAUDECODE=1` (Bash, hooks, status line, stdio MCP subprocesses) and `CLAUDE_CODE_CHILD_SESSION=1` (Bash/PowerShell/Monitor, hooks, status line). Both are set in every host, so they do not identify desktop.
- `claude --version`/`-v`: docs say only "Output the version number"; the `X.Y.Z (Claude Code)` format is observed, not documented.
- Desktop Code tab: plugins managed via "+" menu > Plugins; plugin browser absent in cloud sessions, plugins absent in WSL sessions. Changelog 2.1.290: desktop `/plugin` reply now says where to install/manage plugins. No doc says desktop skips a plugin's sensitive `userConfig`.
- Newest Claude Code listed: 2.1.294 (2026-10-08).
