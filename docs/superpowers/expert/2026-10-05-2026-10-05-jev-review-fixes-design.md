# Domain-Expert Audit (Phase 1B) - Jev review fixes

Spec: `docs/superpowers/specs/2026-10-05-jev-review-fixes-design.md`
Recon read first and deepened: `docs/superpowers/recon/2026-10-05-jev-system-one-classifier-via-openrouter.md`
(through the prior Phase 1B audit, which already deepened it; Trigger 0 for this spec was `kb_skip`).
Date: 2026-10-05. Every web source below was fetched or searched on 2026-10-05.

## 1. Domain(s) Identified

1. **secret-bearing-files** - which repository files hold credentials by convention, and how good name-based and
   content-based filters are at keeping them out of a third-party request (Issue 1).
2. **system-one-classifiers** (existing KB) - OpenRouter's HTTP failure classes and how a client maps them to
   telemetry reasons (Issue 2).
3. **local-retention** - age-based pruning of local data files under the 30-day rule the parent spec set (Issue 3).

## 2. Sources Consulted

**V-memory.** The prompt's recall block (eight rows: parent spec, plan, 1B/1C audits, review record). One extra
search, "secret filename exclusion egress sample", returned the review verdict, this spec, the prior audit's
constraint 6 and the archaeology constraint 11. No new precedent beyond those.

**Agent memory.** `system-one-classifier-calibration.md` (32k window, 402 no-retry, ZDR undocumented): used as
leads. The 402 facts were not re-fetched; the errors page fetched below agrees on 402.

**Knowledge base.** `_knowledge-base/system-one-classifiers.md` (created today, fresh, primary-sourced). Its error
matrix has no row for 401/403; added in section 9. No KB file existed for secret-bearing file names.

**Code read (to scope the domain findings, not to duplicate 1A):** `scripts/compound-v-onboard.py:785-793`
(`_repo_files`), `:1064-1068` (`_UI_SAMPLE_RANK`), `:1168-1200` (`_ui_sample`); `scripts/compound-v-memory.py:64-74`
(`PEM_RE`, `SECRET_RE`); `plugins/compound-v-vault/hooks/vault.tsx:101-108,226-254`; `scripts/compound-v-jev.py:59-61,
271-302`; `hooks/jev-t3.tsx:168-187`.

**Official / primary (fetched):**
- [OpenRouter - API error handling and debugging](https://openrouter.ai/docs/api_reference/errors-and-debugging)
- [Django - deployment checklist, SECRET_KEY](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/)
- [github/gitignore - Drupal template](https://raw.githubusercontent.com/github/gitignore/main/Drupal.gitignore)
- [github/gitignore - Joomla template](https://raw.githubusercontent.com/github/gitignore/main/Joomla.gitignore)
- [github/gitignore - Magento (1) template](https://raw.githubusercontent.com/github/gitignore/main/Magento.gitignore)
- [Composer - authentication for private packages](https://getcomposer.org/doc/articles/authentication-for-private-packages.md)
- [gitleaks PR #1743 "Add database password rule"](https://github.com/gitleaks/gitleaks/pull/1743)

**Secondary (fetched):**
- [kishansavaliya.com - what is Magento env.php](https://kishansavaliya.com/what-is-magento-env-php) (not
  Adobe-authored; Adobe's own page was not fetched)
- [TrustMe00/senstives-files](https://github.com/TrustMe00/senstives-files) - confirms only `wp-config.php` from
  the names checked; not cited for anything else.

**Community (Layer 2/3):**
- [HN: "What xAI's Grok build CLI sends to xAI: A wire-level analysis"](https://news.ycombinator.com/item?id=48877371)
  (539 points, 228 comments, posted about 85 days before 2026-10-05, so about 2026-07-12). One thread.
- `site:reddit.com accidentally committed wp-config.php database password leaked`: **no Reddit hits**.

Queries run: "OpenRouter API error codes 401 403 moderation flagged 2026"; "shhgit sensitive filenames list
wp-config.php configuration.php settings.php env.php"; "gitleaks default rules generic password php define
DB_PASSWORD detection gaps"; "composer auth.json secrets committed github-oauth token leak"; "site:reddit.com
accidentally committed wp-config.php database password leaked"; "site:news.ycombinator.com AI coding tool sent .env
file secrets to LLM provider 2026"; "openrouter.ai docs \"Error Handling\" 403 \"requires moderation\""; "Adobe
Commerce Magento app/etc/env.php database credentials crypt key do not commit"; "GDPR storage limitation retention
mtime based deletion log files personal data local cache 30 days"; "Drupal settings.php $databases password
sites/default/settings.php hardcoded credentials".

## 3. Domain Constraints the Brainstorm Probably Missed

### 3.1 The ranked-extension list is the real egress boundary, and the spec's `config/` rule covers only one of its languages

- `_ui_sample` only reads a file whose extension is in `_UI_SAMPLE_RANK` (`compound-v-onboard.py:1182-1184`). Rank 1 is
  markup; rank 2 is `.php .js .mjs .ts .py .rb .go .java .kt .cs .dart .ex .rs .swift`. A name that is not one of
  these extensions is never read, so `auth.json`, `database.yml`, `appsettings.json`, `secrets.yml` are **out of
  scope here** (they are real secret-bearing files: Composer says "Make sure the `auth.json` file is in
  `.gitignore`" ([Composer docs](https://getcomposer.org/doc/articles/authentication-for-private-packages.md)) - but
  `.json` is not ranked).
- The spec's fourth bullet ("a `.php` file whose parent directory is named `config`") leaves `config/database.js`,
  `config/settings.py`, `config/secrets.rb`, `config/*.ts` sendable. They are in ranked languages and the convention
  is the same.
- Known secret-bearing names **in ranked extensions** that the spec's four bullets miss:
  - Django `settings.py`: "The secret key must be a large random value and it must be kept secret. Make sure that
    the key used in production isn't used anywhere else and avoid committing it to source control"
    ([Django checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/)). Its parent directory is
    the project package, not `config`.
  - Drupal `sites/*/settings.php`, `settings.local.php`: GitHub's template ignores `/web/sites/*/*settings*.php`
    under the comment "Ignore configuration files that may contain sensitive information"
    ([Drupal.gitignore](https://raw.githubusercontent.com/github/gitignore/main/Drupal.gitignore)).
  - Joomla `configuration.php` at the root: ignored as `/configuration.php`
    ([Joomla.gitignore](https://raw.githubusercontent.com/github/gitignore/main/Joomla.gitignore)).
  - Magento 2 `app/etc/env.php`: holds the DB password and the `crypt.key` "that encrypts payment tokens"
    ([secondary source](https://kishansavaliya.com/what-is-magento-env-php); GitHub's Magento template covers only
    Magento 1's `/app/etc/local.xml`). Treat as secondary until Adobe's own doc is fetched.

### 3.2 The non-git fallback sends gitignored files

- `_repo_files` returns `git ls-files` output, and **falls back to `os.walk`** when that is empty
  (`compound-v-onboard.py:785-793`): not a repository, or `git init` with nothing committed yet. The walk prunes
  only `VENDOR_DIRS`. On that path the files a correctly configured project keeps *out* of git (`.env.local`,
  `wp-config.php`, `settings.local.php`, `app/etc/env.php`) are candidates, and the name predicate is the only
  name-level defence.
- The spec's test builds a git repository with the planted files tracked. It does not exercise the walk.

### 3.3 `scan_secrets` does not catch the passwords the reviewer planted

- `SECRET_RE` matches only vendor-prefixed tokens (`sk-`, `ghp_`, `gho_`, `github_pat_`, `AKIA`, `xox?-`) and
  `PEM_RE` only PEM key blocks (`compound-v-memory.py:64-74`). `define('DB_PASSWORD', '...')`,
  `$password = '...'` and `'password' => '...'` pass. That is why the review probe got three planted passwords
  through.
- This is a known gap in the field, not a local oversight. A gitleaks contributor wrote: "there were multiple
  situations where the database passwords outside of connection strings were omitted during checking. Examples
  would be: `DB_PASSWORD`, `DB_PASSWD`, `pwd` etc." The PR was closed unmerged on 2026-04-07
  ([gitleaks #1743](https://github.com/gitleaks/gitleaks/pull/1743)).
- So name-based exclusion is the primary control for low-entropy credentials, and the content filter is a backstop
  only for vendor tokens. The spec's choice (omit the whole file, never redact a head) meets the prior audit's
  fail-closed rule for the files it names. It does not cover a password in a file with an unlisted name.

### 3.4 On OpenRouter, 403 is not "rejected key"

- Verbatim: "**401 Unauthorized**: Invalid credentials (OAuth session expired, disabled/invalid API key)" and
  "**403 Forbidden**: Forbidden (insufficient permissions, guardrail block, or moderation flag)". Guardrail blocks
  happen "before reaching a provider - such as through content filters or prompt-injection detection - the API
  returns a 403 response with details about the block reason"
  ([OpenRouter errors](https://openrouter.ai/docs/api_reference/errors-and-debugging)).
- `vault.tsx:102` maps `401 || 403` to `unavailable('auth')`, and spec decision 1 keeps `auth` "for a 401/403".
  The spec's own rationale is that telemetry must tell failure classes apart. Under that mapping, a T3 prompt that
  an organization's prompt-injection guardrail blocks is logged as a rejected key.
- **Correction to the prior audit.** Constraint 8 of `2026-10-05-2026-10-05-jev-classifier-foundation-design.md`
  said "map 401/403 to `unavailable(no_key)`-class reasons". That conflated the two codes. 401 is a key problem.
  403 may be a key-permission problem or a content block.

### 3.5 Age-based pruning bounds orphans; it does not restore visibility

- `findPending` lists `pending-*.json`, sorts by **name**, and keeps the first 50 (`jev-t3.tsx:175-179`). The name is
  `pending-<sha256(proj|sid)>`, so sort order is hash order and unrelated to age. A 30-day prune limits orphans to
  those created in the last 30 days. If 50 or more accumulate inside that window, a new descriptor whose hash sorts
  after them is still invisible, and shadow still stops silently. `jev-t3.tsx` is frozen (decision 2).
- A file whose mtime is in the future (clock skew, restored backup) is never older than the cutoff and is never
  pruned by an mtime rule.

## 4. Common Traps in This Domain

1. **Exact-basename lists for config files.** CMS and framework conventions use different names in different
   directories (`wp-config.php`, `sites/*/settings.php`, `configuration.php`, `app/etc/env.php`, `settings.py`). A
   rule tied to one parent name (`config`) or one language (`.php`) misses the rest (3.1).
2. **Trusting `.gitignore` as a filter that is not on the code path.** Tracked-files-only holds only while
   `git ls-files` returns something (3.2).
3. **Treating a token-shape regex as a password detector.** Vendor-prefix regexes do not see low-entropy
   database passwords; even the larger open-source scanners have this gap ([gitleaks #1743](https://github.com/gitleaks/gitleaks/pull/1743)) (3.3).
4. **One reason for two HTTP codes.** 401 and 403 have different fixes on OpenRouter; folding them hides a content
   block behind an auth label (3.4).
5. **Tests that only exercise the happy layout.** A selftest with tracked files in a committed repo proves nothing
   about the walk path (3.2).
6. **Silent agent-tool egress of env files is a live concern.** Isolated report (one HN thread, 539 points, 228
   comments, about 2026-07-12): a wire-level analysis states the Grok build CLI "transmits the contents of files it
   reads - including a .env secrets file - to xAI, verbatim and unredacted"
   ([HN 48877371](https://news.ycombinator.com/item?id=48877371)). One thread, below the ten-thread consensus bar;
   cited as a signal of user sensitivity, not as a rule.

## 5. Regulatory / Compliance Notes

- No sector regulation is triggered by these three fixes themselves. What matters is unchanged from the prior
  audit: file heads go to two processors (OpenRouter, TypeSafe) after consent, with no documented zero retention on
  `/api/v1/systemone`. A credential that leaks into a request is disclosed to both and cannot be recalled.
- Issue 3 is a retention control. The 30-day period is a project choice from the parent spec; GDPR sets no fixed
  period. Searches on storage limitation returned only secondary guides (not cited as authority). The relevant point
  is technical: data in the directory that the prune does not reach is kept without limit, which breaks the
  parent spec's stated retention rule.
- Composer's own guidance treats `auth.json` as a credential file ([Composer](https://getcomposer.org/doc/articles/authentication-for-private-packages.md)).
  It is not ranked today. If `.json` is ever added to `_UI_SAMPLE_RANK`, the predicate must grow with it.

## 6. Recent Breaking Changes (last 12 months)

| Date | Change | Source |
|---|---|---|
| 2026 (current docs) | OpenRouter documents 403 as "insufficient permissions, guardrail block, or moderation flag", with guardrail blocks (content filter, prompt-injection detection) returning 403 before any provider is reached | [OpenRouter errors](https://openrouter.ai/docs/api_reference/errors-and-debugging) |
| 2026-04-07 | gitleaks database-password rule PR closed unmerged; DB_PASSWORD-style values remain outside the default ruleset | [gitleaks #1743](https://github.com/gitleaks/gitleaks/pull/1743) |
| about 2026-07-12 | Public wire-level analysis of an agent CLI sending `.env` contents upstream (isolated report) | [HN 48877371](https://news.ycombinator.com/item?id=48877371) |

## 7. Design Constraints for the Plan (non-negotiable)

Lane A (`scripts/compound-v-onboard.py`):

1. **MUST apply the config-directory rule to every extension in `_UI_SAMPLE_RANK`, not only `.php`.** A file whose
   parent directory is named `config` (any depth, case-insensitive) is skipped when its extension is any ranked
   extension. The predicate is the one named place the spec asks for (3.1).
2. **MUST add these basenames to the same predicate** (case-insensitive), each a known credential file in a ranked
   extension: `settings.py` and `local_settings.py` (Django, [checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/));
   any `*settings*.php` (Drupal, [template](https://raw.githubusercontent.com/github/gitignore/main/Drupal.gitignore));
   `configuration.php` (Joomla, [template](https://raw.githubusercontent.com/github/gitignore/main/Joomla.gitignore));
   `env.php` (Magento 2 `app/etc/env.php`, secondary source). The docstring lists them with the spec's four rules.
   Excluding a harmless file only shrinks a sample; including a credential file cannot be undone.
3. **MUST test the walk path.** The selftest row (or a second row) runs `_ui_sample` on a directory that is not a git
   repository, or is `git init` with no commit, holding the same planted files, and asserts the same result: only
   `lib/math.php`, none of the planted values. Without it the test does not cover the layout where gitignored
   secrets are actually present (3.2).
4. **MUST apply the predicate before any read**, including on the walk path, so a file it names is never opened.
   The spec says this for the git path; it holds for both.
5. **MUST NOT describe `scan_secrets` as covering passwords** in any docstring or doc the plan touches. It covers
   vendor tokens and PEM blocks only (3.3).

Lane B (`scripts/compound-v-jev.py`, `tests/test-jev-core.sh`, parent spec table row):

6. **MUST word the parent spec's `auth` row as "HTTP 401 (rejected or disabled key) or HTTP 403 (insufficient
   permissions, guardrail block or moderation flag)"**, citing [OpenRouter errors](https://openrouter.ai/docs/api_reference/errors-and-debugging).
   It must not say "rejected key" alone, because the vault folds both codes into `auth` (3.4).
7. **MUST keep `no_key` distinct from `auth` in the contract check**, as the spec says: a `no_key` response parses to
   `unavailable`/`no_key`, and a 401-sourced `auth` stays `auth`.
8. **MUST NOT prune a `pending-*.json` whose mtime is newer than the cutoff, and MUST NOT follow or remove a
   symlink or directory** (the spec's `lstat` rule). A future mtime is left alone; the docstring says so (3.5).

## 8. Open Questions for the Human

1. **403 in the frozen vault.** Should a later change split `vault.tsx:102` so 403 maps to its own reason (for
   example `blocked`), with `compound-v-jev.py` accepting it? Decision 2 freezes the vault in this run, so today a
   guardrail or moderation block on a T3 prompt is counted as `auth`.
2. **Password detection.** `SECRET_RE` is a shared constant in `compound-v-memory.py`, outside both lanes. Should a
   follow-up add a content rule for assignment-shaped credentials (`DB_PASSWORD`, `password =>`, `$password =`)
   to the onboarding sample check only? It would catch files with unlisted names; the false-positive cost is a
   smaller sample.
3. **Descriptor starvation.** The prune cannot fix the 50-name, hash-ordered window in `jev-t3.tsx`. Is "50 orphans
   within 30 days" acceptable for spec 1 shadow mode, or should a later change sort by mtime or match the expected
   name for the session directly?
4. **Over-exclusion.** Constraints 1-2 can skip legitimate UI files (a `config/routes.js`, a Django `settings.py`
   that only sets `TEMPLATES`). Is a smaller `detect_ui` sample acceptable? This audit recommends yes.

## 9. Knowledge Base Updates

- Appended to `docs/superpowers/expert/_knowledge-base/system-one-classifiers.md` under "Updated 2026-10-05 - Jev
  review fixes": 401/403/408/502/503 rows for the OpenRouter error matrix, a strike-through correction of the
  foundation audit's "401/403 to no_key-class" wording, and a generalized rule on keeping telemetry reasons apart.
- Created `docs/superpowers/expert/_knowledge-base/secret-bearing-files.md`: secret-bearing names by framework with
  sources, the token-regex vs password gap, and the non-git fallback trap.
