#!/bin/sh
# Build the narrated intro that stands on its own for a social post.
#
#   sh demo/scripts/build_intro_clip.sh
#
# Output: demo/media/countersign-intro.mp4 — the rendered composition with its five lines.
set -e
TTS="${TTS:-/tmp/csign_tts}"
OUT="${OUT:-/home/arch/countersign/demo/media}"

python3 - "$TTS" "$OUT/intro-silent.mp4" "$OUT/countersign-intro.mp4" <<'PY'
import os, subprocess, sys

tts, silent, out = sys.argv[1], sys.argv[2], sys.argv[3]
PLACE = [("i1", 0.6), ("i2", 5.5), ("i3", 10.4), ("i4", 17.0), ("i5", 20.8)]

def dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                 "-of", "csv=p=0", p], capture_output=True, text=True).stdout.strip())

total = dur(silent)
inputs, chains = ["-f", "lavfi", "-t", f"{total}", "-i", "anullsrc=r=48000:cl=stereo"], []
lines = []
prev_end = None
for i, (name, at) in enumerate(PLACE, start=1):
    p = os.path.join(tts, name + ".mp3")
    d = dur(p)
    if prev_end is not None and round(at - prev_end, 2) < 0.8:
        sys.exit(f"line {name} starts {round(at-prev_end,2)}s after the previous line ends")
    if at + d > total:
        sys.exit(f"line {name} runs past the picture")
    lines.append((name, at, round(d, 2)))
    prev_end = at + d
    inputs += ["-i", p]
    chains.append(f"[{i}:a]aresample=48000,adelay={int(at*1000)}|{int(at*1000)}[a{i}]")

mix_in = "[0:a]" + "".join(f"[a{i}]" for i in range(1, len(PLACE) + 1))
flt = (";".join(chains) + ";" + mix_in +
       f"amix=inputs={len(PLACE)+1}:normalize=0:duration=first[mixed];"
       "[mixed]highpass=f=70,acompressor=threshold=-18dB:ratio=3:attack=5:release=200,"
       "alimiter=limit=0.95,loudnorm=I=-16:TP=-1.5:LRA=11[out]")
pic = str(inputs.count("-i"))
subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-i", silent, "-filter_complex", flt,
                "-map", f"{pic}:v", "-map", "[out]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                "-shortest", "-movflags", "+faststart", out], check=True)
print("intro clip:", out, f"{total:.1f}s,", sum(l[2] for l in lines), "s of speech")
for name, at, d in lines:
    print(f"  {name} @ {at:5.1f}s  {d:4.1f}s")
PY
