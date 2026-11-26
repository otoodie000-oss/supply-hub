#!/bin/sh
# Resumable training driver: repeats engine/train.py chunks until the run reaches its configured steps.
# Usage: sh engine/train_loop.sh RUN [threads]
RUN=$1
TH=${2:-4}
D=/home/user/work/x/runs/$RUN
while true; do
  python3 /home/user/supply-hub/turbox/engine/train.py --run $RUN --budget 540 --threads $TH >> $D/train.out 2>&1 || exit 1
  python3 - "$D" <<'PY' && exit 0
import json, sys
d = sys.argv[1]
r = json.load(open(d + "/run.json"))
last = [json.loads(l) for l in open(d + "/log.jsonl")][-1]
sys.exit(0 if last["step"] >= r["steps"] else 1)
PY
done
