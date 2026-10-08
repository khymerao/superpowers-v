# Vault Optional via /v:init Implementation Plan

> **For agentic workers:** executed by Compound V on Engine C from one manifest
> (`docs/superpowers/execution/2026-10-05-vault-optional-via-init/manifest.yaml`). Steps use checkbox (`- [ ]`) syntax.

**Goal:** Make `compound-v-vault` installable from the `procoders` marketplace and offered by `/v:init`, as an optional
plugin, with correct key instructions.

**Architecture:** One implementation job (manifest entry, `/v:init` step, two READMEs, a stale comment, test rows), then a
deep review and a same-family second opinion (SCOPED+, no Codex on this machine).

**Tech Stack:** JSON manifests, Markdown command prose, bash tests.

**Spec:** `docs/superpowers/specs/2026-10-05-vault-optional-via-init-design.md`. Constraint sources: the pre-flight audits of the
superseded dependency design, `docs/superpowers/{archaeology,expert,library-audit}/2026-10-05-2026-10-05-vault-as-dependency-design.md`.

## Global Constraints

- No `dependencies` field in `superpowers-v`'s `.claude-plugin/plugin.json`.
- The marketplace entry's `version` is byte-equal to `plugins/compound-v-vault/.claude-plugin/plugin.json` `version` (`0.1.0`).
- Never tell users to set the key in `/config`; the documented path is `/plugin configure compound-v-vault@procoders`.
- `/v:init` never reads, prints, requests or forwards the key value; the user types it into Claude Code's own masked field.
- No version bump, CHANGELOG or release.
- Docs: plain words, every claim true of HEAD, no line over 200 characters outside code/tables.
- Lane discipline; `register-lane` first, with a literal `--cwd`. Commit subjects are plain sentences, no Co-Authored-By trailer.

## Review Focus

- A marketplace entry whose version drifts from the vault's own `plugin.json` (warns on validate, fails `--strict`): pinned by a test row.
- `claude plugin validate .` absorbing the nested vault into `superpowers-v`: `tests/test-jev-t3-mod.sh` must stay green.
- A `/v:init` probe that prints the configure output raw could echo option values: the step parses `set`/`not set` only.
- Users on Claude Code below 2.1.287: the README and `/v:init` say the vault needs 2.1.287 and `/plugin configure` needs 2.1.285.
- A `superpowers-v` `dependencies` entry reintroduced later: pinned by a test row.

---

### Task A: Optional vault, offered by /v:init (`vault-optional`)

**Files:** `.claude-plugin/marketplace.json`, `commands/v-init.md`, `plugins/compound-v-vault/README.md`, `README.md`,
`hooks/jev-t3.tsx` (comment only, ~`:113`), `tests/test-vault-mod.sh`.

- [ ] **Step 1: Failing rows** at the end of `tests/test-vault-mod.sh`, before the summary line:

```bash
# Optional vault: the marketplace lists it, in lockstep with its own manifest; superpowers-v does not depend on it.
mk_check="$(python3 - "$REPO_ROOT" <<'PY'
import json, os, sys
root = sys.argv[1]
mk = json.load(open(os.path.join(root, ".claude-plugin", "marketplace.json")))
entry = next((p for p in mk.get("plugins", []) if p.get("name") == "compound-v-vault"), None)
if entry is None:
    print("no marketplace entry"); raise SystemExit
src = os.path.normpath(os.path.join(root, entry.get("source", "")))
mf = os.path.join(src, ".claude-plugin", "plugin.json")
if not os.path.isfile(mf):
    print("source has no plugin.json"); raise SystemExit
pj = json.load(open(mf))
if pj.get("name") != entry.get("name") or pj.get("version") != entry.get("version"):
    print("name/version mismatch"); raise SystemExit
sv = json.load(open(os.path.join(root, ".claude-plugin", "plugin.json")))
deps = json.dumps(sv.get("dependencies", []))
print("ok" if "compound-v-vault" not in deps else "superpowers-v depends on the vault")
PY
)"
if [ "$mk_check" = ok ]; then ok "marketplace lists the vault in lockstep; superpowers-v does not depend on it"; else bad "vault marketplace entry: $mk_check"; fi
if grep -nE '`/config`' "$PLUGIN/README.md" | grep -qiE 'key|set|fill'; then bad "vault README still sends the key to /config"; else ok "vault README does not send the key to /config"; fi
```

  (`REPO_ROOT` is the repository root as the test computes it; reuse the variable the file already defines, or define
  `REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"` near the top.)
- [ ] **Step 2:** `bash tests/test-vault-mod.sh` → the two new rows FAIL.
- [ ] **Step 3: Marketplace.** Add to `.claude-plugin/marketplace.json` `plugins`, after `superpowers-v`:

```json
    {
      "name": "compound-v-vault",
      "description": "Optional key holder for Compound V's Jev classifier: keeps the OpenRouter key in secure storage and is the only program that calls Jev. Inert without a key. Needs Claude Code 2.1.287 or newer.",
      "version": "0.1.0",
      "source": "./plugins/compound-v-vault",
      "author": {"name": "Oleg", "email": "copeus@gmail.com"}
    }
```
- [ ] **Step 4: Vault README § Setup** becomes: (1) `/plugin install compound-v-vault@procoders`, or let `/v:init` offer it;
  (2) set the key with `/plugin configure compound-v-vault@procoders` (Claude Code 2.1.285 or newer; the install dialog
  may also ask) — it is not listed in `/config`, by design, because sensitive options never are; (3) `/egress allow` in
  each repository. Keep the requirement line (2.1.287) and the dedicated-key advice.
- [ ] **Step 5: Root README § Install**, after the code block:
  "**Jev is optional.** The `compound-v-vault` plugin holds an OpenRouter key for Jev, TypeSafe's System One classifier;
  without it nothing changes. `/v:init` offers it: `/plugin install compound-v-vault@procoders`, then
  `/plugin configure compound-v-vault@procoders` to set the key, then `/egress allow` in each repository."
- [ ] **Step 6: `/v:init`.** In `commands/v-init.md` Step 1 add `### 1g. Jev vault (optional)`:

```bash
claude plugin list --json | python3 -c '
import json, sys
d = json.load(sys.stdin)
v = [p for p in d if str(p.get("id", "")).startswith("compound-v-vault@") and p.get("enabled")]
print(v[0]["id"] if v else "absent")'
```

  then, only when an id was printed, read the key state without its value:

```bash
claude plugin configure "<id>" --json | python3 -c '
import json, sys
d = json.load(sys.stdin)
opts = d.get("options", d) if isinstance(d, dict) else {}
o = opts.get("openrouter_key") if isinstance(opts, dict) else None
print("set" if isinstance(o, dict) and o.get("set") else "not set")'
```

  (Read the real `--json` shape once on this machine and match it exactly; print only `set`/`not set`, never a value.)
  Report: `absent` / `installed, key not set` / `ready`. In Step 2 add the item: vault absent or key not set and the user
  wants Jev → `/plugin install compound-v-vault@procoders` (needs Claude Code 2.1.287), then
  `/plugin configure compound-v-vault@procoders`, then `/egress allow`; re-probe after each; never ask for the key in chat
  or pass it on a command line; declining leaves Jev off and changes nothing else.
- [ ] **Step 7: Comment.** `hooks/jev-t3.tsx` ~`:113`: `/compound-v-vault:egress allow` → `/egress allow`.
- [ ] **Step 8: Verify.** `bash tests/test-vault-mod.sh`, `bash tests/test-jev-t3-mod.sh`, `bash tests/test-run-band-mod.sh`,
  `claude plugin validate .`, `claude plugin validate plugins/compound-v-vault`, `/usr/bin/python3 -B scripts/lint-frontmatter.py .`.
  Prove the revert: remove the marketplace entry → the lockstep row fails; restore.
- [ ] **Step 9: Commit.** `git commit -m "Offer compound-v-vault as an optional plugin from the marketplace and /v:init" -- <the six files>`

### Task R: Review (`spec-review`) — deep, three passes, against the spec and AC-1..AC-4, written to
`docs/superpowers/dogfood/2026-10-05-vault-optional-via-init-review.md`.
