#!/usr/bin/env bash
# 重建收件箱 + git 提交推送（支持双远端：origin=GitHub, gitee=码云Pages）
# gitee 仅当配置了对应 remote 时才推；任一失败不影响另一个。
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
    # 逐个远端推送（origin 必推；gitee 存在才推）
    for remote in origin gitee; do
      if git remote get-url "$remote" >/dev/null 2>&1; then
        if git push "$remote"; then
          echo "published to $remote"
        else
          echo "push to $remote failed (检查 remote / PAT 权限)"
        fi
      fi
    done
  fi
else
  echo "not a git repo / remote not configured, skip publish"
fi
