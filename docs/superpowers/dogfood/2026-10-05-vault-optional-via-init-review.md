# Review Gate: run 2026-10-05-vault-optional-via-init

Reviewer: `superpowers-v:spec-reviewer`, job `spec-review`, direct isolation, baseline pinned at `a5a13f1`.
Reviewed change: `git diff 99bbb4b 414404e` (job `vault-optional`, six files, 89 insertions, 4 deletions).
Spec: `docs/superpowers/specs/2026-10-05-vault-optional-via-init-design.md`.
Plan: `docs/superpowers/plans/2026-10-05-vault-optional-via-init.md`.

Every AC was run on the merged tree, in a scratch `git clone` of the checkout at `a5a13f1`, so the reviewer's own
runs could not leave files in the project checkout. The checkout's untracked `tsconfig.json` files are not in the
clone; the merged tree is what was committed.

## Recall

- The job prompt carried a V-memory block (eight rows: the spec, the three audits of the superseded dependency
  design). The audits were read at their Design Constraints sections; the table under SPEC records each MUST.
- Recall bridge, over the six changed files:

```
$ python3 -B scripts/compound-v-memory.py recall-check --files .claude-plugin/marketplace.json commands/v-init.md \
    README.md plugins/compound-v-vault/README.md hooks/jev-t3.tsx tests/test-vault-mod.sh
recall-check: none (1/2 match on ...)
  not counted (not attributable to a job's own work): harness_fault 5, pipeline_bookkeeping 3, recall_exclude 3,
  test_timeout 1, unattributed 3
```

  Verdict `none`: no repeated job-attributed failure on these paths, nothing to tighten.
- Reviewer memory: the "run doc-embedded code verbatim" and "mutate in a scratch clone" leads were applied
  (extracted the two `bash` fences of `/v:init` 1g and ran them; mutated in a clone). No directive was found in memory.

## SPEC

### Scope

Scope gate receipt (`receipts/vault-optional.gate.json`, `results/vault-optional.json`): verdict `pass`,
`violations: []`. Changed files are exactly the six in `write_allowed`. Confirmed against `git show --stat 414404e`.

### Spec coverage

| Spec requirement | Implemented in | Status |
|---|---|---|
| Marketplace lists `compound-v-vault`, `source` `./plugins/compound-v-vault`, name and version equal to the vault `plugin.json`, one-line description | `.claude-plugin/marketplace.json:18-28` | ✅ |
| `superpowers-v` `plugin.json` gains no `dependencies` | file untouched; `"dependencies" in plugin.json` is `False` | ✅ |
| `/v:init` Step 1 "Jev vault (optional)" reads `claude plugin list --json`, finds an enabled `compound-v-vault@` id | `commands/v-init.md:296-312` | ✅ |
| When installed, `claude plugin configure <id> --json` reports whether `openrouter_key` is set, never the value | `commands/v-init.md:314-329` | ✅ |
| Step 2 item: install, then configure, then `/egress allow`, re-probe after each, never in chat or on a command line, declining changes nothing | `commands/v-init.md:349-354` | ✅ |
| Vault README Setup: install line, `/plugin configure ...@procoders` (2.1.285), install dialog "may" ask, not in `/config` by design, `/egress allow`; 2.1.287 requirement kept | `plugins/compound-v-vault/README.md:14-26` | ✅ |
| Root README: one short paragraph, Jev optional, separate plugin, `/v:init` offers it | `README.md:21-23` | ✅ |
| Stale `/compound-v-vault:egress` comment becomes `/egress` | `hooks/jev-t3.tsx:115` | ✅ |
| Test rows: marketplace entry + source `plugin.json` + name/version equality; no dependency; README not sending the key to `/config` | `tests/test-vault-mod.sh:87-107` | ✅ |

9/9.

### Audit constraints

The spec says the audits of the superseded dependency design "stand as constraints here". Several of their MUSTs
exist only because the vault was going to be a hard dependency; those are marked N/A, not dropped.

| Audit | Constraint | Status | Notes |
|---|---|---|---|
| Expert 1 | Both READMEs say the vault must stay enabled while superpowers-v is | N/A | dependency-design only; under the optional design disabling the vault is allowed |
| Expert 2 | `/plugin configure compound-v-vault@procoders` (qualified) is the primary documented way; install dialog only as "may" | ✅ | vault README:22-23; root README:22 |
| Expert 2 (second half) | also give the shell `--values-stdin` form and say shell `claude plugin install` never prompts | not done; spec governs | spec change 3 enumerates Setup's content and omits it; the plan's Step 4 repeats that list. The spec postdates the audit; see observation 3 |
| Expert 3 | dev-flow line loading both plugins | N/A | dependency-design only: without a dependency superpowers-v loads alone |
| Expert 4 | root README true only for installs that get the new manifest | N/A | that wording was about auto-installed dependencies; the new paragraph tells the user to install it |
| Expert 5 / Library | entry `version` absent or byte-equal to `0.1.0` | ✅ | `"version": "0.1.0"`, both sides; guarded by a test row |
| Expert 6, 7 | AC-3 install observation in a scratch `CLAUDE_CONFIG_DIR` | N/A | that AC-3 belonged to the dependency design |
| Expert 8 | run `tests/test-run-band-mod.sh` and `tests/test-jev-t3-mod.sh` after the change | ✅ | job ran both; reviewer re-ran jev-t3 (AC-1) and both inside the full command (AC-4) |
| Expert 9, 10, 11 | prune docs, bare-string dependency, no cross-marketplace allowlist | N/A | no dependency exists |
| Library | entry `name` exactly `compound-v-vault`, `source` starting `./` | ✅ | |
| Library | document 2.1.285 for configure and 2.1.287 for Jev | ✅ | vault README:15,23; `/v:init`:329,350-351; root README:22 (2.1.287) |
| Library | test row fails on name mismatch | ✅ | `pj.get("name") != entry.get("name")` |
| Library MUST NOT | install dialog stated as fact | ✅ | "the install dialog may also ask for it" |
| Library MUST NOT | `userConfig` added to superpowers-v | ✅ | `plugin.json` untouched |
| Library MUST NOT / global | tell users to look for the key in `/config` | ✅ | only mentions say it is not there |

### Job acceptance

| Job acceptance item | Evidence | Status |
|---|---|---|
| test-vault-mod.sh green with the lockstep and README rows, each failing when reverted | AC-2 below | ✅ |
| test-jev-t3-mod.sh and test-run-band-mod.sh green | AC-1 below; AC-4 below | ✅ |
| both plugin validations pass | AC-1 below | ✅ |
| lint-frontmatter clean | AC-3 below | ✅ |
| the `/v:init` step prints only absent / key-set state, never a value | AC-3 below | ✅ |

### Over-build

The implemented probes differ from the plan's snippets: `2>/dev/null`, try/except around `json.load`, an
`isinstance(p, dict)` guard, a read of `configured` instead of `options.openrouter_key.set`, and a fourth state
`installed, key state unknown`. Plan Step 6 says "Read the real `--json` shape once on this machine and match it
exactly", and its Review Focus names users below 2.1.285/2.1.287. The real shape (below) has no `options` object, so
the plan's snippet would have always printed `not set`; the deviation is the plan's own instruction. Not over-build.
The test row adds `-B` to `python3`, per the run's global rule. Nothing else beyond the spec.

## QUALITY

### Key safety of the `/v:init` step (AC-3 focus)

Real `claude plugin configure compound-v-vault@cv-dev --json` shape on Claude Code 2.1.289, printed with every
scalar replaced by its type (no value was printed):

```
{"pluginId": "<str>", "displayName": "<str>",
 "schema": {"openrouter_key": {"type","title","description","sensitive": "<bool>"}, "route": {...}},
 "inputs": {"openrouter_key": "<str>", "route": "<str>"},
 "choices": {}, "configured": ["openrouter_key"], "unconfigured": ["route"]}
```

A boolean-only probe of `inputs.openrouter_key`:

```
inputs.openrouter_key looks masked: True | equal-to-sentinel-like: True
```

So the CLI already masks the sensitive input, and the step's filter reads only `configured`, a list of option names,
and prints only `set`, `not set` or `unknown`. It never asks for the key, never passes it on a command line, and the
Step 2 item sends the user to Claude Code's masked field. The text also tells the agent never to run the command
unfiltered and never to read `inputs`.

The two fenced blocks of section 1g, extracted from `commands/v-init.md` and run verbatim:

```
== probe 1 (verbatim block)
compound-v-vault@cv-dev
== probe 2 (verbatim block, <id> = probe 1 output)
set
== probe 2, bogus id (CLI error path)
unknown
== probe 1, CLI emitting garbage
absent
```

### Regression

`hooks/jev-t3.tsx` changed one comment line only. The root validate's single warning (`CLAUDE.md at the plugin
root is not loaded`) is identical at the baseline `99bbb4b`; the marketplace entry adds no warning.
Job test evidence (`results/vault-optional.json`): four commands, `exit_code: 0`, `scope: impacted`.

### Test alignment

| MUST | Guard | Status |
|---|---|---|
| marketplace entry present, name/version lockstep | `tests/test-vault-mod.sh` mk_check row | ✅ (AC-2) |
| no superpowers-v dependency on the vault | same row | ✅ (AC-2) |
| vault README does not send the key to `/config` | README grep row | ✅ (AC-2) |
| `/v:init` never prints the key | none automated | review-only, as the spec assigns it (AC-3); observation 1 |

### Fabricated metrics, reward hacking

No number is printed or claimed. No assertion, threshold, scorer or test was removed, skipped or loosened; the test
file only gains rows. §2.6 does not apply (not a marathon blocker).

## INTEGRATION

Single implementation job; no partition seam. The tier-owed tests were derived from the manifest, not taken from
the worker: every changed path matches at least one `impacted_map` rule (`marketplace.json`, `commands/*.md`,
`*.md`, `hooks/*.tsx`, `plugins/compound-v-vault/**`, `tests/test-vault-mod.sh`), and their union is exactly the
four commands the job reported. No unmapped path, so SCOPED owed no `full_command` at job level; AC-4 asks for it
at run level and it was run below.

### AC-1

```
$ claude plugin validate .
  ❯ root: CLAUDE.md at the plugin root is not loaded as project context. ...   (same warning at baseline 99bbb4b)
✔ Validation passed with warnings
exit=0
$ claude plugin validate plugins/compound-v-vault
✔ Validation passed
exit=0
$ bash tests/test-jev-t3-mod.sh
PASS plugin test:  16 pass
PASS plugin test ran hooks/jev-t3.test.tsx
PASS the vault's tests are not run as this plugin's
tests/test-jev-t3-mod.sh: 14 passed, 0 failed
exit=0
```

### AC-2

```
== HEAD unmodified
PASS marketplace lists the vault in lockstep; superpowers-v does not depend on it
PASS vault README does not send the key to /config
tests/test-vault-mod.sh: 15 passed, 0 failed
exit=0
== entry removed
FAIL vault marketplace entry: no marketplace entry
tests/test-vault-mod.sh: 14 passed, 1 failed
exit=1
== entry version 0.1.0 -> 0.1.1
FAIL vault marketplace entry: name/version mismatch
tests/test-vault-mod.sh: 14 passed, 1 failed
exit=1
== superpowers-v dependencies added
FAIL vault marketplace entry: superpowers-v depends on the vault
tests/test-vault-mod.sh: 14 passed, 1 failed
exit=1
== vault README reverted to /config text (git show 99bbb4b:plugins/compound-v-vault/README.md)
FAIL vault README still sends the key to /config
tests/test-vault-mod.sh: 14 passed, 1 failed
exit=1
```

### AC-3

```
$ /usr/bin/python3 -B scripts/lint-frontmatter.py .
✅ All frontmatter clean
exit=0
```

Plus the key-safety probes under QUALITY. No new line in the three changed docs is over 200 characters (an `awk`
length scan lists only pre-existing lines: `README.md:104,116,121`, `commands/v-init.md:2,722`).

### AC-4

The manifest's `test_contract.full_command`, verbatim, run in the scratch clone at `a5a13f1`:

```
$ bash -c 'for s in scripts/compound-v-*.py; do grep -q -- "--selftest" "$s" || continue; \
    /usr/bin/python3 -B "$s" --selftest >/dev/null 2>&1 || { echo "FAIL $s"; exit 1; }; done; \
    for t in tests/*.sh; do bash "$t" >/dev/null 2>&1 || { echo "FAIL $t"; exit 1; }; done; echo all-tests-ok'
all-tests-ok
exit=0 secs=277
```

(`secs` is wall-clock from `date +%s` around the command.)

### Feature acceptance

| Criterion | Evidence | Status |
|---|---|---|
| AC-1 | both validations exit 0; jev-t3 14/14 | ✅ |
| AC-2 | rows pass; fail on removal, version change, added dependency, README revert | ✅ |
| AC-3 | lint clean; step prints only state words; CLI masks the input anyway | ✅ |
| AC-4 | full command: `all-tests-ok`, exit 0 | ✅ |

## Verdict

**APPROVED.**

- PASS 1 SPEC: ✅ requirements 9/9; applicable audit MUSTs met, dependency-only MUSTs marked N/A; job acceptance
  met; no over-build; scope gate `pass`, confirmed at the seam.
- PASS 2 QUALITY: ✅ the `/v:init` step cannot print or forward the key; no regression; every tested MUST has a row
  that fails when reverted; no fabricated metric; no reward hacking.
- PASS 3 INTEGRATION: ✅ no partition seam; floor and tier-owed impacted set ran with exit 0 (job evidence,
  re-derived from `impacted_map`); full command green; AC 4/4.

Non-blocking observations, ranked:

1. No automated guard for "`/v:init` never prints the key". The spec's Tests section assigns it to review (AC-3), so
   this is not a gap in the job. A future row could check that section 1g keeps the `2>/dev/null | python3` filter
   and that its Python never prints `d` or reads `inputs`.
2. Probe 1 reports an installed but disabled vault as `absent`, and the Step 2 item then says
   `/plugin install`, which would answer that it is already installed. The spec defines "installed" as enabled, so the
   job matches it; a later edit could tell the user to enable it instead.
3. Expert audit MUST 2 also asked for the shell form (`claude plugin configure ... --values-stdin`) and a note that
   a shell `claude plugin install` never prompts. The later spec's Setup list omits both and the job follows the
   spec.
4. The vault README attaches "Claude Code 2.1.285 or newer" to the in-session `/plugin configure`; the expert
   audit (line 148) says the in-session form exists below 2.1.285 and the floor is the shell form's. It is the
   spec's wording, conservative rather than false, and moot because the vault needs 2.1.287.
5. The README `/config` row only catches lines with a backticked `/config` that also contain `key`, `set` or
   `fill`, so a future line using "settings" next to `` `/config` `` would trip it falsely and an unbackticked
   `/config` would slip past. Plan-supplied, works on today's text.
6. The run's commits `414404e` ("compound-v: wave 1 ...") and `a5a13f1` ("bookkeeping(...): ...") use the prefix
   forms the global commit-subject rule forbids. They are written by the Engine C pipeline, not by this job.

## Second opinion findings closed (orchestrator)

The six low findings of the same-family second opinion (`receipts/cross-model.json`) are closed in one follow-up commit:
`/v:init` 1g now reports `disabled` apart from `absent` and offers `/plugin enable <id>`; it reports
`installed, inert (Claude Code < 2.1.287)` below the module floor; `ready` became `installed, key set` with the note that
Jev stays off until `/egress allow`; Step 2 configures the id the probe printed. `tests/test-vault-mod.sh` gained a row
that pins all of this on the step's own text (probes filtered through `2>/dev/null | python3`, no `inputs` in probe
code), red before the change; the README row now fails on a missing README and matches `/config` with or without
backticks. Full test command: `all-tests-ok`.
