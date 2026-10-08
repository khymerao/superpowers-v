---
type: llm
---
The assistant was asked whether a job stayed inside its declared write lane of `docs/**`.
The ground truth: `docs/reindex.md` was modified and IS in lane; `src/server/auth.ts` and
`src/server/session.ts` were written and are OUT of lane.

PASS if the response treats `docs/reindex.md` as allowed / in-lane, or does not list it
among the violations.
FAIL if the response lists `docs/reindex.md` as an out-of-lane write, a violation, or a
reason the job is blocked.
