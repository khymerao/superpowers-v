# Library audit (Phase 1C): Jev review fixes

Spec: `docs/superpowers/specs/2026-10-05-jev-review-fixes-design.md`
Recon: `docs/superpowers/recon/2026-10-05-jev-system-one-classifier-via-openrouter.md` (read; its Jev facts are unchanged by this spec, which touches no Jev API).
Date: 2026-10-05. V-memory: the supplied recall block was read (parent spec, plan, prior library audit, review record); no extra search run.

## 1. Tools available

- Context7: NOT available. `ToolSearch` for `context7` and for the explicit `resolve-library-id` / `query-docs` names returned nothing, twice. DEGRADED: WebSearch-only (one query, Python 3.9 EOL). Remaining claims were verified against the repository's own code, which is the authority for this spec.
- Manifests: none (no package.json, pyproject, requirements). The repository is stdlib-only Python 3.9 plus a TSX mod; `.github/workflows/validate.yml` pins `python-version: '3.9'`.
- Bash is clamped for this agent; reads were done with Read/Grep.

## 2. Libraries mentioned

| Name | Spec context | Current | Repo pin | Last release | Maintenance | Status |
|---|---|---|---|---|---|---|
| Python stdlib (`os.lstat`, `os.unlink`, `json`) | `prune` mtime rule, parse | 3.14 line (per KB 2026-09-03) | floor 3.9 (CI pin, parent spec) | 3.9.25 final, EOL 2025-10-31 | 3.9 unsupported | 🟠 floor is EOL (pre-existing, not introduced here) |
| Claude Code mods (`$.process.run`, vault.tsx, jev-t3.tsx) | spec forbids touching both | >= 2.1.287 | AGENTS.md floor 2.1.219 | n/a | active | 🟢 unchanged by this spec |
| OpenRouter / Jev System One | source of 401/403 `auth` reason | jev-1.13.0 (KB 2026-10-05) | n/a | n/a | active | 🟢 no API surface changes here |
| git (`ls-files`) | `_ui_sample` file list via `_repo_files` | not re-checked | stock | n/a | n/a | 🟢 |

No third-party library is added, removed or upgraded by this spec.

## 3. API signatures verified (against the repo)

| Claim in spec | Verified | Result |
|---|---|---|
| vault answers `unavailable(no_key)` at `vault.tsx:236` | yes, line 236 `if (vault.key === '') return unavailable('no_key')` | OK |
| `UNAVAILABLE_REASONS` lacks `no_key` | yes, `compound-v-jev.py:59-60` = no_vault, disabled, egress, timeout, rate_limited, upstream, credits, auth | OK |
| `parse` rewrites unknown reason to `upstream` | yes, `compound-v-jev.py:542` | OK |
| `failed()` yields a status the parser treats as error | vault `failed` emits `status:'error'` (`vault.tsx:95`); parser `ERROR_REASONS` = schema, bad_input | OK, see M1 |
| `prune` uses an `lstat` rule for `req/`, `resp/` | yes, lines 295-302 | OK, but see H1 |
| jev-t3 reads only first 50 `pending-*` sorted | `jev-t3.tsx:176` filters `pending-*.json`, non-link files; the 50 cap was not re-read | not re-verified |
| `_ui_sample` skip rule is `base == ".env"` or suffix test | yes, line 1178; `.env.example`/`.env.local` pass today | OK, the gap is real |

## 4. Critical findings 🔴

None.

## 5. High-priority findings 🟠

H1. Spec statement about symlinks does not match existing `prune` behaviour. Spec Issue 3 says the new `pending-*.json` rule works "by the same `lstat` rule it uses for `req/` and `resp/` (symlinks and directories are never followed or removed)". The code (`compound-v-jev.py:296-302`) calls `os.lstat`, then skips only `os.path.isdir(path)`. `isdir` follows symlinks, so a symlink to a directory is skipped, but a symlink to a file or a dangling symlink older than the cutoff IS `os.unlink`ed (removing the link, not its target). Nothing is followed, but symlinks are removed. If the plan copies the spec's wording into a test ("a symlink is left in place"), the test fails against the shared rule; if it reuses the existing loop, the behaviour is "link removed, target untouched". Alternative: decide which is intended and state it; the safe, spec-matching form is `stat.S_ISREG(st.st_mode)` on the lstat result.

H2. Python 3.9 floor is EOL (2025-10-31, final 3.9.25; WebSearch 2026-10-05 and KB python-tooling 2026-09-03). Not introduced by this spec, and the parent spec fixes the floor, so no change requested. Consequence for this plan: 3.9-incompatible syntax (`match`, `X | Y` in `isinstance`, parenthesised multi-item `with`) passes a developer's newer interpreter and fails only on CI or stock macOS 3.9.6. The new selftest rows and the contract check must be written 3.9-safe. Alternative if the floor is ever revisited: 3.12+ (Python 3.9 removed from GitHub runner images 2026-01-12 per runner-images issue 13468).

## 6. Medium findings 🟡

M1. The contract check must send responses the parser actually routes by reason. `parse_response` (`compound-v-jev.py:537-539`) classifies by `http_status` first and ignores `reason` when `http_status` is a non-2xx integer. The vault attaches `http_status` for 401/403/402/429/5xx/4xx (`vault.tsx:102-108`). So the check should feed `{status, reason, latency_ms}` with NO `http_status`, otherwise `auth`/`credits`/`rate_limited` pass or fail through `_classify_http`, not through `UNAVAILABLE_REASONS`, and removing `no_key` would still not be the only way to break it. Also `status:'error'` maps to parsed status `error` (not `failed`); the spec's phrase "response file of the matching status" must be read as `unavailable`->`unavailable`, `failed()`->`error`.

M2. Literal extraction needs care. `unavailable(` at `vault.tsx:381` is `classify: async () => unavailable('no_vault')` in a fallback object, and `unavailable('no_vault')` is already in the tuple, fine, but the regex must also ignore the two function definitions at lines 87 and 93 (`unavailable(reason: string...`), and must handle the reasons passed as a variable. Check call shapes: `unavailable('x')` with quotes, reason as first arg only. Non-literal reasons (none found today) would be invisible to the check; the spec's "at least one of each status" guard covers the empty case but not a partial miss. Today's literals: unavailable = auth, credits, rate_limited, upstream, timeout, disabled, no_key, egress, no_vault; failed = bad_input, schema. After the change all eleven are in the two tuples.

M3. `missing file` path: `parse_response` returns `unavailable/no_vault` when the response file is absent (line 522-523). Do not confuse with a vault-sent `no_vault`; the check writes a real file so this does not collide.

M4. `_ui_sample` docstring and the parent spec table row: the spec says the table row moves from `auth` to `no_key`; the plan must also search `docs/superpowers/**` and `skills/compound-v/` for other places that list the reason set (the review record, expert audit) so no second table keeps `auth` for a missing key. Not verified by this audit.

M5. The new exclusion rule "path contains `secret` or `credential`" is a substring match; it will also drop legitimate files such as `lib/secretary.php`. Accepted trade-off for a fail-closed sample, but it lowers the sample count for UI detection; note it, no action.

## 7. Design constraints for the plan

MUST:
- Keep all new Python Python-3.9-safe, stdlib only; no `match`, no `X | Y` in runtime expressions, no new dependency.
- Add `no_key` to `UNAVAILABLE_REASONS` only; leave `ERROR_REASONS` and `credits`/`auth` as they are.
- Build the contract-check response files without `http_status`, with `status: unavailable` for `unavailable()` literals and `status: error` for `failed()` literals, and assert the parsed `(status, reason)` pair.
- Extract reasons from `vault.tsx` by a pattern that excludes the two `function` definitions, and fail when either status yields zero literals.
- Resolve H1 explicitly in the plan: either keep the existing unlink-the-link behaviour and word the test accordingly, or restrict the new `pending-*.json` rule to regular files (`stat.S_ISREG` on the `lstat` result).
- Make the new `_ui_sample` predicate case-insensitive and evaluated before any `_read_bounded` call, as the spec states.
- Leave `vault.tsx` and `jev-t3.tsx` byte-identical (AC-5); the contract test reads `vault.tsx`, never writes it.

MUST NOT:
- Rely on a Python newer than 3.9 to prove the rows pass; run them under the CI floor.
- Treat the spec's "symlinks never removed" as already true of `prune`.
- Introduce a second reason list in docs that disagrees with the code after the table row moves.

## 8. Open questions for the human

1. Symlinks in `prune` (H1): should an old symlink named `pending-*.json` be left alone (spec text) or unlinked (current `req/`/`resp/` behaviour)? Default recommendation: leave non-regular files alone for the new candidates.
2. Is the substring rule `secret`/`credential` meant to apply to the whole path (including directory names such as `docs/secrets-policy/…`) as written? Assumed yes.

## 9. Knowledge base updates

Appended `## Updated 2026-10-05 - jev-review-fixes-design` to `docs/superpowers/library-audit/_knowledge-base/typesafe-jev-openrouter.md` (vault reason set, parse routing by http_status, prune symlink behaviour). Python 3.9 EOL was already recorded in `python-tooling.md` (2026-09-03); re-confirmed 2026-10-05, no new append.
