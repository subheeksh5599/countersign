# Revision-moved scene, verbatim

Command: `sh scripts/scene_revision_moved.sh`

```

== task opens and reads pricing.ts (rate = 1) ==
{"verdict": "ADMITTED", "note": "evidence recorded"}
exit=0
digest at read: baa5252515ea   revision at read: a512df3add44

== another actor commits a different rate to that path ==
revision now:   419337eaee65

== the working file is restored to the exact bytes the task read ==
digest now:     baa5252515ea
the file on disk is byte-identical to what the task read

== the task tries to edit ==
  2. re-observe pricing.ts
  3. rerun the affected commands
  4. record the new evidence manifest
Refusal receipt: 361718adb60a2673ea13a90e305f52e4e52e6a5f1747dc488d040ad2f82db99a
The action did not happen.
exit=2

== the file on disk did not change ==
export const rate = 1

A digest comparison alone would have admitted this edit. Both digests match;
only the committed revision for that path moved, and that is the difference the
gate refuses on.
```
