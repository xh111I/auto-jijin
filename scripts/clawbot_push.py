#!/usr/bin/env python3
"""
ClawBot Push Helper - 将消息推送到微信 ClawBot 对话
============================================
由自动化任务调用，在报告生成后推送通知到手机 ClawBot。

用法:
  python3 clawbot_push.py "要发送的消息内容"
  python3 clawbot_push.py --file /path/to/report.html --title "报告标题"

原理（按优先级尝试）:
  方式1: 调用 WorkBuddy MCP 工具 WechatReply（如果在 agent 上下文中运行）
  方式2: 通过 ilinkai.weixin.qq.com API 直接发送（需要凭证）
  方式3: 写入 claw-push-queue.json 供下次 ClawBot 轮询时拾取
"""

import sys
import os
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime

# ── 配置 ──
WORKBUDDY_HOME = Path(os.path.expanduser("~/.workbuddy"))
QUEUE_DIR = Path(os.path.dirname(os.path.abspath(__file__))) / ".." / "data" / "clawbot_queue"
LOG_FILE = QUEUE_DIR / "push_log.json"

# ClawBot 配置（从 settings.json 或环境变量读取）
SETTINGS_FILE = WORKBUDDY_HOME / "settings.json"
CLAWBOT_QUEUE_FILE = QUEUE_DIR / "pending_messages.json"


def load_clawbot_config():
    """加载 ClawBot 配置"""
    config = {}
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                config = data.get("weixinClawBot", {})
        except Exception:
            pass
    # 环境变量覆盖
    for key in ["CLAWBOT_TOKEN", "CLAWBOT_ACCOUNT_ID", "CLAWBOT_CHANNEL_ID"]:
        val = os.environ.get(key)
        if val:
            config_key = key.replace("CLAWBOT_", "").lower()
            config[config_key] = val
    return config


def ensure_queue_dir():
    """确保队列目录存在"""
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    # 确保 pending_messages.json 存在
    if not CLAWBOT_QUEUE_FILE.exists():
        with open(CLABOT_QUEUE_FILE, "w", encoding="utf-8") as f:
            json.dump({"messages": [], "updated_at": None}, f)


def push_to_queue(message: str, title: str = "", metadata: dict = None) -> dict:
    """
    方式3: 写入队列文件，等待 ClawBot 下次轮询时拾取。
    这是最可靠的降级方案——不依赖任何外部连接。
    """
    ensure_queue_dir()

    entry = {
        "id": f"msg-{int(time.time()*1000)}",
        "timestamp": datetime.now().isoformat(),
        "message": message,
        "title": title or "",
        "metadata": metadata or {},
        "status": "pending",
        "delivered": False,
        "delivered_at": None,
    }

    with open(CLABOT_QUEUE_FILE, "r", encoding="utf-8") as f:
        queue_data = json.load(f)

    queue_data["messages"].append(entry)
    queue_data["updated_at"] = datetime.now().isoformat()
    # 只保留最近 50 条
    queue_data["messages"] = queue_data["messages"][-50:]

    with open(CLABOT_QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(queue_data, f, ensure_ascii=False, indent=2)

    log_result(entry["id"], "queued", f"已写入队列 ({len(queue_data['messages'])} 条待处理)")
    return {"ok": True, "method": "queue", "id": entry["id"], "status": "queued"}


def try_wechat_reply(message: str) -> dict:
    """
    方式1: 尝试通过 WechatReply 工具推送。
    注意：此方式仅在 WorkBuddy agent 上下文中可用。
    如果作为独立脚本运行，此方法会跳过并返回 skip。
    """
    # 检查是否在 WorkBuddy agent 上下文中运行
    # 通过检查是否有可用的 WechatReply 工具来判断
    has_tool = os.environ.get("CODEBUDDY_HAS_WECHATREPLY") == "1"

    if not has_tool:
        return {"ok": False, "method": "wechatreply", "status": "skip", "reason": "not_in_agent_context"}

    try:
        # 在 agent 上下文中，直接输出特殊指令让主程序调用 WechatReply
        instruction = (
            f'[WECHAT_REPLY_REQUIRED] chat_id="auto", text="{message[:500]}"'
        )
        print(instruction, file=sys.stderr)
        log_result("agent", "attempted", "已输出 WechatReply 指令到 stderr")
        return {"ok": True, "method": "wechatreply", "status": "instructed"}
    except Exception as e:
        return {"ok": False, "method": "wechatreply", "status": "error", "error": str(e)}


def try_ilinkai_direct(message: str, config: dict) -> dict:
    """
    方式2: 直接调用 ilinkai.weixin.qq.com API 发送消息。
    需要 bot token 凭证。
    """
    token = config.get("token") or config.get("botToken")
    account_id = config.get("accountId")
    channel_id = config.get("channelId")

    if not token:
        return {
            "ok": False,
            "method": "ilinkai_direct",
            "status": "no_credentials",
            "reason": "未找到 bot token（需在配置或环境变量中设置 CLAWBOT_TOKEN）",
        }

    import urllib.request
    import urllib.error

    base_url = "https://ilinkai.weixin.qq.com"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }

    payload = {
        "to_user_id": account_id or "self",
        "client_id": f"clawbot-push-{int(time.time())}-{os.urandom(4).hex()}",
        "message_type": 2,
        "message_state": 2,
        "item_list": [
            {
                "type": "TEXT",
                "text_item": {"text": message},
            }
        ],
    }

    try:
        req = urllib.request.Request(
            f"{base_url}/cgi-bin/message/send",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode())
            errcode = result.get("errcode", -1)
            if errcode == 0:
                msgid = result.get("msgid", "")
                log_result("ilinkai", "sent", f"msgid={msgid}")
                return {"ok": True, "method": "ilinkai_direct", "status": "sent", "msgid": msgid}
            else:
                errmsg = result.get("errmsg", "unknown error")
                log_result("ilinkai", "api_error", f"errcode={errcode} errmsg={errmsg}")
                return {"ok": False, "method": "ilinkai_direct", "status": "api_error", "errcode": errcode, "errmsg": errmsg}
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode()[:200]
        except:
            pass
        log_result("ilinkai", "http_error", f"code={e.code} {body}")
        return {"ok": False, "method": "ilinkai_direct", "status": "http_error", "http_code": e.code, "body": body}
    except Exception as e:
        log_result("ilinkai", "exception", str(e))
        return {"ok": False, "method": "ilinkai_direct", "status": "exception", "error": str(e)}


def log_result(msg_id: str, status: str, detail: str = ""):
    """记录推送结果日志"""
    ensure_queue_dir()
    entry = {
        "msg_id": msg_id,
        "status": status,
        "detail": detail,
        "ts": datetime.now().isoformat(),
    }
    logs = []
    if LOG_FILE.exists():
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                logs = json.load(f)
        except:
            logs = []
    logs.append(entry)
    # 只保留最近 200 条
    logs = logs[-200:]
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)


def push(message: str, title: str = "", metadata: dict = None) -> dict:
    """
    主入口：按优先级依次尝试三种推送方式，返回第一个成功的结果。
    全部失败时降级到队列模式（保证消息不丢失）。
    """
    print(f"[ClawBotPush] 开始推送 (len={len(message)}, title={title})")

    config = load_clawbot_config()

    # 方式1: WechatReply 工具
    r1 = try_wechat_reply(message)
    if r1.get("ok"):
        print(f"[ClawBotPush] ✓ 方式1(WechatReply) 成功: {r1}")
        return r1
    else:
        print(f"[ClawBotPush] ✗ 方式1 跳过/失败: {r1.get('reason', r1.get('error', 'unknown'))}")

    # 方式2: ilinkai 直连 API
    r2 = try_ilinkai_direct(message, config)
    if r2.get("ok"):
        print(f"[ClawBotPush] ✓ 方式2(ilinkai) 成功: {r2}")
        return r2
    else:
        print(f"[ClawBotPush] ✗ 方式2 失败: {r2.get('errmsg', r2.get('error', 'unknown'))}")

    # 方式3: 队列降级（必定成功）
    r3 = push_to_queue(message, title, metadata)
    print(f"[ClawBotPush] → 方式3(队列) 已写入: {r3['id']}")
    return r3


if __name__ == "__main__":
    if len(sys.argv) < 2:
        # 无参数时从 stdin 读
        message = sys.stdin.read().strip()
        if not message:
            print("用法: python3 clawbot_push.py <消息内容>")
            print("      echo 'hello' | python3 clawbot_push.py")
            print("      python3 clawbot_push.py --file report.html --title '报告'")
            sys.exit(0)
    elif "--file" in sys.argv:
        # 从文件读
        file_idx = sys.argv.index("--file")
        file_path = sys.argv[file_idx + 1]
        title_idx = sys.argv.index("--title") if "--title" in sys.argv else -1
        title = sys.argv[title_idx + 1] if title_idx > 0 else Path(file_path).name

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        message = f"[{title}] 报告已生成，请查看网页端。文件: {file_path}"
        metadata = {"file_path": file_path, "content_length": len(content)}
        result = push(message, title, metadata)
    else:
        message = sys.argv[1]
        result = push(message)

    # 输出结果（JSON）给调用方
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result.get("ok") else 0)
