# Multi-developer demo

Two workspaces, one repository, one shared history. This is the case the gate is
built for and the case that shows why the record belongs to the team.

1. Developer A clones the repository and starts a task that reads `pricing.ts`.
2. Developer B, in a second clone, edits and commits `pricing.ts`.
3. A's task tries to edit `pricing.ts`. Its manifest still holds the digest and
   revision from its own clone, so the write is refused.
4. A re-reads, or A's task opens a fresh window, and the edit proceeds with a receipt
   naming the revision it was based on.

Run it with two terminals against two clones and a shared remote; the interesting
artifact is the pair of records (`export` per task) showing the same path observed at
two different revisions with two different verdicts.
