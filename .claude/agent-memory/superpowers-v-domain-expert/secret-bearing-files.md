---
name: secret-bearing-files
description: Credential file names by framework (Django settings.py, Drupal settings.php, Joomla configuration.php) and why token regexes miss DB passwords
metadata:
  type: reference
---

Checked 2026-10-05:
- Django `settings.py` holds SECRET_KEY, "avoid committing it to source control" (docs.djangoproject.com deployment checklist).
- Drupal `sites/*/*settings*.php`, Joomla `/configuration.php`: ignored by github/gitignore templates as sensitive.
- Vendor-prefix secret regexes miss `DB_PASSWORD`-style values; gitleaks PR #1743 for this closed unmerged 2026-04-07.
- In this repo, `_repo_files` in compound-v-onboard.py falls back to os.walk (includes gitignored files) - re-verify.

**How to apply:** leads for any spec that sends repo file content off-machine; re-verify before citing. Detail:
docs/superpowers/expert/_knowledge-base/secret-bearing-files.md. Related: [[system-one-classifier-calibration]]
