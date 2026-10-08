# Library audit: Phase T asks Jev in shadow (2026-10-08)

Spec: `docs/superpowers/specs/2026-10-08-phase-t-jev-shadow-design.md`. Phase 1C, checked 2026-10-08.

## 1. Tools Available

- Context7: NO. `ToolSearch context7` returned no tool; the harness reported `plugin:context7:context7` as needing OAuth (present, unauthorised, not absent). **DEGRADED: WebFetch-only** for the one external lookup; everything else read from the repository.
- V-memory: the prompt's recall block was read. Hits used: `2026-10-05-jev-next-stage.md` (the handoff the spec cites). Nothing in it contradicts the spec.
- Dependency manifests: none relevant. The spec adds no package. The surface is stdlib Python (`scripts/compound-v-jev.py`), bash + `jq` (`hooks/triage-prompt-nudge.sh`), and the Claude Code mods API (`plugins/compound-v-vault/hooks/vault.tsx`).
- Trigger 0 recon doc: none handed.

## 2. Libraries Mentioned

| Name | Spec context | Current | Repo pinned | Last release | Maintenance | Status |
|---|---|---|---|---|---|---|
| Claude Code mods (`$.tool.register`, `tool.call`) | Phase T calls `mcp__compound-v-vault__jev_classify` | 2.1.294 (2026-10-08, changelog) | floor 2.1.219 in AGENTS.md; mods need >= 2.1.287 | 2026-10-08 | Daily releases; typings header says EARLY ACCESS, may change | OK, with caveat (see H1) |
| Jev via OpenRouter `/api/v1/systemone` | Unchanged transport | `jev-1.13.0` as of 2026-10-05; not re-checked today | n/a (route is in `vault.tsx`) | not re-verified | - | OK (no API change in this spec) |
| `jq` (hook state extraction being replaced) | Spec moves it to Python | not checked | system | - | - | OK; removing it |
| Python stdlib (`argparse`, json) | New `t3-request` subcommand | n/a | system | - | - | OK |

No 🔴 or 🟠 dependency. The spec introduces no new third-party library.

## 3. API Signatures Verified

| Signature in spec | Verified against | Result |
|---|---|---|
| `compound-v-jev.py parse --response-file F --repo . --mode shadow --request-file F` | `compound-v-jev.py` argparse, lines 911-916 | Matches. `--hook-budget-left-ms` is optional. |
| `compound-v-jev.py pair --request-file --claude-category --backend --t3-reason --repo` | lines 917-921 | Matches. `--claude-category` is limited to `T3_ORDER` = unknown, user-facing-major, user-facing-minor, plumbing. `--backend`/`--t3-reason` pass `_token_arg` (short lowercase token). `parent` and `sensitive|unbanded|demotion` satisfy it. |
| `compound-v-jev.py t3-request --repo --request-env --prompt-file` | not present | NEW subcommand. The file's header and `sub.add_parser` list (build, parse, pair, eval, data-dir) have no `t3-request`. Its design is the spec's own. |
| `triage --t3-category <enum> --t3-engine <backend>` | `compound-v-preeval.py:274, 1724, 1758-1760` | Matches. `T3_CLI_ENGINES = (claude, codex, parent)`; `--t3-engine` without `--t3-category` is REFUSED (exit 2). |
| `jev_classify` takes `request_file` | `vault.tsx:354-361` | Matches. One required string, `additionalProperties: false`. Arguments are flat on `e` in `tool.call` (`vault.tsx:404-406`), consistent with the 2026-10-08 KB entry. |
| "`jev_classify` returns the response file path" | `vault.tsx:282-290` | PARTIAL. `serveTool` returns refusal strings (`refused: disabled`, `refused: request_file must be an absolute path`, ...) through the same channel as a path. See M2. |
| Hook extraction caps: request 2,000, paths 20, hints 40 | `triage-prompt-nudge.sh:453` (`_T3_STATE_MAX_CHARS=2000`), jq at :467-482 | Matches. The hint cap in the jq is `.[0:40]`; the engine also caps its own list at `MAX_TAXONOMY_CATEGORIES`. |

## 4. Critical Findings 🔴

None.

## 5. High-Priority Findings 🟠

**H1. `t3-request` defaults to the hook timeout, which is wrong for Phase T.**
`vault.tsx:214-215` picks its network cap from the request file's `context`: `hook` = 1,500 ms, `offline` = 5,000 ms. `compound-v-jev.py` has `DEFAULT_CONTEXT = {"t3": "hook", ...}` (line 52), and the spec says `t3-request` "does what `build --point t3` does", so a Phase T call would inherit `context: hook` and a 1.5 s cap. Phase T is an attended command with no hook budget. Round trips that miss 1.5 s record as timeouts in `calls.jsonl` and as non-`ok` pairs, which is the corpus spec 1.5 reads its agreement rate from. The spec does not name a `--context` option. Without one the shadow will under-collect on the very path it exists to fix. The hook path must keep `hook`.

## 6. Medium Findings 🟡

**M1. The tool is probably deferred; "the session has the tool" is not checkable by looking at the tool list.**
Claude Code 2.1.293 added `isDeferred` to `$.tool.register`: "`false` lists the tool's schema in the prompt from the start instead of behind tool search" (changelog 2026-10-08), so the default is behind tool search. `vault.tsx` registers `jev_classify` without `isDeferred`. A Phase T agent that checks its tool list will conclude the tool is absent and skip the step silently, which fails without any error. The step must say to try `ToolSearch` for `jev_classify` before declaring it missing. Also the tool exists only after `session.start` and only when the vault is not disabled (`vault.tsx:353-354`), so "absent" is a normal answer, not an error.

**M2. A refusal and a path share one return channel.**
`jev_classify` returns the string `refused: ...` where it would return a path. The spec's step 4.3 hands "the response file" to `parse`. Without a guard, a refusal string goes to `--response-file`. The step needs: take the value as a path only if it is absolute and the file exists; otherwise one line and stop. This also covers the egress ask: with consent unanswered Jev is off (`EGRESS_ASK`, `vault.tsx:56`), and that must end the step, not be reported as an error.

**M3. `--t3-reason` has no source in Phase T prose.**
The reason (`unbanded|demotion|sensitive`) is in the `needs_t3` JSON (`t3_reason`, `compound-v-preeval.py:711/749/624`), and the hook reads it with `jq -r '.t3_reason // "unbanded"'` (`triage-prompt-nudge.sh:700`). `commands/v-triage.md` T2 never mentions it. The step must name where it comes from and the fallback, or the agent will invent a value. `_token_arg` accepts any short lowercase token, so an invented value would not be rejected and would pollute `shadow-pairs.jsonl`.

**M4. Equivalence of the jq extraction and its Python replacement is the whole risk of AC 2.**
Three points where a port drifts, all checkable from `triage-prompt-nudge.sh:467-482`:
- `[0:$n]` in jq slices by codepoint; Python `str[:2000]` also does, but reading the request from an env var as bytes with a non-UTF-8 value differs. Decode with `errors="replace"` and test a multibyte request that straddles 2,000.
- Hints are taken from the tail after the LAST paths header, not from the whole prompt; the paths block ends at the first blank line (`split("\n\n")[0]`). A prompt with the taxonomy header before the paths header yields no hints. Port that, do not "fix" it.
- Only lines starting `- ` count, with the two characters removed; `(none resolved)` is dropped from paths only, never from hints.

## 7. Design Constraints for the Plan

MUST:
- `t3-request` MUST take a `--context {hook,offline}` option; the hook keeps `hook`, Phase T passes `offline` (H1). It MUST be covered by a selftest row that reads the written request file's `context`.
- The Phase T step MUST locate `jev_classify` with `ToolSearch` before concluding it is absent, and MUST treat absence as a silent no-op of that one step (M1).
- The Phase T step MUST pass `parse --response-file` only a value that is an absolute path to an existing file; any other return is one line and the end of the step (M2).
- The step MUST source `--t3-reason` from the `needs_t3` JSON's `t3_reason`, defaulting `unbanded` as the hook does; it MUST NOT invent one (M3).
- `--t3-engine` MUST be passed together with `--t3-category`; the engine refuses it alone (`compound-v-preeval.py:1760`). A `backend: none` or timed-out classify is NOT an answer and must not reach `--t3-category` (existing prose, `v-triage.md:164-168`); the new `--t3-engine` instruction must not weaken that.
- The Python extraction MUST be byte-equivalent to the jq on a shared fixture, including a multibyte request across the 2,000 cap, last-header selection and the blank-line terminator (M4). The hook test (AC 2) MUST assert the descriptor's key set, not only that it exists.
- The request text MUST reach `t3-request` through the environment only (`--request-env NAME`), as the spec states; the Phase T prose MUST NOT interpolate request text into a command line.

MUST NOT:
- MUST NOT add a Jev or OpenRouter API parameter, route or model string; the transport is unchanged.
- MUST NOT treat the hook-side `_REQUEST_MAX_CHARS=4000` and the Jev-side 2,000 cap as one cap. They are different limits (`triage-prompt-nudge.sh:215` vs `:453`); `t3-request` caps at 2,000 only.
- MUST NOT write the Jev answer onto the record (`t3.shadow`); out of scope per the spec.
- MUST NOT rely on `tool.call` `inputSchema` enforcement: the repo's own `vault.tsx:280-281` says it is unverified, and the changelog shows no entry that settles it. Keep the validation in `serveTool`.

## 8. Open Questions for the Human

1. Phase T runs attended, so 5 s (`offline`) is reasonable, but it lengthens `/v:triage` by up to 5 s on every T3-decided request. Accept that, or keep 1.5 s and accept more timeout rows? This is a product trade-off, not a library fact.
2. Should the shadow step be skipped, not just reported, when the egress consent is unanswered (the vault asks via `/egress`)? The spec says "report and change nothing"; the ask text is a long line.

## 9. Knowledge Base Updates

Appended to `docs/superpowers/library-audit/_knowledge-base/claude-code-mods.md` under `## Updated 2026-10-08 - phase-t-jev-shadow-design`: `isDeferred` default and the vault registration, `context`-driven timeout, newest version 2.1.294. Also added one line to agent memory `drift-jev-and-mods.md`.
