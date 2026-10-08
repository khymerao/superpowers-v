# Compound V eval suite

The first measurement harness this plugin has had. `AGENTS.md` says, of the lane guard's
ambient cost, that "the repo carries no measurement harness to keep one honest". That is
still true of *latency*. This directory closes a different gap: whether the plugin actually
steers Claude to the right **outcome**, measured against a no-plugin baseline, with a score
you can gate a release on.

Run it with [`claude plugin eval`](https://code.claude.com/docs/en/plugin-evals) (Claude Code
**≥ 2.1.269**). It is not part of CI — see [Why this is not in CI](#why-this-is-not-in-ci).

---

## What it measures

Seven cases, each a request a real user would type, each scored by graders that read the
reply, the transcript, or a file. Every case runs twice: once with the plugin loaded
(`WITH`) and once with no plugin at all (`W/OUT`). The difference, `Δ`, is the plugin's
contribution. A case that scores 1.00 in both arms is a case the plugin did not win.

| Case | The question it asks | Fixture |
| :--- | :--- | :--- |
| `manifest-overlap-blocks-dispatch` | Two parallel jobs claim overlapping `write_allowed` globs. Does Claude reach a FAIL verdict and name the collision, or eyeball the YAML and wave it through? | git repo + one run dir, manifest with exactly one defect |
| `codex-job-must-run-in-a-worktree` | The partition is disjoint but a `backend: codex` job sits at `isolation: direct`. Does Claude know `codex ⇒ worktree`? | git repo + one run dir |
| `scope-gate-catches-out-of-lane-write` | A finished job wrote two files outside `docs/**`. BLOCKED, and which paths? | git repo at a tagged baseline + the working tree the job left |
| `run-status-from-state-json` | A halted run's `state.json`, read back as a status report. **Control case** — see below. | git repo + one run dir, `phase: BLOCKED` |
| `toolchain-artifacts-for-a-gitignored-build-artifact` | The gate blocked a job over `tsconfig.tsbuildinfo` that the test floor itself wrote. Does the plugin surface its own answer, `toolchain_artifacts` (v3.6.3)? | none — that is the point |
| `triage-tier-for-a-one-line-readme-fix` | A one-line typo. DIRECT, or does a typo get routed through brainstorm → pre-flights → dispatch? | git repo + the impact taxonomy |
| `unrelated-request-does-not-trigger-compound-v` | A read-only "explain this file" question. Does anything fire that shouldn't? | one ordinary source file |

## What it does **not** measure

- **Nothing here dispatches a real run.** No case spawns workers, no case starts a Codex or
  Antigravity or Cursor process, no case merges anything. A live multi-agent dispatch costs
  minutes and dollars per run, times seven runs per case per arm, and its result is dominated
  by the workers' own variance rather than by the plugin's steering. The dispatch path is
  covered by `tests/` and by the run records under `docs/superpowers/execution/`, not here.
- **Not latency, not cost, not throughput.** The lane guard's per-call cost still has no
  harness; `AGENTS.md` tells you how to measure it on your own machine.
- **Not safety.** A passing suite says the plugin steers well, not that it is safe to load.
  The [doc is explicit](https://code.claude.com/docs/en/plugin-evals) that the run's isolation
  is not a boundary against the plugin's own hooks and MCP servers.
- **Not the slash commands by name.** The prompts are natural language. `/v:status` is
  shorthand in our docs; the real command id is `superpowers-v:v-status`, and typing a
  namespaced command into the baseline arm turns the comparison into an unknown-command error
  rather than a fair contest. What the suite tests is whether the plugin's *knowledge and
  gates* reach the answer, which is what a user actually experiences.

## How to run it

From the plugin root:

```bash
claude plugin eval . \
  --scaffold \
  --allow-tools Bash Write Edit \
  --threshold 0.8 \
  --runs 3 \
  --no-publish \
  --trust-plugin
```

- **`--scaffold` is mandatory.** Scaffold scripts are off by default. Without it every
  fixture workspace is empty and every fixture-backed case scores 0.
- **`--allow-tools Bash`** is what lets a case run the plugin's own gates. `Read`, `Glob`,
  `Grep` and `Skill` need no grant — they are listed in each case's `allowed_tools`.
  Granting Bash puts every command under Claude Code's OS sandbox (see *Known blockers*).
- **`--trust-plugin`** skips the trust prompt. Only pass it because you are the maintainer of
  this plugin and you are the one who wrote these fixtures.
- **`--threshold 0.8`** exits 1 when any case's with-arm score falls below 0.8. The default is
  `1.0`, which is stricter than these cases are meant to be.
- Iterate on one case cheaply with `--case <name> --runs 1 --ablation none`. A single run is
  noisy; confirm anything you learn at `--runs 3` before believing it.

Results land in `evals/results/<timestamp>/` (gitignored).

## Ablation semantics

`--ablation with-without` is the default whenever a plugin resolves, and it is what makes the
suite worth running. Two rules decide what counts:

1. **A grader that the baseline could never pass is excluded from the score in both arms**,
   and reported in the with-arm as a *plugin-fired indicator*. `tool_used: Skill` is excluded
   automatically; anything else you must mark `arm: with-only`. Every grader in this suite
   whose name starts with `indicator-` is one of these: they check that the plugin's own
   script (`compound-v-validate-manifest.py`, `compound-v-scope-check.py`) or its own hook
   (`triage-prompt-nudge.sh`) actually fired. Counting them would push the baseline toward
   zero and inflate `Δ` into a number that means nothing.
2. **`arm: both` forces a grader to be scored in both arms.** The one place this suite uses it
   is `unrelated-request-does-not-trigger-compound-v`, whose `tool_used: Skill` grader has
   `min: 0` / `max: 0` — a "must NOT fire" check is only meaningful if the baseline is held to
   it too.

Under `--ablation none` nothing is excluded, so the same suite reports a different absolute
score. Don't compare a one-arm number with a two-arm one.

## How the fixtures reach the plugin's scripts

Every Compound V command resolves its tooling like this:

```bash
CV="${CLAUDE_PLUGIN_ROOT}"
[ -f "$CV/scripts/compound-v-preeval.py" ] || CV="$PWD"
[ -f "$CV/scripts/compound-v-preeval.py" ] || echo "Compound V: plugin root not found (no harness substitution, and $PWD is not a Compound V checkout); set CV to the plugin directory" >&2
```

Claude Code substitutes the plugin's path for the braced reference in the first line when it
loads a command, skill or agent body (ADR 0005). The variable itself is not set in the Bash tool,
so where nothing substituted it the shell expands it to an empty string, and the second line
accepts `$PWD` only when it holds `scripts/compound-v-preeval.py`; otherwise the third line says
so on stderr. No cache scan, no `$HOME` lookup.

Under `claude plugin eval` the with-arm loads the plugin from its source checkout, so the
substituted path is that source and `CV` points there. `evals/lib/cv-fixture-lib.sh`'s
`cv_vendor_tools` still copies the plugin's `scripts/` and `schemas/` into the workspace root:
that vendored copy is the fallback only, for a step that runs a block nothing substituted (a
reference file read with the Read tool, or the baseline arm), and it is exactly what the second
line accepts.

This is deliberately visible to **both** arms. The baseline can `ls` and find the same
scripts. The delta therefore measures whether the plugin steers Claude to *use* the gate — not
whether the gate happened to be reachable, which would be a rigged comparison.

`cv_vendor_tools` copies the whole `scripts/` directory rather than a hand-picked subset.
`compound-v-preeval.py` alone lazily loads eight siblings, and a subset that is correct today
breaks silently the day one of them gains a dependency. (It was: the first draft picked nine
scripts by hand and still missed `compound-v-update-memory.py`.)

### One fixture interaction to keep an eye on

In the with-arm, `hooks/triage-prompt-nudge.sh` runs *before* Claude sees the prompt and writes
`docs/superpowers/pre-eval/*` and `docs/superpowers/memory/triage-outcomes.jsonl` into the
workspace as untracked files. In `scope-gate-catches-out-of-lane-write` those land under
`docs/**`, which **is** that job's declared lane, so the gate reports them as changed-and-allowed
rather than as violations. That is luck, not design: if that case's lane ever stops covering
`docs/**`, the hook's own writes become extra violations and the grader that names exactly two
paths starts failing for a reason that has nothing to do with the model. Check with
`--keep-temp` before blaming the plugin. Nothing the hook writes in the other cases reaches a
grader.

## Graders

Deterministic by default. Of 25 graders, **21 are free** (20 `regex`, 1 `tool_used`) and
**4 call a judge model** (`type: llm`), each of them on a question a regex genuinely cannot
answer:

| LLM grader | Why it is not a regex |
| :--- | :--- |
| `scope-gate-catches-out-of-lane-write/does-not-blame-the-in-lane-file` | Checks that `docs/reindex.md` is *not* listed as a violation. "Does not appear in a particular role" is not a substring test — the filename legitimately appears in a correct answer. |
| `run-status-from-state-json/identifies-the-culprit` | Checks the response blames the *right* job for the *right* reason. Both tokens appear in any competent answer; their relationship is what is being graded. |
| `toolchain-artifacts-.../keeps-it-out-of-write-allowed` | Checks the recommended fix does not widen a lane. A wrong answer and a right answer contain the same words. |
| `triage-tier-.../does-not-route-a-typo-through-the-pipeline` | Same shape: a correct answer may name the heavier tiers while recommending against them. |

Judge verdicts vary between runs. Use `--judge-model sonnet` when a rubric verdict looks
wrong before you suspect the plugin, as the doc advises. A `llm` grader that disagrees with a
`regex` grader in the same case is a signal to tighten the rubric, not to loosen the regex.

## The control case, and why a zero delta is a result

`run-status-from-state-json` asks Claude to read a JSON file and report it. Any competent
model does that well, plugin or not, so **a `Δ` near zero there is the expected outcome**, not
a defect in the suite or the plugin. It earns its place as the regression tripwire for the
run-directory contract: if `state.json`'s shape changes and the status render stops working,
this is where it shows.

The same honesty applies everywhere. If a case shows the plugin does not change Claude's
behaviour, keep it and say so. That is a finding about the plugin, and finding it is the
entire point of having a suite.

## Known blockers on this machine (read before you conclude the suite is broken)

All three are environment problems, not case problems, and each produces a `score 0.00` that
has nothing to do with the plugin. **Fix them in reverse order of the list below**: the
authentication failure is terminal on its own — the one case that needs no Bash grant skips
the sandbox check entirely and still dies on it — so clearing the Docker blocker alone buys
nothing.

1. **`--allow-tools Bash` refuses to run while `~/.docker` contains a symlink.** The exact
   message: *"the Docker (~/.docker, DOCKER_CONFIG) credential store on this machine holds a
   symbolic link inside it, so the Bash sandbox cannot reliably exclude it — a Bash-granting
   evaluation cannot run here; keep the store's contents in one plain directory (its root may
   be a link)"*. This kills six of the seven cases. Find the offending entry with
   `find ~/.docker -type l` — it is nested, not at the top level — then decide: flatten it, or
   take the hint's other option and make the store's *root* the link. Rearranging a credential
   store is the machine owner's call, so this file tells you the command and stops there.
2. **The nested run cannot authenticate**: *"exit 1: Not logged in · Please run /login"*, and
   the judge graders fail with *"Failed to authenticate: OAuth session expired and could not
   be refreshed"*. Each run gets a throwaway home directory, so it cannot read the interactive
   session's credentials. Provide the credential the
   [requirements](https://code.claude.com/docs/en/plugin-evals#requirements) describe —
   a fresh `/login`, or `ANTHROPIC_API_KEY` in the environment — before trusting any score.
3. **The plugin directory must hold fewer than 20 000 entries.** A checkout with stale
   `.claude/worktrees/` trips it: *"a plugin directory holds more than 20000 entries to check
   for eval directories"*. At the time of writing this checkout carried 8 leftover worktrees
   (21 293 entries) and the suite could not start in place at all. Prune them
   (`git worktree list`, then `git worktree remove` what is genuinely dead) — or run against a
   copy that excludes `.git/` and `.claude/worktrees/`, which is what the recorded run below
   did.

## Last run

**Not yet run.** No score in this file is real, because no case has completed a model call.

| Attempt | Command | Outcome |
| :--- | :--- | :--- |
| 2026-09-21, Claude Code 2.1.263 | `claude plugin eval . --case … --runs 1 --ablation none --scaffold --allow-tools Bash --no-publish` | Refused: `` `plugin eval` is currently in early access ``. The command needs ≥ 2.1.269. |
| 2026-09-21, Claude Code 2.1.278, in place | `claude plugin eval . --case toolchain-artifacts-for-a-gitignored-build-artifact --runs 1 --ablation none --no-publish --trust-plugin` | Refused: plugin directory over 20 000 entries (stale worktrees). |
| 2026-09-21, Claude Code 2.1.278, against a copy excluding `.git/` and `.claude/worktrees/` | same as above | All graders evaluated, run errored: **`exit 1: Not logged in · Please run /login`**; judge graders: **`Failed to authenticate: OAuth session expired and could not be refreshed`**. |
| 2026-09-21, Claude Code 2.1.278, against the same copy, full suite | `claude plugin eval . --runs 1 --scaffold --allow-tools Bash Write Edit --threshold 0.8 --max-cost-usd 3 --no-publish --trust-plugin` | All **7 cases loaded and all 6 scaffolds ran**; all 14 runs errored on the Docker-symlink sandbox refusal above. `mean Δ 0.00`, `$0.00`, 10 s — **an environment failure, not a measurement.** |

What *is* verified, locally, without the harness:

- All seven `case.yaml` files and all 21 graders parse: the harness enumerated every case,
  ran the scaffolds, and evaluated the graders (they reported "pattern not found", which is a
  verdict, not a load error).
- Every scaffold runs clean in an empty directory.
- `manifest-overlap-blocks-dispatch`'s manifest produces **exactly one** validator violation —
  the overlap — and names both jobs and `src/billing`.
- `codex-job-must-run-in-a-worktree`'s manifest produces **exactly one** — *"job
  'task-1-reindex-worker' uses backend codex but isolation is 'direct' (codex requires
  worktree)"*. The job is `run: serial` on purpose; `parallel` + `direct` raises a second,
  different violation and blurs what Claude actually found.
- `scope-gate-catches-out-of-lane-write` produces *"BLOCKED: 2 file(s) written outside
  write_allowed"* naming `src/server/auth.ts` and `src/server/session.ts`.
- `triage-tier-for-a-one-line-readme-fix` scores `"tier": "DIRECT"`,
  `"decision": "FASTPATH_ELIGIBLE"`.

Every grader pattern in this suite is anchored on one of those real outputs, not on a guess
about what the tooling prints.

When you do get a run: replace this section with the summary table verbatim, the exact command,
and the date. Never write a score you did not observe.

## Why this is not in CI

Three reasons, in order of how much they matter:

1. **It needs a signed-in account and spends real tokens.** Fourteen agent runs at `--runs 1`,
   forty-two at the default `--runs 3`, plus three judge calls per `llm` grader per run. That
   is a release gate, not a per-push check.
2. **It grades a non-deterministic agent.** A red CI on one noisy run teaches a team to ignore
   CI. `--runs 3` is the floor for a verdict you should act on, and even then `Δ` moves.
3. **The plugin's own hooks run on the host during an eval**, outside the agent's sandbox.
   `hooks/triage-prompt-nudge.sh` fires on `UserPromptSubmit` in every with-arm run and can
   spend up to ~18 s classifying — and, when the deterministic layers cannot decide, spawn a
   nested `claude -p` whose tokens are **not** counted in the suite's cost estimate. That is
   fine on a maintainer's machine and wrong on a shared runner.

**Run it as a manual release gate**: before tagging a version that changes a skill description,
a command, an agent, or a hook, run the full suite at `--runs 3` and compare `Δ` with the
previous release's. The two things worth reacting to are a case whose `Δ` went negative and a
case whose `indicator-` grader stopped firing — the second means the plugin stopped reaching
for its own gate, which no amount of a good-looking reply makes up for.

If you ever do wire it up, the shape is in the doc: `--trust-plugin`, `--json results.json`,
`--no-publish`, pinned `--model` and `--judge-model` so a model rollout is not mistaken for a
regression, and `--max-cost-usd` as an upper bound.

## Adding a case

1. `mkdir -p evals/<case-name>/graders`.
2. Write `evals/<case-name>/case.yaml`. Required: `schema_version: "1.1"` and `name`.
   `description` and `expected_outcome` are for humans — use them, the next reader is not you.
   Run limits and tools go under `execution:` (`max_turns`, `timeout_seconds`,
   `allowed_tools`, `prompt`); fixtures go under `context:` (`scaffold_script`, `add_dirs`,
   `history_file`). **An unknown key is a load error**, so stay inside the documented set.
3. If the case needs a workspace, write `fixture.sh` beside `case.yaml`, source
   `../lib/cv-fixture-lib.sh`, and use `cv_git_init` / `cv_vendor_tools` / `cv_copy_taxonomy`.
   The script runs **as you**, outside the agent's sandbox, in the empty workspace, and only
   under `--scaffold`.
4. Write one grader per file under `graders/`. The filename is the grader's name — make it a
   sentence about what must be true (`names-both-jobs`, not `grader2`). Prefix it `indicator-`
   and mark it `arm: with-only` if the baseline could never pass it.
5. **Verify the fixture before you write the pattern.** Run the scaffold in a scratch
   directory, run the real script against what it built, and anchor your regex on the output
   you actually saw. Every pattern in this suite was written that way, and it is why they are
   not guesses.
6. Regexes are JavaScript. Case-insensitivity goes in `flags: i`, never inline `(?i)`. The
   default `target` is `last_message`; `trace` is JSON-per-line, so quotes appear as `\"`.
   To require several strings in any order, chain lookaheads and **end with one consuming
   `[\s\S]`** — `(?=[\s\S]*A)(?=[\s\S]*B)[\s\S]`. A lookahead-only pattern matches the empty
   string, which a grader that inspects the matched text rather than the match object would
   read as a miss. The alternation form (`A[\s\S]*B|B[\s\S]*A`) grows factorially past two
   terms; don't.
7. Pilot it: `claude plugin eval . --case <name> --runs 1 --ablation none --scaffold
   --allow-tools Bash --no-publish --trust-plugin`. Then confirm at `--runs 3` with the
   baseline arm on.

**Tune the plugin, not the grader.** If a case fails, the first question is whether the skill
description, the command, or the agent prompt is what is wrong. Loosening a pattern until it
passes converts a measurement into decoration.

## Two files, two formats

`evals/evals.json` belongs to the [skill-creator](https://code.claude.com/docs/en/skills)
plugin and has nothing to do with this suite — the
[doc](https://code.claude.com/docs/en/plugin-evals) says so explicitly. It coexists here
harmlessly: `claude plugin eval` only treats a subdirectory as a case when it contains a
`case.yaml` or a `prompt.md`, and a loose file is neither. Leave it alone.

## Version notes (doc vs. this CLI)

The published doc describes 2.1.269+. On **2.1.263** the command exists and `--help` prints,
but every invocation is refused with `` `plugin eval` is currently in early access ``, and
four documented options are simply absent: `--trust-plugin`, `--allow-real-servers`,
`-j/--concurrency`, and `--verbose`. On **2.1.278** all four are present and the command
behaves as documented.

Two behaviours the doc does not mention, both observed here:

- **The 20 000-entry plugin-directory limit** (see *Known blockers*). Nothing in the doc warns
  that a large checkout cannot be evaluated in place.
- **The Bash sandbox refuses to start when `~/.docker` contains a symlink.** The doc's
  [sandboxing prerequisites](https://code.claude.com/docs/en/sandboxing) cover bubblewrap and
  socat on Linux and WSL2 on Windows; this macOS precondition is not among them.
