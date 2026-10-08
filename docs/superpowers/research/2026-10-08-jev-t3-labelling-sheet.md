# Jev T3 corpus: blind labelling sheet

Label each request by what a reviewer should treat it as. Do not look at `tests/fixtures/jev-t3-corpus.jsonl` (it holds a draft label). Put one code in the **Label** column:

| Code | Category | Meaning |
|---|---|---|
| `p` | plumbing | Internal only: build, tooling, tests, refactors with no change a user can see or feel. |
| `m` | user-facing-minor | A user can see it, but it is small and low-risk: copy, a label, spacing, a tooltip. |
| `M` | user-facing-major | A user-visible change with real risk: behaviour, data, money, auth, flows, anything that can break for users. |
| `u` | unknown | The text does not let you decide. |

When unsure between two, pick the stricter one (`M` over `m`, `m` over `p`). Edit this file in place; I merge the codes into `human_label`.

| # | Request | Paths | Label |
|---|---|---|---|
| t3-001 | Fix the shebang in tools/migrations/run_local.sh so the helper also runs under zsh. It is a developer-only script that starts a local Postgres container; it never runs in CI or production. | `tools/migrations/run_local.sh` |  |
| t3-002 | The lint that checks migration file names rejects names with digits after the timestamp prefix (e.g. 20261001_add_v2_index). Allow digits in the descriptive part. The lint only reads file names. | `scripts/migrations/lint_migration_names.py` |  |
| t3-003 | Send appointment reminder texts 24 hours before the appointment instead of 2 hours before. | `src/notifications/sms.py` |  |
| t3-004 | Increase the tooltip show delay from 200ms to 350ms; users say tooltips flicker when the pointer moves across the toolbar. | `web/static/js/tooltip.ts` |  |
| t3-005 | Wrap the CLI --help output at 100 columns instead of 80. | `cli/src/commands/help.rs` |  |
| t3-006 | Return HTTP 422 instead of 400 when an order payload fails validation. Several partner integrations call this endpoint. | `src/api/v1/orders.py` |  |
| t3-007 | Round displayed amounts to two decimals with banker's rounding instead of round-half-up. | `src/shop/money.py` |  |
| t3-008 | Change how the modal closes. | `apps/web/src/components/Modal.tsx` |  |
| t3-009 | Fix a typo in section 4 of the terms of service: 'thier' should be 'their'. | `web/templates/legal/terms.html` |  |
| t3-010 | Pre-tick the analytics checkbox in the cookie consent banner. | `web/static/js/consent_banner.ts` |  |
| t3-011 | Add the request id to the internal debug log line format. Debug logs are only written when LOG_LEVEL=debug and are never shown to end users. | `src/core/logging/formatter.py` |  |
| t3-012 | Delete the old importer if nothing uses it any more. | `src/legacy/importer.py` |  |
| t3-013 | Add the synonyms from the spreadsheet. | `src/search/synonyms.txt` |  |
| t3-014 | Change the weekly digest email subject from 'Your week in review' to 'Your weekly summary'. It goes to every subscribed user on Monday morning. | `emails/templates/weekly_digest.mjml` |  |
| t3-015 | Remove the %s placeholder from the German 'Bestellung %s bestaetigt' string; the order number is shown elsewhere on the page anyway. | `locales/de/checkout.json` |  |
| t3-016 | Update the site header to match the new brand guidelines. | `web/templates/base.html` |  |
| t3-017 | Change the empty-state message on the saved searches page from 'Nothing here yet' to 'No saved searches yet'. | `apps/web/src/pages/saved/EmptyState.tsx` |  |
| t3-018 | Fix the broken screenshot in step 2 of the public getting started guide. | `docs/site/getting-started.html` |  |
| t3-019 | Run the migration squash tool and commit what it produces. | `db/migrations/tooling/squash.py` |  |
| t3-020 | Pull the duplicated base64 padding code in src/auth/token_store.py into one private helper. Same inputs, same outputs; the existing tests cover both call sites. | `src/auth/token_store.py` |  |
| t3-021 | Change the session cookie SameSite attribute from Lax to Strict. | `src/auth/session/cookie.py` |  |
| t3-022 | Change the account deletion confirmation text from 'This cannot be undone' to 'You can restore your account within 30 days'. | `web/templates/account/delete.html` |  |
| t3-023 | Fix the scheduler so it runs at the right time. | `src/core/scheduler/cron.py` |  |
| t3-024 | On the profile settings page, put the 'Save' button to the right of 'Cancel' instead of the left. | `apps/web/src/pages/settings/Profile.tsx` |  |
| t3-025 | Change the CDN cache settings as suggested in the performance review. | `infra/terraform/cdn.tf` |  |
| t3-026 | Bump the worker timeout; jobs are getting killed. | `config/app/timeouts.yaml` |  |
| t3-027 | The import-order linter crashes on files that start with a UTF-8 byte order mark. Strip a leading BOM before tokenising so the linter reads those files like any other. | `tools/lint/check_imports.py` |  |
| t3-028 | Make the dismiss button on the cookie banner 2px larger; it is hard to hit on phones. Do not change the banner text or what dismissing it does. | `web/static/js/cookie_banner.ts` |  |
| t3-029 | Raise the minimum password length from 8 to 12 characters for new accounts and for password changes. | `src/auth/password_policy.py` |  |
| t3-030 | Darken --color-link-hover from #55aa77 to #448866 so links pass contrast on the pricing page. | `web/static/js/theme_colors.js` |  |
| t3-031 | Stop sending so many notifications. | `src/core/notifications/rules.py` |  |
| t3-032 | Drop the unused legacy_status column from the orders table. | `db/migrations/0057_drop_legacy_status.sql` |  |
| t3-033 | Add a test fixture for a declined card to the payments test fixtures. Production payment code is not touched. | `src/payments/tests/fixtures.py` |  |
| t3-034 | Clean up the settings code, it has grown messy. Use your judgment. | `src/settings/views.py`, `src/settings/forms.py` |  |
| t3-035 | Change the footer copyright year from 2025 to 2026. | `web/templates/footer.html` |  |
| t3-036 | Show the app build number under the version string on the About screen. | `mobile/lib/screens/about_screen.dart` |  |
| t3-037 | Add a `make fmt` target that runs black and isort over src/ and tests/. | `Makefile` |  |
| t3-038 | Add a 'Back to home' link under the message on the 404 page. | `web/templates/404.html` |  |
| t3-039 | Turn the new_checkout flag on by default for every tenant. | `settings/flags.json` |  |
| t3-040 | Rename the 'editor' role to 'contributor' everywhere in the roles module. | `src/auth/roles.py` |  |
| t3-041 | Make the rules engine handle the edge case Maria mentioned on Tuesday. | `src/core/rules/engine.py` |  |
| t3-042 | Make the receipt email look like the new design mockup. | `web/templates/emails/receipt.html` |  |
| t3-043 | Show 'Page 3 of 12' instead of '3 / 12' in the pagination control. The component is used by every table in the app. | `apps/web/src/components/Pagination.tsx` |  |
| t3-044 | Change the search box placeholder from 'Search...' to 'Search products...'. | `web/static/js/search_box.ts` |  |
| t3-045 | Show the estimated reading time next to the publish date on blog posts. | `apps/web/src/pages/blog/Post.tsx` |  |
| t3-046 | Use the same defaults as staging. | `config/app/defaults.yaml` |  |
| t3-047 | Add a docstring to every function in the flag registry module. No flag definition or default changes. | `src/flags/registry.py` |  |
| t3-048 | Add type hints to every function in the serializers module. No runtime change; mypy should pass. | `src/api/serializers.py` |  |
| t3-049 | Replace moment with date-fns inside the shared date helper. Keep the exported function names and the output format strings; the snapshot tests for formatted dates must still pass. | `packages/shared/utils/date.ts` |  |
| t3-050 | Refactor the OAuth callback handler for readability: inline the small helper that checks the state parameter and rename the local variables. Behaviour should stay the same. | `src/auth/oauth/callback.py` |  |
| t3-051 | Replace the hand-rolled LRU cache in src/core/cache/lru.py with functools.lru_cache. The public get/put functions keep their signatures and the existing unit tests must pass unchanged. | `src/core/cache/lru.py` |  |
| t3-052 | Switch CSV exports from comma to semicolon separators. | `src/exports/csv_writer.py` |  |
| t3-053 | Change DEFAULT_PAGE_SIZE from 50 to 25. It is the default for list endpoints when a client sends no page size. | `config/app/settings.py` |  |
| t3-054 | Lower the log level of the 'digest batch started' message from info to debug; it floods the log aggregator. | `src/workers/email_digest.py` |  |
| t3-055 | Fix the typo 'Pasword' in the visible label of the password field on the login page. | `src/auth/templates/login.html` |  |
| t3-056 | Add a benchmark for the search tokenizer with a 10,000-document synthetic input. | `benchmarks/bench_search.py` |  |
| t3-057 | Use the reader's locale for thousands separators in every number the web app displays. | `web/static/js/format_number.ts` |  |
| t3-058 | Round the corners of the product cards on the catalogue page from 4px to 8px. | `web/static/less/cards.less` |  |
| t3-059 | In the English onboarding strings only, change 'Welcome aboard, {{name}}!' to 'Welcome, {{name}}!'. | `locales/en/onboarding.json` |  |
| t3-060 | Raise the local dev Postgres container's healthcheck timeout from 5s to 15s; slow laptops fail the first boot. This override file is only loaded by docker compose on developer machines. | `config/dev/docker-compose.override.yml` |  |
| t3-061 | Move the auth middleware to the new request context object. It should behave the same, but the context object also changes when the current user is looked up during a request. | `src/auth/middleware.py` |  |
| t3-062 | Rename the helper `_parse_semver` to `parse_semver` in the release bump script and update its two call sites in the same file. No behaviour change. | `scripts/release/bump_version.py` |  |
| t3-063 | Add tracking to the new onboarding flow like we discussed. | `web/static/js/analytics.ts` |  |
| t3-064 | In the invoice footer, change the contact address from support@example.com to billing@example.com. | `src/billing/templates/invoice_footer.html` |  |
| t3-065 | Lower the API rate_limit for free-tier keys from 120 to 60 requests per minute. | `settings/limits.json` |  |
| t3-066 | Rank exact title matches above more recent documents in search results. | `src/core/search/ranking.py` |  |
| t3-067 | Run the one-off script in tools/db/migrations that fills users.locale from the stored Accept-Language header for rows where locale is null. | `tools/db/migrations/backfill_user_locale.py` |  |
| t3-068 | Apply the translator's latest French file. | `locales/fr/common.json` |  |
| t3-069 | Fix the typo 'anually' in the heading of the pricing page. No numbers on the page change. | `web/templates/pricing.html` |  |
| t3-070 | Bump the ruff pre-commit hook to the latest release and fix whatever new lint it reports in the config file itself. | `.pre-commit-config.yaml` |  |
| t3-071 | Sort the imports in src/auth/__init__.py and remove the two that flake8 reports as unused. | `src/auth/__init__.py` |  |
| t3-072 | Mark the flaky test_orders_pagination test with our retry decorator (max 2 retries) and leave a comment pointing at the tracking issue. | `tests/integration/test_orders_api.py` |  |
| t3-073 | The numbers in the monthly report look off. Please fix. | `src/reports/monthly.py` |  |
| t3-074 | Make the users endpoint faster. | `src/api/v2/users.py` |  |
| t3-075 | Fix three broken cross-references in the developer architecture notes (the internal docs build warns about them). | `docs/dev/architecture.rst` |  |
| t3-076 | Include the lockfile hash in the CI dependency cache key so a dependency bump stops reusing a stale cache. | `infra/ci/cache-keys.yml` |  |
| t3-077 | Prorate plan downgrades by day instead of by whole month. | `src/billing/proration.py` |  |
| t3-078 | Reword the session-expired banner from 'Session timed out' to 'You were signed out after 30 minutes of inactivity'. | `src/auth/session/expired_banner.tsx` |  |
| t3-079 | Tidy up the payment webhook handler before the audit. | `src/payments/webhooks.py` |  |
| t3-080 | Right-align the numeric columns in the internal admin dashboard table. | `templates/admin/dashboard.html.j2` |  |
