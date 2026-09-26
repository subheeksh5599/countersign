#!/usr/bin/env python3
"""COUNTERSIGN -- a page scraped clean and written over, with the old text still
faintly visible. An agent transcript is that page: the file it describes may
already have changed underneath it, and the task keeps reading from the old text.

The gate refuses a state-changing tool action whose supporting evidence no longer
describes the workspace the action is about to touch. The verdict is computed from
digests, task identity and commit identity stored on disk. No model participates.

Modes, driven by the vendor's lifecycle hook payloads on stdin:
  session-start   open an evidence manifest for this task
  record          record the identity of evidence observed (file reads, commands)
  check           before a state-changing call: admit, or refuse with exit 2

Environment only, no defaults:
  COUNTERSIGN_WORKSPACE           absolute path of the workspace under control
  COUNTERSIGN_REQUIRE_PRIOR_READ  "1" refuses writes to never-observed paths
"""
import hashlib, json, os, subprocess, sys, time

WS = os.environ.get("COUNTERSIGN_WORKSPACE")
STORE = TASKS = EVENTS = None
REQUIRE_PRIOR_READ = os.environ.get("COUNTERSIGN_REQUIRE_PRIOR_READ") == "1"


def bind_workspace(ws):
    """Resolve the workspace and its store. The environment variable wins; the cwd
    every hook payload carries is the fallback, so a global hook works in any
    workspace without per-project configuration. With neither, nothing is verified
    and the caller fails closed."""
    global WS, STORE, TASKS, EVENTS
    WS = ws
    STORE = os.path.join(WS, ".countersign")
    TASKS = os.path.join(STORE, "tasks")
    EVENTS = os.path.join(STORE, "events.jsonl")


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def digest(b):
    return hashlib.sha256(b).hexdigest()


def relpath_in_workspace(p):
    """Tool payloads carry absolute paths. Evidence is keyed by workspace-relative
    path; anything outside the workspace is reported as outside, not silently
    rewritten into a relative path that could collide."""
    if not p:
        return "", False
    ap = os.path.abspath(p) if os.path.isabs(p) else os.path.abspath(os.path.join(WS, p))
    root = os.path.abspath(WS)
    if ap == root or ap.startswith(root + os.sep):
        return os.path.relpath(ap, root), False
    return os.path.abspath(p), True


def file_digest(rel):
    try:
        with open(os.path.join(WS, rel), "rb") as fh:
            return digest(fh.read())
    except (FileNotFoundError, IsADirectoryError):
        return None


def revision_of(rel):
    """Blob id of this path in the current commit, or None."""
    p = subprocess.run(["git", "rev-parse", f"HEAD:{rel}"], cwd=WS,
                       capture_output=True, text=True)
    return p.stdout.strip() or None


def commit_id():
    p = subprocess.run(["git", "rev-parse", "HEAD"], cwd=WS, capture_output=True, text=True)
    return p.stdout.strip() or None


def task_path(sid):
    return os.path.join(TASKS, f"{sid}.json")


def load_task(sid):
    p = task_path(sid)
    if os.path.exists(p):
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    return None


def save_task(sid, m):
    os.makedirs(TASKS, exist_ok=True)
    p = task_path(sid)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(m, fh, indent=2, sort_keys=True)
    os.replace(tmp, p)


def foreign_evidence(path, own_sid):
    """Newest observation of `path` recorded by some other task, if any."""
    best = None
    if not os.path.isdir(TASKS):
        return None
    for name in sorted(os.listdir(TASKS)):
        if not name.endswith(".json") or name[:-5] == own_sid:
            continue
        with open(os.path.join(TASKS, name), encoding="utf-8") as fh:
            m = json.load(fh)
        rec = (m.get("files") or {}).get(path)
        if rec and (best is None or rec["at"] > best[1]["at"]):
            best = (name[:-5], rec)
    return best


def emit(kind, **kw):
    os.makedirs(STORE, exist_ok=True)
    with open(EVENTS, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"at": now(), "event": kind, **kw}, sort_keys=True) + "\n")


def receipt(**kw):
    r = {"at": now(), **kw}
    r["receipt"] = digest(json.dumps(r, sort_keys=True, separators=(",", ":")).encode())
    emit("verdict", **r)
    return r


def read_events():
    out = []
    if os.path.exists(EVENTS):
        with open(EVENTS, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
    return out


def export(sid):
    """Write one hashed evidence record per task: what it observed, what it ran,
    what was refused. Real records only."""
    events = read_events()
    d = os.path.join(STORE, "exports")
    os.makedirs(d, exist_ok=True)
    written = []
    for name in sorted(os.listdir(TASKS)) if os.path.isdir(TASKS) else []:
        if not name.endswith(".json"):
            continue
        task = name[:-5]
        if sid != "all" and task != sid:
            continue
        m = load_task(task)
        verdicts = [e for e in events if e.get("event") == "verdict" and e.get("task") == task]
        rec = {
            "task": task,
            "commit": m.get("commit"),
            "opened_at": m.get("opened_at"),
            "implicit": m.get("implicit"),
            "observations": sorted(
                ({"path": p, "digest": v.get("digest"), "via": v.get("via", "direct"),
                  "at": v.get("at")} for p, v in (m.get("files") or {}).items()),
                key=lambda x: x["path"]),
            "commands": sorted(
                ({"command": c, "digest": v.get("digest"), "at": v.get("at")}
                 for c, v in (m.get("commands") or {}).items()),
                key=lambda x: x["command"]),
            "contradictions": m.get("contradictions", []),
            "verdicts": [{"at": v.get("at"), "verdict": v.get("verdict"),
                          "path": v.get("path"), "codes": v.get("codes"),
                          "receipt": v.get("receipt")} for v in verdicts],
        }
        rec["record_hash"] = digest(json.dumps(rec, sort_keys=True).encode())
        with open(os.path.join(d, f"{task}.json"), "w", encoding="utf-8") as fh:
            json.dump(rec, fh, indent=2, sort_keys=True)
        written.append(f"{task}.json")
    emit("exported", tasks=written)
    print(json.dumps({"exported": written, "dir": os.path.join(STORE, "exports")}))
    return 0


def refuse(code, lines):
    print(f"REFUSED: {code}")
    for l in lines:
        print(l)
    print("The action did not happen.")
    return 2


def admit(note):
    print(json.dumps({"verdict": "ADMITTED", "note": note}))
    return 0


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        sys.stderr.write(f"unreadable hook payload: {e}\n")
        return 2
    if not isinstance(payload, dict):
        sys.stderr.write("hook payload is not an object: failing closed\n")
        return 2
    if not WS:
        bind_workspace(payload.get("cwd"))
    if not WS:
        sys.stderr.write("no workspace: set COUNTERSIGN_WORKSPACE or supply cwd in the "
                         "hook payload\n")
        return 2
    if STORE is None:
        bind_workspace(WS)
    sid = payload.get("session_id") or "unknown"
    inp = payload.get("tool_input") or payload.get("input") or {}
    tool = payload.get("tool_name") or payload.get("tool")
    raw = inp.get("path") or inp.get("file_path") or ""
    path, outside = relpath_in_workspace(raw)

    if mode == "session-start":
        existing = load_task(sid)
        if existing is not None:
            # a resumed task must not lose the evidence it already holds
            existing["resumed_at"] = now()
            save_task(sid, existing)
            emit("manifest_resumed", task=sid,
                 observations=len(existing.get("files") or {}))
            return admit("manifest resumed, evidence preserved")
        m = {"task": sid, "commit": commit_id(), "opened_at": now(),
             "implicit": False, "files": {}, "commands": {}, "contradictions": []}
        save_task(sid, m)
        emit("manifest_opened", task=sid, commit=m["commit"])
        return admit("manifest opened")

    if mode == "probe":
        d = os.path.join(STORE, "payloads")
        os.makedirs(d, exist_ok=True)
        n = len([f for f in os.listdir(d) if f.endswith(".json")])
        ev = payload.get("hook_event_name") or payload.get("event") or "unknown"
        rel = os.path.join(".countersign", "payloads", f"{n:04d}_{ev}.json")
        with open(os.path.join(WS, rel), "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, sort_keys=True)
        emit("payload_probed", file=rel, event=payload.get("event"), tool=payload.get("tool"))
        return admit(f"payload recorded at {rel}")

    m = load_task(sid)

    if mode == "record":
        if m is None:                      # a read is never blocked: open implicitly
            m = {"task": sid, "commit": commit_id(), "opened_at": now(),
                 "implicit": True, "files": {}, "commands": {}, "contradictions": []}
            save_task(sid, m)
            emit("manifest_implicit", task=sid)
        if tool in ("execute_command", "run_command", "shell", "bash", "terminal"):
            cmd = inp.get("command") or ""
            d = digest(str(inp.get("output", "")).encode())
            prev = m["commands"].get(cmd)
            if prev and prev["digest"] != d:
                m["contradictions"].append({"command": cmd, "was": prev["digest"],
                                            "now": d, "task": sid})
                emit("command_contradicted", task=sid, command=cmd)
            m["commands"][cmd] = {"digest": d, "at": now(), "task": sid}
        else:
            sub = inp.get("subtask") or payload.get("subagent_id")
            via = f"subagent:{sub}" if sub else "direct"
            m["files"][path] = {"digest": file_digest(path), "at": now(), "task": sid,
                                "via": via, "revision": revision_of(path)}
            emit("evidence_recorded", path=path, digest=m["files"][path]["digest"],
                 task=sid, via=via)
        save_task(sid, m)
        return admit("evidence recorded")

    if mode == "export":
        return export(sid)

    if mode != "check":  # unknown modes must fail closed, never raise
        sys.stderr.write(f"unknown mode: {mode!r}\n")
        return 2

    if m is None:
        return refuse("NO_MANIFEST",
                      ["No evidence manifest exists for this task.",
                       f"Expected it at {task_path(sid)}.",
                       "Nothing this task relies on has been recorded, so nothing can be "
                       "verified. Fail closed."])

    if outside:
        r = receipt(task=sid, path=path, verdict="REFUSED", codes=["OUTSIDE_WORKSPACE"])
        return refuse("OUTSIDE_WORKSPACE",
                      [f"The proposed action targets {path}, outside the workspace {WS}.",
                       "No evidence can exist for a path this gate never observes, so the",
                       "action cannot be verified.",
                       "Required recovery: run the action inside the workspace, or record",
                       "the path explicitly.",
                       f"Refusal receipt: {r['receipt']}"])

    live = [c for c in m.get("contradictions", []) if c["task"] == sid]
    if live:
        c = live[0]
        r = receipt(task=sid, path=path, verdict="REFUSED", codes=["COMMAND_RESULT_CHANGED"])
        return refuse("COMMAND_RESULT_CHANGED",
                      [f"This task holds a contradicted result for `{c['command']}`.",
                       f"  observed {c['was'][:12]} -> now {c['now'][:12]}",
                       "A state-changing call cannot proceed on a result that changed "
                       "underneath the task.",
                       "Required recovery: reopen the task and rerun the affected commands.",
                       f"Refusal receipt: {r['receipt']}"])

    if not path:
        emit("command_attempted", task=sid, command=inp.get("command") or "")
        return admit("no contradicted command evidence in this task")

    sub = inp.get("subtask") or payload.get("subagent_id")
    if sub:
        rec = m["files"].get(path)
        if not rec or rec.get("via") != f"subagent:{sub}":
            r = receipt(task=sid, path=path, verdict="REFUSED",
                        codes=["UNSUPPORTED_SUBTASK_EVIDENCE"])
            return refuse("UNSUPPORTED_SUBTASK_EVIDENCE",
                          [f"The proposed change to {path} is attributed to subtask {sub}.",
                           "No observation of that path by that subtask is on record.",
                           "The conclusion arrived without evidence behind it.",
                           "Required recovery: let the subtask observe the path, or "
                           "re-observe it in this task.",
                           f"Refusal receipt: {r['receipt']}"])

    reasons, own = [], m["files"].get(path)
    if own is None:
        foreign = foreign_evidence(path, sid)
        if foreign:
            other, rec = foreign
            reasons.append(("CROSS_TASK_EVIDENCE", other, sid,
                            "the only recorded evidence for this path belongs to another task"))
        elif REQUIRE_PRIOR_READ:
            return refuse("UNVERIFIED_TARGET",
                          [f"{path} has never been observed by any task.",
                           "Policy requires prior observation before a state-changing call."])
        else:
            emit("write_without_evidence", task=sid, path=path)
            return admit("no recorded evidence for this path")
    else:
        current = file_digest(path)
        if current != own["digest"]:
            reasons.append(("EVIDENCE_SUPERSEDED", own["digest"], current,
                            "the file changed after this task observed it"))
        rev_now = revision_of(path)
        if own.get("revision") and rev_now and rev_now != own["revision"]:
            reasons.append(("REVISION_MOVED", own["revision"], rev_now,
                            "this path was committed at a different revision after the "
                            "task observed it"))

    if not reasons:
        r = receipt(task=sid, path=path, verdict="ADMITTED", evidence_digest=own["digest"])
        return admit(f"evidence current, receipt {r['receipt'][:12]}")

    lines = [f"About to modify {path}."]
    if own:
        cur = file_digest(path)
        lines.append(f"Evidence this task holds: {str(own['digest'])[:12]}.")
        lines.append(f"Digest on disk now: {str(cur)[:12] if cur else 'file missing'}.")
    for code, was, isnow, why in reasons:
        lines.append(f"  {code}: {str(was)[:12]} -> {str(isnow)[:12]} ({why})")
    lines += ["Required recovery:", "  1. open a fresh task",
              f"  2. re-observe {path}", "  3. rerun the affected commands",
              "  4. record the new evidence manifest"]
    r = receipt(task=sid, path=path, verdict="REFUSED", codes=[x[0] for x in reasons])
    lines.append(f"Refusal receipt: {r['receipt']}")
    return refuse(reasons[0][0], lines)


if __name__ == "__main__":
    sys.exit(main())
