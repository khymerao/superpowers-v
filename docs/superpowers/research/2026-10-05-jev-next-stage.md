# Jev: where spec 1 stopped and what comes next

Handoff for the next session. Branch `feat/jev-classifier-foundation`, PR khymerao/superpowers-v#1.

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

## Open items that are not features

- The lane-guard and re-finalize fixes reach live sessions only after a release (version bump, CHANGELOG,
  marketplace). The vault entry is in `procoders`' `marketplace.json` but nothing is released.
- `compound-v-usage-extract.py` matched no transcripts for the optional-vault run; not investigated.
- `origin/main` is at v3.6.2; PR #1 also carries upstream 3.7 to 3.8.3.
