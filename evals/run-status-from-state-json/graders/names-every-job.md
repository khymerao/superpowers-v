---
type: regex
pattern: '(?=[\s\S]*task-1-api)(?=[\s\S]*task-2-ui)(?=[\s\S]*task-3-docs)[\s\S]'
---

The trailing `[\s\S]` is not decoration: a lookahead-only pattern matches the empty
string, and a grader implementation that tests the matched TEXT rather than the match
object would read that as a miss. One consumed character makes it true under either.
