#!/usr/bin/env bash
set -euo pipefail

WORKDIR="${WORKDIR:-$HOME/douyu-recorder}"
SCRIPT_SRC="/root/.openclaw/workspace-code/douyu_recorder.py"
SCRIPT_DST="$WORKDIR/douyu_recorder.py"
LOGDIR="$WORKDIR/logs"
OUTDIR="${OUTDIR:-$HOME/videos/douyu}"
ROOM_URL="${ROOM_URL:-https://www.douyu.com/22619}"
ROOM_ID="${ROOM_ID:-5551871}"
ROOM_ALIAS="${ROOM_ALIAS:-douyu_22619}"
PLUGIN_DIR="${PLUGIN_DIR:-$WORKDIR/plugins}"
PYTHON_BIN="${PYTHON_BIN:-$(command -v python3)}"

mkdir -p "$WORKDIR" "$LOGDIR" "$OUTDIR" "$PLUGIN_DIR"
cp "$SCRIPT_SRC" "$SCRIPT_DST"
chmod +x "$SCRIPT_DST"

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "[ERROR] 缺少 ffmpeg，请先安装。Debian/Ubuntu: sudo apt-get update && sudo apt-get install -y ffmpeg"
  exit 1
fi

if ! command -v streamlink >/dev/null 2>&1; then
  echo "[ERROR] 缺少 streamlink，请先安装。Debian/Ubuntu: sudo apt-get update && sudo apt-get install -y streamlink"
  exit 1
fi

if [ ! -f "$PLUGIN_DIR/douyu.py" ]; then
  cat <<'EOF'
[WARN] 未发现 Douyu 插件文件：$PLUGIN_DIR/douyu.py
请先下载插件，例如：
mkdir -p "$PLUGIN_DIR"
curl -L https://raw.githubusercontent.com/v2wy/streamlink-plugin-for-douyu/master/douyu.py -o "$PLUGIN_DIR/douyu.py"
EOF
fi

CRON_CMD_22="$PYTHON_BIN $SCRIPT_DST --room-url '$ROOM_URL' --room-id '$ROOM_ID' --room-alias '$ROOM_ALIAS' --plugin-dir '$PLUGIN_DIR' --outdir '$OUTDIR' >> '$LOGDIR/22.log' 2>&1"
CRON_CMD_23="$PYTHON_BIN $SCRIPT_DST --room-url '$ROOM_URL' --room-id '$ROOM_ID' --room-alias '$ROOM_ALIAS' --plugin-dir '$PLUGIN_DIR' --outdir '$OUTDIR' >> '$LOGDIR/23.log' 2>&1"

TMP_CRON="$(mktemp)"
crontab -l 2>/dev/null | grep -v "douyu_recorder.py" > "$TMP_CRON" || true
{
  cat "$TMP_CRON"
  echo "0 22 * * * $CRON_CMD_22"
  echo "0 23 * * * $CRON_CMD_23"
} | crontab -
rm -f "$TMP_CRON"

echo "[OK] 已安装定时任务"
echo "工作目录: $WORKDIR"
echo "插件目录: $PLUGIN_DIR"
echo "录播目录: $OUTDIR"
echo "查看计划任务: crontab -l"
echo "手动测试: $PYTHON_BIN $SCRIPT_DST --room-url '$ROOM_URL' --room-id '$ROOM_ID' --room-alias '$ROOM_ALIAS' --plugin-dir '$PLUGIN_DIR' --outdir '$OUTDIR'"
