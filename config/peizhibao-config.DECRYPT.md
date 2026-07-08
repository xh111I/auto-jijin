# 配置宝加密配置 · 解密指引

- 加密文件: `peizhibao-config.json.enc` (坚果云: `zy:/daily-report/config/`)
- 算法: AES-256-CBC (openssl, PBKDF2 + salt)
- 生成时间: 2026-07-08 11:13:01 +0800

## 解密命令（口令见对话框 / 本地 README，不存储于云端）
```bash
openssl enc -d -aes-256-cbc -pbkdf2 \
  -in peizhibao-config.json.enc \
  -out peizhibao-config.json \
  -pass pass:<你的口令>
```

## 还原后的结构
- account: 账户总资产/日收益/持有收益/累计收益/待买入
- strategy: 本金/风格/止损/止盈/单仓上限/总仓目标
- holdings: 各基金持仓（市值/权重/涨跌/状态/风险标记）
- pending_transactions: 待买入 + 待转换
- position_summary: 集中度/半导体暴露/各板块占比
