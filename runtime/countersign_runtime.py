#!/usr/bin/env python3
"""COUNTERSIGN runtime.

The local control plane. It owns no evidence of its own: every value it serves is
read from the workspace store written by the gate (`.countersign/tasks/*.json`,
`events.jsonl`, `receipts/*.json`) or measured with real `git` and filesystem calls.

  agent --PreToolUse--> gate (countersign.py) --> store on disk
                                                    |
                                    runtime watches --+--> localhost:4319 (HTTP + SSE)

Endpoints
  GET  /api/status                     protection state, repo, session, last verdict
  GET  /api/repo                       path, branch, HEAD, working tree, protected files
  POST /api/repo/connect   {path}      bind a real git repository
  POST /api/repo/demo                  create a real temporary demo repository
  POST /api/repo/protect               install the hook into the repository settings
  POST /api/repo/stop                  remove the hook from the repository settings
  POST /api/repo/refresh               re-read git state, emit git_head_changed
  GET  /api/evidence?filter=           evidence held by the active session vs disk
  POST /api/evidence/recheck {path}    dry-run verdict, nothing written
  POST /api/evidence/refresh {path}    real re-hash and manifest update
  GET  /api/interceptor?filter=        intercepted tool calls with verdicts
  POST /api/interceptor/replay         rerun the deterministic check for a receipt
  GET  /api/receipts                   receipt index
  GET  /api/receipts/<id>              full receipt JSON
  POST /api/receipts/<id>/verify       recompute the hash locally
  GET  /api/receipts/<id>/download     download the stored JSON
  GET  /api/security                   hook / runtime / protection / chain / session
  POST /api/selftest                   full sequence in a fresh temporary repository
  POST /api/demo/start                 same sequence against the demo repository
  GET  /api/stream                     server-sent events

Stdlib only. No model is consulted for any verdict.
"""
import glob
import hashlib
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GATE = os.path.join(ROOT, "countersign.py")
INSTALL = os.path.join(ROOT, "install.sh")
STATE_DIR = os.path.expanduser("~/.countersign")
STATE = os.path.join(STATE_DIR, "runtime.json")
PORT = int(os.environ.get("COUNTERSIGN_PORT", "4319"))
DEMO_DIR = os.path.join(STATE_DIR, "demo-repo")
VERSION = "1.0"

state_lock = threading.Lock()
subscribers = []
sub_lock = threading.Lock()
seen_files = {}          # path -> digest the runtime last reported for the active session
seen_head = {}           # repo -> git head the runtime last reported
event_offset = {}        # ws -> byte offset into events.jsonl


# ------------------------------------------------------------------ small utils
def now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def sha(b):
    return hashlib.sha256(b).hexdigest()


def canon(o):
    return json.dumps(o, sort_keys=True, separators=(",", ":"))


def read_state():
    if os.path.exists(STATE):
        try:
            with open(STATE, encoding="utf-8") as fh:
                return json.load(fh)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def write_state(d):
    os.makedirs(STATE_DIR, exist_ok=True)
    tmp = STATE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(d, fh, indent=2, sort_keys=True)
    os.replace(tmp, STATE)


def workspace():
    if os.environ.get("COUNTERSIGN_WORKSPACE"):
        return os.environ["COUNTERSIGN_WORKSPACE"]
    return read_state().get("repo")


def store(ws):
    return os.path.join(ws, ".countersign") if ws else None


def git(ws, *args):
    try:
        p = subprocess.run(["git", *args], cwd=ws, capture_output=True, text=True,
                           timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return p.stdout.strip() if p.returncode == 0 else None


def gate(ws, mode, payload, timeout=30):
    """Invoke the real gate exactly as a hook would, and keep its exit code."""
    t0 = time.time()
    env = dict(os.environ, COUNTERSIGN_WORKSPACE=ws)
    try:
        p = subprocess.run([sys.executable, GATE, mode], input=json.dumps(payload),
                           capture_output=True, text=True, timeout=timeout, env=env)
        return {"exit_code": p.returncode, "stdout": p.stdout.strip(),
                "stderr": p.stderr.strip(),
                "wall_ms": int(round((time.time() - t0) * 1000))}
    except subprocess.TimeoutExpired:
        return {"exit_code": 124, "stdout": "", "stderr": "gate timeout", "wall_ms": timeout * 1000}


def tail_events(ws, limit=None):
    out = []
    if not ws:
        return out
    f = os.path.join(store(ws), "events.jsonl")
    if os.path.exists(f):
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return out[-limit:] if limit else out


def tasks(ws):
    out = []
    if not ws:
        return out
    d = os.path.join(store(ws), "tasks")
    if os.path.isdir(d):
        for f in sorted(os.listdir(d)):
            if f.endswith(".json"):
                try:
                    with open(os.path.join(d, f), encoding="utf-8") as fh:
                        out.append(json.load(fh))
                except (json.JSONDecodeError, OSError):
                    continue
    return out


def active_session(ws):
    """The session the dashboard controls: the most recently opened or resumed task."""
    rows = tasks(ws)
    if not rows:
        return None
    rows.sort(key=lambda m: m.get("resumed_at") or m.get("opened_at") or "", reverse=True)
    return rows[0].get("task")


def receipts(ws):
    out = []
    if not ws:
        return out
    d = os.path.join(store(ws), "receipts")
    if os.path.isdir(d):
        for f in sorted(os.listdir(d)):
            if f.endswith(".json"):
                try:
                    with open(os.path.join(d, f), encoding="utf-8") as fh:
                        out.append(json.load(fh))
                except (json.JSONDecodeError, OSError):
                    continue
    return out


def verify_receipt(r):
    body = {k: v for k, v in r.items() if k != "receipt_hash"}
    return sha(canon(body).encode()) == r.get("receipt_hash")


def chain_state(ws):
    """Walk the receipts and confirm each one links to the one before it, and that
    every stored hash recomputes."""
    rows = receipts(ws)
    prev = None
    for r in rows:
        if not verify_receipt(r):
            return {"valid": False, "reason": f"{r.get('receipt_id')} hash does not recompute",
                    "count": len(rows)}
        if r.get("previous_receipt_hash") != prev:
            return {"valid": False, "count": len(rows),
                    "reason": f"{r.get('receipt_id')} does not link to the previous receipt"}
        prev = r["receipt_hash"]
    return {"valid": True, "count": len(rows), "head": prev}


def hook_settings_paths(ws):
    return [os.path.join(ws, ".bob", "settings", "settings.json"),
            os.path.join(ws, ".countersign", "hooks.json")]


def hook_scope(ws):
    """Where the hook is actually installed. A workspace settings file protects this
    repository only; the shared settings file protects every repository the agent opens
    on this machine. Reported separately, because they are not the same claim."""
    if not ws:
        return {"installed": False, "scope": None, "files": []}
    for p in hook_settings_paths(ws):
        if os.path.exists(p):
            try:
                with open(p, encoding="utf-8") as fh:
                    if "countersign" in fh.read():
                        return {"installed": True, "scope": "workspace", "files": [p]}
            except OSError:
                continue
    g = os.path.expanduser("~/.bob/settings/settings.json")
    if os.path.exists(g):
        try:
            with open(g, encoding="utf-8") as fh:
                if "countersign" in fh.read():
                    return {"installed": True, "scope": "global", "files": [g]}
        except OSError:
            pass
    return {"installed": False, "scope": None, "files": []}


def hook_installed(ws):
    return hook_scope(ws)["installed"]


def digest_of(ws, rel):
    try:
        with open(os.path.join(ws, rel), "rb") as fh:
            return sha(fh.read())
    except OSError:
        return None


def publish(kind, **kw):
    ev = {"at": now(), "event": kind, **kw}
    dead = []
    with sub_lock:
        for q in subscribers:
            try:
                q.put_nowait(ev)
            except queue.Full:
                dead.append(q)
        for q in dead:
            subscribers.remove(q)
    return ev


# ------------------------------------------------------------------- watcher
MUTATION_EXTS = (".ts", ".js", ".py", ".json", ".md", ".sh", ".yml", ".yaml", ".tsx",
                 ".jsx", ".toml", ".go", ".rs", ".sol", ".css", ".html")


def watcher():
    """Real repository watcher: forwards gate events, notices files changing under a
    session's held evidence, and notices HEAD moving. Nothing here is simulated."""
    while True:
        try:
            ws = workspace()
            if ws and os.path.isdir(store(ws)):
                # 1. new gate events -> stream (session_started, file_read, ...)
                f = os.path.join(store(ws), "events.jsonl")
                if os.path.exists(f):
                    off = event_offset.get(ws, 0)
                    size = os.path.getsize(f)
                    if size < off:
                        off = 0
                    if size > off:
                        with open(f, encoding="utf-8") as fh:
                            fh.seek(off)
                            for line in fh:
                                line = line.strip()
                                if not line:
                                    continue
                                try:
                                    publish("gate_event", record=json.loads(line))
                                except json.JSONDecodeError:
                                    pass
                            event_offset[ws] = fh.tell()
                # 2. held evidence vs disk -> filesystem_changed
                sid = active_session(ws)
                if sid:
                    m = next((t for t in tasks(ws) if t.get("task") == sid), None)
                    for rel, rec in (m or {}).get("files", {}).items():
                        key = f"{ws}:{sid}:{rel}"
                        cur = digest_of(ws, rel)
                        last = seen_files.get(key)
                        if cur is None and rec.get("digest"):
                            if last != "DELETED":
                                seen_files[key] = "DELETED"
                                publish("filesystem_changed", path=rel, status="DELETED",
                                        held=rec.get("digest"), current=None,
                                        session_id=sid, detail="file no longer exists")
                        elif cur and cur != rec.get("digest") and last != cur:
                            seen_files[key] = cur
                            publish("filesystem_changed", path=rel, status="STALE",
                                    held=rec.get("digest"), current=cur, session_id=sid,
                                    detail="held evidence no longer matches the repository")
                        elif cur == rec.get("digest"):
                            seen_files[key] = cur
                # 3. HEAD moving
                h = git(ws, "rev-parse", "HEAD")
                if h and seen_head.get(ws) not in (None, h):
                    publish("git_head_changed", repo=ws, previous=seen_head[ws], head=h,
                            branch=git(ws, "rev-parse", "--abbrev-ref", "HEAD"))
                seen_head[ws] = h
        except Exception as e:  # the watcher must never take the runtime down
            publish("watcher_error", detail=str(e))
        time.sleep(0.5)


# ----------------------------------------------------------------- repo actions
def install_hooks(ws):
    if not os.path.exists(INSTALL):
        return {"ok": False, "detail": "install.sh missing"}
    p = subprocess.run(["sh", INSTALL, ws], cwd=ROOT, capture_output=True, text=True,
                       timeout=60)
    return {"ok": p.returncode == 0, "exit_code": p.returncode,
            "output": (p.stdout or p.stderr).strip().splitlines()[-6:]}


def stop_protection(ws):
    """Remove the hook entries the installer added. A real edit of real settings."""
    removed = []
    for p in hook_settings_paths(ws):
        if not os.path.exists(p):
            continue
        with open(p, encoding="utf-8") as fh:
            raw = fh.read()
        try:
            cfg = json.loads(raw)
        except json.JSONDecodeError:
            continue
        entries = ((cfg.get("hooks") or {}).get("PreToolUse") or [])
        kept = [e for e in entries if "countersign" not in json.dumps(e)]
        if len(kept) != len(entries):
            cfg.setdefault("hooks", {})["PreToolUse"] = kept
            with open(p, "w", encoding="utf-8") as fh:
                json.dump(cfg, fh, indent=2)
            removed.append(p)
            publish("protection_stopped", file=p, removed=len(entries) - len(kept))
    return {"ok": True, "files": removed}


def make_repo(path, seed=None):
    """A real git repository on disk."""
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(os.path.join(path, "src"), exist_ok=True)
    subprocess.run(["git", "init", "-q", path], check=False)
    subprocess.run(["git", "-C", path, "config", "user.email", "runtime@countersign.local"],
                   check=False)
    subprocess.run(["git", "-C", path, "config", "user.name", "countersign runtime"],
                   check=False)
    with open(os.path.join(path, "src", "payment-refund.ts"), "w", encoding="utf-8") as fh:
        fh.write("export function refund(order: Order) {\n  return charge(order.id)\n}\n")
    with open(os.path.join(path, "src", "config.ts"), "w", encoding="utf-8") as fh:
        fh.write(f"export const RETRY_LIMIT = {seed if seed is not None else 3}\n")
    with open(os.path.join(path, "README.md"), "w", encoding="utf-8") as fh:
        fh.write("# repository under Countersign\n")
    subprocess.run(["git", "-C", path, "add", "-A"], check=False)
    subprocess.run(["git", "-C", path, "commit", "-qm", "initial"], check=False)
    return path


def external_change(ws, rel, content):
    """Change a file from a separate process, so the change is genuinely external to
    the session that holds the old evidence."""
    p = os.path.join(ws, rel)
    subprocess.run(["sh", "-c", f"cat > {json.dumps(p)} <<'EOF'\n{content}EOF\n"],
                   check=False)
    return digest_of(ws, rel)


# ---------------------------------------------------------------- the sequence
def sequence(ws, sid_prefix, label):
    """The whole product, run for real: real repository, real reads through the gate,
    real external write, real intercepted call with its real exit code, real refresh,
    real retry, real receipts for both attempts."""
    sid = f"{sid_prefix}_{int(time.time())}"
    steps = []

    def step(name, detail, mode=None, payload=None, expect=None):
        s = {"step": name, "detail": detail, "at": now()}
        if mode:
            r = gate(ws, mode, payload)
            s.update({"mode": mode, "exit_code": r["exit_code"], "wall_ms": r["wall_ms"],
                      "stdout": r["stdout"][:1200], "stderr": r["stderr"][:400]})
            ok = (r["exit_code"] == expect) if expect is not None else (r["exit_code"] == 0)
            s["ok"] = ok
        else:
            s["ok"] = True
        steps.append(s)
        publish("selftest_step", run=label, **s)
        return s

    hooks = install_hooks(ws)
    steps.append({"step": "install hook", "detail": f"{hooks.get('ok')} on {ws}",
                  "at": now(), "ok": bool(hooks.get("ok")), "output": hooks.get("output")})

    step("session start", f"session {sid} opens an evidence manifest", "session-start",
         {"hook_event_name": "SessionStart", "session_id": sid, "cwd": ws})

    held_before = digest_of(ws, "src/config.ts")
    step("agent reads src/config.ts", "read routed through the gate so the digest is "
         "recorded as evidence", "record",
         {"hook_event_name": "PostToolUse", "session_id": sid, "tool_name": "read_file",
          "cwd": ws, "tool_input": {"path": "src/config.ts"}})

    m = next((t for t in tasks(ws) if t.get("task") == sid), None) or {}
    held = (m.get("files") or {}).get("src/config.ts", {}).get("digest")
    steps.append({"step": "evidence held", "detail": f"sha256 {held}", "at": now(),
                  "ok": held == held_before, "held": held})

    new_text = "export const RETRY_LIMIT = 99\n"
    changed = external_change(ws, "src/config.ts", new_text)
    steps.append({"step": "a second process changes src/config.ts", "at": now(),
                  "detail": f"sha256 {changed}", "ok": changed != held, "held": held,
                  "current": changed})
    publish("filesystem_changed", path="src/config.ts", held=held, current=changed,
            status="STALE", session_id=sid, detail="external process")

    refused = step("agent attempts the edit", "apply_diff on src/config.ts while the held "
                   "evidence is stale", "check",
                   {"hook_event_name": "PreToolUse", "session_id": sid,
                    "tool_name": "apply_diff", "cwd": ws,
                    "tool_input": {"path": "src/config.ts",
                                   "diff": "-export const RETRY_LIMIT = 99\n"
                                           "+export const RETRY_LIMIT = 5\n"}}, expect=2)
    file_untouched = open(os.path.join(ws, "src/config.ts"), encoding="utf-8").read() == new_text
    steps.append({"step": "repository untouched by the refused call", "at": now(),
                  "detail": "src/config.ts still holds the value written by the other process",
                  "ok": file_untouched})

    step("operator refreshes evidence", "the runtime re-hashes the files the session holds "
         "and rewrites the manifest", "refresh",
         {"hook_event_name": "PostToolUse", "session_id": sid, "cwd": ws, "tool_input": {}})

    allowed = step("retry the same edit", "same tool, same path, evidence now current",
                   "check", {"hook_event_name": "PreToolUse", "session_id": sid,
                             "tool_name": "apply_diff", "cwd": ws,
                             "tool_input": {"path": "src/config.ts"}}, expect=0)

    # the agent actually performs the edit it was just allowed to make
    with open(os.path.join(ws, "src/config.ts"), "w", encoding="utf-8") as fh:
        fh.write("export const RETRY_LIMIT = 5\n")
    after = digest_of(ws, "src/config.ts")
    step("the allowed edit is applied", f"src/config.ts now sha256 {after}", None, None)
    gate(ws, "record", {"hook_event_name": "PostToolUse", "session_id": sid,
                        "tool_name": "read_file", "cwd": ws,
                        "tool_input": {"path": "src/config.ts"}})

    rows = [r for r in receipts(ws) if r.get("session_id") == sid]
    return {
        "label": label, "session_id": sid, "repository": ws,
        "held_digest": held, "digest_after_external_change": changed,
        "digest_after_allowed_edit": after,
        "run_1": {"verdict": refused.get("stdout", "").splitlines()[0] if refused["stdout"] else "",
                  "exit_code": refused["exit_code"],
                  "receipt": next((r for r in rows if r["verdict"] == "REFUSED"), None)},
        "run_2": {"verdict": allowed.get("stdout", "").splitlines()[0] if allowed["stdout"] else "",
                  "exit_code": allowed["exit_code"],
                  "receipt": next((r for r in rows if r["verdict"] == "ADMITTED"), None)},
        "receipts": rows, "steps": steps, "hook_install": hooks,
        "file_after": open(os.path.join(ws, "src/config.ts"), encoding="utf-8").read(),
    }


# -------------------------------------------------------------------- payloads
def evidence_rows(ws, sid=None, filt="all"):
    if not ws:
        return {"session_id": None, "rows": [],
                "counts": {"total": 0, "stale": 0, "current": 0, "deleted": 0}}
    sid = sid or active_session(ws)
    m = next((t for t in tasks(ws) if t.get("task") == sid), None)
    rows = []
    for rel, rec in sorted((m or {}).get("files", {}).items()):
        cur = digest_of(ws, rel)
        if cur is None:
            status = "DELETED"
        elif cur == rec.get("digest"):
            status = "CURRENT"
        else:
            status = "STALE"
        rows.append({
            "path": rel, "type": "file_read", "held_digest": rec.get("digest"),
            "current_digest": cur, "git_revision": rec.get("revision"),
            "read_at": rec.get("at"), "verified_at": rec.get("verified_at") or rec.get("at"),
            "via": rec.get("via", "direct"), "status": status,
        })
    for cmd, rec in sorted((m or {}).get("commands", {}).items()):
        rows.append({
            "path": f"$ {cmd}", "type": "command_result", "held_digest": rec.get("digest"),
            "current_digest": None, "git_revision": None, "read_at": rec.get("at"),
            "verified_at": rec.get("at"), "via": "command", "status": "CURRENT",
        })
    if filt != "all":
        rows = [r for r in rows if r["status"] == filt.upper()]
    return {"session_id": sid, "rows": rows,
            "counts": {"total": len(rows),
                       "stale": len([r for r in rows if r["status"] == "STALE"]),
                       "current": len([r for r in rows if r["status"] == "CURRENT"]),
                       "deleted": len([r for r in rows if r["status"] == "DELETED"])}}


def interceptor_rows(ws, filt="all"):
    """Intercepted calls come from the store the gate wrote: one `tool_intercepted`
    event per call, paired with the receipt that carries the verdict, digests and
    latency. Pairing is greedy in order, because two calls can land in the same second
    and a timestamp comparison alone would hand both of them the first receipt."""
    if not ws:
        return []
    rs = sorted(receipts(ws), key=lambda x: x.get("seq", 0))
    unassigned = {}
    for r in rs:
        unassigned.setdefault(r.get("session_id"), []).append(r)
    rows = []
    for e in tail_events(ws):
        if e.get("event") != "tool_intercepted":
            continue
        sid = e.get("task")
        pool = unassigned.get(sid) or []
        nxt = None
        if pool:
            exact = next((r for r in pool if r.get("tool_name") == e.get("tool")
                          and (r.get("affected_paths") or [None])[0] == e.get("path")), None)
            nxt = exact or pool[0]
            pool.remove(nxt)
        row = {"at": e.get("at"), "tool": e.get("tool"),
               "classification": e.get("classification"),
               "classification_reason": e.get("classification_reason"),
               "path": e.get("path"), "session_id": sid,
               "verdict": (nxt or {}).get("verdict", "NO_MANIFEST" if e.get("path") else "?"),
               "reason_code": (nxt or {}).get("reason_code"),
               "exit_code": (nxt or {}).get("exit_code", 2),
               "latency_ms": (nxt or {}).get("runtime_latency_ms"),
               "receipt_id": (nxt or {}).get("receipt_id"),
               "receipt_hash": (nxt or {}).get("receipt_hash"),
               "held_digest": ((nxt or {}).get("evidence_hashes") or {}).get(e.get("path")),
               "current_digest": ((nxt or {}).get("current_hashes") or {}).get(e.get("path")),
               "arguments": (nxt or {}).get("tool_arguments"),
               "arguments_hash": (nxt or {}).get("tool_arguments_hash")}
        rows.append(row)
    if filt == "refused":
        rows = [r for r in rows if r["verdict"] == "REFUSED"]
    elif filt == "allowed":
        rows = [r for r in rows if r["verdict"] == "ADMITTED"]
    return sorted(rows, key=lambda r: r["at"] or "", reverse=True)


def status(ws):
    if not ws:
        return {"protected": False, "repository": None, "branch": None, "head": None,
                "session_id": None, "hook_installed": False, "last_verdict": None,
                "last_receipt_id": None, "last_receipt_hash": None, "last_latency_ms": None,
                "receipt_count": 0, "chain": {"valid": False, "count": 0,
                                              "reason": "no repository connected"},
                "evidence": {"total": 0, "stale": 0, "current": 0, "deleted": 0}, "stale": 0,
                "runtime": {"version": VERSION, "port": PORT, "pid": os.getpid(),
                            "now": now(), "uptime_s": int(time.time() - START),
                            "platform": sys.platform},
                "disconnected": True,
                "detail": "no repository connected: POST /api/repo/connect or /api/repo/demo"}
    rows = receipts(ws)
    last = rows[-1] if rows else None
    ch = chain_state(ws)
    sid = active_session(ws)
    ev = evidence_rows(ws, sid)
    return {
        "protected": bool(ws and hook_installed(ws)),
        "repository": ws, "branch": git(ws, "rev-parse", "--abbrev-ref", "HEAD") if ws else None,
        "head": git(ws, "rev-parse", "HEAD") if ws else None,
        "session_id": sid, "hook_installed": bool(ws and hook_installed(ws)),
        "hook_scope": hook_scope(ws),
        "last_verdict": last.get("verdict") if last else None,
        "last_receipt_id": last.get("receipt_id") if last else None,
        "last_receipt_hash": last.get("receipt_hash") if last else None,
        "last_latency_ms": last.get("runtime_latency_ms") if last else None,
        "receipt_count": len(rows), "chain": ch,
        "evidence": ev["counts"], "stale": ev["counts"]["stale"],
        "runtime": {"version": VERSION, "port": PORT, "pid": os.getpid(),
                    "now": now(), "uptime_s": int(time.time() - START),
                    "platform": sys.platform},
    }


def git_status_lines(ws):
    """Porcelain output must not be stripped globally: the first column of the first
    line is part of the status, and losing it mangles the path."""
    try:
        p = subprocess.run(["git", "status", "--porcelain"], cwd=ws, capture_output=True,
                           text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return []
    return [l for l in p.stdout.splitlines() if l.strip()]


def repo_payload(ws):
    if not ws:
        return {"repository": None}
    lines = git_status_lines(ws)
    changed, store_dirty = [], False
    for l in lines:
        parts = l.strip().split(None, 1)
        path = parts[1] if len(parts) == 2 else parts[0]
        if path.startswith(".countersign/"):
            store_dirty = True          # the gate's own store, not repository code
            continue
        changed.append(path)
    sid = active_session(ws)
    m = next((t for t in tasks(ws) if t.get("task") == sid), None) or {}
    return {
        "repository": ws, "branch": git(ws, "rev-parse", "--abbrev-ref", "HEAD"),
        "head": git(ws, "rev-parse", "HEAD"),
        "head_short": (git(ws, "rev-parse", "--short", "HEAD") or ""),
        "working_tree": {"clean": not changed and not store_dirty, "changed": changed,
                         "store_untracked": store_dirty},
        "protected_files": sorted((m.get("files") or {}).keys()),
        "session_id": sid, "protected": hook_installed(ws),
        "hook_scope": hook_scope(ws),
        "remote": git(ws, "remote", "get-url", "origin"),
        "commits": git(ws, "rev-list", "--count", "HEAD"),
        "settings": [p for p in hook_settings_paths(ws) if os.path.exists(p)],
    }


# ---------------------------------------------------------------------- HTTP
class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _send(self, obj, code=200, ctype="application/json"):
        body = obj if isinstance(obj, bytes) else json.dumps(obj, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if not n:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode() or "{}")
        except json.JSONDecodeError:
            return {}

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "content-type")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.end_headers()

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        ws = workspace()
        p = u.path
        try:
            if p == "/api/status":
                return self._send(status(ws))
            if p == "/api/repo":
                return self._send(repo_payload(ws))
            if p == "/api/evidence":
                return self._send(evidence_rows(ws, q.get("session", [None])[0],
                                                q.get("filter", ["all"])[0]))
            if p == "/api/interceptor":
                return self._send({"rows": interceptor_rows(ws, q.get("filter", ["all"])[0])})
            if p == "/api/receipts":
                rows = receipts(ws)
                return self._send({"rows": [
                    {k: r.get(k) for k in ("receipt_id", "receipt_hash", "timestamp",
                                           "session_id", "tool_name", "tool_classification",
                                           "verdict", "reason_code", "exit_code",
                                           "runtime_latency_ms", "affected_paths",
                                           "previous_receipt_hash", "seq")}
                    for r in reversed(rows)], "count": len(rows),
                    "chain": chain_state(ws)})
            m = re.match(r"^/api/receipts/([\w.-]+)$", p)
            if m:
                rid = m.group(1)
                r = next((x for x in receipts(ws) if x.get("receipt_id") == rid
                          or x.get("receipt_hash", "").startswith(rid)), None)
                if not r:
                    return self._send({"error": "no such receipt"}, 404)
                r = dict(r)
                r["verified"] = verify_receipt(r)
                return self._send(r)
            m = re.match(r"^/api/receipts/([\w.-]+)/download$", p)
            if m:
                rid = m.group(1)
                f = next((x for x in glob.glob(os.path.join(store(ws), "receipts", "*.json"))
                          if os.path.basename(x).startswith(rid[:5]) or rid in os.path.basename(x)), None)
                if not f:
                    return self._send({"error": "no such receipt"}, 404)
                with open(f, "rb") as fh:
                    return self._send(fh.read(), ctype="application/json")
            if p == "/api/security":
                hs = hook_scope(ws)
                return self._send({
                    "hook_installed": hs["installed"], "hook_scope": hs["scope"],
                    "runtime_connected": True, "repository_protected": bool(ws and hook_installed(ws)),
                    "receipt_chain": chain_state(ws),
                    "session_valid": bool(active_session(ws)),
                    "verdict_path": "deterministic sha256 comparison, no model",
                    "hook_files": hs["files"],
                })
            if p == "/api/session":
                sid = active_session(ws)
                m = next((t for t in tasks(ws) if t.get("task") == sid), None) or {}
                return self._send({"session_id": sid,
                                   "agent": m.get("agent") or "not recorded by the hook",
                                   "started": m.get("opened_at") or m.get("resumed_at"),
                                   "commit": m.get("commit") or git(ws, "rev-parse", "HEAD"),
                                   "implicit": m.get("implicit"),
                                   "evidence": evidence_rows(ws, sid)["counts"]})
            if p == "/api/stream":
                return self._stream()
            return self._send({"error": "unknown route", "path": p}, 404)
        except Exception as e:  # never leak a stack trace into the UI
            return self._send({"error": str(e)}, 500)

    def do_POST(self):
        u = urlparse(self.path)
        p = u.path
        ws = workspace()
        b = self._body()
        try:
            if p == "/api/repo/connect":
                cand = b.get("path") or ""
                if not os.path.isdir(os.path.join(cand, ".git")) and not os.path.isdir(os.path.join(cand)):
                    return self._send({"ok": False, "detail": "not a directory"}, 400)
                st = read_state()
                st["repo"] = os.path.abspath(cand)
                write_state(st)
                publish("repository_connected", repo=st["repo"])
                return self._send({"ok": True, "repo": repo_payload(st["repo"])})
            if p == "/api/repo/demo":
                path = make_repo(DEMO_DIR, seed=b.get("seed", 3))
                st = read_state()
                st["repo"] = path
                st["demo"] = True
                write_state(st)
                publish("repository_connected", repo=path, demo=True)
                return self._send({"ok": True, "repo": repo_payload(path)})
            if p == "/api/repo/protect":
                r = install_hooks(ws)
                publish("protection_started", repo=ws, **r)
                return self._send({"ok": r.get("ok"), "detail": r}, 200 if r.get("ok") else 500)
            if p == "/api/repo/stop":
                r = stop_protection(ws)
                return self._send({"ok": True, "detail": r})
            if p == "/api/repo/refresh":
                h = git(ws, "rev-parse", "HEAD")
                prev = seen_head.get(ws)
                seen_head[ws] = h
                publish("git_head_changed" if prev and prev != h else "git_state_refreshed",
                        repo=ws, previous=prev, head=h)
                return self._send({"ok": True, "repo": repo_payload(ws)})
            if p == "/api/session/start":
                sid = b.get("session") or f"session_{int(time.time())}"
                r = gate(ws, "session-start", {"hook_event_name": "SessionStart",
                                               "session_id": sid, "cwd": ws})
                publish("session_started", session_id=sid, exit_code=r["exit_code"])
                return self._send({"ok": r["exit_code"] == 0, "session_id": sid,
                                   "gate": r})
            if p == "/api/evidence/read":
                sid = b.get("session") or active_session(ws)
                if not b.get("path"):
                    return self._send({"error": "path is required"}, 400)
                r = gate(ws, "record", {"hook_event_name": "PostToolUse", "session_id": sid,
                                        "tool_name": "read_file", "cwd": ws,
                                        "tool_input": {"path": b["path"]}})
                publish("file_read", session_id=sid, path=b["path"],
                        exit_code=r["exit_code"])
                row = next((x for x in evidence_rows(ws, sid)["rows"]
                            if x["path"] == b["path"]), None)
                return self._send({"ok": r["exit_code"] == 0, "gate": r, "evidence": row},
                                  200 if r["exit_code"] == 0 else 500)
            if p == "/api/interceptor/attempt":
                """Run the real hook command exactly as the agent's PreToolUse would, and
                keep the exit code it returned plus the receipt it wrote."""
                sid = b.get("session") or active_session(ws)
                tool = b.get("tool") or "apply_diff"
                args = dict(b.get("arguments") or {})
                if b.get("path"):
                    args.setdefault("path", b["path"])
                r = gate(ws, "check", {"hook_event_name": "PreToolUse", "session_id": sid,
                                       "tool_name": tool, "cwd": ws, "tool_input": args})
                row = next((x for x in interceptor_rows(ws)
                            if x.get("session_id") == sid), None)
                return self._send({"ok": r["exit_code"] == 0, "exit_code": r["exit_code"],
                                   "stdout": r["stdout"].splitlines()[:16], "gate": r,
                                   "call": row,
                                   "note": "this is the hook command, run with the payload "
                                           "the agent sends"}, 200)
            if p == "/api/evidence/refresh":
                sid = b.get("session") or active_session(ws)
                payload = {"hook_event_name": "PostToolUse", "session_id": sid, "cwd": ws,
                           "tool_input": {"path": b["path"]} if b.get("path") else {}}
                r = gate(ws, "refresh", payload)
                publish("evidence_refreshed", session_id=sid, path=b.get("path"),
                        exit_code=r["exit_code"])
                return self._send({"ok": r["exit_code"] == 0, "gate": r,
                                   "evidence": evidence_rows(ws, sid)},
                                  200 if r["exit_code"] == 0 else 500)
            if p == "/api/evidence/recheck":
                sid = b.get("session") or active_session(ws)
                r = gate(ws, "recheck", {"hook_event_name": "PreToolUse", "session_id": sid,
                                         "tool_name": b.get("tool", "apply_diff"), "cwd": ws,
                                         "tool_input": {"path": b.get("path", "")}})
                try:
                    out = json.loads(r["stdout"] or "{}")
                except json.JSONDecodeError:
                    out = {"raw": r["stdout"]}
                publish("evidence_checked", session_id=sid, path=b.get("path"),
                        verdict=out.get("verdict"))
                return self._send({"ok": True, "verdict": out, "gate": r})
            if p == "/api/interceptor/replay":
                rid = b.get("receipt_id")
                r0 = next((x for x in receipts(ws) if x.get("receipt_id") == rid), None)
                if not r0:
                    return self._send({"error": "no such receipt"}, 404)
                args = dict(r0.get("tool_arguments") or {})
                if r0.get("affected_paths"):
                    args.setdefault("path", r0["affected_paths"][0])
                r = gate(ws, "recheck", {"hook_event_name": "PreToolUse",
                                         "session_id": r0.get("session_id"), "cwd": ws,
                                         "tool_name": r0.get("tool_name"),
                                         "tool_input": args})
                try:
                    out = json.loads(r["stdout"] or "{}")
                except json.JSONDecodeError:
                    out = {"raw": r["stdout"]}
                publish("check_replayed", receipt_id=rid, verdict=out.get("verdict"))
                return self._send({"ok": True, "original": {k: r0.get(k) for k in
                                                            ("verdict", "reason_code",
                                                             "evidence_hashes",
                                                             "current_hashes")},
                                   "now": out, "exit_code": r["exit_code"]})
            m = re.match(r"^/api/receipts/([\w.-]+)/verify$", p)
            if m:
                rid = m.group(1)
                r0 = next((x for x in receipts(ws) if x.get("receipt_id") == rid), None)
                if not r0:
                    return self._send({"error": "no such receipt"}, 404)
                body = {k: v for k, v in r0.items() if k != "receipt_hash"}
                recomputed = sha(canon(body).encode())
                return self._send({"receipt_id": rid, "valid": recomputed == r0["receipt_hash"],
                                   "stored": r0["receipt_hash"], "recomputed": recomputed})
            if p == "/api/selftest":
                path = b.get("path") or make_repo(os.path.join(STATE_DIR, "selftest-repo"),
                                                  seed=b.get("seed", 3))
                if b.get("fresh", True) and not b.get("path"):
                    path = make_repo(os.path.join(STATE_DIR, "selftest-repo"), seed=b.get("seed", 3))
                st = read_state(); st["repo"] = path; st["demo"] = False; write_state(st)
                publish("selftest_started", repo=path)
                out = sequence(path, "selftest", "self-test")
                publish("selftest_finished", repo=path,
                        run_1=out["run_1"]["exit_code"], run_2=out["run_2"]["exit_code"])
                return self._send({"ok": True, **out})
            if p == "/api/demo/start":
                path = DEMO_DIR if os.path.isdir(DEMO_DIR) else make_repo(DEMO_DIR)
                publish("demo_started", repo=path)
                out = sequence(path, "demo", "demo")
                return self._send({"ok": True, **out})
            if p == "/api/stream/test":
                publish("runtime_ping", detail="manual")
                return self._send({"ok": True, "subscribers": len(subscribers)})
            return self._send({"error": "unknown route", "path": p}, 404)
        except Exception as e:
            return self._send({"error": str(e)}, 500)

    def _stream(self):
        q = queue.Queue(maxsize=500)
        with sub_lock:
            subscribers.append(q)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        try:
            hello = {"at": now(), "event": "runtime_hello",
                     "repository": workspace(), "session_id": active_session(workspace())}
            self.wfile.write(f"data: {json.dumps(hello)}\n\n".encode())
            self.wfile.flush()
            last = time.time()
            while True:
                try:
                    ev = q.get(timeout=1.0)
                    self.wfile.write(f"data: {json.dumps(ev, default=str)}\n\n".encode())
                    self.wfile.flush()
                    last = time.time()
                except queue.Empty:
                    if time.time() - last > 15:     # keep the connection warm
                        self.wfile.write(b": keepalive\n\n")
                        self.wfile.flush()
                        last = time.time()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            with sub_lock:
                if q in subscribers:
                    subscribers.remove(q)


START = time.time()


def main():
    os.makedirs(STATE_DIR, exist_ok=True)
    threading.Thread(target=watcher, daemon=True).start()
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    ws = workspace()
    print(f"countersign runtime {VERSION} on http://127.0.0.1:{PORT}")
    print(f"workspace: {ws or '(none connected - POST /api/repo/connect)'}")
    print(f"gate: {GATE}")
    sys.stdout.flush()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
