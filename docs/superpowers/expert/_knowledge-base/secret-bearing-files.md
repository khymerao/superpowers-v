# Secret-Bearing Files Knowledge Base

Maintained by Compound V Phase 1B advisor. Append at the bottom on each pass.

---

## Updated 2026-10-05 - Jev review fixes (detect_ui sample egress)

### Credential files by convention (checked 2026-10-05)

| Framework | File | Holds | Source |
|---|---|---|---|
| WordPress | `wp-config.php` | DB credentials, auth keys | [TrustMe00 list](https://github.com/TrustMe00/senstives-files) (names it); review probe in this repo |
| Django | `settings.py` | `SECRET_KEY` ("avoid committing it to source control") | [Django checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/) |
| Drupal | `sites/*/*settings*.php` | `$databases` | [github/gitignore Drupal](https://raw.githubusercontent.com/github/gitignore/main/Drupal.gitignore): "Ignore configuration files that may contain sensitive information" |
| Joomla | `configuration.php` (root) | DB credentials, secret | [github/gitignore Joomla](https://raw.githubusercontent.com/github/gitignore/main/Joomla.gitignore) |
| Magento 2 | `app/etc/env.php` | DB password, `crypt.key` | [secondary](https://kishansavaliya.com/what-is-magento-env-php); Adobe doc not fetched |
| Magento 1 | `app/etc/local.xml` | DB credentials | [github/gitignore Magento](https://raw.githubusercontent.com/github/gitignore/main/Magento.gitignore) |
| Composer | `auth.json` | repo tokens, basic auth | [Composer docs](https://getcomposer.org/doc/articles/authentication-for-private-packages.md): "Make sure the `auth.json` file is in `.gitignore`" |
| Any | `.env*` | environment secrets | convention; HN isolated report on agent CLI egress ([HN 48877371](https://news.ycombinator.com/item?id=48877371)) |

### Rules (generalizable)

- Scope a name filter to what the sampler can actually read. If only some extensions are ever read, the list must
  cover every one of those extensions, and must grow when the extension list grows.
- Directory-name rules (`config/`) must not be tied to one language; frameworks in every language use them.
- Vendor-prefix token regexes do not detect low-entropy database passwords (`DB_PASSWORD`, `pwd`). gitleaks PR to
  add such a rule was closed unmerged 2026-04-07 ([gitleaks #1743](https://github.com/gitleaks/gitleaks/pull/1743)).
  Name exclusion is the primary control for these files.
- A "tracked files only" sampler that falls back to a directory walk (no repo, or no commit yet) includes gitignored
  files, which is where these credentials live in a correctly configured project. Test the fallback path.
- Omit the whole file rather than redact a head: redaction of unknown password shapes cannot be shown complete.
