# -*- coding: utf-8 -*-
"""阶段 2 · 端到端验证脚本（仅 Python 标准库，不依赖第三方包）。

对运行中的服务（默认 http://127.0.0.1:8000）做 5 项检查：
  T1 新会话正常问答：SSE 事件序列 status→message→citations→done 完整；
  T2 同会话追问陷阱题：回答包含"制度中未找到"；
  T3 空问题：HTTP 400 + 错误码 40001；
  T4 不存在的会话：HTTP 404 + 错误码 40401；
  T5 SQLite 持久化：会话数=1、消息数=4、助手消息带引用。

用法：先启动服务，再运行  python scripts/api_test.py
"""
from __future__ import annotations

import json
import sqlite3
import sys
import urllib.error
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8000"
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "app.db"

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"  {'✅' if ok else '❌'} {name}" + (f" —— {detail}" if detail else ""))


def post_chat(payload: dict):
    """POST /api/chat：返回 (HTTP状态码, 事件列表 或 JSON 错误体)。"""
    req = urllib.request.Request(
        BASE + "/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            events, cur = [], "message"
            for raw in r:                                  # 逐行读取 SSE 流
                line = raw.decode("utf-8").rstrip("\n")
                if line.startswith("event:"):
                    cur = line[6:].strip()
                elif line.startswith("data:"):
                    try:
                        events.append((cur, json.loads(line[5:].strip())))
                    except json.JSONDecodeError:
                        pass                               # 忽略 ping 注释等
            return r.status, events
    except urllib.error.HTTPError as e:                    # 流式开始前的 HTTP 错误
        return e.code, json.loads(e.read().decode("utf-8"))


def main() -> int:
    print("═" * 60)
    print("阶段 2 端到端验证")
    print("═" * 60)

    # ── T1 新会话正常问答 ──
    print("[T1] 新会话 · 制度类问题")
    status, body = post_chat({"question": "补退选的截止时间是什么时候？"})
    events = body if isinstance(body, list) else []
    names = [e for e, _ in events]
    answer = "".join(d.get("delta", "") for e, d in events if e == "message")
    session_id = next((d.get("session_id") for e, d in events if e == "done"), None)
    check("HTTP 200", status == 200)
    check("SSE 事件序列含 status→message→citations→done",
          all(n in names for n in ("status", "message", "citations", "done")),
          f"事件={names}")
    check("回答非空且命中选课时间条文", ("补退选" in answer) or ("第 18 周" in answer),
          answer.split("\n")[0][:50])
    check("返回 session_id", bool(session_id))

    # ── T2 同会话陷阱题（制度中不存在）──
    print("[T2] 同会话 · 陷阱题")
    status, body = post_chat({"session_id": session_id, "question": "学校运动会什么时候举行？"})
    events = body if isinstance(body, list) else []
    answer = "".join(d.get("delta", "") for e, d in events if e == "message")
    check("HTTP 200", status == 200)
    check("回答包含'制度中未找到'", "制度中未找到" in answer, answer[:60])

    # ── T3 参数错误 ──
    print("[T3] 空问题（参数校验）")
    status, body = post_chat({"question": ""})
    check("HTTP 400 + 40001", status == 400 and body.get("code") == "40001",
          f"{status} {body}")

    # ── T4 会话不存在 ──
    print("[T4] 不存在的会话")
    status, body = post_chat({"session_id": "not-exist-session", "question": "测试"})
    check("HTTP 404 + 40401", status == 404 and body.get("code") == "40401",
          f"{status} {body}")

    # ── T5 SQLite 持久化 ──
    print("[T5] SQLite 持久化检查")
    if DB_PATH.exists():
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        conv_n = cur.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
        msg_n = cur.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        cited = cur.execute(
            "SELECT COUNT(*) FROM messages WHERE role='assistant' AND citations IS NOT NULL"
        ).fetchone()[0]
        con.close()
        check("会话数 = 1（两次提问同一会话）", conv_n == 1, f"实际 {conv_n}")
        check("消息数 = 4（2 问 + 2 答）", msg_n == 4, f"实际 {msg_n}")
        check("2 条助手消息均带引用来源", cited == 2, f"实际 {cited}")
    else:
        check("数据库文件存在", False, str(DB_PATH))

    # ── 汇总 ──
    passed = sum(1 for _, ok, _ in results if ok)
    print("─" * 60)
    print(f"结果：{passed}/{len(results)} 通过")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
