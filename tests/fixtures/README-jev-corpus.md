# Jev T3 eval corpus

`jev-t3-corpus.jsonl` holds 80 synthetic change requests shaped like the ones Compound V's triage sends to its
T3 classify step. It exists so the Jev classifier and the existing Claude classifier can be compared on the same
committed inputs, offline, before Jev is allowed to decide anything.

Every request, path and name in it was written for this file. None comes from a real project, a customer or a
user, and the file must never hold a secret, a key, a token or personal data. Keep it that way when adding rows.

## Schema

One JSON object per line, with exactly these keys in this order:

| Key | Type | Meaning |
|---|---|---|
| `id` | string | `t3-001` to `t3-080`, unique |
| `request` | string | The change request text, under 2,000 characters (the classify input limit) |
| `paths` | list of strings | The resolved file paths the request touches, one or two for most rows |
| `hints` | list of strings | Taxonomy category hints: the content-pattern `kind` values of `.claude/compound-v-impact-taxonomy.example.yaml`, the list `_default_t3_prompt` in `scripts/compound-v-preeval.py` passes. The same on every row |
| `t3_reason` | string | Why triage would ask T3: `unbanded`, `demotion` or `sensitive` (see below) |
| `label_draft` | string | The implementer's guess: `plumbing`, `user-facing-minor`, `user-facing-major` or `unknown` |
| `label_source` | string | Always `implementer-draft` |
| `human_label` | null | Filled by the maintainer before the eval |
| `claude_label` | null | Filled by running the existing classifier before the eval |

## Labels

`label_draft` is the implementer's guess, not ground truth. It uses the four categories of
`scripts/compound-v-classify-request.py` (`CATEGORIES`), and each category has 20 rows. Rows appear in a fixed
shuffled order, so a row's position says nothing about its label.

`human_label` is filled by the maintainer, one row at a time, without looking at `label_draft` first.
`claude_label` is filled before the eval by running the existing classifier,
`scripts/compound-v-classify-request.py --classify-headless`, on each row's `request` and `paths`; it prints JSON
whose `category` field is the label. Neither field is filled in this commit.

## How `t3_reason` was chosen

Each `t3_reason` names the route the row's paths would take through `scripts/compound-v-preeval.py`, read against
the example taxonomy (`.claude/compound-v-impact-taxonomy.example.yaml`) plus the broad rows named below.
File contents are not modelled: the reasons assume the touched files trip no high-impact content pattern.

- `unbanded` (44 rows): no `path_patterns` row of the example taxonomy matches any path (`.py`, `.ts`, `.html`,
  `.json`, `.yaml` and similar files outside the listed globs), so T1 cannot band the change.
- `demotion` (17 rows): the paths sit under directories that a project taxonomy would band high with a broad
  glob. The example taxonomy has no such row; these rows assume a project that adds `src/core/**`, `config/**`,
  `apps/web/**`, `packages/shared/**` and `infra/**` at difficulty and impact `high`. Each row has at most two
  paths (`DEMOTION_MAX_FAN_OUT`) and none is on the sensitive list.
- `sensitive` (19 rows): one path on the example taxonomy's `sensitive_path_list` (`src/auth/**`,
  `**/session/**`, `**/payments/**`, `**/billing/**`, `**/migrations/**`, `**/*.sql`, `**/*.tf`), never one of
  the `NEVER_DEMOTE_GLOBS` (`**/*.pem`, `**/*.key`, `**/*.env`, `.github/**`), which never reach T3.

## Ambiguity tally

45 of the 80 rows are deliberately ambiguous: plumbing 8, user-facing-minor 9, user-facing-major
8, unknown 20. They are the cases a classifier is most likely to get wrong: copy that may be minor or major,
refactors that touch an auth path, config constants, migration-named files that are really tooling (or the
reverse), low-risk edits on sensitive paths or on consent and flag files, refactors with a user-visible edge, and underspecified requests.

| id | label_draft | t3_reason | Why it is ambiguous |
|---|---|---|---|
| `t3-001` | `plumbing` | `sensitive` | migration named like tooling |
| `t3-002` | `plumbing` | `sensitive` | migration named like tooling |
| `t3-004` | `user-facing-minor` | `unbanded` | config constant |
| `t3-008` | `unknown` | `demotion` | underspecified request |
| `t3-009` | `user-facing-major` | `unbanded` | minor-vs-major copy |
| `t3-012` | `unknown` | `unbanded` | underspecified request |
| `t3-013` | `unknown` | `unbanded` | underspecified request |
| `t3-014` | `user-facing-minor` | `unbanded` | minor-vs-major copy |
| `t3-015` | `user-facing-major` | `unbanded` | minor-vs-major copy |
| `t3-016` | `unknown` | `unbanded` | minor-vs-major copy |
| `t3-019` | `unknown` | `sensitive` | migration named like tooling |
| `t3-020` | `plumbing` | `sensitive` | refactor touching an auth path |
| `t3-022` | `user-facing-major` | `unbanded` | minor-vs-major copy |
| `t3-023` | `unknown` | `demotion` | underspecified request |
| `t3-025` | `unknown` | `sensitive` | underspecified request |
| `t3-026` | `unknown` | `demotion` | config constant |
| `t3-028` | `user-facing-minor` | `unbanded` | consent surface, style-only edit |
| `t3-030` | `user-facing-major` | `unbanded` | minor-vs-major copy |
| `t3-031` | `unknown` | `demotion` | underspecified request |
| `t3-033` | `plumbing` | `sensitive` | sensitive path, low-risk edit |
| `t3-034` | `unknown` | `unbanded` | underspecified request |
| `t3-040` | `unknown` | `sensitive` | refactor touching an auth path |
| `t3-041` | `unknown` | `demotion` | underspecified request |
| `t3-042` | `unknown` | `unbanded` | minor-vs-major copy |
| `t3-043` | `user-facing-minor` | `demotion` | minor-vs-major copy |
| `t3-046` | `unknown` | `demotion` | config constant |
| `t3-047` | `plumbing` | `unbanded` | feature-flag file, comment-only edit |
| `t3-049` | `plumbing` | `demotion` | refactor with a user-visible edge |
| `t3-050` | `user-facing-major` | `sensitive` | refactor touching an auth path |
| `t3-053` | `user-facing-major` | `demotion` | config constant |
| `t3-055` | `user-facing-minor` | `sensitive` | sensitive path, low-risk edit |
| `t3-059` | `user-facing-minor` | `unbanded` | minor-vs-major copy |
| `t3-060` | `plumbing` | `demotion` | config constant |
| `t3-061` | `unknown` | `sensitive` | refactor touching an auth path |
| `t3-063` | `unknown` | `unbanded` | underspecified request |
| `t3-064` | `user-facing-minor` | `sensitive` | sensitive path, low-risk edit |
| `t3-065` | `user-facing-major` | `unbanded` | config constant |
| `t3-067` | `user-facing-major` | `sensitive` | migration named like tooling |
| `t3-068` | `unknown` | `unbanded` | minor-vs-major copy |
| `t3-069` | `user-facing-minor` | `unbanded` | minor-vs-major copy |
| `t3-071` | `plumbing` | `sensitive` | refactor touching an auth path |
| `t3-073` | `unknown` | `unbanded` | underspecified request |
| `t3-074` | `unknown` | `unbanded` | underspecified request |
| `t3-078` | `user-facing-minor` | `sensitive` | minor-vs-major copy |
| `t3-079` | `unknown` | `sensitive` | underspecified request |

## Checks

Before committing a change to the corpus, check that every line parses as JSON with exactly the keys above, ids
are unique, each category has 20 rows, every `request` is under 2,000 characters, `label_source` is
`implementer-draft`, `human_label` and `claude_label` are null until the eval fills them, and `SECRET_RE` and
`PEM_RE` from `scripts/compound-v-memory.py` find nothing in the file.
