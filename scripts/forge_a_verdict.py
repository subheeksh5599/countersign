#!/usr/bin/env python3
"""Forge one verdict inside a store, to prove the replay has teeth.

Used by the CI workflow: if a store with a forged admission still replays clean, the
check is decorative. Nothing here is part of the product path.

    python3 scripts/forge_a_verdict.py <store-dir>
"""
import glob
import json
import os
import sys


def main():
    store = sys.argv[1] if len(sys.argv) > 1 else ".countersign"
    d = os.path.join(store, "receipts")
    if not os.path.isdir(d):
        print(f"no receipts in {d}", file=sys.stderr)
        return 1
    for f in sorted(glob.glob(os.path.join(d, "*.json"))):
        rec = json.load(open(f, encoding="utf-8"))
        if rec.get("verdict") != "REFUSED":
            continue
        rec["verdict"], rec["exit_code"] = "ADMITTED", 0
        with open(f, "w", encoding="utf-8") as fh:
            json.dump(rec, fh, indent=2, sort_keys=True)
        print(f"forged an admission on {os.path.basename(f)} (was {rec.get('reason_code')})")
        return 0
    print("no refusal in this store to forge", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
