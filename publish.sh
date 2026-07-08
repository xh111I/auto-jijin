#!/usr/bin/env bash
# 重建收件箱 + git 提交推送(未配置远程则优雅跳过)
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

bash "$ROOT/rebuild_index.sh" || true

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git add -A
  if git diff --cached --quiet; then
    echo "no changes to publish"
  else
    git commit -m "auto: fund reports $(date +%Y-%m-%dT%H:%M)" >/dev/null
    if git push; then
      echo "published to remote"
    else
      echo "push failed (检查 remote / PAT 权限)"
    fi
  fi
else
  echo "not a git repo / remote not configured, skip publish"
fi
