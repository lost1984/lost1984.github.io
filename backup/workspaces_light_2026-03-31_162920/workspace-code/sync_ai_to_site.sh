#!/usr/bin/env bash
set -euo pipefail

SRC_DIR="${SRC_DIR:-/root/ai}"
SITE_REPO_DIR="${SITE_REPO_DIR:-/root/ai-site}"
SITE_GIT_DIR="${SITE_GIT_DIR:-/root/.ai-site-git}"
SITE_TITLE="${SITE_TITLE:-YT /root/ai 镜像站}"
BRANCH="${BRANCH:-master}"

if [[ ! -d "$SRC_DIR" ]]; then
  echo "[ERR] source dir not found: $SRC_DIR" >&2
  exit 1
fi

if [[ ! -d "$SITE_GIT_DIR" ]]; then
  echo "[ERR] bare git repo not found: $SITE_GIT_DIR" >&2
  echo "先初始化 GitHub 仓库镜像。" >&2
  exit 1
fi

mkdir -p "$SITE_REPO_DIR"

python3 /root/.openclaw/workspace-code/site_sync.py \
  --src "$SRC_DIR" \
  --dst "$SITE_REPO_DIR" \
  --title "$SITE_TITLE"

export GIT_DIR="$SITE_GIT_DIR"
export GIT_WORK_TREE="$SITE_REPO_DIR"

git add -A
if git diff --cached --quiet; then
  echo "[OK] no changes"
  exit 0
fi

git commit -m "sync ai mirror: $(date '+%F %T %z')"
git push origin "$BRANCH"

echo "[OK] synced to GitHub Pages"
