#!/usr/bin/env bash
set -euo pipefail
cd /root/.openclaw/workspace-code

PY=python3
SCRIPT=/root/.openclaw/workspace-code/douyu_recorder.py
PLUGIN=/root/.openclaw/workspace-code/.douyu-plugin
BASE_OUT=/root/.openclaw/workspace-code/test_recordings/minana_schedule
ROOM_URL='https://www.douyu.com/22619'

run_slot() {
  local label="$1"
  local outdir="$BASE_OUT/$label"
  mkdir -p "$outdir"
  "$PY" "$SCRIPT" \
    --room-url "$ROOM_URL" \
    --plugin-dir "$PLUGIN" \
    --outdir "$outdir" \
    --keep-source \
    --max-minutes 30
}

run_slot "2200_2230"
run_slot "2300_2330"
