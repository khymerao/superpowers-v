# jev_classify flat arguments - Code Archaeology

Spec: `docs/superpowers/specs/2026-10-08-vault-jev-classify-flat-arguments-design.md`. V-memory recall: the handoff
`docs/superpowers/research/2026-10-05-jev-next-stage.md` ("FIRST") states the same cause and fix as the spec; the code
confirms the cause (below). Recalled prose about reason vocabulary was not needed. Context7 was not reachable (the
plugin:context7 server needs authorization), and the Bash tool was clamped to git/memory commands, so the CLI could not
be run: every claim about Claude Code's event shape below is unverified by this audit and is marked as such.

## 1. Matrix

The tool-call path has one gate and few branches. Dimensions that decide the outcome of `serveTool`
(`plugins/compound-v-vault/hooks/vault.tsx:278-315`):

| Dimension | Values | Handled today | New code must |
|---|---|---|---|
| Event shape of `request_file` | flat `e.request_file` (real CC) / nested `e.input.request_file` (test only) | only nested (line 401 reads `e.input`; `isRecord(undefined)` is false, so `given` is `undefined`, line 281 refuses) | accept flat only |
| Vault disabled (`CV_HEADLESS_CLASSIFY`) | yes/no | `isDisabled` at 279, before the argument is read | keep the order: disabled still wins over a bad argument |
| `request_file` type/shape | non-string, relative, `.`/`..`, missing, link, non-file, outside root, wrong name, non-JSON | 281-303, 7 test rows in `REFUSALS` | unchanged |
| Egress / key / route | inside `classify()`, not in `serveTool` | `classify` returns an unavailable/error JevResponse, written to the resp file | unchanged |

Cell tested today: only the nested one. Cell that exists in production: only the flat one. The two never intersect, which is the bug.

## 2. Shared State

`input` parameter of `serveTool` (`vault.tsx:278`, `unknown`): set at `vault.tsx:401` from `e.input`.
- Real Claude Code event (per spec; unverified here): flat, so `e.input === undefined` in every call. `given` is `undefined`, refusal text `request_file must be an absolute path` (281). That message is the same for "argument missing" and "argument relative", so the misleading error hid the cause.
- Test event: `$.tool.call({ tool: TOOL, input: { request_file } })` (`vault.test.tsx:31`) puts a key named `input` flat, which the handler reads. Handler and test share the same wrong assumption.

`e` also carries `tool` and the call id beside the argument (per the spec's quoted types). A name collision is possible in principle if a future argument were named `tool` or `id`; `jev_classify` has only `request_file` (`additionalProperties: false`, 354-359), so there is none today.

If the plan passes the whole event `e` into `serveTool` and keeps `isRecord(input) ? input.request_file`, the parameter now holds the event, not the argument: rename it, or the next reader repeats the confusion. If it passes `e.request_file` (a `string | undefined`), `isRecord` at 280 becomes dead and must go, since `typeof given !== 'string'` already covers it. `isRecord` itself stays (other uses: confirm before deleting; `hooks/jev-t3.tsx:34` has its own copy).

## 3. Sibling Code

No sibling `tool.call` hook exists: `rg` over `*.ts`/`*.tsx` finds this as the only `tool.call` consumer. Related reads:
- `plugins/compound-v-vault/hooks/vault.tsx:404-406`, `command.run` hook, reads `e.args` flat (`e.args ?? ''`). The same plugin already reads the event flat for commands, and its test (`$.command.run({ command: 'egress', args })`, test lines 23, 37) passes it flat. The `tool.call` hook is the odd one out, which supports the spec's "contract is flat" choice. No latent bug there.
- `hooks/jev-t3.tsx` (root plugin) does not register a tool; it calls `$.jev.*`. Not affected.
- Callers of the tool: `skills/compound-v/onboarding.md:84,172` and `commands/v-onboard.md:43` instruct the model to call `jev_classify` with `{"request_file": "<path>"}`. That already matches the registered `inputSchema` (flat property). No caller change.

## 4. External APIs

Claude Code mod API (`tool.call` event, `$.tool.call` testing call). Context7 was unavailable and the CLI could not be run, so this audit has no first-hand check. Facts and gaps:
- The spec quotes the 2.1.293 `ToolCallInput` ("the tool's arguments beside them, `e.command` for Bash"). The repo's own pin is lower: `tests/test-vault-mod.sh:16` `PIN="2.1.289"` (CI fetches this via npx when no local claude >= 2.1.287 exists), and the header comment `vault.tsx:7-8` says the API was checked against 2.1.289. **Unknown: whether 2.1.289 delivers `tool.call` args flat and whether its `$.tool.call` test helper accepts a flat argument.** If the flat shape is new in a version after 2.1.289, CI under the pin would fail the new tests, or pass the old ones. The plan must establish which versions deliver flat arguments (read the typings of the pinned CLI) before moving the pin or the floor.
- Vault README floor is 2.1.287 (`plugins/compound-v-vault/README.md:15`), `v-init` 1g checks 2.1.287, marketplace text says 2.1.287. If flat delivery is newer than 2.1.287, the stated floor is wrong for this tool.
- Whether a nested `input` argument is rejected by the harness before the hook (spec AC3 expects `refused`, i.e. the hook ran) is unverified.

## 5. Regression Surface

- `jev_classify` serves nothing at all today, so no working user path can regress from the handler change itself; the risk is entirely in the test suite and the CI pin.
- The 32 existing tests: 6 + 10 `STATUS_ROWS` + 10 singles + 7 `REFUSALS` -> counted 32 (matches AC4). Only 9 of them reach `toolCall` (2 happy-path rows, 7 refusal rows). The others use the `jev` probe command through `$.jev.classify` and are untouched by this change.
- 7 refusal rows pass vacuously on the old code and would also pass if the handler reads nothing (every refusal is `^refused: `). Flat-izing the helper does not make them stronger: with a broken reader they all still pass. Only the two happy-path rows (370, 383) and the new row prove the argument arrives. The "reverting change 1 makes the suite fail" claim (AC2) holds only because of those rows.
- `expectNoKeyOutsideFetchAuth` / `vtest` record `out` for the key check; unchanged.
- `tests/test-vault-mod.sh:41` asserts the hook string `tool.call{tool=mcp__compound-v-vault__jev_classify}` appears in `claude plugin validate` output: the registration signature must not change (keep the `{ tool: ... }` filter).
- The shell test greps `sk-or-` in the plugin folder (80-85): a new test row must not spell a key-shaped literal (AC4 already says so).
- Installed copy: a reinstall in `cv-dev` loads the plugin from the marketplace; the manifest and marketplace version are both `0.1.0` (`plugin.json`, `.claude-plugin/marketplace.json:22`). The check at `test-vault-mod.sh:87-107` demands lockstep between the two. If the harness caches by version, a fix at an unchanged `0.1.0` may not reach an installed copy. Whether to bump is not decided by the spec ("Reinstalling ... out of scope") and is a finding: the live smoke test depends on it.

## 6. DRY Findings

No duplicate path to the tool. One duplicated reader style: the command hook reads `e.args` flat, the tool hook should read in the same style; no shared helper is warranted for two one-line reads. `isRecord` exists in `vault.tsx:83` and `hooks/jev-t3.tsx:34` (separate plugins; they cannot share). No refactor needed.

Doc duplication: the flat contract is stated in the hook header comment (`vault.tsx:23-25`) and nowhere else. `plugins/compound-v-vault/README.md:71` describes the tool as `jev_classify({ request_file })` with no mention of delivery shape; fine.

## 7. Design constraints for the spec

1. The `tool.call` hook MUST read `request_file` from the event itself and MUST NOT fall back to `e.input` (spec change 1; confirmed necessary: `vault.tsx:401` is the only reader).
2. `serveTool`'s parameter name and the `isRecord(input) ? input.request_file` line (`vault.tsx:278,280`) MUST be made consistent with whichever form is chosen (event vs `e.request_file`); the spec leaves both open and the plan MUST pick one. Passing `e.request_file` is the narrower form and removes `isRecord` from this function; passing `e` keeps a `Record` check.
3. `isDisabled` (279) MUST still run before the argument is read, so a disabled vault refuses with `refused: disabled` even for a bad argument.
4. The test helper `toolCall` (`vault.test.tsx:30-35`) MUST pass `request_file` flat, and the new regression row MUST assert on a distinguishing outcome. A `^refused: ` match is not enough: the flat-valid row must equal `RESP_FILE` and show a fetch, and the nested row must be refused with exactly `request_file must be an absolute path`.
5. The plan MUST NOT rely on the 7 `REFUSALS` rows as evidence the reader works; AC2 is satisfied by the happy-path rows plus the new row.
6. The plan MUST establish, from the pinned CLI's typings (2.1.289, `tests/test-vault-mod.sh:16`), that `tool.call` delivers flat arguments and that `$.tool.call` accepts a flat argument in the test runtime. If the pin predates flat delivery, the plan MUST say whether to raise `PIN`, the `2.1.287` floor (`test-vault-mod.sh:23`, README:15, `v-init` 1g, marketplace text) or both. This audit could not verify it.
7. The registration `tool.call{tool=mcp__compound-v-vault__jev_classify}` MUST remain unchanged (shell test row at `test-vault-mod.sh:41`).
8. The spec MUST decide whether `plugin.json` and `marketplace.json` versions move together (`0.1.0` -> next). The shell test enforces lockstep only; an unchanged version may leave the cv-dev reinstall on the cached broken copy.
9. The header comment edit (spec change 4) belongs at `vault.tsx:23-25`; the line-7 sentence "API confirmed ... against the pinned CLI (2.1.289)" becomes inaccurate for this one fact unless constraint 6 shows 2.1.289 is flat.
10. No new key-shaped literal (`sk-or-`) in any new test text (`test-vault-mod.sh:80-85`).

## 8. File Touch Map

- `plugins/compound-v-vault/hooks/vault.tsx` - edit lines 23-25 (comment), 278-281 (`serveTool` argument), 400-402 (hook). Not shared.
- `plugins/compound-v-vault/.tests/vault.test.tsx` - edit `toolCall` (30-35), add one regression row near 383-412. Not shared.
- `plugins/compound-v-vault/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` - only if constraint 8 decides to bump; the two MUST change together. SHARED RESOURCE: `marketplace.json` is a registry other plugin entries sit in.
- `tests/test-vault-mod.sh` - only if constraint 6 moves `PIN` or the floor. SHARED RESOURCE: a CI-run test that the validate.yml sweep discovers.
- `plugins/compound-v-vault/README.md`, `commands/v-init.md`, `.claude-plugin/marketplace.json` description - only if the floor moves (constraint 6).
- `CHANGELOG.md` - if the repo convention is a changelog line per release; not checked.
