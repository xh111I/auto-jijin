#!/usr/bin/env bash
# 重建报告收件箱 index.html v2
# 改进: 仅展示HTML报告(过滤.py/.json等)、中文类型标签、时间排序、统计计数
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
OUT="$ROOT/index.html"

# 根据文件名返回 (标签, 排序权重, 显示名)
# 排序权重: 早间1 午盘2 盘中预警3 尾盘4 晚间9 其他5
classify() {
  local f="$1"
  case "$f" in
    早间*|early-morning*)   echo "🌅|1|早间全球分析" ;;
    午盘*|morning-close*|pre-close*) echo "📊|2|午盘收盘分析" ;;
   盘中预警*|intraday-alert*) echo "⚡|3|盘中预警" ;;
    尾盘*|tail-decision*)   echo "🎯|4|尾盘决策" ;;
    晚间*|evening-review*)  echo "🌙|9|晚间复盘" ;;
    *)                     echo "📄|5|$f" ;;
  esac
}

{
  echo '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><title>基金报告收件箱</title>'
  echo '<meta name="viewport" content="width=device-width,initial-scale=1">'
  cat <<'CSS'
<style>
body{font-family:-apple-system,"PingFang SC",sans-serif;max-width:800px;margin:0 auto;padding:20px;background:#f7f8fa;color:#1f2937}
h1{font-size:22px;margin:0 0 4px}.subtitle{color:#9ca3af;font-size:13px;margin-bottom:16px}
.date-row{display:flex;align-items:center;gap:8px;margin:18px 0 8px;border-bottom:1px solid #e5e7eb;padding-bottom:4px}
.date{color:#374151;font-size:15px;font-weight:600}
.count{background:#e0e7ff;color:#4338ca;font-size:11px;padding:1px 8px;border-radius:10px}
a{display:flex;align-items:center;gap:8px;padding:10px 12px;margin:4px 0;background:#fff;border-radius:8px;text-decoration:none;color:#1f2937;box-shadow:0 1px 3px rgba(0,0,0,.05);transition:transform .1s}
a:hover{transform:translateY(-1px);box-shadow:0 2px 6px rgba(0,0,0,.08)}
.type-badge{background:#f3f4f6;color:#4b5563;font-size:11px;padding:2px 8px;border-radius:4px;white-space:nowrap;flex-shrink:0}
.fname{font-size:14px;overflow:hidden;text-overflow:ellipsis}
.time-hint{color:#9ca3af;font-size:11px;margin-left:auto;flex-shrink:0}
.footer{margin-top:24px;color:#9ca3af;font-size:12px;text-align:center}
</style>
CSS
  echo '</head><body>'
  echo "<h1>📱 基金报告收件箱</h1>"
  echo '<div class="subtitle">每日自动生成 · 仅展示正式报告</div>'

  if [ -d "$ROOT/data/reports" ]; then
    # 按日期倒序（最新在前）
    for d in $(ls -r "$ROOT/data/reports" 2>/dev/null); do
      dir="$ROOT/data/reports/$d"

      # 只统计 .html 文件
      html_count=$(find "$dir" -maxdepth 1 -name "*.html" 2>/dev/null | wc -l)
      [ "$html_count" -eq 0 ] && continue

      echo "<div class=\"date-row\"><span class=\"date\">📅 $d</span><span class=\"count\">${html_count} 份报告</span></div>"

      # 收集所有 .html 文件并排序：按分类权重→按文件修改时间（新在前）
      declare -A entries   # key=filename  value="label|weight|display_name|mtime"
      weights=""
      for f in $(ls "$dir" 2>/dev/null); do
        # 跳过非 HTML 文件
        [[ "$f" != *.html ]] && continue
        IFS='|' read -r badge w disp <<< "$(classify "$f")"
        mtime=$(stat -c %Y "$dir/$f" 2>/dev/null || stat -f %m "$dir/$f" 2>/dev/null || echo 0)
        # 用 weight.mtime 作为排序键，保证同类按时排序
        printf -v key '%s.%010d' "$w" "$mtime"
        entries["$key"]="$f|$badge|$disp"
        weights="$weights $key"
      done

      # 按 key 排序（同类排一起，新文件在前）
      for k in $(echo $weights | tr ' ' '\n' | sort); do
        IFS='|' read -r fname badge disp <<< "${entries[$k]}"
        # 从文件名提取时间提示（如 _1351 → 13:51）
        time_hint=""
        if [[ "$fname" =~ _(20[0-9]{6})_([0-9]{4}) ]]; then
          time_hint="${BASH_REMATCH[2]:0:2}:${BASH_REMATCH[2]:2:2}"
        fi

        if [ -n "$time_hint" ]; then
          echo "<a href=\"data/reports/$d/$fname\"><span class=\"type-badge\">$badge</span><span class=\"fname\">$disp</span><span class=\"time-hint\">$time_hint</span></a>"
        else
          echo "<a href=\"data/reports/$d/$fname\"><span class=\"type-badge\">$badge</span><span class=\"fname\">$disp</span></a>"
        fi
      done
    done
  fi

  echo '<div class="viewbox">'
  echo '<b>📂 如何查看报告（重要）</b><br>'
  echo '请用 <b>真实浏览器（Chrome / Edge）</b> 打开，<b>不要</b>用 WorkBuddy App 内置预览面板（沙箱 webview 解析不了相对路径、连不上 github.io，会显示空白）。三种方式任选：<br>'
  echo '① <b>本地文件（最稳）</b>：直接双击 <code>C:/Users/LEGION/Nutstore/1/daily-report/index.html</code><br>'
  echo '② <b>本机服务</b>：若已运行本地 HTTP 服务则访问 <code>http://localhost:8123</code>（启动：<code>python -m http.server 8123 --directory "C:/Users/LEGION/Nutstore/1/daily-report"</code>）<br>'
  echo '③ <b>网页端</b>：GitHub Pages <code>https://xh111i.github.io/auto-jijin/</code>（真实浏览器 + 硬刷新 Ctrl+F5）'
  echo '</div>'
  echo '<div class="footer">由每日基金自动报告系统生成 · 数据来源 NeoData · 仅供参考，不构成投资建议</div>'
  echo '</body></html>'
} > "$OUT"
echo "rebuilt $OUT ($html_count total reports)"
