#!/usr/bin/env bash
# 重建报告收件箱 index.html(纯 bash,无外部依赖)
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
OUT="$ROOT/index.html"
{
  echo '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><title>基金报告收件箱</title>'
  echo '<meta name="viewport" content="width=device-width,initial-scale=1">'
  echo '<style>body{font-family:-apple-system,"PingFang SC",sans-serif;max-width:800px;margin:0 auto;padding:20px;background:#f7f8fa;color:#1f2937}a{display:block;padding:10px;margin:6px 0;background:#fff;border-radius:8px;text-decoration:none;color:#1f2937;box-shadow:0 1px 3px rgba(0,0,0,.05)}h1{font-size:22px}.date{color:#6b7280;font-size:13px;margin:14px 0 6px}</style>'
  echo '</head><body>'
  echo '<h1>📱 基金报告收件箱</h1>'
  if [ -d "$ROOT/data/reports" ]; then
    for d in $(ls -r "$ROOT/data/reports" 2>/dev/null); do
      echo "<div class=\"date\">$d</div>"
      for f in $(ls "$ROOT/data/reports/$d" 2>/dev/null); do
        echo "<a href=\"data/reports/$d/$f\">$f</a>"
      done
    done
  fi
  echo '<div class="date" style="margin-top:20px;color:#9ca3af">由每日基金自动报告系统生成 · 仅供参考,不构成投资建议</div>'
  echo '</body></html>'
} > "$OUT"
echo "rebuilt $OUT"
