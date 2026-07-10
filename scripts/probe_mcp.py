#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe the local MCP connector-proxy: initialize + list tools + one kline call."""
import json, urllib.request, urllib.error

URL = "http://127.0.0.1:53312/mcp"
HEADERS = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}


def _parse_body(resp):
    raw = resp.read().decode("utf-8", "replace")
    ct = resp.headers.get("Content-Type", "")
    if "text/event-stream" in ct:
        # SSE: extract last data: line
        out = None
        for line in raw.splitlines():
            if line.startswith("data:"):
                out = line[5:].strip()
        return out
    return raw


def mcp_post(payload, sid=None):
    data = json.dumps(payload).encode("utf-8")
    h = dict(HEADERS)
    if sid:
        h["Mcp-Session-Id"] = sid
    req = urllib.request.Request(URL, data=data, headers=h, method="POST")
    try:
        resp = urllib.request.urlopen(req, timeout=30)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        return e.code, body, e.headers.get("Mcp-Session-Id")
    sid2 = resp.headers.get("Mcp-Session-Id")
    return resp.status, _parse_body(resp), sid2


def main():
    # 1) initialize
    init = {
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "wb-probe", "version": "1.0"},
        },
    }
    code, body, sid = mcp_post(init)
    print("INIT status", code, "sid", sid)
    print("INIT body[:500]:", body[:500] if body else None)

    # 2) initialized notification
    note = {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}
    try:
        req = urllib.request.Request(URL, data=json.dumps(note).encode(),
                                     headers={**(HEADERS), **({"Mcp-Session-Id": sid} if sid else {})},
                                     method="POST")
        urllib.request.urlopen(req, timeout=20)
        print("NOTIFIED ok")
    except Exception as e:
        print("notify err", e)

    # 3) tools/list
    tl = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    code, body, _ = mcp_post(tl, sid)
    print("LIST status", code)
    try:
        d = json.loads(body)
        tools = [t["name"] for t in d.get("result", {}).get("tools", [])]
        print("TOOLS count", len(tools))
        print("TOOLS sample:", tools[:20])
    except Exception as e:
        print("list parse err", e, "body[:300]:", body[:300] if body else None)


if __name__ == "__main__":
    main()
