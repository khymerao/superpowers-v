---
type: llm
---
The user asked how a one-line README typo fix should be routed through Compound V.
The correct sizing is DIRECT: implement it in place, run the test floor, and commit the
change together with its triage record. DIRECT explicitly does NOT mean brainstorming,
pre-flight audits, a manifest, or a parallel dispatch.

PASS if the recommended route is to make the change directly (with, at most, the floor test
and the record commit), even if the response also mentions what the heavier tiers would be.
FAIL if the recommended route for THIS change is a brainstorm, a spec, pre-flight audits,
a manifest/orchestrate step, or a dispatch.
