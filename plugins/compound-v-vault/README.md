# compound-v-vault

A small Claude Code plugin that holds the OpenRouter API key for Compound V's Jev classifier and is the only
program that talks to Jev. Compound V itself never sees the key: its Python layer (`scripts/compound-v-jev.py`)
writes request files and reads response files, and this plugin sends the requests.

Jev is TypeSafe's System One classifier, reached through OpenRouter's System One route. The model is pinned to
`typesafe/jev-1.13`; the response names the resolved model id, and Compound V records that id.

The vault is optional. Without it, every Compound V consumer of Jev runs its deterministic or Claude path, exactly as
it does with no Jev at all.

## Requirements

- Claude Code 2.1.287 or newer. The plugin is a hooks module (a "mod"); older versions do not load it.
- An OpenRouter account and API key.

## Setup

1. Install the plugin from the same marketplace as Compound V and enable it.
2. Set the key: run `/config`, find **compound-v-vault**, and fill in **OpenRouter API key**. The field is marked
   sensitive, so Claude Code keeps it in secure storage, not in a settings file.
3. In each repository where you want Jev, run `/egress allow` once (see Egress below).

Use a dedicated OpenRouter key with a credit limit set on the OpenRouter side. The vault cannot cap spending; the
limit on the key can.

The status line shows `Jev: on` when calls for the current repository would be sent, and `Jev: off (<reason>)`
otherwise. Reasons: `no_key`, `egress`, `disabled`, `route`, `repo`.

## Egress

Nothing leaves the machine for a repository until you answer for it:

| Command | Effect |
|---|---|
| `/egress allow` | Requests from this repository are sent to Jev. |
| `/egress deny` | Nothing from this repository is sent. Consumers fall back as if the vault were absent. |
| `/egress status` | Shows the current answer: `allow`, `deny` or `not answered`. |

The answer is per user and per repository. It is kept in this plugin's own store (`$.store`, a file under your
Claude Code configuration directory) under `egress:<repository real path>`. It is never written to the repository.

Until you answer, each request returns `unavailable(egress)` and the vault shows one toast per session pointing at
the command.

## What leaves the machine, and to whom

When egress is allowed, the request body built by `scripts/compound-v-jev.py` is sent to OpenRouter, which passes it
to TypeSafe, the provider that runs Jev. Depending on the decision point, the body holds:

- the change request text, cut to at most 2,000 characters;
- file paths (at most 20);
- taxonomy hints from the repository's taxonomy (at most 40);
- for UI detection only, the first lines of a few sampled files.

Compound V runs the text through its existing outbound redaction before the request file is written. This README
makes no claim about how long OpenRouter or TypeSafe keep what they receive; read their own policies.

The key itself is sent only to the configured System One endpoint, only as the `Authorization` header. The endpoint
must be an `https://` URL; any other value is refused before a request is made.

## What the vault offers other plugins and the model

- The `jev` noun on `$` for other hooks modules: `$.jev.classify(request)` answers
  `{ status, reason?, http_status?, latency_ms, body? }`, and `$.jev.status(repoRealPath)` answers
  `{ on, reason? }`. The types are in `types/index.d.ts`.
- One model tool, `jev_classify({ request_file })`. It accepts only a regular file named `<name>.req.json` in a
  `req/` directory under `~/.claude/compound-v-jev/<repo-digest>/`, checked by its real path (no symbolic links, no
  `.` or `..` segments). It writes `<name>.resp.json` to the sibling `resp/` directory (mode 0600) and returns that
  path, or `refused: <reason>`.

Answers: `ok` with the parsed body (`usage.cost` removed); `unavailable` with `no_key`, `disabled`, `egress`,
`timeout`, `rate_limited` (429), `upstream` (5xx, 524, 529, or no connection), `credits` (402) or `auth`
(401, 403); `error` with `bad_input` (400, 422, or a malformed request) or `schema` (a reply that is not a JSON
object). An error reply's body is never read or copied: OpenRouter's error bodies carry the account's `user_id`, so
only the HTTP status is kept.

Timeouts: 1,500 ms for requests from a hook, 5,000 ms offline. Offline only, a 429 is retried once when its
`Retry-After` header says 1 second or less; with no such header there is no retry. 401, 402 and 403 are never
retried. `latency_ms` is measured around the request.

When `CV_HEADLESS_CLASSIFY` is set (Compound V's nested `claude -p` classifier), the vault sends nothing and
registers no tool.

## Boundary

What the vault guarantees: the key is never in the model's environment, an environment variable, a command line, a
file, a tool result, a status line or toast, or the transcript. As a backstop, any transcript row that would contain
the key has it replaced by `[redacted]` before it is stored. The plugin has no settings (command) hooks, so Claude
Code exports none of its options as `CLAUDE_PLUGIN_OPTION_*` to any hook process.

What it does not guarantee: hooks modules are not sandboxed from each other. Another mod that loads earlier in the
chain can observe the vault's calls, including the `Authorization` header of `$.http.fetch` and the `jev.classify`
event. Install only mods you trust next to it.

The vault never answers a Bash tool call. Permission prompts, sandbox rules and Compound V's `lane-guard.sh` apply to
every command exactly as they do without it.

## Tests

`tests/test-vault-mod.sh` runs `claude plugin validate` on this folder and `claude plugin test` on a temporary copy
of it. The tests in `.tests/vault.test.tsx` stub the network, the file system, the clock and the store, and after
every test check that the key appears only in the fetch `Authorization` header.

The tests sit in the dot-folder `.tests/` on purpose. `claude plugin test <dir>` runs every `*.test.ts(x)` under
`<dir>` and skips dot-folders, so a test file elsewhere in this folder would also be picked up by the Compound V
root plugin's own `claude plugin test .` and run against the wrong plugin. The script copies this folder to a
temporary directory, moves the tests into its `hooks/`, and runs them there.
