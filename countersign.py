#!/usr/bin/env python3
"""COUNTERSIGN -- the gate.

An agent transcript is a page written over an older page: the file it describes may
already have changed underneath it, and the task keeps reading from the old text.

Before a state-changing tool call this gate compares the evidence the task holds
(file digests, command results, committed revision) against the repository right now.
If they disagree the call is refused with exit code 2, and a receipt is persisted.

The verdict is a hash comparison. No model participates.

Modes (hook payload on stdin, JSON):
  session-start   open an evidence manifest for this task
  record          record evidence observed (file reads, command results)
  check           before a state-changing call: admit, or refuse with exit 2
  refresh         re-hash held evidence and update the manifest (real mutation)
  recheck         dry run: compute the verdict, change nothing, write no receipt
  replay          recompute every stored verdict from its own recorded inputs
  probe           record raw payloads without ever blocking
  export          write one hashed evidence record per task

Environment only, no defaults:
  COUNTERSIGN_WORKSPACE           absolute path of the workspace under control
  COUNTERSIGN_REQUIRE_PRIOR_READ  "1" refuses writes to never-observed paths
"""
import hashlib, json, os, re, subprocess, sys, time

WS = os.environ.get("COUNTERSIGN_WORKSPACE")
STORE = TASKS = EVENTS = RECEIPTS = None
REQUIRE_PRIOR_READ = os.environ.get("COUNTERSIGN_REQUIRE_PRIOR_READ") == "1"
STARTED = time.time()

# ---------------------------------------------------------------- tool policy
# Explicit classification. Unknown state-changing tools fail closed: the gate must
# decide about a mutation it does not recognise, not wave it through.
READ_ONLY_TOOLS = {
    "read_file", "glob", "grep", "search", "list_dir", "list_files", "ls",
    "view_file", "open_file", "cat", "head", "tail", "stat", "file_info",
    "web_search", "web_fetch", "todo_read", "think",
}
STATE_CHANGING_TOOLS = {
    "write_file", "apply_diff", "search_and_replace", "edit_file", "create_file",
    "str_replace", "insert_content", "append_file", "delete_file", "remove_file",
    "move_file", "rename_file", "copy_file", "mkdir", "execute_command",
    "run_command", "shell", "bash", "terminal", "git_commit", "git_checkout",
    "git_reset", "git_merge", "git_rebase", "package_install",
}
MUTATING_COMMAND_PATTERNS = [
    (re.compile(r"\bgit\s+(commit|checkout|reset|merge|rebase|cherry-pick|revert|clean|push|apply|stash)\b"), "git mutation"),
    (re.compile(r"\b(npm|pnpm|yarn|bun)\s+(i|install|add|remove|uninstall|update|upgrade)\b"), "package install that changes lockfiles"),
    (re.compile(r"\b(pip|pip3|poetry|uv)\s+(install|add|remove|uninstall)\b"), "package install"),
    (re.compile(r"\b(rm|rmdir|mv|cp|install|truncate|tee)\b"), "filesystem mutation"),
    (re.compile(r"\bsed\s+-i\b|\bperl\s+-i\b"), "in-place edit"),
    (re.compile(r"\b(chmod|chown|ln)\b"), "permission or link change"),
    (re.compile(r"(^|[^>])>{1,2}[^>]"), "shell redirect writes a file"),
    (re.compile(r"\b(codegen|scaffold|generate)\b"), "code generation into the repository"),
]
# Commands that only observe. Anything absent from this list and matching no mutation
# pattern is refused rather than assumed harmless.
READ_ONLY_COMMANDS = re.compile(
    r"^git\s+(status|log|diff|show|rev-parse|describe|ls-files|ls-tree|cat-file|blame|"
    r"shortlog|remote\s+-v|branch|tag|stash\s+list|config\s+--get)\b"
    r"|^(ls|cat|head|tail|wc|grep|rg|find|file|stat|pwd|which|env|du|df|tree|jq|sort|uniq|"
    r"cut|echo|printf|sed\s+-n|node\s+--version|python3?\s+--version|npm\s+(ls|view))\b")


REDACT_KEYS = re.compile(
    r"(api[_-]?key|token|secret|password|passwd|authorization|auth|cookie|"
    r"private[_-]?key|credential|bearer|session[_-]?key|access[_-]?key)", re.I)
REDACT_VALUES = re.compile(
    r"(sk-[A-Za-z0-9]{12,}|ghp_[A-Za-z0-9]{12,}|gho_[A-Za-z0-9]{12,}|"
    r"bob_prod_[A-Za-z0-9_.-]{12,}|xox[baprs]-[A-Za-z0-9-]{10,}|"
    r"eyJ[A-Za-z0-9._-]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)")


def classify(tool, inp):
    """Return (kind, reason). Deterministic, no model.

    A shell call is judged by its command first: a mutation pattern makes it
    state-changing, an explicit read-only allowlist makes it read-only, and anything
    else fails closed, because an unreadable command must not be waved through.
    """
    cmd = str(inp.get("command") or inp.get("cmd") or "")
    if cmd:
        for pat, why in MUTATING_COMMAND_PATTERNS:
            if pat.search(cmd):
                return "state_changing", f"mutating command: {why}"
        if READ_ONLY_COMMANDS.match(cmd.strip()):
            return "read_only", "command is in the read-only allowlist and mutates nothing"
        return "state_changing", ("command is not in the read-only allowlist: fail closed")
    if tool in STATE_CHANGING_TOOLS:
        return "state_changing", f"tool {tool} is classified state-changing"
    if tool in READ_ONLY_TOOLS:
        return "read_only", f"tool {tool} is classified read-only"
    if tool is None:
        return "state_changing", "no tool name in the payload: fail closed"
    return "state_changing", f"tool {tool} is not in the read-only policy: fail closed"


def redact(value, depth=0):
    """Mask secrets but keep the shape of the arguments, so a reviewer can see which
    operation was intercepted and what it was aimed at."""
    if depth > 6:
        return "<deeply nested>"
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if isinstance(v, str) and (REDACT_KEYS.search(str(k)) or REDACT_VALUES.search(v)):
                out[k] = f"<redacted:{len(v)} chars:sha256:{digest(v.encode())[:8]}>"
            else:
                out[k] = redact(v, depth + 1)
        return out
    if isinstance(value, list):
        return [redact(v, depth + 1) for v in value[:50]]
    if isinstance(value, str):
        if REDACT_VALUES.search(value):
            return REDACT_VALUES.sub("<redacted>", value)
        if REDACT_KEYS.search(value) and len(value) > 40:
            return f"<redacted:{len(value)} chars:sha256:{digest(value.encode())[:8]}>"
        return value if len(value) <= 4000 else value[:4000] + "<truncated>"
    return value


# ---------------------------------------------------------------- store plumbing
def bind_workspace(ws):
    """Resolve the workspace and its store. The environment variable wins; the cwd in
    the hook payload is the fallback; with neither the caller fails closed."""
    global WS, STORE, TASKS, EVENTS, RECEIPTS
    WS = ws
    STORE = os.path.join(WS, ".countersign")
    TASKS = os.path.join(STORE, "tasks")
    EVENTS = os.path.join(STORE, "events.jsonl")
    RECEIPTS = os.path.join(STORE, "receipts")


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def digest(b):
    return hashlib.sha256(b).hexdigest()


def canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def relpath_in_workspace(p):
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
    except (FileNotFoundError, IsADirectoryError, PermissionError, OSError):
        return None


def git(*args):
    p = subprocess.run(["git", *args], cwd=WS, capture_output=True, text=True)
    return p.stdout.strip() or None


def revision_of(rel):
    return git("rev-parse", f"HEAD:{rel}")


def commit_id():
    return git("rev-parse", "HEAD")


def branch():
    return git("rev-parse", "--abbrev-ref", "HEAD")


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
    """Append one line to the event log. Kept in the readable shape every recorded
    store already uses (plain json.dumps); receipts use canonical JSON instead."""
    os.makedirs(STORE, exist_ok=True)
    with open(EVENTS, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"at": now(), "event": kind, **kw}, sort_keys=True) + "\n")


def latency_ms():
    return int(round((time.time() - STARTED) * 1000))


def write_receipt(**kw):
    """Persist one immutable receipt file with the full field set, and chain it to the
    previous receipt by hash. Returns the receipt as stored."""
    os.makedirs(RECEIPTS, exist_ok=True)
    existing = sorted(f for f in os.listdir(RECEIPTS) if f.endswith(".json"))
    previous_hash = None
    if existing:
        with open(os.path.join(RECEIPTS, existing[-1]), encoding="utf-8") as fh:
            previous_hash = json.load(fh).get("receipt_hash")
    body = {
        "timestamp": now(),
        "repository": os.path.abspath(WS),
        "branch": branch(),
        "git_head": commit_id(),
        "exit_code": kw.pop("exit_code", 0),
        "runtime_latency_ms": latency_ms(),
        "previous_receipt_hash": previous_hash,
        **kw,
    }
    # receipt_id is derived from the content before it is added, receipt_hash from
    # the content after: verification is one local recomputation over the file
    # minus receipt_hash, and the id prefix matches the stored file name.
    seq = len(existing)
    body["seq"] = seq
    seed = digest(canon(body).encode())[:12]
    body["receipt_id"] = f"rcpt_{seq:05d}_{seed}"
    body["receipt_hash"] = digest(canon(body).encode())
    with open(os.path.join(RECEIPTS, f"{seq:05d}_{body['receipt_hash'][:12]}.json"), "w",
              encoding="utf-8") as fh:
        json.dump(body, fh, indent=2, sort_keys=True)
    return body


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
            "task": task, "commit": m.get("commit"), "opened_at": m.get("opened_at"),
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
        rec["record_hash"] = digest(canon(rec).encode())
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


def decide(sid, tool, inp, path, outside):
    """The deterministic verdict. Returns a dict; writes nothing."""
    m = load_task(sid)
    if m is None:
        return {"verdict": "REFUSED", "codes": ["NO_MANIFEST"], "path": path,
                "held": None, "current": None}
    if outside:
        return {"verdict": "REFUSED", "codes": ["OUTSIDE_WORKSPACE"], "path": path,
                "held": None, "current": None}
    live = [c for c in m.get("contradictions", []) if c["task"] == sid]
    if live:
        return {"verdict": "REFUSED", "codes": ["COMMAND_RESULT_CHANGED"], "path": path,
                "held": live[0]["was"], "current": live[0]["now"],
                "command": live[0]["command"]}
    if not path:
        return {"verdict": "ADMITTED", "codes": [], "path": None, "held": None,
                "current": None, "note": "no contradicted command evidence"}
    sub = inp.get("subtask")
    if sub:
        rec = m["files"].get(path)
        if not rec or rec.get("via") != f"subagent:{sub}":
            return {"verdict": "REFUSED", "codes": ["UNSUPPORTED_SUBTASK_EVIDENCE"],
                    "path": path, "held": None, "current": None, "subtask": sub}
    reasons = []
    own = m["files"].get(path)
    if own is None:
        foreign = foreign_evidence(path, sid)
        if foreign:
            other, _ = foreign
            reasons.append(("CROSS_TASK_EVIDENCE", None, None,
                            "the only recorded evidence for this path belongs to "
                            f"another task ({other})"))
        elif REQUIRE_PRIOR_READ:
            return {"verdict": "REFUSED", "codes": ["UNVERIFIED_TARGET"], "path": path,
                    "held": None, "current": None}
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
        held = own["digest"] if own else None
        return {"verdict": "ADMITTED", "codes": [], "path": path, "held": held,
                "current": file_digest(path) if own else None,
                "note": "evidence current"}
    return {"verdict": "REFUSED", "codes": [r[0] for r in reasons], "path": path,
            "held": reasons[0][1], "current": reasons[0][2],
            "reasons": [{"code": c, "held": a, "current": b, "why": w}
                        for c, a, b, w in reasons]}


def persist_verdict(decision, sid, tool, inp, path):
    args = redact(inp)
    kind, why = classify(tool, inp)
    r = write_receipt(
        session_id=sid, tool_name=tool, tool_classification=kind,
        classification_reason=why, tool_arguments=args,
        tool_arguments_hash=digest(canon(inp).encode()),
        affected_paths=[path] if path else [],
        evidence_hashes={path: decision.get("held")} if path else {},
        current_hashes={path: decision.get("current")} if path else {},
        verdict=decision["verdict"], reason_code=(decision["codes"] or ["NONE"])[0],
        reason_codes=decision["codes"], reason_detail=decision.get("reasons", []),
        exit_code=2 if decision["verdict"] == "REFUSED" else 0,
    )
    return r


# ------------------------------------------------------------------- replay
DIGEST_REASONS = {"EVIDENCE_SUPERSEDED", "REVISION_MOVED"}
NO_PATH_REASONS = {"COMMAND_RESULT_CHANGED", "NO_MANIFEST"}
MANIFEST_REASONS = {"NO_MANIFEST", "CROSS_TASK_EVIDENCE", "UNVERIFIED_TARGET",
                    "UNSUPPORTED_SUBTASK_EVIDENCE", "COMMAND_RESULT_CHANGED",
                    "OUTSIDE_WORKSPACE"}
HAS_REASONS = {"EVIDENCE_SUPERSEDED", "REVISION_MOVED"}


def blob_digest(commit, rel):
    """The digest of a path as it was committed at that revision, or None if the object
    is not present locally. This is what makes a receipt checkable from another machine:
    the repository carries the tree the verdict was reached against."""
    if not commit:
        return None
    try:
        out = subprocess.run(["git", "cat-file", "-p", f"{commit}:{rel}"], cwd=WS,
                             capture_output=True)
    except OSError:
        return None
    if out.returncode != 0:
        return None
    return digest(out.stdout)


def replay_store(as_json=False):
    """Recompute every stored verdict from the inputs the receipt itself recorded.

    This is the half that can run where the gate ran, and also in CI after a clone: it
    needs the receipts and the repository, never the machine that produced them. It
    checks three things.

      1. the stored hash recomputes from the stored content;
      2. the chain links: each receipt names the hash of the one before it;
      3. the verdict follows from the digests the receipt recorded. A receipt that says
         REFUSED for EVIDENCE_SUPERSEDED while its own two digests are equal has been
         edited, and a receipt that says ADMITTED while its digests differ contradicts
         itself. Either one fails.
    """
    rows = []
    previous = None
    failures = 0
    for name in sorted(os.listdir(RECEIPTS)) if os.path.isdir(RECEIPTS) else []:
        if not name.endswith(".json"):
            continue
        with open(os.path.join(RECEIPTS, name), encoding="utf-8") as fh:
            r = json.load(fh)
        row = {"receipt_id": r.get("receipt_id"), "verdict": r.get("verdict"),
               "reason_code": r.get("reason_code"), "exit_code": r.get("exit_code"),
               "checks": {}, "notes": []}

        body = {k: v for k, v in r.items() if k != "receipt_hash"}
        row["checks"]["hash_recomputes"] = digest(canon(body).encode()) == r.get("receipt_hash")
        row["checks"]["chain_links"] = r.get("previous_receipt_hash") == previous
        previous = r.get("receipt_hash")

        paths = r.get("affected_paths") or []
        held = (r.get("evidence_hashes") or {}).get(paths[0]) if paths else None
        current = (r.get("current_hashes") or {}).get(paths[0]) if paths else None
        code = r.get("reason_code")
        verdict = r.get("verdict")

        if not paths:
            row["checks"]["verdict_follows_from_inputs"] = code in NO_PATH_REASONS or verdict == "ADMITTED"
        elif held and current:
            if held != current:
                row["checks"]["verdict_follows_from_inputs"] = (
                    verdict == "REFUSED" and code in DIGEST_REASONS)
                row["notes"].append(f"held {held[:12]} != current {current[:12]}, refusal required")
            else:
                row["checks"]["verdict_follows_from_inputs"] = (
                    verdict == "ADMITTED" or code in MANIFEST_REASONS)
                row["notes"].append(f"held == current {held[:12]}, a digest refusal would be "
                                    f"a contradiction")
        elif held is None and code in HAS_REASONS:
            row["checks"]["verdict_follows_from_inputs"] = False
            row["notes"].append("a digest refusal without a recorded digest pair")
        else:
            row["checks"]["verdict_follows_from_inputs"] = True

        # information, not a failure: the working tree at verdict time need not have been
        # committed, so a receipt is bound to a tree only when the blob is there
        if paths and current:
            blob = blob_digest(r.get("git_head"), paths[0])
            row["tree"] = ("bound" if blob == current else
                           "drifted" if blob else "not in that revision")
            row["notes"].append(f"{paths[0]} at {str(r.get('git_head'))[:8]}: {row['tree']}")

        row["ok"] = all(row["checks"].values())
        if not row["ok"]:
            failures += 1
        rows.append(row)

    summary = {"receipts": len(rows), "failures": failures,
               "chain_head": previous, "ok": failures == 0}
    if as_json:
        print(json.dumps({"summary": summary, "receipts": rows}, indent=2, sort_keys=True))
    else:
        for row in rows:
            mark = "PASS" if row["ok"] else "FAIL"
            checks = " ".join(f"{k}={'yes' if v else 'NO'}" for k, v in row["checks"].items())
            print(f"{mark}  {row['receipt_id']}  {row['verdict']:<8} {row['reason_code']:<26} "
                  f"{checks}")
            for n in row["notes"]:
                print(f"        {n}")
        print(f"\n{len(rows)} receipts, {failures} failed. chain head {str(previous)[:12]}")
    return 2 if failures else 0


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "replay":
        if not WS:
            bind_workspace(os.environ.get("COUNTERSIGN_WORKSPACE") or os.getcwd())
        if STORE is None:
            bind_workspace(WS)
        return replay_store(as_json="--json" in sys.argv[2:])
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
            existing["resumed_at"] = now()
            save_task(sid, existing)
            emit("manifest_resumed", task=sid, observations=len(existing.get("files") or {}))
            emit("session_started", task=sid, resumed=True,
                 observations=len(existing.get("files") or {}))
            return admit("manifest resumed, evidence preserved")
        m = {"task": sid, "commit": commit_id(), "opened_at": now(),
             "implicit": False, "files": {}, "commands": {}, "contradictions": []}
        save_task(sid, m)
        emit("manifest_opened", task=sid, commit=m["commit"])
        emit("session_started", task=sid, resumed=False, commit=m["commit"])
        return admit("manifest opened")

    if mode == "probe":
        d = os.path.join(STORE, "payloads")
        os.makedirs(d, exist_ok=True)
        n = len([f for f in os.listdir(d) if f.endswith(".json")])
        ev = payload.get("hook_event_name") or payload.get("event") or "unknown"
        rel = os.path.join(".countersign", "payloads", f"{n:04d}_{ev}.json")
        with open(os.path.join(WS, rel), "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, sort_keys=True)
        emit("payload_probed", file=rel, event=ev, tool=tool)
        return admit(f"payload recorded at {rel}")

    m = load_task(sid)

    if mode == "record":
        if m is None:                      # a read is never blocked: open implicitly
            m = {"task": sid, "commit": commit_id(), "opened_at": now(),
                 "implicit": True, "files": {}, "commands": {}, "contradictions": []}
            save_task(sid, m)
            emit("manifest_implicit", task=sid)
            emit("session_started", task=sid, resumed=False, implicit=True)
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
                                "via": via, "revision": revision_of(path),
                                "verified_at": now()}
            emit("evidence_recorded", path=path, digest=m["files"][path]["digest"],
                 task=sid, via=via)
            emit("file_read", task=sid, path=path, digest=m["files"][path]["digest"])
            emit("evidence_created", task=sid, path=path)
        save_task(sid, m)
        return admit("evidence recorded")

    if mode == "export":
        return export(sid)

    if mode == "refresh":
        """Re-hash the evidence this task holds and update the manifest. This is the
        recovery action the refusal tells the operator to take, and it really mutates
        the store."""
        if m is None:
            sys.stderr.write("no manifest to refresh for this task\n")
            return 2
        target = path if raw else None
        refreshed, removed = [], []
        for p in sorted(m.get("files") or {}):
            if target and p != target:
                continue
            d = file_digest(p)
            if d is None:
                removed.append(p)
                emit("evidence_missing", task=sid, path=p)
                m["files"].pop(p, None)
                continue
            m["files"][p].update({"digest": d, "at": now(), "task": sid,
                                  "revision": revision_of(p), "verified_at": now()})
            refreshed.append({"path": p, "digest": d})
        m["contradictions"] = [c for c in m.get("contradictions", []) if c["task"] != sid]
        m["refreshed_at"] = now()
        save_task(sid, m)
        emit("evidence_refreshed", task=sid, paths=[r["path"] for r in refreshed],
             removed=removed)
        print(json.dumps({"verdict": "REFRESHED", "session_id": sid,
                          "refreshed": refreshed, "removed": removed}))
        return 0

    if mode == "recheck":
        """Dry run: same deterministic decision, nothing written."""
        d = decide(sid, tool, inp, path, outside)
        d["latency_ms"] = latency_ms()
        d["session_id"] = sid
        d["tool_name"] = tool
        d["dry_run"] = True
        print(json.dumps(d, sort_keys=True))
        return 2 if d["verdict"] == "REFUSED" else 0

    if mode != "check":  # unknown modes must fail closed, never raise
        sys.stderr.write(f"unknown mode: {mode!r}\n")
        return 2

    kind, why = classify(tool, inp)
    emit("tool_intercepted", task=sid, tool=tool, classification=kind,
         classification_reason=why, path=path or None)

    if m is None:
        r = write_receipt(session_id=sid, tool_name=tool, tool_classification=kind,
                          classification_reason=why, tool_arguments=redact(inp),
                          tool_arguments_hash=digest(canon(inp).encode()),
                          affected_paths=[path] if path else [], evidence_hashes={},
                          current_hashes={}, verdict="REFUSED", reason_code="NO_MANIFEST",
                          reason_codes=["NO_MANIFEST"], exit_code=2)
        emit("evidence_checked", task=sid, verdict="REFUSED", codes=["NO_MANIFEST"])
        emit("tool_refused", task=sid, tool=tool, path=path or None,
             codes=["NO_MANIFEST"], receipt=r["receipt_hash"])
        return refuse("NO_MANIFEST",
                      ["No evidence manifest exists for this task.",
                       f"Expected it at {task_path(sid)}.",
                       "Nothing this task relies on has been recorded, so nothing can be "
                       "verified. Fail closed.",
                       f"Refusal receipt: {r['receipt_hash']}"])

    decision = decide(sid, tool, inp, path, outside)
    r = persist_verdict(decision, sid, tool, inp, path)
    emit("verdict", task=sid, path=path or None, verdict=decision["verdict"],
         codes=decision["codes"], receipt=r["receipt_hash"],
         evidence_digest=decision.get("held"))
    emit("receipt_created", receipt=r["receipt_hash"], receipt_id=r["receipt_id"],
         task=sid, verdict=decision["verdict"])
    emit("evidence_checked", task=sid, verdict=decision["verdict"],
         codes=decision["codes"], latency_ms=r["runtime_latency_ms"],
         held=decision.get("held"), current=decision.get("current"), path=path or None)

    if decision["verdict"] == "ADMITTED":
        emit("tool_allowed", task=sid, tool=tool, path=path or None,
             receipt=r["receipt_hash"])
        return admit(f"evidence current, receipt {r['receipt_hash'][:12]}")

    emit("tool_refused", task=sid, tool=tool, path=path or None,
         codes=decision["codes"], receipt=r["receipt_hash"])
    code = decision["codes"][0]
    lines = []
    if code == "OUTSIDE_WORKSPACE":
        lines = [f"The proposed action targets {path}, outside the workspace {WS}.",
                 "No evidence can exist for a path this gate never observes, so the",
                 "action cannot be verified.",
                 "Required recovery: run the action inside the workspace, or record the",
                 "path explicitly."]
    elif code == "COMMAND_RESULT_CHANGED":
        c = decision
        lines = [f"This task holds a contradicted result for `{c.get('command')}`.",
                 f"  observed {str(c['held'])[:12]} -> now {str(c['current'])[:12]}",
                 "A state-changing call cannot proceed on a result that changed "
                 "underneath the task.",
                 "Required recovery: reopen the task and rerun the affected commands."]
    elif code == "UNSUPPORTED_SUBTASK_EVIDENCE":
        lines = [f"The proposed change to {path} is attributed to subtask "
                 f"{decision.get('subtask')}.",
                 "No observation of that path by that subtask is on record.",
                 "The conclusion arrived without evidence behind it.",
                 "Required recovery: let the subtask observe the path, or re-observe it "
                 "in this task."]
    elif code == "UNVERIFIED_TARGET":
        lines = [f"{path} has never been observed by any task.",
                 "Policy requires prior observation before a state-changing call."]
    elif code == "CROSS_TASK_EVIDENCE":
        lines = [f"About to modify {path}.",
                 "The only recorded evidence for this path belongs to another task.",
                 "A different task's observation is not this task's evidence.",
                 "Required recovery: observe the path in this task, then retry."]
    else:
        lines = [f"About to modify {path}."]
        cur = file_digest(path)
        if decision.get("held"):
            lines.append(f"Evidence this task holds: {str(decision['held'])[:12]}.")
            lines.append(f"Digest on disk now: {str(cur)[:12] if cur else 'file missing'}.")
        for x in decision.get("reasons", []):
            lines.append(f"  {x['code']}: {str(x['held'])[:12]} -> {str(x['current'])[:12]}"
                         f" ({x['why']})")
        lines += ["Required recovery:", "  1. open a fresh task",
                  f"  2. re-observe {path}", "  3. rerun the affected commands",
                  "  4. record the new evidence manifest"]
    lines.append(f"Refusal receipt: {r['receipt_hash']}")
    lines.append(f"Receipt id: {r['receipt_id']} | latency {r['runtime_latency_ms']} ms")
    return refuse(code, lines)


if __name__ == "__main__":
    sys.exit(main())
