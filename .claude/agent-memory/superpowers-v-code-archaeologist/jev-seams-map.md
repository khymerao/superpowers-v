---
name: jev-seams-map
description: Where the Jev classifier seams live (vault reasons, parse, prune, pending descriptors, detect_ui sample) and hidden couplings found auditing the review fixes
metadata:
  type: reference
---

Map facts as of 2026-10-05 (3.9.x checkout). Leads, not verdicts: re-verify before use.

- Vault reason literals live only in `plugins/compound-v-vault/hooks/vault.tsx` as `unavailable('x')` / `failed('x')` calls; `compound-v-jev.py` `UNAVAILABLE_REASONS` / `ERROR_REASONS` is the Python mirror. No shared schema. `parse_response` ignores the vault reason whenever `http_status` is a non-2xx int (uses `_classify_http`).
- `statusFrom` / `offReason` reasons (`route`, `repo`) are status-line only, never a JevResponse.
- `prune()` in `compound-v-jev.py` runs on every build/parse/pair/eval; `hooks/triage-prompt-nudge.sh` (`_write_t3_descriptor`) calls `build` right before writing `pending-<sha256>.json`; `hooks/jev-t3.tsx` `findPending` reads only the first 50 names sorted (sha256 hex, so an arbitrary slice).
- `detect_ui` sample: `_ui_sample` in `compound-v-onboard.py`; `SECRET_RE` (from `compound-v-memory.py`) catches token families only, never `password = ...` lines. `.php` with HTML outside `<?php ?>` flips the deterministic floor to UI, so `jev_requests` sends nothing. `.env.*` files have no ranked extension and are never sampled.
- `skills/compound-v/onboarding.md:78-79` documents the sample's exclusions; `commands/v-onboard.md` does not.
- Parent spec `2026-10-05-jev-classifier-foundation-design.md` repeats the reason vocabulary at lines ~68 and ~219.
