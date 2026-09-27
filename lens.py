#!/usr/bin/env python3
"""Render the evidence store as one self-contained page: what each task held,
what was refused, and the receipts. Reads only real records; nothing is invented.
Usage: python3 lens.py <workspace> [-o out.html]
"""
import html, json, os, sys


def load(store):
    events = []
    ep = os.path.join(store, "events.jsonl")
    if os.path.exists(ep):
        with open(ep, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
    tasks = {}
    tp = os.path.join(store, "tasks")
    if os.path.isdir(tp):
        for name in sorted(os.listdir(tp)):
            if name.endswith(".json"):
                with open(os.path.join(tp, name), encoding="utf-8") as fh:
                    tasks[name[:-5]] = json.load(fh)
    return events, tasks


def esc(v):
    return html.escape(str(v))


def render(ws, events, tasks):
    verdicts = [e for e in events if e.get("event") == "verdict"]
    refused = [e for e in verdicts if e.get("verdict") == "REFUSED"]
    admitted = [e for e in verdicts if e.get("verdict") == "ADMITTED"]
    obs = [e for e in events if e.get("event") == "evidence_recorded"]
    rows = "".join(
        f"<tr><td>{esc(e['at'])}</td><td class='k'>{esc(e['event'])}</td>"
        f"<td>{esc(e.get('task',''))}</td><td class='mono'>{esc(e.get('path',''))}</td>"
        f"<td class='mono'>{esc(str(e.get('digest') or e.get('receipt') or '' )[:16])}</td></tr>"
        for e in events)
    cards = "".join(
        "<div class='card'><div class='code'>REFUSED: " + esc(",".join(e.get("codes", []))) +
        "</div><div class='meta'>task <b>" + esc(e.get("task")) + "</b> &middot; " +
        esc(e.get("path") or "(command)") + " &middot; " + esc(e.get("at")) + "</div>" +
        "<div class='mono'>receipt " + esc(e.get("receipt")) + "</div></div>"
        for e in refused)
    tree = "".join(
        "<div class='card'><div class='code'>manifest " + esc(sid) + "</div>" +
        "<div class='meta'>commit " + esc(str(m.get("commit"))[:12]) +
        " &middot; opened " + esc(m.get("opened_at")) +
        " &middot; implicit " + esc(m.get("implicit")) + "</div><ul>" +
        "".join(f"<li class='mono'>{esc(p)} &middot; {esc(str(v.get('digest'))[:16])}"
                f" &middot; via {esc(v.get('via','direct'))}</li>"
                for p, v in sorted((m.get("files") or {}).items())) + "</ul></div>"
        for sid, m in sorted(tasks.items()))
    subs = {}
    for sid, m in tasks.items():
        for p, v in (m.get("files") or {}).items():
            subs.setdefault(v.get("via", "direct"), []).append((sid, p, v.get("digest")))
    subrows = "".join(
        "<div class='card'><div class='code'>" + esc(via) + "</div><div class='meta'>" +
        esc(len(items)) + " observation(s)</div><ul>" +
        "".join(f"<li class='mono'>{esc(s)} &middot; {esc(p)} &middot; "
                f"{esc(str(d)[:16])}</li>" for s, p, d in sorted(items)) + "</ul></div>"
        for via, items in sorted(subs.items()))
    return f"""<!doctype html><meta charset="utf-8"><title>Countersign - {esc(os.path.basename(ws.rstrip('/')) or ws)}</title>
<style>
 body{{background:#0d0f12;color:#e6e8eb;font:14px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;margin:0;padding:32px}}
 h1{{font-size:18px;margin:0 0 4px}} h2{{font-size:13px;text-transform:uppercase;letter-spacing:.12em;color:#8b93a1;margin:28px 0 8px}}
 .banner{{border-left:3px solid #d64545;padding:8px 12px;background:#1a1113;margin:16px 0}}
 .counts{{display:flex;gap:24px;margin:12px 0 0}} .counts div b{{display:block;font-size:22px}}
 table{{width:100%;border-collapse:collapse}} td,th{{text-align:left;padding:4px 8px;border-bottom:1px solid #1c2127;vertical-align:top}}
 th{{color:#8b93a1;font-weight:400;font-size:12px}} .mono{{color:#9fb0c4}} .k{{color:#e2b341}}
 .card{{border:1px solid #1c2127;border-radius:6px;padding:10px 12px;margin:8px 0;background:#111419}}
 .code{{color:#ff7b72;font-weight:600}} .meta{{color:#8b93a1;margin:4px 0}} ul{{margin:4px 0 0 18px;padding:0}}
 .note{{color:#8b93a1;margin:8px 0 0;max-width:80ch}}
</style>
<h1>Countersign</h1><div class="meta">workspace <span title="{esc(ws)}">{esc(os.path.basename(ws.rstrip('/')) or ws)}</span></div>
<p class="note">A static record of one run, rendered from the store that run left on disk.
The operable console reads a live runtime instead: clone the repository, run
<span class="mono">sh run.sh</span>, and open <span class="mono">http://127.0.0.1:4311/console</span>.</p>
<p class="banner">Every refusal below is a state-changing action that did not run, because the
evidence the task was holding no longer described this workspace.</p>
<div class="counts"><div><b>{len(tasks)}</b>tasks</div><div><b>{len(obs)}</b>observations</div>
<div><b>{len(refused)}</b>refusals</div><div><b>{len(admitted)}</b>admissions</div></div>
<h2>Refusals</h2>{cards or "<div class='meta'>none recorded</div>"}
<h2>What each task holds</h2>{tree or "<div class='meta'>no manifests</div>"}
<h2>Who observed what</h2>{subrows or "<div class='meta'>nothing observed</div>"}
<h2>Event log</h2><table><tr><th>at</th><th>event</th><th>task</th><th>path</th><th>digest / receipt</th></tr>{rows}</table>
"""


def main():
    ws = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("COUNTERSIGN_WORKSPACE")
    if not ws:
        sys.stderr.write("usage: lens.py <workspace> [-o out.html]\n")
        return 2
    out = None
    if "-o" in sys.argv:
        out = sys.argv[sys.argv.index("-o") + 1]
    events, tasks = load(os.path.join(ws, ".countersign"))
    page = render(ws, events, tasks)
    if out:
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(page)
        print(f"wrote {out} ({len(page)} bytes)")
    else:
        sys.stdout.write(page)
    return 0


if __name__ == "__main__":
    sys.exit(main())
