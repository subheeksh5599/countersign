#!/usr/bin/env python3
"""Receipt, chain, redaction, policy-classification and recovery tests.

Every case builds a real workspace, runs the gate as a subprocess, and reads what it
actually wrote to disk.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
GATE = os.path.join(os.path.dirname(HERE), "countersign.py")
PASSED, FAILED = [], []


def case(name, ok, detail=""):
    (PASSED if ok else FAILED).append(name)
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"\n        {detail}" if detail and not ok else ""))


def ws_new():
    d = tempfile.mkdtemp(prefix="csign_receipts_")
    subprocess.run(["git", "init", "-q", d], check=False)
    for k, v in (("user.email", "t@t"), ("user.name", "t")):
        subprocess.run(["git", "-C", d, "config", k, v], check=False)
    os.makedirs(os.path.join(d, "src"), exist_ok=True)
    open(os.path.join(d, "src", "config.ts"), "w").write("export const RETRY_LIMIT = 3\n")
    subprocess.run(["git", "-C", d, "add", "-A"], check=False)
    subprocess.run(["git", "-C", d, "commit", "-qm", "init"], check=False)
    return d


def run(ws, mode, payload, extra_env=None):
    env = dict(os.environ, COUNTERSIGN_WORKSPACE=ws)
    if extra_env:
        env.update(extra_env)
    p = subprocess.run([sys.executable, GATE, mode], input=json.dumps(payload),
                       capture_output=True, text=True, env=env)
    return p.returncode, p.stdout + p.stderr


def receipts_of(ws):
    d = os.path.join(ws, ".countersign", "receipts")
    if not os.path.isdir(d):
        return []
    out = []
    for f in sorted(os.listdir(d)):
        with open(os.path.join(d, f), encoding="utf-8") as fh:
            out.append((f, json.load(fh)))
    return out


def events_of(ws):
    f = os.path.join(ws, ".countersign", "events.jsonl")
    if not os.path.exists(f):
        return []
    return [json.loads(l) for l in open(f, encoding="utf-8") if l.strip()]


# 1 a refusal writes one receipt carrying every field the console and the chain need
ws = ws_new()
run(ws, "session-start", {"session_id": "s1", "cwd": ws})
run(ws, "record", {"session_id": "s1", "cwd": ws, "tool_name": "read_file",
                   "tool_input": {"path": "src/config.ts"}})
open(os.path.join(ws, "src", "config.ts"), "w").write("export const RETRY_LIMIT = 9\n")
rc, out = run(ws, "check", {"session_id": "s1", "cwd": ws, "tool_name": "write_file",
                            "tool_input": {"path": "src/config.ts"}})
rows = receipts_of(ws)
r = rows[0][1] if rows else {}
need = ("receipt_id", "timestamp", "session_id", "repository", "branch", "git_head",
        "tool_name", "tool_arguments_hash", "affected_paths", "evidence_hashes",
        "current_hashes", "verdict", "reason_code", "exit_code", "runtime_latency_ms",
        "previous_receipt_hash", "receipt_hash", "tool_arguments", "tool_classification")
case("a refusal writes a receipt carrying the full field set",
     rc == 2 and r.get("verdict") == "REFUSED" and all(k in r for k in need),
     f"missing: {[k for k in need if k not in r]}")
case("the stored hash recomputes from the stored content",
     hashlib.sha256(json.dumps({k: v for k, v in r.items() if k != "receipt_hash"},
                               sort_keys=True, separators=(",", ":")).encode()).hexdigest()
     == r.get("receipt_hash"),
     f"stored {r.get('receipt_hash')}")
case("the receipt records which digests disagreed",
     r.get("evidence_hashes", {}).get("src/config.ts") != r.get("current_hashes", {}).get("src/config.ts")
     and r.get("evidence_hashes", {}).get("src/config.ts") is not None,
     json.dumps({"held": r.get("evidence_hashes"), "now": r.get("current_hashes")}))
case("latency was measured at runtime, not assumed",
     isinstance(r.get("runtime_latency_ms"), int) and r["runtime_latency_ms"] >= 0,
     str(r.get("runtime_latency_ms")))

# 2 stored arguments never carry a secret, but keep their structure
ws = ws_new()
run(ws, "session-start", {"session_id": "s2", "cwd": ws})
sec = "sk-abcdefghijklmnopqrstuvwxyz012345"
rc, out = run(ws, "check", {"session_id": "s2", "cwd": ws, "tool_name": "write_file",
                            "tool_input": {"path": "src/config.ts", "api_key": sec,
                                           "authorization": "Bearer ghp_" + "a" * 24,
                                           "password": "hunter2-not-real",
                                           "content": "const x = 1\n"}})
f, r = receipts_of(ws)[0]
raw = open(os.path.join(ws, ".countersign", "receipts", f), encoding="utf-8").read()
case("a secret in the tool arguments never reaches the stored receipt",
     sec not in raw and "hunter2-not-real" not in raw and "a" * 24 not in raw,
     f"receipt file still contains a secret value")
case("redaction preserves the shape of the arguments",
     set(r["tool_arguments"]) == {"path", "api_key", "authorization", "password", "content"}
     and r["tool_arguments"]["path"] == "src/config.ts"
     and r["tool_arguments"]["content"] == "const x = 1\n"
     and "redacted" in r["tool_arguments"]["api_key"],
     json.dumps(r["tool_arguments"]))

# 3 classification is deterministic and fails closed for unknown tools
ws = ws_new()
run(ws, "session-start", {"session_id": "s3", "cwd": ws})
kinds = []
for tool, inp in (("write_file", {"path": "src/config.ts"}),
                  ("read_file", {"path": "src/config.ts"}),
                  ("execute_command", {"command": "rm -rf build"}),
                  ("execute_command", {"command": "git status"}),
                  ("some_new_tool", {}),
                  ("mystery", {"text": "hello"})):
    run(ws, "check", {"session_id": "s3", "cwd": ws, "tool_name": tool, "tool_input": inp})
    kinds.append(receipts_of(ws)[-1][1]["tool_classification"])
case("writes and mutating commands are classified state-changing, reads are not",
     kinds[0] == "state_changing" and kinds[1] == "read_only"
     and kinds[2] == "state_changing" and kinds[3] == "read_only",
     str(kinds))
case("an unrecognised tool fails closed as state-changing",
     kinds[4] == "state_changing" and kinds[5] == "state_changing", str(kinds))

# 4 the receipt chain links each receipt to the previous one
chain = [x[1] for x in receipts_of(ws)]
links = all(chain[i]["previous_receipt_hash"] == chain[i - 1]["receipt_hash"]
            for i in range(1, len(chain)))
case("each receipt stores the hash of the one before it",
     len(chain) >= 3 and chain[0]["previous_receipt_hash"] is None and links,
     f"{len(chain)} receipts, linked={links}")

# 5 refresh is a real mutation: it rewrites the manifest and the next check admits
ws = ws_new()
run(ws, "session-start", {"session_id": "s5", "cwd": ws})
run(ws, "record", {"session_id": "s5", "cwd": ws, "tool_name": "read_file",
                   "tool_input": {"path": "src/config.ts"}})
open(os.path.join(ws, "src", "config.ts"), "w").write("export const RETRY_LIMIT = 42\n")
rc1, _ = run(ws, "check", {"session_id": "s5", "cwd": ws, "tool_name": "write_file",
                           "tool_input": {"path": "src/config.ts"}})
m_before = json.load(open(os.path.join(ws, ".countersign", "tasks", "s5.json")))
rc2, out2 = run(ws, "refresh", {"session_id": "s5", "cwd": ws, "tool_input": {}})
m_after = json.load(open(os.path.join(ws, ".countersign", "tasks", "s5.json")))
rc3, _ = run(ws, "check", {"session_id": "s5", "cwd": ws, "tool_name": "write_file",
                           "tool_input": {"path": "src/config.ts"}})
case("refresh rewrites the manifest digest that the refusal named",
     rc1 == 2 and rc2 == 0
     and m_before["files"]["src/config.ts"]["digest"] != m_after["files"]["src/config.ts"]["digest"]
     and m_after["files"]["src/config.ts"]["digest"] == hashlib.sha256(
         open(os.path.join(ws, "src", "config.ts"), "rb").read()).hexdigest(),
     f"before {m_before['files']['src/config.ts']['digest'][:12]} after "
     f"{m_after['files']['src/config.ts']['digest'][:12]}")
case("after refresh the same call is admitted",
     rc3 == 0 and "ADMITTED" in out2 or "ADMITTED" in run(
         ws, "check", {"session_id": "s5", "cwd": ws, "tool_name": "write_file",
                       "tool_input": {"path": "src/config.ts"}})[1],
     f"refresh exit {rc2}, retry exit {rc3}")

# 6 a dry run changes nothing (run against a genuinely stale workspace)
ws = ws_new()
run(ws, "session-start", {"session_id": "s6", "cwd": ws})
run(ws, "record", {"session_id": "s6", "cwd": ws, "tool_name": "read_file",
                   "tool_input": {"path": "src/config.ts"}})
open(os.path.join(ws, "src", "config.ts"), "w").write("export const RETRY_LIMIT = 77\n")
before_events = len(events_of(ws))
before_receipts = len(receipts_of(ws))
rc, out = run(ws, "recheck", {"session_id": "s6", "cwd": ws, "tool_name": "write_file",
                              "tool_input": {"path": "src/config.ts"}})
after_events = len(events_of(ws))
after_receipts = len(receipts_of(ws))
case("a re-check returns a verdict but writes no receipt and no event",
     rc == 2 and "REFUSED" in out and after_receipts == before_receipts
     and after_events == before_events,
     f"receipts {before_receipts}->{after_receipts}, events {before_events}->{after_events}")

# 7 a resumed session keeps the evidence it already had
ws = ws_new()
run(ws, "session-start", {"session_id": "s7", "cwd": ws})
run(ws, "record", {"session_id": "s7", "cwd": ws, "tool_name": "read_file",
                   "tool_input": {"path": "src/config.ts"}})
run(ws, "session-start", {"session_id": "s7", "cwd": ws})
m = json.load(open(os.path.join(ws, ".countersign", "tasks", "s7.json")))
case("resuming a session does not erase the evidence it holds",
     "src/config.ts" in m.get("files", {}) and m.get("resumed_at"),
     json.dumps(list(m.get("files", {}))))

for w in [d for d in os.listdir(tempfile.gettempdir()) if d.startswith("csign_receipts_")]:
    shutil.rmtree(os.path.join(tempfile.gettempdir(), w), ignore_errors=True)

print(f"\n{len(PASSED)}/{len(PASSED) + len(FAILED)} passed")
if FAILED:
    print("failed: " + ", ".join(FAILED))
sys.exit(1 if FAILED else 0)
