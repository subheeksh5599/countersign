#!/usr/bin/env python3
"""Real gate tests: a git workspace, real files, real subprocess calls.
Each test asserts the exit code and the reason code printed by the gate."""
import json, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
GATE = os.path.join(HERE, "..", "countersign.py")
results = []


def run(ws, mode, payload, env_extra=None):
    env = dict(os.environ, COUNTERSIGN_WORKSPACE=ws)
    env.update(env_extra or {})
    p = subprocess.run([sys.executable, GATE, mode], input=json.dumps(payload),
                       capture_output=True, text=True, env=env, cwd=ws)
    return p.returncode, p.stdout + p.stderr


def ws_new():
    ws = tempfile.mkdtemp(prefix="countersign_ws_")
    subprocess.run(["git", "init", "-q"], cwd=ws, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=ws, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=ws, check=True)
    open(os.path.join(ws, "pricing.ts"), "w").write("export const rate = 1\n")
    subprocess.run(["git", "add", "."], cwd=ws, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=ws, check=True)
    return ws


def case(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not ok else ""))


# 1 admit a write whose evidence is current
ws = ws_new()
start = {"event": "SessionStart", "session_id": "task_A"}
run(ws, "session-start", start)
run(ws, "record", {"event": "PostToolUse", "session_id": "task_A",
                   "tool": "read_file", "input": {"path": "pricing.ts"}})
rc, out = run(ws, "check", {"event": "PreToolUse", "session_id": "task_A",
                            "tool": "write_file", "input": {"path": "pricing.ts"}})
case("current evidence is admitted", rc == 0 and "ADMITTED" in out, out.strip())

# 2 refuse after the file changed underneath the task
open(os.path.join(ws, "pricing.ts"), "a").write("// changed by another task\n")
rc, out = run(ws, "check", {"event": "PreToolUse", "session_id": "task_A",
                            "tool": "write_file", "input": {"path": "pricing.ts"}})
case("external change refused", rc == 2 and "EVIDENCE_SUPERSEDED" in out, out.strip())

# 3 a fresh task that re-observes is admitted again
run(ws, "session-start", {"event": "SessionStart", "session_id": "task_A2"})
run(ws, "record", {"event": "PostToolUse", "session_id": "task_A2",
                   "tool": "read_file", "input": {"path": "pricing.ts"}})
rc, out = run(ws, "check", {"event": "PreToolUse", "session_id": "task_A2",
                            "tool": "write_file", "input": {"path": "pricing.ts"}})
case("fresh observation is admitted", rc == 0 and "ADMITTED" in out, out.strip())

# 4 evidence observed by a different task is refused
run(ws, "session-start", {"event": "SessionStart", "session_id": "task_C"})
rc, out = run(ws, "check", {"event": "PreToolUse", "session_id": "task_C",
                            "tool": "write_file", "input": {"path": "pricing.ts"}})
case("cross-task evidence refused", rc == 2 and "CROSS_TASK_EVIDENCE" in out, out.strip())

# 5 a commit that changes this path after observation is refused
open(os.path.join(ws, "pricing.ts"), "a").write("// committed by someone else\n")
subprocess.run(["git", "commit", "-qam", "someone else committed this path"], cwd=ws, check=True)
rc, out = run(ws, "check", {"event": "PreToolUse", "session_id": "task_A2",
                            "tool": "write_file", "input": {"path": "pricing.ts"}})
case("revision move refused", rc == 2 and "REVISION_MOVED" in out, out.strip())

# 6 a command result that changes under the task is refused
ws2 = ws_new()
run(ws2, "session-start", {"event": "SessionStart", "session_id": "task_D"})
run(ws2, "record", {"event": "PostToolUse", "session_id": "task_D", "tool": "execute_command",
                    "input": {"command": "npm test", "output": "84 passing"}})
run(ws2, "record", {"event": "PostToolUse", "session_id": "task_D", "tool": "execute_command",
                    "input": {"command": "npm test", "output": "83 passing"}})
rc, out = run(ws2, "check", {"event": "PreToolUse", "session_id": "task_D",
                             "tool": "write_file", "input": {"path": "pricing.ts"}})
case("contradicted command result refused", rc == 2 and "COMMAND_RESULT_CHANGED" in out, out.strip())

# 7 policy: refuse writes to a path this task never observed
ws4 = ws_new()
run(ws4, "session-start", {"event": "SessionStart", "session_id": "task_F"})
rc, out = run(ws4, "check", {"event": "PreToolUse", "session_id": "task_F",
                             "tool": "write_file", "input": {"path": "never_read.ts"}},
              env_extra={"COUNTERSIGN_REQUIRE_PRIOR_READ": "1"})
case("unobserved target refused under policy", rc == 2 and "UNVERIFIED_TARGET" in out, out.strip())

# 8 no manifest at all fails closed
ws3 = ws_new()
rc, out = run(ws3, "check", {"event": "PreToolUse", "session_id": "task_E",
                             "tool": "write_file", "input": {"path": "pricing.ts"}})
case("missing manifest fails closed", rc == 2 and "NO_MANIFEST" in out, out.strip())

# 9 a state-changing command is refused while a result is contradicted
rc, out = run(ws2, "check", {"event": "PreToolUse", "session_id": "task_D",
                             "tool": "execute_command", "input": {"command": "rm -rf build"}})
case("contradicted command blocks further commands", rc == 2 and "COMMAND_RESULT_CHANGED" in out, out.strip())

# 10 every refusal wrote a hashed receipt
ev = open(os.path.join(ws2, ".countersign", "events.jsonl")).read()
case("refusals recorded with receipts", ev.count('"event": "verdict"') >= 2 and ev.count("receipt") >= 2)

# 11 a subtask claim with no observation behind it is refused
ws5 = ws_new()
run(ws5, "session-start", {"event": "SessionStart", "session_id": "task_G"})
rc, out = run(ws5, "check", {"event": "PreToolUse", "session_id": "task_G", "tool": "write_file",
                             "input": {"path": "pricing.ts", "subtask": "sub_1"}})
case("unsupported subtask claim refused", rc == 2 and "UNSUPPORTED_SUBTASK_EVIDENCE" in out, out.strip())

# 12 the same claim is admitted once that subtask has observed the path
run(ws5, "record", {"event": "PostToolUse", "session_id": "task_G", "tool": "read_file",
                    "input": {"path": "pricing.ts", "subtask": "sub_1"}})
rc, out = run(ws5, "check", {"event": "PreToolUse", "session_id": "task_G", "tool": "write_file",
                             "input": {"path": "pricing.ts", "subtask": "sub_1"}})
case("supported subtask claim admitted", rc == 0 and "ADMITTED" in out, out.strip())

# 13 the lens renders the real record into one page
rc, out = run(ws5, "session-start", {"event": "SessionStart", "session_id": "task_H"})
lens = os.path.join(HERE, "..", "lens.py")
p = subprocess.run([sys.executable, lens, ws5, "-o", os.path.join(ws5, "lens.html")],
                   capture_output=True, text=True)
page = open(os.path.join(ws5, "lens.html"), encoding="utf-8").read() if p.returncode == 0 else ""
case("lens renders real refusals", p.returncode == 0 and "UNSUPPORTED_SUBTASK_EVIDENCE" in page
     and "receipt" in page, p.stdout + p.stderr)

# 14 probe captures a real payload and never blocks a call
p = subprocess.run([sys.executable, GATE, "probe"],
                   input=json.dumps({"event": "PreToolUse", "session_id": "task_G",
                                     "tool": "write_file",
                                     "input": {"path": "pricing.ts"}}),
                   capture_output=True, text=True,
                   env=dict(os.environ, COUNTERSIGN_WORKSPACE=ws5), cwd=ws5)
payloads = os.path.join(ws5, ".countersign", "payloads")
case("probe never blocks and records the payload",
     p.returncode == 0 and os.path.isdir(payloads) and len(os.listdir(payloads)) == 1,
     p.stdout + p.stderr)

# 15 export writes one hashed evidence record per task
p = subprocess.run([sys.executable, GATE, "export"],
                   input=json.dumps({"session_id": "all"}), capture_output=True, text=True,
                   env=dict(os.environ, COUNTERSIGN_WORKSPACE=ws5), cwd=ws5)
exp = os.path.join(ws5, ".countersign", "exports", "task_G.json")
rec = json.load(open(exp)) if os.path.exists(exp) else {}
case("export produces a hashed task record",
     p.returncode == 0 and rec.get("record_hash") and rec.get("observations"),
     p.stdout + p.stderr)

for w in (ws, ws2, ws3, ws4, ws5):
    shutil.rmtree(w, ignore_errors=True)

bad = [r for r in results if not r[1]]
print(f"\n{len(results) - len(bad)}/{len(results)} passed")
sys.exit(1 if bad else 0)
