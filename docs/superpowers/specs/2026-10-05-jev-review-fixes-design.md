# Jev classifier foundation: closing the three review issues - design

Follow-up to run `2026-10-05-jev-classifier-foundation`. Its Review Gate returned ISSUES (3):
`docs/superpowers/dogfood/2026-10-05-jev-classifier-foundation-review.md` § Verdict. This spec closes all three.
Triage: FULL, record `2026-10-05T094210Z-close-the-three-issues-from-docs-superpowers-dogfood-2026-10-d9a4`.
Trigger 0: `kb_skip` (same-day review, spec, plan and recon cover this code).

Parent spec: `docs/superpowers/specs/2026-10-05-jev-classifier-foundation-design.md`. Its global constraints
stand unchanged (Python 3.9, stdlib only, no key outside the vault, no fabricated metrics, every behavioural
change ships a test row that fails when the change is reverted).

## Decisions (maintainer, 2026-10-05)

1. A missing key keeps its own reason, `no_key`. It is added to `compound-v-jev.py`'s `UNAVAILABLE_REASONS`, and
   the parent spec's table row moves from `auth` to `no_key`. `auth` stays the reason for a 401/403 from
   OpenRouter. A missing key and a rejected key need different fixes, so telemetry must tell them apart.
2. The vault (`plugins/compound-v-vault/hooks/vault.tsx`) and the T3 module (`hooks/jev-t3.tsx`) do not change.

## Issue 1 (high): secret-bearing files reach the `detect_ui` sample

**Today.** `_ui_sample` in `scripts/compound-v-onboard.py` skips `.env`, `*.pem`, `*.key`, `.github/**`, Layer A
sensitive globs and files `scan_secrets` flags. Expert audit item 6
(`docs/superpowers/expert/2026-10-05-2026-10-05-jev-classifier-foundation-design.md:133`) also requires skipping
secret-bearing names. The reviewer's probe showed `wp-config.php`, `config/database.php` and
`lib/credentials.php` in a built request, with their planted passwords.

**Change.** Before any file is read, `_ui_sample` also skips a path when any of these hold (case-insensitive):

- its basename is `wp-config.php`;
- its basename starts with `.env` (this covers `.env.example`, `.env.local`);
- the path contains `secret` or `credential`;
- it is a `.php` file whose parent directory is named `config`, at any depth (`config/x.php`, `app/config/x.php`).

The check is one named predicate beside the existing `.env`/`.pem`/`.key` test, so the exclusion list is read in
one place. The docstring lists the new names. If `skills/compound-v/onboarding.md` or `commands/v-onboard.md`
describes what the sample excludes, it is updated to match; if neither does, neither changes.

**Test.** A selftest row builds a git repository holding `wp-config.php`, `config/database.php`,
`lib/credentials.php`, `.env.example` and `lib/math.php`, each secret-bearing file with a planted password line.
It asserts that `_ui_sample` returns only `lib/math.php`, and that the request file `jev-requests --point
detect_ui` writes contains none of the planted values. The row fails when the new predicate is removed.

## Issue 2 (medium): `no_key` is logged as `upstream`

**Today.** The vault answers `unavailable(no_key)` (`vault.tsx:236`). `parse` in `scripts/compound-v-jev.py`
rewrites any reason outside `UNAVAILABLE_REASONS` to `upstream`, so `calls.jsonl` and the eval report count a
missing key as a provider outage.

**Change.** `UNAVAILABLE_REASONS` gains `no_key`. The parent spec's failure table row
"Key missing or lost from secure storage" reads `unavailable(no_key)`; status line says so.

**Test.** `tests/test-jev-core.sh` gains a contract check. It extracts every reason literal the vault passes to
`unavailable('…')` and `failed('…')` in `plugins/compound-v-vault/hooks/vault.tsx`, feeds each through
`compound-v-jev.py parse` as a response file of the matching status, and asserts that the parsed reason equals
the one sent. It also asserts the extraction found at least one reason of each status, so a changed call shape
cannot pass the check by finding nothing. A reason added on one side without the other fails it; removing
`no_key` from `UNAVAILABLE_REASONS` fails it.

## Issue 3 (low): orphaned `pending-*.json` descriptors are never pruned

**Today.** `prune()` in `scripts/compound-v-jev.py` applies the 30-day cutoff to `calls.jsonl`,
`shadow-pairs.jsonl`, `eval-t3.json`, `req/` and `resp/`. The T3 hook writes `pending-*.json` descriptors into the
same data directory; one the module never consumes stays forever. `hooks/jev-t3.tsx` reads only the first 50
`pending-*` names in sorted order, so enough orphans hide new descriptors and shadow stops without an error.

**Change.** `prune()` also removes regular files named `pending-*.json` in the data directory whose mtime is older
than the cutoff, by the same `lstat` rule it uses for `req/` and `resp/` (symlinks and directories are never
followed or removed). The docstring says so.

**Test.** A selftest row creates one `pending-*.json` older than 30 days and one fresh one, runs `prune`, and
asserts the old one is gone and the fresh one stays. The row fails when the new candidates are removed from
`prune`.

## Partition

Two lanes, no shared file:

- Lane A: `scripts/compound-v-onboard.py`, plus `skills/compound-v/onboarding.md` and `commands/v-onboard.md`
  only if they describe the sample's exclusions.
- Lane B: `scripts/compound-v-jev.py`, `tests/test-jev-core.sh`,
  `docs/superpowers/specs/2026-10-05-jev-classifier-foundation-design.md` (the one table row).

## Acceptance criteria

- AC-1 `scripts/compound-v-onboard.py --selftest` passes, including the new row, and that row fails with the
  exclusion predicate removed.
- AC-2 A `detect_ui` request built from the probe repository of Issue 1 holds no secret-bearing file and none of
  the planted values.
- AC-3 `scripts/compound-v-jev.py --selftest` and `tests/test-jev-core.sh` pass; the contract check covers every
  reason literal in `vault.tsx`, and a `no_key` response parses to `unavailable` / `no_key`.
- AC-4 `prune` removes a `pending-*.json` older than 30 days and keeps a fresh one; the row fails with the change
  reverted.
- AC-5 The manifest's full test command passes on the merged tree, and `vault.tsx` and `jev-t3.tsx` are
  byte-identical to HEAD at the start of the run.
