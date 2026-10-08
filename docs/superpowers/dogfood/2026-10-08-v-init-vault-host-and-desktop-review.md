# Review Gate — run 2026-10-08-v-init-vault-host-and-desktop

FINAL INTEGRATION, one implementation job (`host-desktop`, wave commit `d0fb32c`, baseline `4b876c0`), reviewed on the
merged tree at `e67a93d`. Reviewer job `spec-review`, `direct` isolation. Every mutation below ran in a `git archive`
copy of HEAD under the session scratchpad, never in the checkout.

## Recall

- The V-memory block in the job prompt carried eight hits. The two that bear on this run: the 2026-10-05 vault review
  (`docs/superpowers/dogfood/2026-10-05-vault-optional-via-init-review.md`), whose filtered-probe row this run must keep
  green, and `docs/superpowers/research/2026-10-05-jev-next-stage.md` ("Finding from the first live attempt",
  "Confirmed by the maintainer"), the source of the desktop defect. Both re-read against the tree; the probe row is
  unchanged (see QUALITY).
- `compound-v-memory.py recall-check --files commands/v-init.md plugins/compound-v-vault/README.md tests/test-vault-mod.sh`:

  ```
  recall-check: none (1/2 match on commands/v-init.md, plugins/compound-v-vault/README.md, tests/test-vault-mod.sh)
    not counted (not attributable to a job's own work): harness_fault 5, pipeline_bookkeeping 3, recall_exclude 3, test_timeout 1, unattributed 3
  ```

  No escalation.
- Own memory leads, re-verified here rather than trusted: "run the AC, do not read the selftest", "a mutation must hit
  the code it names", "read the audits' section 7 MUSTs". The second one paid off in this run (see AC-2, M1).

### Live environment capture (cited per the plan's Global Constraints and library-audit MUST-7)

The plan records the desktop capture of 2026-10-08: `CLAUDE_CODE_ENTRYPOINT=claude-desktop`,
`CLAUDE_CODE_EXECPATH=~/Library/Application Support/Claude/claude-code/2.1.293/<hash>/claude.app/Contents/MacOS/claude`,
whose `--version` prints `2.1.293 (Claude Code)`; terminal transcripts record `entrypoint: cli`.

This review job itself ran in a desktop Code-tab session, which gave an independent second capture. The step-1g
host-version block, extracted from `commands/v-init.md` and run with `CV` set to the checkout, and the step-1g desktop
probe printed:

```
=== live host block (this session; prints version + source only)
2.1.293 host
=== desktop probe (this session)
desktop
entrypoint=claude-desktop
```

Terminal side: a count of the `entrypoint` field over this project's session transcripts (values only, no content):

```
4820 "entrypoint":"claude-desktop"
  71 "entrypoint":"cli"
```

No terminal Bash `printenv` capture was taken; the terminal side rests on transcript records, which is what the plan
settled for. See SPEC, library-audit MUST-7.

## SPEC

### Scope

Gate receipt `receipts/host-desktop.gate.json` / `results/host-desktop.json`: verdict `pass`, `changed` =
`commands/v-init.md`, `plugins/compound-v-vault/README.md`, `tests/test-vault-mod.sh`, all three in `write_allowed`,
`violations: []`. `git show --stat d0fb32c` lists the same three files. No scope leak at the seam.

### Spec coverage

| Requirement (spec "Change" + plan Global Constraints) | Implemented in | Status |
|---|---|---|
| One fenced host-version block in 1g, marker `# cv-host-version` | `commands/v-init.md:330-342` | ✅ |
| `"$CLAUDE_CODE_EXECPATH" --version` only after `[ -x ]`, `</dev/null`, under `compound-v-run-with-timeout.py --timeout 5 --` | `commands/v-init.md:333-336` (`[ -n ] && [ -f ] && [ -x ]`) | ✅ |
| First anchored `x.y.z`, else `claude --version` (same timeout), else `unknown` | `commands/v-init.md:334,337-341` | ✅ |
| Prints `<x.y.z> host`, `<x.y.z> path` or `unknown` | `commands/v-init.md:341`; live run `2.1.293 host` | ✅ |
| Version never taken from the directory name; block never reads `plugin configure` | `commands/v-init.md:344-348`; block contains 0 `plugin configure`/`inputs` lines | ✅ |
| `unknown` never passes the floor; state `installed, host version unknown (...)` | `commands/v-init.md:350-352,378` | ✅ |
| Desktop only on the exact `claude-desktop`, own one-line probe printing a fixed token | `commands/v-init.md:315-325` | ✅ |
| Desktop state text verbatim, worded as observed and dated | `commands/v-init.md:321-325,377` | ✅ |
| No `CLAUDECODE` / `CLAUDE_CODE_CHILD_SESSION`, no gist cited | grep of 1g: none | ✅ |
| State order: absent, disabled, desktop, unknown, below floor, key not set/unknown, key set; key probe skipped on desktop | `commands/v-init.md:372-385`, `:321-322` | ✅ |
| Stale "one of three states" intro fixed | `commands/v-init.md:298-299` | ✅ |
| Step 2 vault bullet: desktop host gets "run it in a terminal `claude`", not in-place `/plugin configure` | `commands/v-init.md:401,409-411` | ✅ |
| Restart note everywhere the key is entered or changed | 1g key-set state `:381-384`; Step 2 `:408-409`; README `:26-27` | ✅ |
| Step 1f `/skill-doctor` floor reads the 1g host block; `unknown` skips | `commands/v-init.md:252-258` | ✅ |
| README: one dated desktop sentence, one restart sentence | `plugins/compound-v-vault/README.md:26-27,30-31` | ✅ |
| Test row 1 (host block, stubs, explicit env) and row 2 (states, floor paragraph, 1f, Step 2, README) | `tests/test-vault-mod.sh:146-242` (row 1 `:146-188`, row 2 `:189-242`) | ✅ |
| `hooks/session-banner.sh:84` left alone, recorded as follow-up | not in the diff; follow-up recorded below | ✅ |
| No version bump, CHANGELOG or release | `git diff --stat 4b876c0..HEAD -- CHANGELOG.md .claude-plugin plugins/compound-v-vault/.claude-plugin` empty | ✅ |

The spec's Change 1 says the block "prints only the `x.y.z`"; the plan's Global Constraints (binding, later) require
`<x.y.z> <source>`. The implementation and test follow the plan. Not a gap: the spec line is superseded.

### Audit constraints

| Audit | Constraint | Status | Evidence |
|---|---|---|---|
| Archaeology 7.1 | define `unknown`, must not pass the floor | ✅ | `:350-352,378` |
| Archaeology 7.2 | entrypoint read in its own one-line block printing a fixed token | ✅ | `:317-319` |
| Archaeology 7.3 | the `claude-desktop` value captured, not assumed | ✅ | plan capture + this session's capture (Recall) |
| Archaeology 7.4 | quoted path, `-x`, `</dev/null`, anchored parse, `unknown`, no `inputs`/`plugin configure` | ✅ | block; grep count 0 |
| Archaeology 7.5 | keep `2.1.287`, `/egress allow`, `/plugin enable`, `disabled:`, filtered probe | ✅ | existing row PASS on M0 |
| Archaeology 7.6 | row 1 under `env -i`; non-executable and no-`x.y.z` cases | ✅ | `tests/test-vault-mod.sh:167-186` (also directory and empty cases) |
| Archaeology 7.7 | row 2 scoped to the floor paragraph | ✅ | M5 below |
| Archaeology 7.8 | reword the 1g intro | ✅ | `:298-299` |
| Archaeology 7.9 | Step 2: no `/plugin configure` remedy for desktop; restart sentence there | ✅ | M7 below |
| Archaeology 7.10 | decide 1f and `session-banner.sh:84` | ✅ | 1f in scope; banner named out of scope in the plan |
| Archaeology 7.11 | CI-CLI selectors in `tests/test-*-mod.sh` unchanged | ✅ | `tests/test-vault-mod.sh:1-145` identical to `4b876c0` |
| Archaeology 7.12 | README sentences under Setup, test substring fixed | ✅ | README `:26-31`; row 2 keys on `desktop`+`2026-10-08`+`terminal`, `restart`+`key` |
| Library MUST-1 | both variables undocumented, never fail | ✅ | `:325,344-348`; row 1 unset/empty/directory cases |
| Library MUST-2 | `-x` and a timeout on the host binary | ✅ | `:333-334` |
| Library MUST-3 | anchored `x.y.z` "from the first line of output"; `unknown` defined for the floor | ✅ met per the plan | the plan's Global Constraint (plan lines 23-25, "take the first anchored `x.y.z`") is the binding, later document and supersedes the audit's "first line" wording; the block follows it (`grep -oE '^[0-9]+\.[0-9]+\.[0-9]+' \| head -n 1`, the first line that starts with a version). `unknown` is defined for the floor at `:350-352`. Not blocking |
| Library MUST-4 | stubs `N.N.N (Claude Code)` plus a no-version stub | ✅ | `tests/test-vault-mod.sh:160-164` |
| Library MUST-5 | desktop worded as observed; key probe unrun there | ✅ | `:321-325` |
| Library MUST-6 | filtered probe unchanged; host block never touches `plugin configure` | ✅ | probe block identical to `4b876c0`; grep count 0 |
| Library MUST-7 | live capture, desktop and terminal, cited in the dogfood record | ✅ met per the plan | desktop: two captures, the plan's and this session's (Recall). Terminal: this review ran in a `claude-desktop` session, so it cannot take a terminal `printenv`; the plan (line 22) settled for transcript records, confirmed by the `entrypoint` count in Recall. Not blocking: both block branches are stub-tested, so the unobserved terminal `CLAUDE_CODE_EXECPATH` value changes no behaviour. The missing observation is follow-up 3 |
| Library MUST NOT-1 | no `CLAUDECODE` / `CLAUDE_CODE_CHILD_SESSION` | ✅ | M6 below |
| Library MUST NOT-2 | no gist as the contract | ✅ | grep of 1g: none |
| Library MUST NOT-3 | version never parsed from the directory name | ✅ | `:347-348` |

### Job acceptance

| Item | Evidence | Status |
|---|---|---|
| test-vault-mod.sh green with both new rows | M0: `18 passed, 0 failed` | ✅ |
| each new row fails when its change is reverted | M1, M1b, M2-M7 | ✅ |
| lint-frontmatter clean | `✅ All frontmatter clean`, rc=0 | ✅ |
| existing filtered-probe row green | M0 PASS; M8 shows it still guards | ✅ |
| host block run live once, output quoted | Recall: `2.1.293 host` | ✅ |

### Over-build

Clean. The two extra row-1 cases (directory as host, empty host) are test coverage of the "never fails when unset,
empty or malformed" constraint. Nothing in the spec's "Out of scope" (vault code, Phase T, plugin-root resolver,
the Anthropic issue) is touched.

## QUALITY

- **Code quality.** The block is linear and fails closed to `unknown`; `CV_HOST_SRC` is set before the version is known
  but is always overwritten on the fallback path, so the printed source is correct (row 1 covers all seven cases).
  Prose is precise about which binary each command runs (the key probe deliberately stays on `PATH`, `:369-371`).
- **No regression.** `tests/test-vault-mod.sh:1-145` is byte-identical to the baseline; the filtered `configure` probe
  block is byte-identical to the baseline. The diff is additive in the test file.
- **Test alignment / mutation results.** Every MUST above has a row that moves when it breaks. Each mutation ran on its
  own `git archive HEAD` copy with the full `tests/test-vault-mod.sh`:

  | Mutation | Row that moved | Result |
  |---|---|---|
  | M0 unmodified | none | `18 passed, 0 failed`, rc=0 |
  | M1 host block body replaced by plain `claude --version` (marker kept) | row 1 | `FAIL v-init 1g host-version block: host stub gave '2.1.289 (Claude Code)'; unset gave '2.1.289 (Claude Code)'; ...; no version anywhere gave 'Claude Code'; ...` |
  | M1b only `"$CLAUDE_CODE_EXECPATH" --version` swapped for `claude --version` | row 1 | `FAIL v-init 1g host-version block: host stub gave '2.1.289 host'; versionless host gave '2.1.289 host'` |
  | M2 desktop state removed from the list | row 2 | `FAIL v-init 1g desktop/restart: no desktop-inert state` |
  | M3 README desktop sentence removed | row 2 | `FAIL ...: README has no dated desktop sentence` |
  | M4 README restart sentence removed | row 2 | `FAIL ...: README has no restart sentence` |
  | M5 1g floor paragraph back to `claude --version` | row 2 | `FAIL ...: the 1g floor paragraph does not read the host block` |
  | M6 desktop probe gated on `CLAUDECODE` | row 2 | `FAIL ...: 1g reads CLAUDECODE` |
  | M7 Step 2 desktop note removed | row 2 | `FAIL ...: Step 2 vault bullet lacks the desktop or restart note` |
  | M8 key probe unfiltered | existing row | `FAIL v-init 1g: configure probe not filtered` |

  A first M1 attempt anchored on the marker text alone and hit the 1f prose that names the marker
  ("the fenced block that starts `# cv-host-version`"), mutating prose instead of the block; all rows stayed green. It
  was a broken mutation, not a gap: re-anchored on the fence (```` ```bash\n# cv-host-version ````) it fails as shown.
- **No fabricated metrics.** None. The only numbers added are observed versions and the observation date.
- **No reward-hacking.** No assertion removed, loosened or skipped; the pre-existing rows are unchanged.

## INTEGRATION

- **Partition / seams.** One implementation job, no Task 0, no shared file: nothing can leak at a seam.
- **Tests the tier owes.** `triage.tier: FULL` with a declared `impacted_map`, so the derived default applies. Each
  changed path matches a rule: `commands/v-init.md` → `commands/*.md`; `plugins/compound-v-vault/README.md` →
  `plugins/compound-v-vault/**` (and `*.md`); `tests/test-vault-mod.sh` → itself. No unmapped path, so `full_command`
  is not owed by the job. The job's `tests.command` lists the floor and the three rule commands it resolved, `exit_code`
  0, `scope: impacted`, `selected_count: 3`. The `*.md` rule's own command (`lint-frontmatter.py .`) is contained in
  the `commands/*.md` rule's command, and I ran it independently (AC-4).
- **Where the commands ran.** Every command in this review ran on `git archive HEAD` (`e67a93d`), the merged tree's
  content, extracted under the session scratchpad: a direct-isolation reviewer that ran the suites in the checkout would
  leave files there for the scope gate to charge to it. Scripts: `/private/tmp/claude-501/-Users-koristuvac-compound-superpowers-v--claude-worktrees-practical-nightingale-b06689/f84cc98b-e3e7-46fd-8520-473e7d7661f2/scratchpad/mutate.sh` (M0, M1b-M8, AC-4, live block),
  `/private/tmp/claude-501/-Users-koristuvac-compound-superpowers-v--claude-worktrees-practical-nightingale-b06689/f84cc98b-e3e7-46fd-8520-473e7d7661f2/scratchpad/mutate2.sh` (M1), `/private/tmp/claude-501/-Users-koristuvac-compound-superpowers-v--claude-worktrees-practical-nightingale-b06689/f84cc98b-e3e7-46fd-8520-473e7d7661f2/scratchpad/full.sh` (full suite).
- **Run-level full suite.** The manifest's `full_command`, verbatim, on a `git archive HEAD` copy (with a one-commit
  `git init` so git-reading tests have a repository):

  ```
  all-tests-ok
  rc=0 wall=323s
  ```

  Build green. (`wall` is a measured `date +%s` difference, the only number here.)

### Acceptance criteria, run on the merged tree

| AC | Command | Output | Status |
|---|---|---|---|
| AC-1 `tests/test-vault-mod.sh` passes, both new rows | `bash tests/test-vault-mod.sh` (M0 copy of HEAD) | `PASS v-init 1g host-version block: host first, PATH fallback, unknown` / `PASS v-init 1g: desktop and host-unknown states, host floor (1g, 1f), restart; README desktop and restart` / `tests/test-vault-mod.sh: 18 passed, 0 failed` | ✅ |
| AC-2 reverting the host block fails row 1; removing the desktop state or either README sentence fails row 2 | M1, M1b, M2, M3, M4 (each on its own copy) | M1b: `FAIL v-init 1g host-version block: host stub gave '2.1.289 host'; versionless host gave '2.1.289 host'`; M2: `FAIL v-init 1g desktop/restart: no desktop-inert state`; M3: `... README has no dated desktop sentence`; M4: `... README has no restart sentence`; M1 full excerpt in QUALITY | ✅ |
| AC-3 1g never reads, prints, requests or forwards the key value | existing row + M8; grep of the host block | `PASS v-init 1g: filtered probes, egress, 2.1.287, disabled and probed id covered`; M8 → `FAIL v-init 1g: configure probe not filtered`; host block has 0 `plugin configure`/`inputs` lines; the desktop probe prints only `desktop`/`not-desktop` | ✅ |
| AC-4 `scripts/lint-frontmatter.py .` passes | `/usr/bin/python3 -B scripts/lint-frontmatter.py .` | `✅ All frontmatter clean`, rc=0 | ✅ |

### Follow-ups (not defects of this run)

1. `hooks/session-banner.sh:84` reads the floor the same way 1g used to; out of this run's lanes per the plan's Global
   Constraints. Recorded here as the follow-up the plan asks for.
2. The engine-authored wave and bookkeeping commit subjects (`compound-v: wave 1 of run ...`,
   `bookkeeping(...): wave 1 finalized`) carry prefixes that the "plain sentence" commit rule forbids. The job did
   not author them; this is a pipeline matter for the orchestrator, not a finding against `host-desktop`.
3. No terminal-side `printenv | grep -E '^CLAUDE_CODE_(ENTRYPOINT|EXECPATH)='` capture exists yet (library-audit MUST-7);
   take one in a terminal `claude` and append it to this record.

## Verdict

**APPROVED.**

- PASS 1 SPEC: 18/18 requirements; archaeology 12/12 and library-audit 10/10 constraints (MUST-3 and MUST-7 met as
  the plan reconciled them); over-build clean; job acceptance 5/5.
- PASS 2 QUALITY: no regression (pre-existing rows and the filtered probe byte-identical to the baseline); every MUST
  has a row that moves under mutation (M1-M8); no fabricated metrics; no reward-hacking.
- PASS 3 INTEGRATION: no partition leak (scope gate `pass`, three files, all in lane); floor and impacted commands
  ran with exit 0 (`results/host-desktop.json` `tests`); full suite `all-tests-ok`; AC-1..AC-4 4/4.

No numbered issues. Three follow-ups are listed above; none is a defect of this run.
