# Commands

A command that changed its answer is evidence that changed.

- `record` stores each command with a digest of its recorded result.
- Running the same command again inside the same task and getting a different result
  is recorded as a contradiction.
- While an unresolved contradiction exists for the task, every state-changing call is
  refused with `COMMAND_RESULT_CHANGED`, writes and commands alike, because either
  could be relying on an answer that is no longer the answer.

This is the honest way to treat test suites, builds and deploys: the gate does not
decide whether the new result is better or worse, only that the task's picture of
the world moved and the task has not acknowledged it.
