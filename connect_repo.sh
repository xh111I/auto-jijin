#!/usr/bin/env bash
# 一次性连接 GitHub 仓库(需提供 用户名 + 仓库名 + PAT)
# 用法: bash connect_repo.sh <user> <repo> <PAT>
if [ $# -lt 3 ]; then echo "usage: connect_repo.sh <user> <repo> <PAT>"; exit 1; fi
USER="$1"; REPO="$2"; PAT="$3"
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

git init -q 2>/dev/null || true
git config user.email "wb-automation@local" 2>/dev/null || true
git config user.name "WorkBuddy Automation" 2>/dev/null || true
git branch -M main 2>/dev/null || true
git remote remove origin 2>/dev/null || true
git remote add origin "https://$USER:$PAT@github.com/$USER/$REPO.git"
echo "remote set -> github.com/$USER/$REPO (branch main)"

git add -A
if git diff --cached --quiet; then
  echo "nothing to commit"
else
  git commit -q -m "chore: connect repo sync $(date +%F)"
fi

# 首次推送(仓库需已存在; Fine-grained PAT 需: Repository access 包含该仓库 + Contents=Read and write)
if git push -u origin main 2>push_err.txt; then
  echo "initial push ok"
else
  sed "s/$PAT/[REDACTED]/g" push_err.txt
  echo "initial push failed: 请确认 (1)仓库已存在 (2)Fine-grained PAT 的 Repository access 包含该仓库 (3)Contents 权限=Read and write"
fi
rm -f push_err.txt
echo "下一步: 在 GitHub 仓库 Settings -> Pages 选择 main 分支 / root,稍候即可访问 https://$USER.github.io/$REPO/"
