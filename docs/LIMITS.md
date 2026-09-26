# Limits, stated deliberately

What this gate does not do, in the same breath as what it does.

- The runtime's own edit path may already refuse a write to a file changed since it
  was read. Its tool documentation describes no such behaviour, but silence is not
  evidence. The cross-task, revision, command-result and subtask cases are the ones
  this gate provably owns, and they are covered by tests.
- A competent agent often refreshes its evidence before writing, and then the gate
  admits. That is correct behaviour, not a gap: the gate exists for the moment when
  a task acts on evidence it did not refresh. Staging that moment on demand is a
  concurrency problem, not a coding problem; the live demonstration uses a labelled
  harness that writes the path inside the read -> write window.
- Subtask attribution requires the payload to identify the subtask. The payloads
  observed so far do not carry a subtask id, so per-subtask manifests are separated
  by the gate's own contract, not by an observed field.
- Command results are compared by digest of the recorded result text. A command whose
  output changes for benign reasons (timestamps, durations) will register as a
  contradiction. Treat that as a fact to resolve, not a bug to silence.
- Revisions are read with `git rev-parse HEAD:<path>`. Workspaces that are not git
  repositories fall back to digest comparison alone.
- Nothing here reads a private API. The gate consumes the public hook payload and the
  workspace itself.
