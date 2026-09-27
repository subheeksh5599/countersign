#!/bin/sh
# Verify the shipped demo instead of asserting it is fine.
#
#   sh demo/scripts/verify_cut.sh
#
# Checks, in order:
#   1  the file plays back: duration, fps, size, an audio stream that is not silent
#   2  every narration line starts where it was planned, within 0.35 s
#   3  the refusal moment is not covered by speech
#   4  the positive claim is on screen: a frame carrying REFUSED / EVIDENCE_SUPERSEDED
#   5  no frame carries a state the demo is not allowed to show (cold loader, browser
#      transfer chrome, the static record page, an error page)
#   6  the voice is male: median F0 of the delivered audio, 100-130 Hz is the adult band
set -e
MEDIA="${1:-/home/arch/countersign/demo/media}"
DEMO="$MEDIA/countersign-demo.mp4"
[ -s "$DEMO" ] || { echo "missing $DEMO" >&2; exit 1; }
work=$(mktemp -d)
fail=0
note() { printf '%-6s %s\n' "$1" "$2"; }
[ "$1" = "--keep" ] || true

echo "== 1. playback =="
ffprobe -v error -show_entries format=duration,size -show_entries stream=codec_type,codec_name,width,height,r_frame_rate \
  -of default=noprint_wrappers=1 "$DEMO"
D=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$DEMO")
AUD=$(ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of csv=p=0 "$DEMO")
[ -n "$AUD" ] || { note FAIL "no audio stream"; fail=1; }
awk -v d="$D" 'BEGIN{ if (d < 60 || d > 80) { printf "FAIL   duration %.1fs outside the 60-80s window\n", d; exit 1 } }' || fail=1

echo "== 2. line placement =="
ffmpeg -hide_banner -nostats -i "$DEMO" -af "silencedetect=noise=-42dB:d=0.25" -f null - 2>&1 |
python3 -c "
import re, sys
plan = {'i1':0.6,'i2':5.5,'i3':10.4,'i4':17.0,'i5':20.8,'d1':27.0,'d2':32.0,'d3':39.8,
        'd4':48.0,'d5':55.4,'d6':61.6,'d7':66.9}
starts=[]
for line in sys.stdin:
    m=re.search(r'silence_end: ([0-9.]+)', line)
    if m: starts.append(float(m.group(1)))
bad=0; n=0
for name, want in plan.items():
    n+=1
    near=[s for s in starts if abs(s-want)<=0.35]
    if not near:
        print(f'  FAIL  {name}: no speech starts within 0.35s of {want}s (found {[round(s,1) for s in starts]})')
        bad+=1
print(f'  {\"ok\" if not bad else \"FAIL\"}    {n-bad}/{n} lines start where planned')
sys.exit(1 if bad else 0)
" || fail=1

echo "== 3. the refusal moment is silent =="
ffmpeg -hide_banner -nostats -i "$DEMO" -af "silencedetect=noise=-42dB:d=0.9" -f null - 2>&1 |
python3 -c "
import re, sys
sil=[]; cur=None
for line in sys.stdin:
    m=re.search(r'silence_start: ([0-9.]+)', line)
    if m: cur=float(m.group(1))
    m=re.search(r'silence_end: ([0-9.]+)', line)
    if m and cur is not None: sil.append((cur, float(m.group(1)))); cur=None
hit=[s for s in sil if s[0] <= 46.4 and s[1] >= 47.9]
print(f'  {\"ok\" if hit else \"FAIL\"}    a silence of at least 0.9s covers 46.4-47.9s ({len(sil)} silences found)')
sys.exit(0 if hit else 1)
" || fail=1

echo "== 4/5. what the frames carry =="
ffmpeg -v error -i "$DEMO" -vf fps=1 -q:v 4 "$work/f_%03d.png"
positive=0; bad=""
for f in "$work"/f_*.png; do
  t=$(tesseract "$f" - --psm 6 2>/dev/null | tr '\n' ' ')
  echo "$t" | grep -qiE "EVIDENCE_SUPERSEDED|REFUSED" && positive=$((positive+1))
  echo "$t" | grep -qiE "Transferring data from|not found|does not exist|static record of one run|This site can.t be reached|loading" && bad="$bad $(basename "$f")"
done
if [ "$positive" -ge 3 ]; then note ok "$positive frames carry the refusal"; else note FAIL "only $positive frames carry the refusal"; fail=1; fi
if [ -z "$bad" ]; then note ok "no unwanted state in any frame"; else note FAIL "unwanted state in:$bad"; fail=1; fi

echo "== 6. the voice is male =="
ffmpeg -v error -y -i "$DEMO" -ac 1 -ar 8000 -f s16le "$work/a.raw"
python3 - "$work/a.raw" <<'PY'
import struct, sys
raw = open(sys.argv[1], "rb").read()
n = len(raw) // 2
x = struct.unpack("<%dh" % n, raw[:n*2])
SR = 8000
win = int(SR * 0.04)          # 40 ms windows
hop = int(SR * 0.02)
f0s = []
energy = [sum(abs(v) for v in x[i:i+win]) / win for i in range(0, n - win, hop)]
peak = max(energy) if energy else 0
for i in range(0, n - win, hop):
    seg = x[i:i+win]
    e = sum(abs(v) for v in seg) / win
    if e < peak * 0.25:        # skip silence and quiet frames
        continue
    best, bestlag = 0.0, 0
    for lag in range(40, 121):  # 66-200 Hz at 8 kHz
        c = 0.0
        for j in range(win - lag):
            c += seg[j] * seg[j + lag]
        c /= (win - lag)
        if c > best:
            best, bestlag = c, lag
    if bestlag:
        f0s.append(SR / bestlag)
f0s.sort()
med = f0s[len(f0s)//2] if f0s else 0
ok = 100 <= med <= 130
print(f"  {'ok' if ok else 'FAIL'}    median F0 {med:.1f} Hz over {len(f0s)} voiced windows "
      f"({'adult male band' if ok else 'outside the adult male band'})")
sys.exit(0 if ok else 1)
PY
[ $? -eq 0 ] || fail=1

echo
if [ "$fail" -eq 0 ]; then echo "VERIFIED: $DEMO"; else echo "VERIFICATION FAILED"; exit 1; fi
