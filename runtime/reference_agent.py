#!/usr/bin/env python3
"""A reference agent.

It is deliberately not a model. It is a small deterministic agent loop that makes the
same tool calls an agent makes, through the same gate command a hook runs, so the
control plane can demonstrate interception on a machine with no vendor key and no spend.
Every step is a real subprocess call: a real read, a real gate verdict with its real exit
code, and a real file write only when the gate admitted it.

    python3 runtime/reference_agent.py --workspace /path/to/repo \
        --session ref_1 --prompt "set RETRY_LIMIT to 5 in src/config.ts"

Prints one JSON object: the plan, every step with its exit code, and what the gate said.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
GATE = os.path.join(os.path.dirname(HERE), "countersign.py")
PATH_RE = re.compile(r"[\w./-]+\.(ts|tsx|js|jsx|py|json|md|sh|yml|yaml|toml|go|rs|sol)")
SET_RE = re.compile(r"set\s+([A-Za-z_][A-Za-z0-9_]*)\s+to\s+([^\s,.;]+)", re.I)
ASSIGN_RE = None


def gate(ws, mode, payload, timeout=60):
    env = dict(os.environ, COUNTERSIGN_WORKSPACE=ws)
    p = subprocess.run([sys.executable, GATE, mode], input=json.dumps(payload),
                       capture_output=True, text=True, timeout=timeout, env=env)
    return {"exit_code": p.returncode, "stdout": p.stdout.strip(), "stderr": p.stderr.strip()}


def plan(prompt, ws):
    """Read the request: which path, which constant, which value. No model, so the
    request has to be explicit; the point is the tool calls, not the language."""
    m = PATH_RE.search(prompt)
    rel = m.group(0) if m else "src/config.ts"
    rel = rel.lstrip("./")
    if not os.path.exists(os.path.join(ws, rel)):
        for cand in ("src/config.ts", "config.ts", "src/index.ts", "package.json"):
            if os.path.exists(os.path.join(ws, cand)):
                rel = cand
                break
    s = SET_RE.search(prompt)
    name = s.group(1) if s else None
    value = s.group(2).strip("\"'") if s else None
    if not name:
        try:
            text = open(os.path.join(ws, rel), encoding="utf-8").read()
            m2 = re.search(r"(?:const|let|var)\s+([A-Z_][A-Z0-9_]*)\s*=", text)
            name = m2.group(1) if m2 else None
        except OSError:
            name = None
    return {"path": rel, "constant": name, "value": value}


def rewrite(text, name, value):
    """Replace the value of an assignment, keeping everything else."""
    if not name or value is None:
        return text
    pat = re.compile(rf"(\b{re.escape(name)}\s*[:=]\s*)([^,;\n]+)")
    if not pat.search(text):
        return text
    return pat.sub(lambda m: m.group(1) + value, text, count=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--session", required=True)
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--allow-write", default="1")
    ap.add_argument("--hold", type=float, default=0.0,
                    help="seconds to hold between recording evidence and the check; a real "
                         "second writer can move the file inside this window")
    a = ap.parse_args()
    ws = os.path.abspath(a.workspace)
    steps = []

    def emit(kind, **kw):
        step = {"step": kind, **kw}
        steps.append(step)
        print(json.dumps(step), flush=True)

    p = plan(a.prompt, ws)
    emit("plan", **p)

    r = gate(ws, "session-start", {"hook_event_name": "SessionStart", "session_id": a.session,
                                   "cwd": ws})
    emit("session_start", exit_code=r["exit_code"], detail=r["stdout"][:200])

    target = os.path.join(ws, p["path"])
    try:
        before = open(target, encoding="utf-8").read()
    except OSError as e:
        emit("abort", detail=f"cannot read {p['path']}: {e}")
        print(json.dumps({"summary": "aborted", "steps": steps}))
        return 1

    r = gate(ws, "record", {"hook_event_name": "PostToolUse", "session_id": a.session,
                            "tool_name": "read_file", "cwd": ws,
                            "tool_input": {"path": p["path"]}})
    emit("read_file", path=p["path"], exit_code=r["exit_code"],
         detail="digest recorded as evidence")

    if a.hold > 0:
        emit("holding", seconds=a.hold,
             detail="waiting before the check; another process may move the file now")
        time.sleep(a.hold)

    after = rewrite(before, p["constant"], p["value"])
    if after == before:
        emit("abort", detail=f"nothing to change: {p['constant']} not found in {p['path']}")
        print(json.dumps({"summary": "aborted", "steps": steps}))
        return 1

    diff = {"path": p["path"], "diff": f"--- {p['path']}\n+++ {p['path']}\n"
            f"-{before.strip()}\n+{after.strip()}\n"}
    r = gate(ws, "check", {"hook_event_name": "PreToolUse", "session_id": a.session,
                           "tool_name": "apply_diff", "cwd": ws, "tool_input": diff})
    verdict = "REFUSED" if r["exit_code"] == 2 else "ADMITTED"
    emit("apply_diff", path=p["path"], exit_code=r["exit_code"], verdict=verdict,
         detail=r["stdout"].splitlines()[0] if r["stdout"] else "")

    if r["exit_code"] != 0:
        emit("stopped", detail="the gate refused the call; this agent writes nothing")
        print(json.dumps({"summary": "refused", "path": p["path"], "exit_code": r["exit_code"],
                          "gate_output": r["stdout"], "steps": steps}))
        return 2

    if a.allow_write == "1":
        with open(target, "w", encoding="utf-8") as fh:
            fh.write(after)
        r2 = gate(ws, "record", {"hook_event_name": "PostToolUse", "session_id": a.session,
                                 "tool_name": "read_file", "cwd": ws,
                                 "tool_input": {"path": p["path"]}})
        emit("wrote", path=p["path"], exit_code=r2["exit_code"],
             detail="the admitted edit was applied and re-recorded")

    print(json.dumps({"summary": "applied", "path": p["path"], "steps": steps}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
