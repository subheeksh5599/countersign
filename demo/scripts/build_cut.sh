#!/bin/sh
# Build the demo: the recording, cut to what carries product, then the narrated intro in
# front of it, then the narration over the whole thing.
#
#   sh demo/scripts/build_cut.sh
#
# Output: docs/media/countersign-demo.mp4   (intro + recording, narrated)
#         docs/media/countersign-cut.mp4    (intro + recording, no narration)
#
# The submission rules ask for a video of 3 minutes or less with at least 90 seconds showing
# the solution in action. The first cut carried 44s of the recording, which is under that
# floor, so this cut carries 95.2s of it. Every trim is a real source range; there is no
# re-staging and no re-encode of the source.
set -e
SRC="${SRC:-/home/arch/Videos/recording_2026-09-27_14.35.18.mp4}"
INTRO="${INTRO:-/home/arch/countersign/docs/media/countersign-intro.mp4}"
TTS="${TTS:-/tmp/csign_tts2}"
OUT="${OUT:-/home/arch/countersign/docs/media}"
W=1364
H=766
FPS=30
TAIL=3.1     # the last frame is held, so the closing line has room to land

mkdir -p "$OUT"

# --- 1. the cut ----------------------------------------------------------------------
# 1   3.5  -   8.0   landing: the claim, then the failure story
# 2  14.0  -  26.0   landing: the sections, one screen of the product's own words
# 3  41.5  -  43.0   console, before anything runs: receipts 0, no verdict
# 4  44.2  -  67.5   the operator bar, create demo repository, run the agent turn, the refusal
# 5  67.5  -  91.5   the self-test page: the acceptance check run on demand, every step passing
# 6  91.5  - 100.0   evidence: each session's manifest, then the interceptor's classified calls
# 7 100.0  - 106.4   receipts: replay both receipts, 0 failed, chain head held at the end
# 8 107.0  - 122.0   the published record page, scrolled
#
# Removed: 0-3.5 and 8.0-14.0 and 26.0-41.5 (landing scrolling with nothing changing),
# 43.0-44.2 (a scroll that previews the refusal before the narration sets it up).
ffmpeg -v error -y -i "$SRC" -i "$INTRO" -filter_complex "\
[0:v]trim=start=3.5:end=8.0,setpts=PTS-STARTPTS[s0];\
[0:v]trim=start=14.0:end=26.0,setpts=PTS-STARTPTS[s1];\
[0:v]trim=start=41.5:end=43.0,setpts=PTS-STARTPTS[s2];\
[0:v]trim=start=44.2:end=67.5,setpts=PTS-STARTPTS[s3];\
[0:v]trim=start=67.5:end=91.5,setpts=PTS-STARTPTS[s4];\
[0:v]trim=start=91.5:end=100.0,setpts=PTS-STARTPTS[s5];\
[0:v]trim=start=100.0:end=106.4,setpts=PTS-STARTPTS[s6];\
[0:v]trim=start=107.0:end=122.0,setpts=PTS-STARTPTS[s7];\
[s0][s1][s2][s3][s4][s5][s6][s7]concat=n=8:v=1:a=0[cut];\
[cut]fps=${FPS},scale=${W}:${H}:flags=lanczos,setsar=1,tpad=stop_mode=clone:stop_duration=${TAIL}[cutp];\
[1:v]fps=${FPS},scale=${W}:${H}:flags=lanczos,setsar=1[intro];\
[intro][cutp]concat=n=2:v=1:a=0[vout]" \
  -map "[vout]" -r ${FPS} -crf 20 -preset veryfast -pix_fmt yuv420p -movflags +faststart \
  "$OUT/countersign-cut.mp4"

ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT/countersign-cut.mp4" |
  awk '{printf "cut (intro + recording, silent): %.1fs\n", $1}'

# --- 2. the narration ---------------------------------------------------------------
# Placement is absolute on the final timeline. Every line is measured before mixing, and
# this script fails if two lines are closer than 0.8 s or if a line runs past the picture.
python3 - "$TTS" "$OUT/countersign-cut.mp4" "$OUT/countersign-demo.mp4" <<'PY'
import json, os, subprocess, sys

tts, cut, out = sys.argv[1], sys.argv[2], sys.argv[3]

# line -> absolute start on the final timeline. The intro holds 0.0-26.5, then the
# recording: 26.5 landing, 44.5 the console and the refusal, 67.8 the self-test,
# 91.8 evidence and the interceptor, 100.3 receipts, 106.7 the published record.
PLACE = [
    ("i1", 0.6), ("i2", 5.5), ("i3", 10.4), ("i4", 17.0), ("i5", 20.8),
    ("d1", 26.8), ("d2", 33.0), ("d3", 40.5),
    ("d4", 46.0), ("d5", 52.5), ("d6", 58.6), ("d7", 64.3),
    ("d8", 73.0), ("d9", 79.5),
    ("d10", 92.0), ("d11", 96.0), ("d12", 101.0), ("d13", 107.6), ("d14", 118.0),
]

def dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                 "-of", "csv=p=0", p], capture_output=True, text=True).stdout.strip())

total = dur(cut)
lines = []
for name, start in PLACE:
    p = os.path.join(tts, name + ".mp3")
    if not os.path.exists(p):
        sys.exit(f"missing narration line: {p}")
    d = dur(p)
    lines.append({"line": name, "at": start, "dur": round(d, 2), "file": p})

lines.sort(key=lambda x: x["at"])
for i, ln in enumerate(lines):
    ln["end"] = round(ln["at"] + ln["dur"], 2)
    if i:
        gap = round(ln["at"] - lines[i - 1]["end"], 2)
        ln["gap"] = gap
        if gap < 0.8:
            sys.exit(f"line {ln['line']} starts {gap}s after {lines[i-1]['line']} ends; 0.8s minimum")
    if ln["end"] > total:
        sys.exit(f"line {ln['line']} ends at {ln['end']}s, past the picture ({total:.1f}s)")

print(f"narration: {len(lines)} lines, {sum(l['dur'] for l in lines):.1f}s of speech "
      f"over {total:.1f}s of picture ({sum(l['dur'] for l in lines)/total*100:.0f}%)")

# mix: one input per line, delayed to its start, over a silent base as long as the cut
inputs, chains = ["-f", "lavfi", "-t", f"{total}", "-i", "anullsrc=r=48000:cl=stereo"], []
for i, ln in enumerate(lines, start=1):
    inputs += ["-i", ln["file"]]
    chains.append(f"[{i}:a]aresample=48000,adelay={int(ln['at']*1000)}|{int(ln['at']*1000)}[a{i}]")
mix_in = "[0:a]" + "".join(f"[a{i}]" for i in range(1, len(lines) + 1))
flt = (";".join(chains) + ";" + mix_in +
       f"amix=inputs={len(lines)+1}:normalize=0:duration=first[mixed];"
       "[mixed]highpass=f=70,acompressor=threshold=-18dB:ratio=3:attack=5:release=200,"
       "alimiter=limit=0.95,loudnorm=I=-16:TP=-1.5:LRA=11[out]")

pic = str(inputs.count("-i"))        # input index of the picture: after anullsrc and every line
subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-i", cut, "-filter_complex", flt,
                "-map", f"{pic}:v", "-map", "[out]",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
                "-movflags", "+faststart", out], check=True)
print("wrote", out)
PY
