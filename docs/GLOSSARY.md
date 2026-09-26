# Glossary

- **manifest** — the per-task record of what a task observed: file digests, command
  results, provenance, contradictions.
- **observation** — one recorded file read, with digest, time and provenance.
- **digest** — SHA-256 over the file's bytes; equal digests mean the same content.
- **receipt** — SHA-256 over a verdict and its inputs, written to the event log.
- **refusal code** — the named reason a call was refused, e.g. `EVIDENCE_SUPERSEDED`.
- **evidence identity** — the question this gate asks: is the evidence a task holds
  still the evidence for the workspace it is about to change.
- **write window** — the interval between a task's observation of a file and its edit
  of that file. All of this gate's refusals live in that interval.
- **probe mode** — records raw payloads without ever blocking, used to learn a
  runtime's real payload shape.
