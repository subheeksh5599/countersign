# Exports

`export` writes one hashed evidence record per task:

```
.countersign/exports/<task>.json
```

Each record contains the task, the commit it opened on, every observation with its
digest and provenance, every command with its result digest, every contradiction,
every verdict with its code and receipt, and a digest over the whole record. It is
the artifact to hand to a reviewer, an incident postmortem, or an outside party who
was not the agent's user.
