# Jev: where spec 1 stopped and what comes next

Handoff for the next session. Branch `feat/jev-classifier-foundation`, PR khymerao/superpowers-v#1.

## Update 2026-10-08: handoff items 1-5 done, Jev live

Every item below ran as its own FULL Compound V change (triage record, pre-flight, plan, manifest, Engine C, three-pass
review) and is merged on the branch. Run directories are under `docs/superpowers/execution/2026-10-08-*`.

| Item | Result | Run(s) |
|---|---|---|
| 1. `jev_classify` refused every call | Fixed: the handler reads `request_file` flat from the `tool.call` event | `2026-10-08-vault-jev-classify-flat-arguments` |
| 2. `/v:init` 1g version and desktop | Fixed: the `cv-host-version` block reads `"$CLAUDE_CODE_EXECPATH" --version`; `CLAUDE_CODE_ENTRYPOINT=claude-desktop` reports the vault inert; README says so; a new key needs a restart | `2026-10-08-v-init-vault-host-and-desktop` |
| 3. Phase T never asked Jev | Fixed: one builder `compound-v-jev.py t3-request` for the hook and Phase T; Phase T records `t3` and runs the shadow step (`jev_classify`, `parse --mode shadow`, `pair`) | `2026-10-08-phase-t-jev-shadow` |
| 4. Plugin-root resolver | Replaced, see ADR 0005: the 38 entry points take `CV="${CLAUDE_PLUGIN_ROOT}"` (harness-substituted, verified live), the project root is `--repo` or the git toplevel, never `__file__` | `2026-10-08-plugin-root-run-a`, `-project-root-run-b`, `-project-root-run-b2` |
| 5. Downstream harness bugs | #1 the run-wide gate now applies `toolchain_artifacts` (one reader in scope-check); #2 triage-outcomes no longer writes into the plugin cache (run B); #3 = item 1; #4 `resolve-model` without `--config` reads `<project>/.claude/compound-v.json` | `2026-10-08-gate-toolchain-and-model-config` |
| new | `detect_ui` was rejected with 400: Noul `criteria` must be `{"true": ..., "false": ...}`; fixed and verified live (`noul: 0.99`) | `2026-10-08-detect-ui-noul-criteria` |

Facts established on 2026-10-08:

- **Live calls work** from a terminal `claude` (2.1.294): 9/9 `ok` in `connect-cf7-to-hubspot` (`onboard_layer`), and in
  the throwaway repo `~/jev_test` (a small Memory card game; egress allowed) every path: `onboard_layer`, `detect_ui`, the
  hook T3 shadow and the Phase T shadow. Model id `typesafe/jev-1.13-20260917`, 290-690 ms typical, one 1.8 s answer.
- **The vault reads its key at load.** After `/plugin configure` the running session keeps the old key: restart
  `claude`. (A changed key gave nine `401` until the restart, then nine `ok`.)
- **Desktop stays inert** on the bundled 2.1.293 too (`Jev: off (no_key)` with the key set), so the cause is not the
  version; `/v:init` reports it as inert.
- **Endpoint:** `POST https://openrouter.ai/api/v1/systemone`, key as `Authorization: Bearer`.
- `calls.jsonl` is written by `compound-v-jev.py parse` (and by the onboard consumers), not by `jev_classify` itself.

Data so far (not an eval): `~/jev_test` data dir has 11 `calls.jsonl` lines and 4 shadow pairs; T3 agreement with
Claude 3/3 where both answered; corpus labels still 0/80 human, 0/80 Claude.

Open, found during the work (each needs its own triage):

1. `detect-ui --jev-responses <dir>` re-parses every file in the shared `resp/` directory: an old error is re-logged to
   `calls.jsonl` with a new timestamp and old answers take part in the decision.
2. The hook T3 budget (1,500 ms) timed out once while Jev answered in about 1.8 s.
3. A vault `refused: ...` result in the Phase T shadow step leaves its request file behind (rare).
4. `hooks/session-banner.sh:84` still reads `claude --version` (PATH CLI) for its floor warning.
5. `resolve-model --repo-dir <non-git dir>` uses the built-in table; untested.
6. Not done: a release (version bump, CHANGELOG); an issue for Anthropic about the desktop app and sensitive
   `userConfig`.

**Measurement and eval run (2026-10-08, later).** Run `2026-10-08-t3-measurement-and-eval` merged: the headless
Claude T3 classify now records `wall_ms`, `duration_api_ms` and tokens (`claude -p --output-format json`) into every
shadow pair, and `eval --t3` gained `--freeze`, `--label-claude`, `--merge-human`, 6 Jev calls per row and the decision
report. Its review returned ISSUES (open, fix run not started at the maintainer's request): (1) the trust rule's
`subtype`/`type` conjuncts have no isolated test rows; (2) the report's flip counter has no fixture with a flip; (3)
`--label-claude` counts a failed Claude run as an `unknown` vote and codex answers as Claude labels, and the report
prints codex `wall_ms` as Claude's. The maintainer confirmed decision threshold (c): `SKIPPABLE_SHARE_MIN = 0.25`. A live
probe showed the headless classify loading the whole Claude Code context: one one-word answer took 9.9 s wall, 2.4 s
API, 53,136 input tokens (cache creation). The blind labelling sheet is
`docs/superpowers/research/2026-10-08-jev-t3-labelling-sheet.md` (80 rows, codes `p m M u`).

Next: fix run for the three review issues, then item 6 of the original list. Label the corpus (`claude_label` by the Claude classifier, `human_label` by the
maintainer), run `compound-v-jev.py eval --t3 --prepare`, send the requests through `jev_classify` from a terminal
`claude`, then `eval --t3 --report`; decide spec 1.5 from the report.

## Where it stands

Spec 1 (`docs/superpowers/specs/2026-10-05-jev-classifier-foundation-design.md`) is built, reviewed and merged on the
branch: the `compound-v-vault` plugin (key holder, only HTTP client), the key-free `scripts/compound-v-jev.py`, the
record `t3` block, T3 in **shadow** only, the deterministic `detect_ui` floor plus Jev for UI and onboarding layers,
the 80-request synthetic corpus and the offline eval. Follow-ups closed on the same branch: the review fixes, the
Engine C re-finalize and lane-guard fixes, the vault offered as an optional plugin through `/v:init`.

Today Jev only advises. The tier is still decided by Claude or Codex, and every Jev failure falls back to exactly
what Compound V does without it.

Installed for live testing from the local marketplace `cv-dev` (`superpowers-v@cv-dev`, `compound-v-vault@cv-dev`,
user scope; the procoders 3.7.5 copy is disabled). The key is set. Re-sync recipe: the session transcript, or
rebuild `~/.claude/local-marketplaces/cv-dev/` from `git archive HEAD` and reinstall `superpowers-v@cv-dev`
(`plugin update` is a no-op while the version stays 3.8.3).

## What is missing before the next stage can be decided

Spec 1.5 (T3 **active**) is gated on evidence, by the spec's own rule ("decided on the first eval report").
None of that evidence exists yet:

| Evidence | State on 2026-10-05 |
|---|---|
| Live shadow data (`~/.claude/compound-v-jev/<digest>/calls.jsonl`, `shadow-pairs.jsonl`) | 0 calls: no live run yet |
| Corpus labels (`tests/fixtures/jev-t3-corpus.jsonl`) | 80 rows, `human_label` 0/80, `claude_label` 0/80 |
| Eval report (`compound-v-jev.py eval --t3 --report`) | never run against the live model |
| A live call through the vault with a real key | not yet verified |

## Next session, in order

1. **Live smoke test.** In a real repository: `/egress allow`, status line `Jev: on`, one change request that reaches
   T3. Check `calls.jsonl` (status `ok`, `latency_ms`, the resolved model id, e.g. `typesafe/jev-1.13-20260917`)
   and one `shadow-pairs.jsonl` line; confirm the triage decision and hook output are unchanged.
2. **Label the corpus.** `claude_label` by running the existing Claude T3 classifier over each row; `human_label` by
   the maintainer (the eval's ground truth). Commit the labels.
3. **Run the eval live.** `compound-v-jev.py eval --t3 --prepare`, send the request files through `jev_classify`,
   then `eval --t3 --report`. Read: agreement with human labels (Wilson intervals), strictness inversions (Jev
   less strict than the label; rule of three when zero), order and wording flip rates, the probability histogram
   and the share of hard 0/1 answers.
4. **Decide spec 1.5 from the report** (brainstorm, then the full pipeline). The candidate policy is in the spec
   (decision 6): a stricter Jev answer decides at once; a demoting answer at `p ≥ θ_demote` gives a *provisional*
   tier confirmed by Claude at `/v:orchestrate` bind; below `θ_demote` falls back to Claude. Deferred items to
   re-add: `active`, `provisional`, `t3-decide`, `confirm`, successor records (`supersedes`), the model-drift gate,
   the bind step. The plan-review amendment warns that on the committed records every T3 consultation was a
   demotion, so `active` may save no Claude call; let the report decide whether 1.5 is worth building.
5. **Spec 2, after 1.5** (`## Out of scope (spec 2)` in the spec): the RAG evidence filter over V-memory recall and
   pre-flight inputs; advisory probabilities on pre-flight skip, Sonnet eligibility and recon gate 1;
   change-request detection; skill hints.

## FIRST: jev_classify refuses every live call (found 2026-10-06)

The first live attempt that reached the vault (`connect-cf7-to-hubspot`, `jev-requests --point onboard_layer`, 9 request
files) got `refused: request_file must be an absolute path` on every call, with an absolute path. Cause: the vault's
`tool.call` handler (`plugins/compound-v-vault/hooks/vault.tsx:400-402`) passes `e.input` to `serveTool`, but Claude
Code carries a tool's arguments flat beside `tool` on that event (`e.request_file`; the bundled types say "the tool's
arguments beside them (`e.command` for Bash)"). The test hid it by calling `$.tool.call({ tool, input: { request_file } })`.
Fix: read the argument flat, and make the test pass it flat so it fails on the old code. Triage record:
`2026-10-06T134630Z-fix-the-compound-v-vault-jev-classify-tool-its-tool-call-han-74e1` (FULL, committed, not yet run).
After the fix the vault must be reinstalled in `cv-dev`, which clears the key: re-enter it with
`/plugin configure compound-v-vault@cv-dev` in a terminal `claude`. Nothing else produces Jev data until this lands.

## Finding from the first live attempt (2026-10-05)

- The Claude desktop app's Code tab runs its own bundled Claude Code (here 2.1.286, `CLAUDE_CODE_EXECPATH=
  ~/Library/Application Support/Claude/claude-code/2.1.286/...`), not the CLI on `PATH` (2.1.289). On 2.1.286 the vault
  module loads but receives an empty sensitive option: status `Jev: off (no_key)`, and no request is sent. A terminal
  `claude` on 2.1.289 in the same repository shows `Jev: on`. Run the live test from a terminal `claude` until the
  desktop app bundles 2.1.287 or newer. The Keychain access-control change tried during diagnosis was not needed.
- **Bug to fix first next session:** `/v:init` step 1g gates on `claude --version`, which reads the CLI on `PATH`, not
  the host running the session. In the desktop app it reports 2.1.289 while the session runs 2.1.286, so it would
  say `installed, key set` for an inert vault. Use the running host's version (the version segment of
  `CLAUDE_CODE_EXECPATH`, or `"$CLAUDE_CODE_EXECPATH" --version`), falling back to `claude --version` only when that
  variable is unset; pin it with a test row.

## Confirmed by the maintainer (2026-10-05)

Jev does not work in the Claude desktop app's Code tab at all: the vault loads and shows
`Jev: off (no_key)`, so the module never receives the key the CLI stored. The terminal `claude` works with the same key.
Whether the cause is the bundled 2.1.286 or the app process not reading the CLI's keychain entry is not settled.
Decided direction (do not store the key in a file or an env var; that defeats the vault):

1. `/v:init` 1g detects a desktop host (`CLAUDE_CODE_ENTRYPOINT=claude-desktop`) and reports
   `installed, inert in the desktop app — use Jev from a terminal claude`, instead of `installed, key set`.
2. The version gate reads the running host (`CLAUDE_CODE_EXECPATH`), not `claude --version`.
3. The vault README states the desktop limitation in one sentence.
4. Optionally, an issue for Anthropic: the desktop app does not pass a plugin's `sensitive` `userConfig` to its
   function-hooks module, and offers no `/plugin configure` to set it in place.

## Plugin-root resolver bug (found 2026-10-05)

Every command resolves `CV` with `ls -d "$HOME"/.claude/plugins/cache/*/superpowers-v/*/ | sort -V | tail -1`. That
sorts whole paths, so the marketplace name decides before the version: with `cv-dev/.../3.8.3` and
`procoders/.../3.7.5` both cached, it picked the older, disabled `procoders` copy, and a terminal epic session ran
3.7.5's scripts (no Jev). Workaround applied: `superpowers-v@procoders` uninstalled and its orphaned cache moved to
`~/.claude/plugins/cache-retired/`. Real fix: prefer `CLAUDE_PLUGIN_ROOT`, else the installed and enabled entry from
`claude plugin list --json`, else sort on the version component only; one helper, one test row, every command
updated.

## Shadow covers only the hook path (found 2026-10-06)

Live work on `connect-cf7-to-hubspot` (terminal CLI 2.1.290, `cv-dev` build, egress allowed, taxonomy present)
produced no Jev request. Of three triage records, the one that reached T3 (2026-10-06T13:32, `tiers_signalled:
localization, T3`) was classified by the agent running `/v:triage` Phase T itself (`compound-v-classify-request.py
--classify-headless`). Spec 1 wires the shadow only to `hooks/triage-prompt-nudge.sh` (pending descriptor) and
`hooks/jev-t3.tsx` (consumer); Phase T never leaves a descriptor, so Jev is never asked on that path, which in real
use is where most T3 decisions happen. Next step, before the eval can gather data: make Phase T leave the same
pending descriptor after its classify (or call `jev_classify` directly and run `parse --mode shadow` and `pair`),
with a test row, and record `t3` on Phase T records (they show `t3: null` even when T3 was signalled).

## Harness bugs reported by a downstream run (2026-10-06)

From `connect-cf7-to-hubspot`'s `docs/superpowers/execution/2026-10-06-multi-object-closeout.md` § Harness behaviour
observed. Each needs its own triage before a fix.

1. The run-wide re-derivation in `compound-v-integration-gate.py` ignores `toolchain_artifacts`, which the per-job gate
   honours; gitignored files that change during a run (`.DS_Store`, `.phpunit.cache`, a job's `.baseline`) made review
   jobs that changed nothing read `contradicted` or `forged`. Not yet reproduced here.
2. `compound-v-triage-outcomes.py` resolves its default stream from its own location (`default_stream_path()` ->
   `_repo_root()` from `__file__`, `scripts/compound-v-triage-outcomes.py:260`), so run from the plugin cache it
   appends to the plugin's copy, not the project's. Confirmed in the code; the downstream run used `--stream` as the
   workaround. The same pattern is reported for `compound-v-jev.py`. Fix: default to the git toplevel of the current
   working directory (or require `--repo`), with a test row.
3. `jev_classify` refuses every call: see "FIRST" above.
4. `compound-v-resolve-model.py resolve-model` without `--config` ignores the project's `models` table and resolves
   `standard` to Sonnet. Not yet reproduced here.

## Open items that are not features

- The lane-guard and re-finalize fixes reach live sessions only after a release (version bump, CHANGELOG,
  marketplace). The vault entry is in `procoders`' `marketplace.json` but nothing is released.
- `compound-v-usage-extract.py` matched no transcripts for the optional-vault run; not investigated.
- `origin/main` is at v3.6.2; PR #1 also carries upstream 3.7 to 3.8.3.
