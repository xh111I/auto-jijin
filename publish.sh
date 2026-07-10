#!/usr/bin/env bash
# 重建收件箱 + git 提交推送（支持双远端：origin=GitHub, gitee=码云Pages）
# gitee 仅当配置了对应 remote 时才推；任一失败不影响另一个。
# push 自带重试(最多6次, 退避5秒), 仍全失败则留给『Git推送探活』自动化兜底。
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

# 优化 git 传输参数（多文件小体积报告场景；幂等，失败不影响主流程）
git config --local http.postBuffer 524288000 2>/dev/null || true
git config --local core.compression 9 2>/dev/null || true

bash "$ROOT/rebuild_index.sh" || true

# 带重试的推送函数（正确用 $? 判断退出码，杜绝管道假阳性）
push_with_retry() {
  local remote="$1"
  local max=6 attempt=1 rc=1
  while [ $attempt -le $max ]; do
    echo "→ push $remote (attempt $attempt/$max)"
    if git push "$remote" >"/tmp/pub_${remote}.log" 2>&1; then
      echo "✅ published to $remote"
      return 0
    fi
    rc=$?
    tail -2 "/tmp/pub_${remote}.log"
    attempt=$((attempt + 1))
    [ $attempt -le $max ] && sleep 5
  done
  echo "⚠️ push to $remote failed after $max attempts (待『Git推送探活』兜底重试)"
  return $rc
}

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git add -A
  if git diff --cached --quiet; then
    echo "no changes to publish"
  else
    git commit -m "auto: fund reports $(date +%Y-%m-%dT%H:%M)" >/dev/null
    # 逐个远端推送（origin 必推；gitee 存在才推）
    for remote in origin gitee; do
      if git remote get-url "$remote" >/dev/null 2>&1; then
        push_with_retry "$remote" || true
      fi
    done
  fi
else
  echo "not a git repo / remote not configured, skip publish"
fi
