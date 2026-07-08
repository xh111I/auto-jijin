#!/usr/bin/env bash
# 一次性连接 GitHub 仓库(需提供 用户名 + 仓库名 + PAT)
# 用法: bash connect_repo.sh <user> <repo> <PAT>
set -e
if [ $# -lt 3 ]; then echo "usage: connect_repo.sh <user> <repo> <PAT>"; exit 1; fi
USER="$1"; REPO="$2"; PAT="$3"
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if [ ! -d .git ]; then git init -q; fi
git branch -M main 2>/dev/null || true
git remote remove origin 2>/dev/null || true
git remote add origin "https://$USER:$PAT@github.com/$USER/$REPO.git"
echo "remote set -> github.com/$USER/$REPO (branch main)"

# 首次推送(仓库需已存在,且 PAT 需有 repo 写权限)
if git push -u origin main; then
  echo "initial push ok"
else
  echo "initial push failed: 请确认仓库已创建且 PAT 具备 repo 权限"
fi
echo "下一步: 在 GitHub 仓库 Settings -> Pages 选择 main 分支 / root,稍候即可访问 https://$USER.github.io/$REPO/"
