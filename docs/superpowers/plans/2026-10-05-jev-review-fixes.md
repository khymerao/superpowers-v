# Jev Review Fixes Implementation Plan

> **For agentic workers:** executed by Compound V on Engine C from one manifest
> (`docs/superpowers/execution/2026-10-05-jev-review-fixes/manifest.yaml`). Each task is one job in its own lane.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the three ISSUES the Review Gate of run `2026-10-05-jev-classifier-foundation` returned.

**Architecture:** Two disjoint lanes. Lane A tightens what `scripts/compound-v-onboard.py` puts into the
`detect_ui` Jev sample. Lane B makes `scripts/compound-v-jev.py` accept the vault's `no_key` reason (pinned by a
cross-language contract check), and prunes stale `pending-*.json` descriptors. A three-pass review follows.

**Tech Stack:** Python 3.9 stdlib, bash tests.

**Spec:** `docs/superpowers/specs/2026-10-05-jev-review-fixes-design.md`. Its "Pre-flight amendments" section
overrides the sections above it. Pre-flight audits:
`docs/superpowers/archaeology/2026-10-05-2026-10-05-jev-review-fixes-design.md`,
`docs/superpowers/expert/2026-10-05-2026-10-05-jev-review-fixes-design.md`,
`docs/superpowers/library-audit/2026-10-05-2026-10-05-jev-review-fixes-design.md`.

## Global Constraints

- Python 3.9 syntax, stdlib only; no `match`; no `X | Y` annotations.
- `plugins/compound-v-vault/hooks/vault.tsx` and `hooks/jev-t3.tsx` stay byte-identical to the run's base.
- Every behavioural change ships a selftest/test row that fails when the change is reverted.
- The sample rules only remove files from what is sent; nothing new is ever sent.
- No text claims "no secrets are sent"; the residual is stated.
- No fabricated metrics; no cost or savings text (anti-ruflo regex, `.github/workflows/validate.yml:194`).
- Docs: plain words, every claim true of HEAD, no line over 200 characters outside code/tables.
- Lane discipline: touch only your `write_allowed`; `register-lane` first, with a literal `--cwd`. Run python with `-B`.
- Commit subjects are plain sentences, no `feat:`/`fix:`; no Co-Authored-By trailer.

## Partition Map

| Task | Job id | Files (write) |
|---|---|---|
| A | `ui-sample` | `scripts/compound-v-onboard.py`, `skills/compound-v/onboarding.md` |
| B | `jev-reasons-prune` | `scripts/compound-v-jev.py`, `tests/test-jev-core.sh`, `docs/superpowers/specs/2026-10-05-jev-classifier-foundation-design.md` |
| R | `spec-review` | `docs/superpowers/dogfood/2026-10-05-jev-review-fixes-review.md`, `.claude/agent-memory/superpowers-v-spec-reviewer/**` |

No file is shared. A and B run in parallel; R depends on both.

---

### Task A: Secret-bearing files leave the `detect_ui` sample (`ui-sample`)

**Files:**
- Modify: `scripts/compound-v-onboard.py` (`_ui_sample` near line 1168; selftest near lines 2490-2535)
- Modify: `skills/compound-v/onboarding.md:78-79`

**Interfaces:**
- Consumes: nothing new.
- Produces: `_secret_named(path) -> bool` (pure, name only, case-insensitive) and
  `_has_credential_assignment(text) -> bool`. `_ui_sample(repo)` keeps its signature and return shape.

- [ ] **Step 1: Write the failing selftest rows.** In `_selftest`, beside the existing `jev detect_ui` block,
  build a probe repo with `_touch`, enable Jev for it with `_set_jev_cfg(rp, {"enabled": True, "detect_ui":
  {"mode": "active"}})`, and `git init && git add -A && git commit` it (reuse the selftest's git helper; every
  file must be tracked, because untracked files are invisible to the sample once anything is tracked). PHP
  probes carry no HTML outside `<?php ?>`, so the floor stays `no-ui`. Planted values are `DB_PASSWORD`-style
  literals that `SECRET_RE` does not match.

```python
_PLANTS = {
    "wp-config.php": "<?php\ndefine('DB_PASSWORD', 'plant-wp-0001');\n",
    "config/database.php": "<?php\nreturn ['password' => 'plant-cfg-0002'];\n",
    "config/database.js": "module.exports = { password: 'plant-js-0003' };\n",
    "config/settings.py": "PASSWORD = 'plant-py-0004'\n",
    "app/settings.py": "DEBUG = True\n",
    "lib/credentials.php": "<?php\n$x = 1;\n",
    "lib/secret_store.py": "x = 1\n",
    "web/configuration.php": "<?php\n$x = 1;\n",
    "lib/db.py": "db_password = 'plant-db-0005'\n",
}
for rel, body in _PLANTS.items():
    _touch(rp, rel, body)
_touch(rp, "lib/math.php", "<?php\nfunction add($a, $b) { return $a + $b; }\n")
```

  Rows (each named after the planted failure it catches):
  - `ui sample: secret-named files are skipped (wp-config, config/ dir any ext, settings, credentials, secret)`:
    `[f["path"] for f in _ui_sample(rp)] == ["lib/math.php"]`.
  - `ui sample: a credential assignment omits the file (lib/db.py)` — covered by the row above; add a direct
    unit row `_has_credential_assignment("db_password = 'plant-db-0005'") is True` and
    `_has_credential_assignment("x = 1") is False` and `_has_credential_assignment("token: ''") is False`.
  - `jev detect_ui: the request exists, holds lib/math.php, and none of the planted values`: build with
    `jev_requests(rp, "detect_ui")`, assert exactly one request file, read its text, assert `lib/math.php` is
    in it and no `plant-` substring and no excluded path is.
  - `ui sample: the os.walk path applies the same rules`: copy the probe tree without `.git` into a second temp
    dir (`shutil.copytree(rp, rw, ignore=shutil.ignore_patterns(".git"))`) and assert the same
    `_ui_sample(rw)` result.

- [ ] **Step 2: Run them, see them fail.**
  Run: `/usr/bin/python3 -B scripts/compound-v-onboard.py --selftest`
  Expected: FAIL on the new rows (the sample still holds the secret-named files).

- [ ] **Step 3: Implement.** Near `_UI_SAMPLE_RANK`:

```python
_SECRET_BASENAMES = ("wp-config.php", "settings.py", "local_settings.py", "configuration.php", "env.php")
_CRED_ASSIGN_RE = re.compile(
    r"""(?ix)
    ["']?[a-z0-9_.-]*(?:password|passwd|pwd|secret|api_?key|auth_?key|token)[a-z0-9_.-]*["']?
    \s*(?:=>|=|:|,)\s*
    (?P<q>["'])(?:(?!(?P=q)).){4,}(?P=q)
    """)


def _secret_named(path):
    """True when a path's NAME alone marks it secret-bearing: these are skipped before any read."""
    low = path.lower()
    parts = low.split("/")
    base = parts[-1]
    if base.startswith(".env") or base in _SECRET_BASENAMES:
        return True
    if base.endswith(".php") and "settings" in base:
        return True
    if "secret" in low or "credential" in low:
        return True
    return "config" in parts[:-1]


def _has_credential_assignment(text):
    """True when a bounded read assigns a quoted literal of 4+ chars to a credential-looking name."""
    return _CRED_ASSIGN_RE.search(text) is not None
```

  In `_ui_sample`, replace the first-loop guard so the name test runs before ranking (hence before any read):

```python
        if base == ".env" or low.endswith((".env", ".pem", ".key")) or low.startswith(".github/"):
            continue
        if _secret_named(f) or _exclude_reason(f):
            continue
```

  and after `if scan_secrets(text): continue` add `if _has_credential_assignment(text): continue`. Update the
  docstring: it lists the new name rules, the assignment rule, and says a secret in a file matching none of
  them can still be sampled.

- [ ] **Step 4: Run, see them pass, and prove the revert.**
  Run: `/usr/bin/python3 -B scripts/compound-v-onboard.py --selftest`
  Expected: all rows pass. Then temporarily make `_secret_named` return `False` and
  `_has_credential_assignment` return `False`, rerun, see the new rows fail, and restore.

- [ ] **Step 5: Update `skills/compound-v/onboarding.md:78-79`.** The sentence becomes: one request over at most
  12 files × 20 lines, which leaves out `.env*`, `*.pem`, `*.key`, `.github/**`, the sensitive globs, files whose
  names look secret-bearing (`wp-config.php`, `settings.py`, `local_settings.py`, `configuration.php`,
  `env.php`, `*settings*.php`, any path under a `config` directory or containing `secret` or `credential`),
  any file the secret scan flags, and any file that assigns a quoted literal to a password-, secret-, key- or
  token-like name. A secret in a file none of these rules catches can still be sampled.
  Run: `/usr/bin/python3 -B scripts/lint-frontmatter.py .` — Expected: clean.

- [ ] **Step 6: Commit.** `git commit -m "Keep secret-bearing files out of the detect_ui Jev sample" -- scripts/compound-v-onboard.py skills/compound-v/onboarding.md`

---

### Task B: `no_key` survives `parse`, and stale descriptors are pruned (`jev-reasons-prune`)

**Files:**
- Modify: `scripts/compound-v-jev.py:59-60` (`UNAVAILABLE_REASONS`), `:271-302` (`prune`), selftest near `:993`
- Modify: `tests/test-jev-core.sh` (new contract section after the parse checks, near line 109)
- Modify: `docs/superpowers/specs/2026-10-05-jev-classifier-foundation-design.md:68-70` and `:219`

**Interfaces:**
- Consumes: the reason literals in `plugins/compound-v-vault/hooks/vault.tsx` (read-only).
- Produces: `UNAVAILABLE_REASONS` containing `"no_key"`; `prune(dd, now=None)` unchanged in signature.

- [ ] **Step 1: Write the failing contract check** in `tests/test-jev-core.sh`, after the parse section. It
  reuses the request `$B` built earlier (so `parse` finds its request meta) and writes response files without
  `http_status`:

```bash
# 6b. contract: every reason the vault can send survives parse unchanged.
VAULT="$ROOT/plugins/compound-v-vault/hooks/vault.tsx"
reasons="$("$PY" -B - "$VAULT" <<'PYEOF'
import re, sys
src = open(sys.argv[1]).read()
for fn, status in (("unavailable", "unavailable"), ("failed", "error")):
    found = sorted(set(re.findall(r"\b%s\('([a-z_]+)'" % fn, src)))
    if not found:
        print("NONE %s" % status)
    for r in found:
        print("%s %s" % (status, r))
PYEOF
)"
if printf '%s\n' "$reasons" | grep -q '^NONE'; then fail "contract: no reason literals found in vault.tsx"; fi
n=0
while read -r st rs; do
  [ -n "$st" ] || continue
  printf '{"status": "%s", "reason": "%s", "latency_ms": 1}' "$st" "$rs" >"$DD/resp/$B.resp.json"
  out="$("$PY" -B "$SCRIPT" parse --response-file "$DD/resp/$B.resp.json" --repo "$REPO" --mode shadow)"
  got="$(jget "$out" 'd["status"] + " " + d.get("reason", "")')"
  if [ "$got" = "$st $rs" ]; then n=$((n + 1)); else fail "contract: vault $st($rs) parsed as '$got'"; fi
done <<EOF
$reasons
EOF
[ "$n" -gt 0 ] && pass "contract: $n vault reasons survive parse unchanged"
```

  (The `def` lines `function unavailable(reason` and `function failed(reason` do not match `\b%s\('`.)

- [ ] **Step 2: Write the failing prune rows** in `_selftest` of `scripts/compound-v-jev.py`:

```python
    dd = data_dir(repo_for_selftest)
    old_p = os.path.join(dd, "pending-old.json")
    new_p = os.path.join(dd, "pending-new.json")
    fut_p = os.path.join(dd, "pending-future.json")
    for p in (old_p, new_p, fut_p):
        with open(p, "w") as fh:
            fh.write("{}")
    now = _now()
    os.utime(old_p, (now - RETENTION_S - 60, now - RETENTION_S - 60))
    os.utime(fut_p, (now + 3600, now + 3600))
    link_p = os.path.join(dd, "pending-link.json")
    os.symlink(old_p + ".target", link_p)  # dangling on purpose
    os.utime(link_p, (now - RETENTION_S - 60, now - RETENTION_S - 60), follow_symlinks=False)
    prune(dd, now)
    check("prune: a pending-*.json older than 30 days is removed", not os.path.exists(old_p))
    check("prune: a fresh pending-*.json stays", os.path.exists(new_p))
    check("prune: a future-dated pending-*.json stays", os.path.exists(fut_p))
    check("prune: a pending-*.json symlink is never removed", os.path.islink(link_p))
```

  (Use the selftest's existing temp HOME and repo variables; name them as the surrounding code does.)

- [ ] **Step 3: Run both, see them fail.**
  Run: `/usr/bin/python3 -B scripts/compound-v-jev.py --selftest` — Expected: FAIL on the old-descriptor row.
  Run: `bash tests/test-jev-core.sh` — Expected: FAIL `contract: vault unavailable(no_key) parsed as 'unavailable upstream'`.

- [ ] **Step 4: Implement.**

```python
UNAVAILABLE_REASONS = ("no_vault", "disabled", "no_key", "egress", "timeout", "rate_limited",
                       "upstream", "credits", "auth")
```

  In `prune`, after the `req`/`resp` candidate loop and its unlink loop, add (with `import stat` at the top if
  absent):

```python
    try:
        names = os.listdir(dd)
    except OSError:
        names = []
    for n in names:
        if not (n.startswith("pending-") and n.endswith(".json")):
            continue
        path = os.path.join(dd, n)
        try:
            st = os.lstat(path)
        except OSError:
            continue
        if stat.S_ISREG(st.st_mode) and st.st_mtime < cutoff:
            with contextlib.suppress(OSError):
                os.unlink(path)
```

  Update `prune`'s docstring: it also removes regular `pending-*.json` descriptors older than the cutoff, and
  never follows or removes a symlink among them.

- [ ] **Step 5: Run both, see them pass, and prove the revert.** Rerun the two commands; expect green. Remove
  `"no_key"` and rerun `tests/test-jev-core.sh` (expect the contract FAIL); drop the new prune block and rerun
  the selftest (expect the prune FAIL); restore both.

- [ ] **Step 6: Update the parent spec.** In
  `docs/superpowers/specs/2026-10-05-jev-classifier-foundation-design.md` lines 68-70, the `unavailable` list
  gains `` `no_key` (no key in the vault) `` and its `auth` entry reads `` `auth` (HTTP 401: rejected or
  disabled key; HTTP 403: insufficient permissions, guardrail block or moderation flag) ``. Line 219 becomes
  `| Key missing or lost from secure storage | `unavailable(no_key)`; status line says so |`, and the
  `402 / 401 / 403` row keeps `auth` for 401/403. Then
  `grep -rn "unavailable(auth)" docs/ skills/` must show no line that names a missing key.
  Run: `/usr/bin/python3 -B scripts/lint-frontmatter.py .` — Expected: clean.

- [ ] **Step 7: Commit.** `git commit -m "Keep the vault's no_key reason through parse and prune stale T3 descriptors" -- scripts/compound-v-jev.py tests/test-jev-core.sh docs/superpowers/specs/2026-10-05-jev-classifier-foundation-design.md`

---

### Task R: Review Gate (`spec-review`)

Three passes against `docs/superpowers/specs/2026-10-05-jev-review-fixes-design.md` (amendments first) and
AC-1..AC-5, written to `docs/superpowers/dogfood/2026-10-05-jev-review-fixes-review.md` with sections
`## Recall`, `## SPEC`, `## QUALITY`, `## INTEGRATION`, `## Verdict`. Each AC is run on the merged tree with its
command and output quoted, including: the reviewer's original probe from the parent review (Issue 1), a
`no_key` response through `parse`, `git diff <base> -- plugins/compound-v-vault/hooks/vault.tsx hooks/jev-t3.tsx`
empty, and the manifest's full test command. Verdict APPROVED or ISSUES with a numbered list.

## Self-review

- Spec coverage: Issue 1 + amendments 1-6 + test → Task A; Issue 2 + both parent-spec places + contract shape →
  Task B steps 1, 4, 6; Issue 3 + exact rule + `listdir` guard → Task B steps 2, 4; residuals → Task A step 3/5
  docstring and doc text, and Task R. AC-5 → Task R.
- Names used across tasks: `_secret_named`, `_has_credential_assignment`, `UNAVAILABLE_REASONS`, `prune` — each
  defined in its own task; no task consumes another task's code.
