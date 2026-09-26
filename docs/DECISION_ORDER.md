# Decision order

The gate evaluates conditions in a fixed order. The first condition that applies
decides the outcome, which is what makes the behaviour testable as a matrix.

| # | condition | outcome |
|---|---|---|
| 1 | no manifest for this task | `NO_MANIFEST` (refuse) |
| 2 | a command result in this task changed under it | `COMMAND_RESULT_CHANGED` (refuse) |
| 3 | target path resolves outside the workspace | `OUTSIDE_WORKSPACE` (refuse) |
| 4 | call attributed to a subtask with no observation by that subtask | `UNSUPPORTED_SUBTASK_EVIDENCE` (refuse) |
| 5 | path unobserved here but observed by another task | `CROSS_TASK_EVIDENCE` (refuse) |
| 6 | path unobserved and policy demands prior observation | `UNVERIFIED_TARGET` (refuse) |
| 7 | path unobserved, default policy | admit, recorded as `write_without_evidence` |
| 8 | path observed by this task and the file digest differs | `EVIDENCE_SUPERSEDED` (refuse) |
| 9 | path observed and the committed revision for that path moved | `REVISION_MOVED` (refuse) |
| 10 | otherwise | admit, with a receipt |

`tests/test_matrix.py` builds 500 cases across this table. Every case runs the gate
as a subprocess in a real git workspace and asserts both the exit code and the code.
