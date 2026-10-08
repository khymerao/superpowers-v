---
description: Run an independent cross-model (Codex) adversarial review of a Compound V plan/manifest before dispatch, then arbitrate the findings. Codex advises; the orchestrator decides.
---

You are running a **second-opinion review** on `{{args}}` — a different model family (Codex/GPT) when one is available, per the ladder in [cross-model-review.md](../skills/compound-v/cross-model-review.md).

> Run it on demand, or **automatically before dispatch** when the project set `review.cross_model: true` at [`/v:init`](v-init.md) Step 3c (read from `.claude/compound-v.json`). Either way the stakes check below still applies — skip small/mechanical plans.

## Resolving the plugin root

The `scripts/` this command calls ship with the plugin — they are not files in your own
repository. Resolve the plugin root once per session before calling any of them:

```bash
CV="${CLAUDE_PLUGIN_ROOT}"
[ -f "$CV/scripts/compound-v-preeval.py" ] || CV="$PWD"
[ -f "$CV/scripts/compound-v-preeval.py" ] || echo "Compound V: plugin root not found (no harness substitution, and $PWD is not a Compound V checkout); set CV to the plugin directory" >&2
```

`CLAUDE_PLUGIN_ROOT` is set for hooks but is not set in this Bash environment. Claude Code
substitutes the plugin's path for the braced reference in the first line when it loads this
file, so that line already holds the path of the copy it loaded. Where nothing substituted it
(another harness, or this file read with the Read tool), the shell expands the unset variable to
an empty string; the second line then accepts `$PWD` only when it is a checkout of this plugin,
and the third says so on stderr instead of guessing.

## Steps

1. **Resolve the plan path.** Use `{{args}}`; if empty, list `docs/superpowers/plans/*.md` and ask which to review.

2. **Stakes check (gating).** Confirm this plan warrants a cross-model review (security/auth/payments/migrations, large/coupled partition, architectural change, or the user asked). If it's small/mechanical, say so and recommend skipping — the Opus `partition-reviewer` + `validate-manifest.py` already cover it.

3. **Run the ladder** — [cross-model-review.md § The ladder](../skills/compound-v/cross-model-review.md#the-ladder):
   1. **Codex CLI present → dispatch the read-only Codex reviewer:**
      ```bash
      "$CV/scripts/compound-v-codex-review.sh" --plan-file "<plan>" --repo "$PWD" --effort xhigh
      ```
      (Add `--context-file <audit>` for any archaeology/domain/library audits that ground the review.) The model is resolved for codex / tier `frontier` (e.g. `gpt-6-astra`) — review runs on the strongest codex tier, one rung above implementation's `deep`/`standard`. Codex reads the repo read-only and returns findings JSON per `schemas/plan-review.schema.json`.
   2. **No Codex, an advisor configured → an advisor-assisted second look.** Dispatch one
      read-only Opus subagent through the Agent tool with the same adversarial prompt the
      driver above embeds, plus one addition: consult the advisor tool before writing the
      verdict. It returns the same `plan-review.schema.json` shape. State the disclosure
      line verbatim: *"Second look by the same model family (Claude + advisor) — no
      decorrelation; not a cross-model review."*
   3. **Neither → skip**, and say plainly that no second opinion ran and why.

4. **ARBITRATE — you own the decision, Codex is advisory.** For EVERY finding, do one of:
   - **ACCEPT** → the objection is real; note the fix (and apply it / fold it into the plan).
   - **OVERRIDE** → wrong or already handled; give a one-line rebuttal with the reasoning.

   Then: **escalate to the human** any critical/high finding you want to OVERRIDE; set the real verdict yourself (Codex's `reject` may become "proceed with fixes"); and present a short arbitration table (finding → ACCEPT/OVERRIDE → why).

5. **Hand back** the arbitrated decision: proceed to dispatch, revise the plan first, or escalate. Do NOT treat Codex's verdict as a hard gate — the deterministic `validate-manifest.py` is the only hard gate.

## Safety

- The review is **read-only** (`--sandbox read-only`) — it never modifies the repo.
- Codex never has final authority; arbitration is mandatory.
- Gate by stakes — a max-effort GPT review is not free.
