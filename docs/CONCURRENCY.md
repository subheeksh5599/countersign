# Concurrency

Two tasks, one repository, one file. The failure this gate exists for.

```
task A                    disk                      task B
  read pricing.ts   ->    rate = 1
                          rate = 1 + B's edit   <-   write pricing.ts
  write pricing.ts  ->    REFUSED (EVIDENCE_SUPERSEDED)
```

What the gate does not attempt to do is arbitrate between the two tasks. It refuses
the write whose evidence stopped describing the file, names both digests, and states
the recovery. The losing task is not damaged: nothing was written.

Cases covered by the matrix suite: read-then-write, write-then-read, read-write-read,
two writers, and interleaved orders, each with and without drift, across four write
tools.
