# The replay: what a machine that never ran the gate can still check

The gate decides locally. That is deliberate: the evidence it compares is on the machine
the agent is editing, and no server is consulted for a verdict. It leaves two questions
open, and this is the answer to both.

1. Can someone who was not there check that a verdict was reached, rather than typed?
2. Can the check run somewhere the gate never ran, for example in CI after a clone?

## What is checked

`python3 countersign.py replay`, with `COUNTERSIGN_WORKSPACE` pointing at the repository,
walks every receipt in the store and recomputes three things from the receipt's own
contents:

| check | what it means |
|---|---|
| `hash_recomputes` | the stored `receipt_hash` is the hash of the receipt with that field removed. A receipt edited after the fact fails here. |
| `chain_links` | `previous_receipt_hash` equals the hash of the receipt before it. A removed or reordered receipt breaks the link. |
| `verdict_follows_from_inputs` | the verdict follows from the digests the receipt itself recorded. A refusal that names a digest reason while recording two equal digests contradicts itself, and so does an admission whose digests differ. Both fail. |

It also reports, as information rather than a pass or fail, whether the file at the
receipt's recorded revision is still the blob the receipt recorded (`bound`, `drifted`, or
`not in that revision`). A refusal can be reached against a working tree that was never
committed, so that column is evidence, not a verdict.

Exit code 0 when every receipt holds, 2 when any does not. `--json` prints the same report
for a machine to read.

## In CI

`.github/workflows/replay.yml` runs on every push and pull request:

1. the committed bundle in `docs/evidence-store/ci-bundle/` is copied to `.countersign/`;
2. `python3 countersign.py replay` must exit 0;
3. `python3 scripts/forge_a_verdict.py .countersign` forges an admission on a refusal, and
   the replay must then exit non-zero.

Step 3 is the point. A build that only ran the replay proves nothing about whether the
replay can fail. A green build here means the check has teeth.

Reproduce it locally in one go:

```sh
rm -rf /tmp/replay-check && mkdir -p /tmp/replay-check && cd /tmp/replay-check
git init -q .
cp -r /path/to/countersign/docs/evidence-store/ci-bundle .
mkdir .countersign
cp -r ci-bundle/tasks ci-bundle/receipts .countersign/
cp ci-bundle/events.jsonl ci-bundle/stale.jsonl .countersign/
cp /path/to/countersign/countersign.py .

COUNTERSIGN_WORKSPACE=$PWD python3 countersign.py replay          # 3 receipts, 0 failed
python3 /path/to/countersign/scripts/forge_a_verdict.py .countersign
COUNTERSIGN_WORKSPACE=$PWD python3 countersign.py replay          # 3 receipts, 1 failed
echo "exit $?"                                                    # 2
```

## What this does not do

- It does not re-run the *gate* against a new repository state. It re-derives each stored
  verdict from its own inputs. A verdict can be consistent and still have been reached
  against a tree that later changed; that is what the revision column is for.
- It does not make the gate depend on a server. The verdict path stays a local hash
  comparison with no model and no network.
- It does not cover a change that exists only on another machine and was never fetched.
  Two clones keep two manifests; the receipts are what reconcile them.
