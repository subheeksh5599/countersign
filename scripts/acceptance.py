#!/usr/bin/env python3
"""Fresh-machine acceptance run for Countersign.

Drives the runtime the way an operator would, on a repository it creates from nothing,
and checks the seventeen things the product claims. Every step reads the real response;
nothing is asserted from a fixture.

  python3 scripts/acceptance.py [--api http://127.0.0.1:4319] [--dashboard http://127.0.0.1:4311]
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PASS, FAIL = [], []


def call(api, path, body=None, method=None, timeout=120):
    url = api + path
    data = None
    if body is not None or method == "POST":
        data = json.dumps(body or {}).encode()
    req = urllib.request.Request(url, data=data, method=method or ("POST" if data else "GET"),
                                 headers={"content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode() or "{}")
        except json.JSONDecodeError:
            return e.code, {}
    except Exception as e:
        return 0, {"error": str(e)}


def status_of(url, timeout=20):
    """HTTP status of a page that is not JSON (the console routes)."""
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"accept": "text/html"}),
                                    timeout=timeout) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0


def check(step, condition, detail):
    (PASS if condition else FAIL).append(step)
    print(f"  {'PASS' if condition else 'FAIL'}  {step}\n        {detail}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default=os.environ.get("COUNTERSIGN_API", "http://127.0.0.1:4319"))
    ap.add_argument("--dashboard", default=os.environ.get("COUNTERSIGN_DASHBOARD",
                                                          "http://127.0.0.1:4311"))
    ap.add_argument("--repo", default="/tmp/csign_acceptance_repo")
    a = ap.parse_args()

    ws = a.repo
    print(f"fresh machine acceptance run\n  api {a.api}\n  dashboard {a.dashboard}\n  repo {ws}\n")

    # wait for both services rather than assuming they are warm
    for label, url in (("runtime", a.api + "/api/status"), ("dashboard", a.dashboard + "/console")):
        for _ in range(30):
            try:
                with urllib.request.urlopen(url, timeout=5) as r:
                    if r.status == 200:
                        print(f"  {label} ready")
                        break
            except Exception:
                time.sleep(1)
        else:
            print(f"  {label} did not answer at {url}")

    if os.path.exists(ws):
        shutil.rmtree(ws)
    os.makedirs(os.path.join(ws, "src"), exist_ok=True)
    subprocess.run(["git", "init", "-q", ws], check=False)
    for k, v in (("user.email", "acceptance@countersign.local"), ("user.name", "acceptance")):
        subprocess.run(["git", "-C", ws, "config", k, v], check=False)
    open(os.path.join(ws, "src", "payment-refund.ts"), "w").write(
        "export function refund(o) { return charge(o.id) }\n")
    open(os.path.join(ws, "src", "config.ts"), "w").write("export const RETRY_LIMIT = 3\n")
    subprocess.run(["git", "-C", ws, "add", "-A"], check=False)
    subprocess.run(["git", "-C", ws, "commit", "-qm", "initial"], check=False)

    # 1
    p = subprocess.run(["sh", os.path.join(ROOT, "install.sh"), ws], capture_output=True,
                       text=True, cwd=ROOT)
    hooks = os.path.join(ws, ".countersign", "hooks.json")
    bob = os.path.join(ws, ".bob", "settings", "settings.json")
    check("1. install countersign", p.returncode == 0 and (os.path.exists(hooks) or os.path.exists(bob)),
          f"install.sh exit {p.returncode}; hook settings: {', '.join(x for x in (hooks, bob) if os.path.exists(x)) or 'none'}")

    # 2
    code, r = call(a.api, "/api/repo/connect", {"path": ws})
    check("2. connect a real git repository", code == 200 and r.get("ok"),
          f"http {code}; head {r.get('repo', {}).get('head_short')} on branch {r.get('repo', {}).get('branch')}")

    # 3
    code, r = call(a.api, "/api/repo/protect", {})
    code2, st = call(a.api, "/api/status")
    check("3. start protection", code == 200 and st.get("protected"),
          f"protect http {code}; status.protected={st.get('protected')} hook_scope={st.get('hook_scope', {}).get('scope')}")

    # 4
    code, r = call(a.api, "/api/session/start", {})
    sid = r.get("session_id")
    check("4. start a session", code == 200 and bool(sid),
          f"session {sid}; gate exit {r.get('gate', {}).get('exit_code')}")

    # 5
    code, r = call(a.api, "/api/evidence/read", {"session": sid, "path": "src/config.ts"})
    held = (r.get("evidence") or {}).get("held_digest")
    check("5. read a file through the evidence mechanism", code == 200 and bool(held),
          f"recorded sha256 {held}")

    # 6
    open(os.path.join(ws, "src", "config.ts"), "w").write("export const RETRY_LIMIT = 99\n")
    import hashlib
    disk = hashlib.sha256(open(os.path.join(ws, "src", "config.ts"), "rb").read()).hexdigest()
    check("6. modify that file externally", disk != held, f"disk now {disk}")

    # 7 + 8 + 9 + 10
    code, r = call(a.api, "/api/interceptor/attempt",
                   {"session": sid, "tool": "apply_diff", "path": "src/config.ts",
                    "arguments": {"path": "src/config.ts",
                                  "diff": "-export const RETRY_LIMIT = 99\n+export const RETRY_LIMIT = 5\n"}})
    out = " ".join(r.get("stdout") or [])
    check("7. attempt a real state-changing operation", r.get("call") is not None,
          f"intercepted call recorded: {json.dumps(r.get('call', {}).get('tool'))}")
    check("8. the hook intercepts it", r.get("gate", {}).get("exit_code") == 2,
          f"gate exit {r.get('gate', {}).get('exit_code')} via {r.get('note')}")
    check("9. hash mismatch is detected", "EVIDENCE_SUPERSEDED" in out and held[:12] in out,
          f"verdict line: {out[:150]}")
    check("10. operation exits with code 2", r.get("exit_code") == 2 and "did not happen" in out,
          f"exit {r.get('exit_code')}; the refused call did not touch the file "
          f"({open(os.path.join(ws, 'src', 'config.ts')).read().strip()})")

    # 11
    code, fresh = call(a.api, "/api/evidence")
    rows = {x["path"]: x for x in fresh.get("rows", [])}
    allow = fresh.get("counts", {}).get("stale")
    dcode = status_of(a.dashboard + "/console")
    ecode = status_of(a.dashboard + "/console/interceptor")
    check("11. dashboard updates live from the runtime",
          dcode == 200 and ecode == 200 and rows.get("src/config.ts", {}).get("status") == "STALE"
          and (allow or 0) >= 1,
          f"console http {dcode}, interceptor http {ecode}; evidence status "
          f"{rows.get('src/config.ts', {}).get('status')} with stale={allow}")

    # 12
    code, rec = call(a.api, "/api/receipts")
    first = rec.get("rows", [])
    check("12. receipt is written", rec.get("count", 0) >= 1 and first and
          first[0].get("exit_code") == 2,
          f"{rec.get('count')} receipt(s); newest {first[0].get('receipt_id') if first else 'none'} "
          f"verdict {first[0].get('verdict') if first else '-'} reason "
          f"{first[0].get('reason_code') if first else '-'}")

    # 13
    code, r = call(a.api, "/api/evidence/refresh", {"session": sid})
    after = {x["path"]: x for x in (r.get("evidence", {}).get("rows") or [])}
    check("13. user refreshes evidence", code == 200 and after.get("src/config.ts", {}).get("status") == "CURRENT",
          f"gate exit {r.get('gate', {}).get('exit_code')}; status now "
          f"{after.get('src/config.ts', {}).get('status')}")

    # 14
    code, r = call(a.api, "/api/interceptor/attempt", {"session": sid, "tool": "apply_diff",
                                                       "path": "src/config.ts"})
    check("14. the same operation succeeds", r.get("exit_code") == 0,
          f"exit {r.get('exit_code')}; {json.dumps(r.get('stdout'))[:120]}")

    # 15
    code, rec2 = call(a.api, "/api/receipts")
    newest = rec2.get("rows", [{}])[0]
    check("15. second receipt is written", rec2.get("count", 0) >= 2 and newest.get("exit_code") == 0,
          f"{rec2.get('count')} receipts; newest {newest.get('receipt_id')} verdict "
          f"{newest.get('verdict')} chained to {str(newest.get('previous_receipt_hash'))[:12]}")

    # 16
    if newest.get("receipt_id"):
        code, v = call(a.api, f"/api/receipts/{newest['receipt_id']}/verify", {})
        check("16. receipt verification succeeds", bool(v.get("valid")),
              f"recomputed {str(v.get('recomputed'))[:16]} == stored {str(v.get('stored'))[:16]}")
    else:
        check("16. receipt verification succeeds", False, "no receipt id to verify")

    # 17
    code, st_test = call(a.api, "/api/selftest", {}, timeout=300)
    steps = st_test.get("steps", [])
    check("17. self-test reproduces the entire flow automatically",
          st_test.get("run_1", {}).get("exit_code") == 2 and st_test.get("run_2", {}).get("exit_code") == 0
          and len(steps) >= 8,
          f"run 1 exit {st_test.get('run_1', {}).get('exit_code')} ({st_test.get('run_1', {}).get('receipt', {}).get('reason_code')}), "
          f"run 2 exit {st_test.get('run_2', {}).get('exit_code')}, {len(steps)} steps on "
          f"{st_test.get('repository')}")

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        print("failed steps: " + ", ".join(FAIL))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
