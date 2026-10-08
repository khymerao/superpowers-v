# Jev review fixes Code Archaeology

Spec: `docs/superpowers/specs/2026-10-05-jev-review-fixes-design.md`. Recon: Trigger 0 was `kb_skip`; the recon
doc and the parent archaeology (`2026-10-05-2026-10-05-jev-classifier-foundation-design.md`) were read first and
not repeated. V-memory recall in the prompt was used as leads and every claim below was re-read in the code.
Bash in this run was clamped to memory search and git read, so everything was read with Read/Grep, and nothing
below was executed.

## 1. Matrix

Dimension 1: which file classes reach the `detect_ui` sample today (`_ui_sample`, `scripts/compound-v-onboard.py:1168`).
A file is sampled only when it survives the skip tests, has an extension in `_UI_SAMPLE_RANK` (:1064), is not matched
by a sensitive glob, reads cleanly under 64 KiB, and `scan_secrets` (:12) finds nothing.

| Probe file (spec) | Ranked ext? | Skipped today by | Reaches request today | After spec predicate |
|---|---|---|---|---|
| `wp-config.php` | yes (.php) | nothing (the reviewer's probe confirms) | yes | no (basename) |
| `config/database.php` | yes | nothing | yes | no (`.php` under `config`) |
| `lib/credentials.php` | yes | nothing (`**/credentials/**` matches a directory, not a file name) | yes | no (`credential` in path) |
| `.env.example`, `.env.local` | **no** (no ranked suffix) | rank test | **never** | no |
| `lib/math.php` | yes | n/a | yes | yes (control) |
| `config/settings.py`, `config/default.js`, `app/config/x.rb`, `src/config/prod.ts` | yes | nothing | yes | **yes, still sent** (predicate is `.php`-only) |
| `settings.py`, `appsettings.*.cs`-style files with a password literal | yes | nothing | yes | **yes, still sent** |

`scan_secrets` is not the safety net it looks like: `SECRET_RE` (`scripts/compound-v-memory.py:67`) matches only provider
token families (`sk-`, `ghp_`, `gho_`, `github_pat_`, `AKIA`, `xox*`) plus PEM blocks. A `password = '...'` line matches
nothing. That is why the three probe files got through.

Dimension 2: `no_key` as it travels vault -> parse.

| Vault emission (`plugins/compound-v-vault/hooks/vault.tsx`) | Status sent | In `UNAVAILABLE_REASONS` / `ERROR_REASONS` today | Parsed today | After spec |
|---|---|---|---|---|
| `unavailable('no_key')` :236 | unavailable | no | `upstream` (wrong) | `no_key` |
| `unavailable('no_vault')` :381, `disabled` :235, `egress` :249, `timeout` :226, `upstream` :227/:254 | unavailable | yes | kept | kept |
| `unavailable('auth')` :102, `credits` :103, `rate_limited` :104 | unavailable (carries `http_status`) | yes | kept, but when `http_status` is present `parse_response` ignores the vault reason and uses `_classify_http` (jev.py:417, :537-539) | same |
| `failed('bad_input')` :106/237/239, `failed('schema')` :108/117/119 | error | yes (`ERROR_REASONS`) | kept | kept |

Complete literal set the contract check must find: unavailable = {auth, credits, rate_limited, upstream, timeout,
disabled, no_key, egress, no_vault} (9); failed = {bad_input, schema} (2). Reasons `route` and `repo` exist only in
`statusFrom` (:77-78) and `offReason` (:181-183), which feed the status line and never a `JevResponse`.

Dimension 3: which entries `prune()` (jev.py:271) reaches in the data dir.

| Entry | Pruned today | After spec |
|---|---|---|
| `calls.jsonl`, `shadow-pairs.jsonl` | yes (line timestamps) | yes |
| `eval-t3.json`, `req/*`, `resp/*` | yes (lstat mtime) | yes |
| `pending-<sha256>.json` (written by `hooks/triage-prompt-nudge.sh:506`) | **no** | yes |
| `.pending.XXXXXX` (same writer, :499, left if the writer dies before `mv`) | no | **no** (name does not match `pending-*.json`) |
| `.tmp-*` from `_replace_private` (jev.py:259) | no | no |

## 2. Shared State

`UNAVAILABLE_REASONS` (jev.py:59). Read by exactly one function, `parse_response` (:542). Set nowhere else. Nothing
else in the repo hard-codes the tuple: `eval_report` groups by `"%s/%s" % (status, reason)` (:709) and
`telemetry_line` copies `reason` through (:569), so a new member needs no second edit in Python. Docs that list the
vocabulary: `plugins/compound-v-vault/README.md:73` (already lists `no_key`) and the parent spec (see Finding 7).

`resp.http_status` (response file, set by vault `byStatus`). When it is a non-2xx int, `parse_response` returns the
class from `_classify_http` and never reads `resp["reason"]`. A contract test that sends a response with
`http_status` would test `_classify_http`, not the vocabulary.

`cutoff` in `prune` (`now - RETENTION_S`, 30 days). Applied to `st_mtime` for file candidates. A descriptor's mtime is
its write time: `mv -f` of a freshly created temp file preserves it, and a rewrite for the same `sha256(proj|sid)`
refreshes it.

`dd` (data dir) at prune time. Exists whenever `prune` runs (`_append_jsonl` and `build_request` both call it after
`data_dir()` created it). `os.listdir(dd)` is therefore safe at the same call sites that already `os.path.join(dd, ...)`.

`_repo_files(repo)` (onboard.py:785) feeds `_ui_sample`. Git-tracked files only when `git ls-files` returns anything;
otherwise an `os.walk` fallback that includes untracked files. Gap: in a git repo where only some files are `git add`ed,
untracked files are invisible to the sample. A test that tracks some probe files and not others passes vacuously.

## 3. Sibling Code

`_ui_sample` skip block (onboard.py:1175-1185). Entry gate: `base == ".env" or low.endswith((".env", ".pem", ".key")) or
low.startswith(".github/")`, then `_exclude_reason(f)` (vendored/generated/binary, :32), then rank. Sensitive globs and
`scan_secrets` run later, after rank and cap check. The spec's "one named predicate beside the existing test" fits
this block. Note the existing `base == ".env"` is redundant with `endswith(".env")`. `.github/` is matched only as a
root prefix, not nested.

`jev_requests` detect_ui (onboard.py:1237-1244). Returns `[]` when the point is off, when the floor already says UI, or
when `_ui_sample` returns `[]`. So a repo whose every candidate is excluded sends nothing: a fail-closed property the new
predicate keeps.

Deterministic floor on `.php` (onboard.py:435-440, :397-409). Any `.php` file whose text outside `<?php ... ?>` holds an
HTML tag makes the floor return `deterministic:php-markup`, and `jev_requests` then returns `{"request_files": []}`
before `_ui_sample` runs. Probe PHP files must be pure PHP.

`prune` req/resp loop (jev.py:290-302). Rule: `os.lstat(path)`; unlink when `st_mtime < cutoff and not
os.path.isdir(path)`. `os.path.isdir` follows symlinks, so a symlink to a file with an old own-mtime IS unlinked (the
link, not its target), and a symlink to a directory is kept. It never follows a link to read or delete a target. The spec
says the new candidates follow the same rule and also that "symlinks and directories are never followed or removed". The
first half is true; "never removed" is false for the existing rule (Finding 10).

Consumer of the descriptors, `hooks/jev-t3.tsx:169-194` (`findPending`). Lists the data dir, keeps non-link files named
`pending-*.json`, sorts by name, takes the first 50 (`MAX_PENDING`, :26), reads each and matches `sid` and `proj` by
content. Names are sha256 hex, so the 50 kept are an arbitrary slice, not the oldest or newest. Symlinks named
`pending-*` are already invisible to it.

Producer, `hooks/triage-prompt-nudge.sh:457-511` (`_write_t3_descriptor`). Calls `compound-v-jev.py build` (which prunes)
immediately before writing the descriptor, so prune runs on the same path that creates orphans. A crash between
`mktemp "${dd}/.pending.XXXXXX"` (:499) and `mv` leaves a dot-file the new rule will not match.

Existing selftest rows to sit beside: onboard.py:2489-2541 (the `detect_ui` jev block; expected sample exactly
`["site/index.html","site/page.html","cli/main.py"]` at :2510) and jev.py:1156-1177 (pruning rows; `old = _now() - 31 *
86400`, `os.utime`). `test-jev-core.sh` section 6 reads the LAST line of `calls.jsonl` right after its own parse and
section 7 greps `calls.jsonl` and `$DD` for `LEAKMARKER`; a new section that runs `parse` many times must not put
those strings in a response.

## 4. External APIs (via context7)

None touched by this change. No third-party API or library call is added or changed: the work is Python 3.9 stdlib,
one bash test, and one doc edit. The OpenRouter and vault contract is internal to the repo (`vault.tsx` plus
`compound-v-jev.py`); the HTTP-status mapping already sits in selftest rows (jev.py:1120-1129). Phase 1C owns library
currency. Context7 was not queried; nothing here would be answered by it.

## 5. Regression Surface

- `jev_requests --point detect_ui` for existing users: an over-broad predicate silently removes legitimate sample files
  (templates under a `credentials/` or `secretary/` directory, `app/config/*.php` views), lowering `jev:sample` recall.
  Fail-closed, not a break. The existing selftest row (:2510) pins the sample and must still pass.
- `onboarding.md` text: a new exclusion is user-visible behaviour; the doc must say it or it lies (Finding 4).
- `parse_response` for every other reason: adding one tuple member cannot change them. A response with
  `reason: "no_key"` changes from `unavailable/upstream` to `unavailable/no_key`; `calls.jsonl` and `eval_report`
  buckets for existing users' history are unaffected (past lines keep `upstream`).
- `prune()` runs on every `build`, `parse`, `pair`, `eval`. A bug in the new branch (non-existent `dd`, a directory named
  `pending-x.json`, a permission error) would break the T3 hook's `build` call and drop shadow telemetry. The existing
  loop already swallows `OSError` from `lstat` and `unlink`; `os.listdir(dd)` has no such guard.
- `tests/test-jev-core.sh`: sections 6 and 7 read `calls.jsonl` assuming order; a new section that adds lines ahead of
  them changes what "last line" means.
- `plugins/compound-v-vault/hooks/vault.tsx` and `hooks/jev-t3.tsx` (AC-5): nothing in this change may touch them.

## 6. DRY Findings

- The contract check re-derives the reason vocabulary from a TypeScript file by regex. There is no shared schema file
  between the two sides today (`schemas/` has no Jev schema). The spec's regex-over-source test is the cheapest
  existing-pattern option; it is a drift detector, not a single source of truth. Decision: acceptable, extend; do not add a
  third copy of the vocabulary.
- `prune`'s candidate loop is already the shared place for age-based removal. Extend `candidates`, do not write a second
  loop.
- Secret-name tests exist in three places that disagree: `_SENS_ALWAYS` (onboard.py:723), `_SENS_SEGS` (:724) and the
  inline `_ui_sample` test (:1178). The spec adds a fourth predicate in the same inline block. Do not fork the secret
  content patterns (`SECRET_RE` is imported, per `.claude/rules/scripts.md`); a named predicate is fine, but it must not
  duplicate `_SENS_*` entries.

## 7. Design constraints for the spec

1. **Findings 1 and 2 (scope of Issue 1).** The `config` rule is `.php`-only, yet `_UI_SAMPLE_RANK` includes `.py`, `.js`,
   `.ts`, `.rb`, `.go`, `.java`, `.kt`, `.cs`. A `config/settings.py` or `settings.py` with a password literal is
   sampled after the fix. The spec must either widen the `config` rule to every ranked extension, or state in the spec that
   non-PHP config files stay in scope of the sample and why that is accepted. It must not claim the leak class is closed.
2. **Finding 3 (vacuous test rows).** The Issue 1 row must: `git add` every probe file (or use no git at all); make every
   PHP probe pure PHP with no HTML outside `<?php ... ?>`; enable `jev.enabled` and `jev.detect_ui.mode: active` in the
   probe repo's `.claude/compound-v.json`; plant password-shaped values that do NOT match `SECRET_RE` (a token-shaped value
   would be dropped by `scan_secrets` and mask the new predicate); and assert that the request file exists and holds
   `lib/math.php`. Without the last assertion, "contains none of the planted values" passes on an empty request.
3. **Finding 2.** `.env.example` and `.env.local` have no ranked suffix and are never sampled; they cannot prove the `.env*`
   predicate. State that the three PHP files carry the row, or add a ranked-extension file whose basename starts `.env`.
4. **Finding 4.** `skills/compound-v/onboarding.md:78-79` lists the sample's exclusions. It MUST be updated (the spec's
   "only if" resolves to yes). `commands/v-onboard.md` lines 42-44 and 92-93 do not list exclusions; it must NOT change.
   Move `skills/compound-v/onboarding.md` from "only if" to a firm Lane A file.
5. **Finding 7 (spec table).** The parent spec lists reasons at lines 68-70 (`unavailable: no_vault, disabled, ...`) and in the
   failure table at line 219. Both must carry `no_key`; Lane B's "the one table row" understates it. Line 222 (`401/403 ->
   auth`) stays.
6. **Finding 8 (contract test).** Responses fed to `parse` must omit `http_status`. Extraction must match call shape
   `unavailable('x'` and `failed('x'` only (not `reason: 'x'`, which would sweep in `route` and `repo`), must not match the
   definitions at :87 and :93, and must assert at least one reason per status (the spec already requires this). Expected
   today: 9 unavailable, 2 error.
7. **Finding 9 (test ordering).** Place the new section after section 6's last-line reads (or reset `calls.jsonl` assumptions),
   keep Bash 3.2 compatibility (no `mapfile`, no associative arrays), keep the response files free of `LEAKMARKER`, and keep
   the key-shaped literals spelled in pieces as the file already does.
8. **Finding 10 (symlink wording).** Decide and write one rule: either reuse the existing `lstat` + `not isdir` rule (links
   can be unlinked, never followed) and fix the spec sentence, or require `stat.S_ISREG(st.st_mode)` for `pending-*.json`.
   The spec as written promises behaviour the existing rule does not have.
9. **Finding 11 (residual).** The prune bounds orphan age but does not guarantee visibility: 50 or more orphans within
   30 days still push descriptors out of `findPending`'s first 50. `hooks/jev-t3.tsx` may not change (decision 2), so the
   spec must say the issue is reduced, not closed, and must not claim AC-4 removes the silent-stop failure.
10. **Finding 12 (docstrings).** Update the `prune` docstring (jev.py:272, currently "jsonl lines and req/resp files") and
    the module docstring sentence at jev.py:18-23 that lists what the data dir holds.
11. **Prune guard.** `os.listdir(dd)` must be wrapped like the `lstat` calls so a listing error cannot break `build`, `parse`,
    `pair` or `eval` (Section 5).
12. **Pending-row test.** Use the `now` parameter or `os.utime` as the existing row does (jev.py:1164); create the stale file
    older than 30 days and a fresh one; also assert a directory named `pending-x.json` and a symlink survive or follow the rule
    chosen in item 8. The row must fail with the new candidates removed.
13. **AC-5.** `vault.tsx` and `jev-t3.tsx` stay byte-identical; `vault.test.tsx:224-230` already asserts `no_key` and
    `Jev: off (no_key)`, so no vault test changes.

Findings count: 14. The "Finding N" references above point at the list below.

### Finding list

1. Secret-file predicate is `.php`-only for `config`; non-PHP config files stay sampled. (Section 1)
2. `.env*` files are never sampled (no ranked extension); the `.env.example` probe proves nothing.
3. Issue 1 test can pass vacuously (untracked files, floor flips to UI on HTML in PHP, config off, token-shaped plants, empty request).
4. `onboarding.md:78-79` documents the exclusions and must change; `v-onboard.md` must not.
5. `secret`/`credential` as a path substring over-excludes (directory names); fail-closed, accepted.
6. `onboard_layer` sends file path names (not contents, up to 30 per directory) and is outside the new predicate; names only.
7. Parent spec lists reasons in two more places than the spec names.
8. Contract test must omit `http_status`, match call shape only, and pin 9 + 2 reasons.
9. `test-jev-core.sh` ordering and Bash 3.2 constraints.
10. Spec says symlinks are "never removed"; the existing `prune` rule removes old symlinks to files.
11. Pruning is bounded, not a cure: 50 or more orphans inside 30 days still hide descriptors; `.pending.*` crash leftovers are out of the glob.
12. `prune` and module docstrings describe an incomplete set.
13. `os.listdir(dd)` is unguarded in a function every writer calls.
14. Stale parent-spec telemetry path (`docs/superpowers/memory/jev-calls.jsonl` vs the real `~/.claude/compound-v-jev/<digest>/calls.jsonl`) (spec line 71); not this change, but Lane B edits that spec.

## 8. File Touch Map (for Phase 2 partitioning)

| File | Lane | Note |
|---|---|---|
| `scripts/compound-v-onboard.py` | A | `_ui_sample` predicate (:1175-1185), docstring (:1169), selftest row beside :2489-2541. Not a SHARED RESOURCE. |
| `skills/compound-v/onboarding.md` | A | Lines 78-79, firm. Prose read by V-memory; no generated output. |
| `commands/v-onboard.md` | none | Does not describe exclusions; do not touch. |
| `scripts/compound-v-jev.py` | B | `UNAVAILABLE_REASONS` (:59), `prune` (:271) and docstrings (:18-23, :272), selftest row beside :1156-1177. Not a SHARED RESOURCE. |
| `tests/test-jev-core.sh` | B | New contract section after section 7. Sibling `tests/` sweep runs it recursively, no registration. |
| `docs/superpowers/specs/2026-10-05-jev-classifier-foundation-design.md` | B | Lines 68-70 and 219 (constraint 5), not only one row. Indexed by V-memory. |
| `plugins/compound-v-vault/hooks/vault.tsx` | read-only | Read by the new test; must stay byte-identical (AC-5). |
| `hooks/jev-t3.tsx` | read-only | Must stay byte-identical (AC-5). |

No file is shared by Lane A and Lane B. No lockfile, schema dump, route registry, migration or barrel file is touched.
