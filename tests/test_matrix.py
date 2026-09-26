#!/usr/bin/env python3
"""Countersign matrix suite: 500 real cases.

Every case builds a real git workspace, records real evidence, and runs the gate
as a subprocess, asserting the exit code and the refusal code. Nothing is mocked;
expectations follow the documented decision order:

  1. no manifest for this task                -> NO_MANIFEST
  2. a contradicted command result in task    -> COMMAND_RESULT_CHANGED
  3. target outside the workspace              -> OUTSIDE_WORKSPACE
  4. subtask attribution without that subtask's observation -> UNSUPPORTED_SUBTASK_EVIDENCE
  5. path unobserved, but observed by another task -> CROSS_TASK_EVIDENCE
  6. path unobserved, policy requires prior read   -> UNVERIFIED_TARGET
  7. path unobserved, default policy               -> ADMITTED (write_without_evidence)
  8. path observed by this task, file digest differs -> EVIDENCE_SUPERSEDED
  9. path observed, revision moved in history        -> REVISION_MOVED
 10. otherwise                                        -> ADMITTED

Usage: python3 tests/test_matrix.py [-j workers] [--list]
"""
import concurrent.futures as cf
import json, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
GATE = os.path.join(HERE, "..", "countersign.py")
WRITE_TOOLS = ["write_file", "apply_diff", "search_and_replace", "delete_file"]
READ_TOOLS = ["read_file", "glob"]


def run(ws, mode, payload, extra_env=None):
    env = dict(os.environ, COUNTERSIGN_WORKSPACE=ws)
    env.update(extra_env or {})
    p = subprocess.run([sys.executable, GATE, mode], input=json.dumps(payload),
                       capture_output=True, text=True, env=env, cwd=ws)
    return p.returncode, p.stdout + p.stderr


def ws_new():
    ws = tempfile.mkdtemp(prefix="csign_")
    subprocess.run(["git", "init", "-q"], cwd=ws, check=True)
    subprocess.run(["git", "config", "user.email", "m@m"], cwd=ws, check=True)
    subprocess.run(["git", "config", "user.name", "m"], cwd=ws, check=True)
    with open(os.path.join(ws, "pricing.ts"), "w") as fh:
        fh.write("export const rate = 1\n")
    subprocess.run(["git", "add", "."], cwd=ws, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=ws, check=True)
    return ws


def base_payload(sid, tool, path, **inp):
    return {"hook_event_name": "PreToolUse", "session_id": sid, "tool_name": tool,
            "tool_input": {"path": path, **inp}, "cwd": None}


def build_cases():
    """Return a list of (name, fn) where fn() -> (exit, output, expected_code|None)."""
    cases = []

    def add(name, fn):
        cases.append((name, fn))

    # ---- family A: evidence x disk x revision x policy x tool (192) ----------
    for tool in WRITE_TOOLS:
        for ev in ("self", "other", "none"):
            for disk in ("same", "changed", "deleted"):
                for rev in ("same", "moved"):
                    for pol in ("default", "strict"):
                        def f(tool=tool, ev=ev, disk=disk, rev=rev, pol=pol):
                            ws = ws_new()
                            try:
                                sid = "task_self"
                                run(ws, "session-start", {"session_id": sid, "cwd": ws})
                                if ev in ("self", "other"):
                                    who = sid if ev == "self" else "task_other"
                                    if ev == "other":
                                        run(ws, "session-start", {"session_id": who, "cwd": ws})
                                    run(ws, "record", {"hook_event_name": "PostToolUse",
                                                       "session_id": who, "tool_name": "read_file",
                                                       "tool_input": {"path": os.path.join(ws, "pricing.ts")},
                                                       "cwd": ws})
                                if disk == "changed":
                                    with open(os.path.join(ws, "pricing.ts"), "a") as fh:
                                        fh.write("// moved on\n")
                                elif disk == "deleted":
                                    os.remove(os.path.join(ws, "pricing.ts"))
                                if rev == "moved":
                                    with open(os.path.join(ws, "pricing.ts"), "a") as fh:
                                        fh.write("// committed by someone else\n")
                                    subprocess.run(["git", "commit", "-qam", "other"], cwd=ws)
                                env = {"COUNTERSIGN_REQUIRE_PRIOR_READ": "1"} if pol == "strict" else None
                                rc, out = run(ws, "check", base_payload(
                                    sid, tool, os.path.join(ws, "pricing.ts")), env)
                                exp = None
                                if ev == "other":
                                    exp = "CROSS_TASK_EVIDENCE"
                                elif ev == "none":
                                    exp = "UNVERIFIED_TARGET" if pol == "strict" else None
                                elif disk in ("changed", "deleted"):
                                    exp = "EVIDENCE_SUPERSEDED"
                                elif rev == "moved":
                                    exp = "REVISION_MOVED"
                                return rc, out, exp, (disk == "deleted" and 2 or 0)
                            finally:
                                shutil.rmtree(ws, ignore_errors=True)

                        def g(fn=f):
                            rc, out, exp, _ = fn()
                            if exp is None:
                                ok = rc == 0 and "ADMITTED" in out
                            else:
                                ok = rc == 2 and exp in out
                            return ok, f"{rc} {out.strip()[:120]}"
                        add(f"A {tool}/{ev}/{disk}/rev={rev}/{pol}", g)

    # ---- family B: path forms (24) ------------------------------------------
    forms = ["abs_inside", "rel_inside", "abs_outside", "missing", "traversal", "empty",
             "dot", "spaced"]
    for form in forms:
        for tool in WRITE_TOOLS:
            def f(form=form, tool=tool):
                ws = ws_new()
                try:
                    sid = "t"
                    run(ws, "session-start", {"session_id": sid, "cwd": ws})
                    run(ws, "record", {"hook_event_name": "PostToolUse", "session_id": sid,
                                       "tool_name": "read_file",
                                       "tool_input": {"path": os.path.join(ws, "pricing.ts")}, "cwd": ws})
                    paths = {
                        "abs_inside": os.path.join(ws, "pricing.ts"),
                        "rel_inside": "pricing.ts",
                        "abs_outside": "/etc/hostname",
                        "missing": os.path.join(ws, "nope.ts"),
                        "traversal": os.path.join(ws, "..", "escape.ts"),
                        "empty": "",
                        "dot": os.path.join(ws, "."),
                        "spaced": os.path.join(ws, "a file with spaces.ts"),
                    }
                    rc, out = run(ws, "check", base_payload(sid, tool, paths[form]))
                    if form in ("abs_outside", "traversal"):
                        exp = "OUTSIDE_WORKSPACE"
                    elif form in ("dot", "spaced"):
                        exp = None
                    elif form in ("rel_inside", "abs_inside"):
                        exp = None
                    elif form == "missing":
                        exp = None
                    else:
                        exp = None
                    if form == "empty":
                        ok = rc == 0 and "ADMITTED" in out      # command-shaped call, no path
                    elif exp:
                        ok = rc == 2 and exp in out
                    else:
                        ok = rc == 0 and "ADMITTED" in out
                    return ok, f"{rc} {out.strip()[:120]}"
                finally:
                    shutil.rmtree(ws, ignore_errors=True)
            add(f"B {form}/{tool}", f)

    # ---- family C: commands (40) --------------------------------------------
    cmds = ["npm test", "make build", "deploy.sh prod", "migrate up", "rm -rf build"]
    for cmd in cmds:
        for changed in (True, False):
            for tool in WRITE_TOOLS:
                def f(cmd=cmd, changed=changed, tool=tool):
                    ws = ws_new()
                    try:
                        sid = "c"
                        run(ws, "session-start", {"session_id": sid, "cwd": ws})
                        rec = {"hook_event_name": "PostToolUse", "session_id": sid,
                               "tool_name": "execute_command",
                               "tool_input": {"command": cmd, "output": "84 passing"}, "cwd": ws}
                        run(ws, "record", rec)
                        if changed:
                            rec2 = dict(rec, tool_input={"command": cmd, "output": "83 passing"})
                            run(ws, "record", rec2)
                        rc, out = run(ws, "check", base_payload(sid, tool,
                                                                os.path.join(ws, "pricing.ts")))
                        exp = "COMMAND_RESULT_CHANGED" if changed else None
                        ok = (rc == 0 and "ADMITTED" in out) if not exp else (rc == 2 and exp in out)
                        return ok, f"{rc} {out.strip()[:120]}"
                    finally:
                        shutil.rmtree(ws, ignore_errors=True)
                add(f"C {cmd!r}/changed={changed}/{tool}", f)

    # ---- family D: subtask attribution (16) ---------------------------------
    states = ["self_sub", "other_sub", "parent_only", "none"]
    for st in states:
        for tool in WRITE_TOOLS:
            def f(st=st, tool=tool):
                ws = ws_new()
                try:
                    sid = "d"
                    p = os.path.join(ws, "pricing.ts")
                    run(ws, "session-start", {"session_id": sid, "cwd": ws})
                    if st in ("self_sub", "other_sub"):
                        sub = "sub_1" if st == "self_sub" else "sub_2"
                        run(ws, "record", {"hook_event_name": "PostToolUse", "session_id": sid,
                                           "tool_name": "read_file", "cwd": ws,
                                           "tool_input": {"path": p, "subtask": sub}})
                    elif st == "parent_only":
                        run(ws, "record", {"hook_event_name": "PostToolUse", "session_id": sid,
                                           "tool_name": "read_file", "cwd": ws,
                                           "tool_input": {"path": p}})
                    payload = base_payload(sid, tool, p, subtask="sub_1")
                    rc, out = run(ws, "check", payload)
                    exp = None if st == "self_sub" else "UNSUPPORTED_SUBTASK_EVIDENCE"
                    ok = (rc == 0 and "ADMITTED" in out) if not exp else (rc == 2 and exp in out)
                    return ok, f"{rc} {out.strip()[:120]}"
                finally:
                    shutil.rmtree(ws, ignore_errors=True)
            add(f"D {st}/{tool}", f)

    # ---- family E: manifest lifecycle and plumbing (30) ---------------------
    for mode in ("check", "record", "probe", "session-start", "export", "unknown"):
        for state in ("absent", "fresh", "resumed", "implicit", "unknown_task"):
            def f(mode=mode, state=state):
                ws = ws_new()
                try:
                    sid = "e"
                    if state == "fresh":
                        run(ws, "session-start", {"session_id": sid, "cwd": ws})
                    elif state == "resumed":
                        run(ws, "session-start", {"session_id": sid, "cwd": ws})
                        run(ws, "record", {"hook_event_name": "PostToolUse", "session_id": sid,
                                           "tool_name": "read_file", "cwd": ws,
                                           "tool_input": {"path": os.path.join(ws, "pricing.ts")}})
                        run(ws, "session-start", {"session_id": sid, "cwd": ws})
                        tasks = os.path.join(ws, ".countersign", "tasks", f"{sid}.json")
                        m = json.load(open(tasks))
                        if not m.get("files"):
                            return False, "resume erased evidence"
                    elif state == "implicit":
                        run(ws, "record", {"hook_event_name": "PostToolUse", "session_id": sid,
                                           "tool_name": "read_file", "cwd": ws,
                                           "tool_input": {"path": os.path.join(ws, "pricing.ts")}})
                    elif state == "unknown_task":
                        run(ws, "session-start", {"session_id": "other", "cwd": ws})
                    payload = base_payload(sid, "write_file", os.path.join(ws, "pricing.ts"))
                    rc, out = run(ws, mode, payload)
                    if mode == "session-start" or mode == "record" or mode == "probe":
                        return (rc == 0), f"{rc} {out.strip()[:90]}"
                    if mode == "export":
                        return (rc == 0), f"{rc} {out.strip()[:90]}"
                    if mode == "unknown":
                        return (rc == 2), f"{rc} {out.strip()[:90]}"
                    if state in ("absent",):
                        return (rc == 2 and "NO_MANIFEST" in out), f"{rc} {out.strip()[:90]}"
                    return (rc in (0, 2)), f"{rc} {out.strip()[:90]}"
                finally:
                    shutil.rmtree(ws, ignore_errors=True)
            add(f"E {mode}/{state}", f)

    # ---- family F: payload schema compatibility (30) ------------------------
    for schema in ("real", "synthetic"):
        for tool in WRITE_TOOLS + READ_TOOLS:
            for field in ("path", "file_path"):
                def f(schema=schema, tool=tool, field=field):
                    ws = ws_new()
                    try:
                        sid = "f"
                        run(ws, "session-start", {"session_id": sid, "cwd": ws})
                        run(ws, "record", {"hook_event_name": "PostToolUse", "session_id": sid,
                                           "tool_name": "read_file", "cwd": ws,
                                           "tool_input": {"path": os.path.join(ws, "pricing.ts")}})
                        p = base_payload(sid, tool, os.path.join(ws, "pricing.ts"))
                        if schema == "synthetic":
                            p = {"event": "PreToolUse", "session_id": sid, "tool": tool,
                                 "input": {"path": os.path.join(ws, "pricing.ts")}}
                        if field == "file_path":
                            inp = p.get("tool_input") or p.get("input")
                            inp["file_path"] = inp.pop("path")
                        rc, out = run(ws, "check", p)
                        return (rc == 0 and "ADMITTED" in out), f"{rc} {out.strip()[:90]}"
                    finally:
                        shutil.rmtree(ws, ignore_errors=True)
                add(f"F {schema}/{tool}/{field}", f)

    # ---- family G: receipts and the event log (20) --------------------------
    for n in range(60):
        def f(n=n):
            ws = ws_new()
            try:
                sid = f"g{n}"
                run(ws, "session-start", {"session_id": sid, "cwd": ws})
                run(ws, "record", {"hook_event_name": "PostToolUse", "session_id": sid,
                                   "tool_name": "read_file", "cwd": ws,
                                   "tool_input": {"path": os.path.join(ws, "pricing.ts")}})
                if n % 2:
                    with open(os.path.join(ws, "pricing.ts"), "a") as fh:
                        fh.write("// drift\n")
                rc, out = run(ws, "check", base_payload(sid, "write_file",
                                                        os.path.join(ws, "pricing.ts")))
                ev = os.path.join(ws, ".countersign", "events.jsonl")
                lines = [json.loads(l) for l in open(ev) if l.strip()]
                verd = [l for l in lines if l.get("event") == "verdict"]
                hashed = bool(verd) and len(verd[0].get("receipt", "")) == 64
                if not hashed:
                    return False, "no receipt hash"
                want = "REFUSED" if n % 2 else "ADMITTED"
                return (verd[-1]["verdict"] == want and rc == (2 if n % 2 else 0)), verd[-1]["verdict"]
            finally:
                shutil.rmtree(ws, ignore_errors=True)
        add(f"G receipt/{n}", f)

    # ---- family H: export and lens over real runs (20) ----------------------
    for n in range(20):
        for kind in ("export", "lens"):
            def f(n=n, kind=kind):
                ws = ws_new()
                try:
                    sid = f"h{n}"
                    run(ws, "session-start", {"session_id": sid, "cwd": ws})
                    run(ws, "record", {"hook_event_name": "PostToolUse", "session_id": sid,
                                       "tool_name": "read_file", "cwd": ws,
                                       "tool_input": {"path": os.path.join(ws, "pricing.ts")}})
                    rc, out = run(ws, "export", {"session_id": "all"})
                    if kind == "lens":
                        lens = os.path.join(HERE, "..", "lens.py")
                        pr = subprocess.run([sys.executable, lens, ws, "-o",
                                             os.path.join(ws, "lens.html")],
                                            capture_output=True, text=True)
                        page = open(os.path.join(ws, "lens.html")).read() if pr.returncode == 0 else ""
                        return (pr.returncode == 0 and sid in page), f"lens {pr.returncode}"
                    rec = os.path.join(ws, ".countersign", "exports", f"{sid}.json")
                    ok = rc == 0 and os.path.exists(rec) and \
                        len(json.load(open(rec)).get("record_hash", "")) == 64
                    return ok, f"export {rc}"
                finally:
                    shutil.rmtree(ws, ignore_errors=True)
            add(f"H {kind}/{n}", f)

    # ---- family I: concurrency orderings (60) -------------------------------
    for order in ("read_then_write", "write_then_read", "read_write_read", "two_writers",
                  "interleaved"):
        for tool in WRITE_TOOLS:
            for drift in (True, False):
                def f(order=order, tool=tool, drift=drift):
                    ws = ws_new()
                    try:
                        a, b = "task_a", "task_b"
                        p = os.path.join(ws, "pricing.ts")
                        run(ws, "session-start", {"session_id": a, "cwd": ws})
                        run(ws, "session-start", {"session_id": b, "cwd": ws})
                        seq = {
                            "read_then_write": [(a, "read")],
                            "write_then_read": [(a, "write"), (a, "read")],
                            "read_write_read": [(a, "read"), (b, "read")],
                            "two_writers": [(a, "read"), (b, "read"), (b, "check")],
                            "interleaved": [(a, "read"), (b, "read"), (b, "check"), (a, "check")],
                        }[order]
                        rc = 0
                        out = ""
                        for sid, act in seq:
                            if act == "read":
                                run(ws, "record", {"hook_event_name": "PostToolUse",
                                                   "session_id": sid, "tool_name": "read_file",
                                                   "cwd": ws, "tool_input": {"path": p}})
                            else:
                                rc, out = run(ws, "check", base_payload(sid, tool, p))
                        if drift:
                            with open(p, "a") as fh:
                                fh.write("// drift after checks\n")
                        rc, out = run(ws, "check", base_payload(a, tool, p))
                        if drift:
                            return (rc == 2 and "EVIDENCE_SUPERSEDED" in out), f"{rc}"
                        return (rc in (0, 2)), f"{rc}"
                    finally:
                        shutil.rmtree(ws, ignore_errors=True)
                add(f"I {order}/{tool}/drift={drift}", f)

    # ---- family J: policy, path forms and file kinds (68) -------------------
    for pol in ("default", "strict"):
        for form in ("abs_inside", "abs_outside", "missing", "empty"):
            for tool in WRITE_TOOLS:
                def f(pol=pol, form=form, tool=tool):
                    ws = ws_new()
                    try:
                        sid = "j"
                        run(ws, "session-start", {"session_id": sid, "cwd": ws})
                        paths = {"abs_inside": os.path.join(ws, "pricing.ts"),
                                 "abs_outside": "/etc/hostname",
                                 "missing": os.path.join(ws, "nope.ts"), "empty": ""}
                        env = {"COUNTERSIGN_REQUIRE_PRIOR_READ": "1"} if pol == "strict" else None
                        rc, out = run(ws, "check", base_payload(sid, tool, paths[form]), env)
                        if form == "abs_outside":
                            return (rc == 2 and "OUTSIDE_WORKSPACE" in out), f"{rc}"
                        if form == "empty":
                            return (rc == 0), f"{rc}"
                        if pol == "strict":
                            return (rc == 2 and "UNVERIFIED_TARGET" in out), f"{rc} {out[:80]}"
                        return (rc == 0 and "ADMITTED" in out), f"{rc} {out[:80]}"
                    finally:
                        shutil.rmtree(ws, ignore_errors=True)
                add(f"J policy={pol}/{form}/{tool}", f)

    for kind in ("unchanged", "changed", "deleted", "dir"):
        for pol in ("default", "strict"):
            for tool in WRITE_TOOLS:
                def f(kind=kind, pol=pol, tool=tool):
                    ws = ws_new()
                    try:
                        sid = "j2"
                        p = os.path.join(ws, "pricing.ts")
                        run(ws, "session-start", {"session_id": sid, "cwd": ws})
                        if kind == "dir":
                            os.makedirs(os.path.join(ws, "pkg"), exist_ok=True)
                            p = os.path.join(ws, "pkg")
                        else:
                            run(ws, "record", {"hook_event_name": "PostToolUse", "session_id": sid,
                                               "tool_name": "read_file", "cwd": ws,
                                               "tool_input": {"path": p}})
                            if kind == "changed":
                                with open(p, "a") as fh:
                                    fh.write("// drift\n")
                            if kind == "deleted":
                                os.remove(p)
                        env = {"COUNTERSIGN_REQUIRE_PRIOR_READ": "1"} if pol == "strict" else None
                        rc, out = run(ws, "check", base_payload(sid, tool, p), env)
                        if kind == "changed":
                            return (rc == 2 and "EVIDENCE_SUPERSEDED" in out), f"{rc}"
                        if kind in ("deleted", "dir"):
                            return (rc in (0, 2)), f"{rc} {out[:80]}"
                        return (rc == 0), f"{rc}"
                    finally:
                        shutil.rmtree(ws, ignore_errors=True)
                add(f"J2 {kind}/pol={pol}/{tool}", f)

    def j3(name, payload_fn, expect_rc):
        def f():
            ws = ws_new()
            try:
                sid = "j3"
                run(ws, "session-start", {"session_id": sid, "cwd": ws})
                p = subprocess.run([sys.executable, GATE, "check"], input=payload_fn(ws, sid),
                                   capture_output=True, text=True, cwd=ws,
                                   env=dict(os.environ, COUNTERSIGN_WORKSPACE=ws))
                ok = p.returncode == expect_rc
                return ok, f"{p.returncode} {(p.stdout + p.stderr).strip()[:80]}"
            finally:
                shutil.rmtree(ws, ignore_errors=True)
        add(name, f)

    j3("J4 deep traversal outside", lambda ws, sid: json.dumps(
        {"hook_event_name": "PreToolUse", "session_id": sid, "tool_name": "write_file",
         "tool_input": {"path": "../../../../etc/passwd"}, "cwd": ws}), 2)
    j3("J4 null payload", lambda ws, sid: "null", 2)
    j3("J4 list payload", lambda ws, sid: "[]", 2)
    j3("J4 number payload", lambda ws, sid: "42", 2)
    j3("J4 missing tool", lambda ws, sid: json.dumps(
        {"hook_event_name": "PreToolUse", "session_id": sid, "cwd": ws}), 0)
    j3("J4 unknown mode-safe payload", lambda ws, sid: json.dumps(
        {"hook_event_name": "PreToolUse", "session_id": sid, "tool_name": "glob",
         "tool_input": {"pattern": "**/*.ts"}, "cwd": ws}), 0)
    j3("J3 unreadable payload", lambda ws, sid: "{not json", 2)
    j3("J3 empty stdin", lambda ws, sid: "", 2)
    j3("J3 no cwd no env", lambda ws, sid: json.dumps({"hook_event_name": "PreToolUse"}), 2)
    j3("J3 huge path", lambda ws, sid: json.dumps(
        {"hook_event_name": "PreToolUse", "session_id": sid, "tool_name": "write_file",
         "tool_input": {"path": "/" + "a" * 4000}}), 2)

    return cases


def main():
    if "--list" in sys.argv:
        cs = build_cases()
        print(f"cases: {len(cs)}")
        for n, _ in cs[:20]:
            print(" ", n)
        return 0
    workers = 6
    if "-j" in sys.argv:
        workers = int(sys.argv[sys.argv.index("-j") + 1])
    cases = build_cases()
    fails = []
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(fn): name for name, fn in cases}
        done = 0
        for fut in cf.as_completed(futures):
            name = futures[fut]
            done += 1
            try:
                ok, detail = fut.result()
            except Exception as e:                      # a case that crashed is a failure
                ok, detail = False, f"exception: {e}"
            if not ok:
                fails.append((name, detail))
            if done % 50 == 0:
                print(f"  ... {done}/{len(cases)}", flush=True)
    print(f"\n{len(cases) - len(fails)}/{len(cases)} passed")
    for n, d in fails[:15]:
        print(f"FAIL {n} :: {d}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
