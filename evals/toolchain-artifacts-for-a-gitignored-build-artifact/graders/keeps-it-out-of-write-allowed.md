---
type: llm
---
The user asked how to stop Compound V's scope gate blocking a job over a gitignored build
artifact (`tsconfig.tsbuildinfo`) that the test floor writes, WITHOUT widening the job's
`write_allowed` lane.

The correct answer is the manifest's top-level `toolchain_artifacts` list, which is separate
from `write_allowed` precisely so disjointness is untouched, and whose paths are subtracted
only when git confirms they are ignored.

PASS if the response's recommended fix keeps the artifact OUT of any job's `write_allowed`
and puts it in a separate declaration at the manifest level.
FAIL if the response's recommended fix is to add the path to a job's `write_allowed`, to
loosen the gate generally, to delete the artifact, or if it offers no concrete declaration.
