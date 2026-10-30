# -*- coding: utf-8 -*-
"""阶段 3 · 批 1 端到端验证脚本（仅 Python 标准库）。

覆盖：JWT 三角色鉴权、知识库上传/删除热生效、页面权限。
前置：服务已启动（默认 http://127.0.0.1:8000），数据库为首次启动的干净状态。

用例：
  T1  管理员登录成功 → 返回 token + role
  T2  错误密码 → 401 + 40102
  T3  GET /api/auth/me（Bearer）→ 管理员信息
  T4  未登录调 POST /api/chat → 401 + 40101
  T5  学生登录 + 提问 → SSE 完整 + 会话归属回填
  T6  学生访问管理员接口 → 403 + 40301
  T7  管理员文档列表 → 含种子文档（教务管理制度.md）
  T8  上传"场馆报修规定.md" → 切片入库 + 列表 +1
  T9  提问场馆报修 → 回答来自新上传文档（索引热生效）
  T10 删除该文档 → 列表恢复 + 提问同一问题 → "制度中未找到"
  T11 上传 .txt → 40001 拒绝
  T12 GET /login 页面 → 200
  T13 GET /admin/kb 未登录 → 303 跳转 /login
  T14 GET /admin/kb 管理员 Cookie → 200
  T15 SQLite：users=3、prompt_templates=1、conversations.user_id 已回填
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


def request(method: str, path: str, body: dict | None = None,
            headers: dict | None = None, follow_redirects: bool = True):
    """通用请求：返回 (状态码, JSON/文本)。POST dict → JSON；POST bytes → 原样。"""
    data = None
    hdrs = dict(headers or {})
    if isinstance(body, dict):
        data = json.dumps(body).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/json")
    elif isinstance(body, bytes):
        data = body

    req = urllib.request.Request(BASE + path, data=data, method=method, headers=hdrs)
    opener = urllib.request.build_opener() if follow_redirects else _NO_REDIRECT
    try:
        with opener.open(req, timeout=60) as r:
            raw = r.read().decode("utf-8")
            try:
                return r.status, json.loads(raw)
            except json.JSONDecodeError:
                return r.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, raw


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """禁止自动跟随重定向（用于验证 303 跳转）。"""

    def redirect_request(self, *args, **kwargs):  # noqa: D102
        return None


_NO_REDIRECT = urllib.request.build_opener(_NoRedirect)


def post_chat_sse(payload: dict, token: str | None):
    """POST /api/chat 并消费 SSE 流：返回 (状态码, 事件列表)。"""
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    status, body = request("POST", "/api/chat", payload, headers)
    if status != 200:
        return status, body
    events, cur = [], "message"
    for line in body.split("\n"):
        line = line.rstrip()
        if line.startswith("event:"):
            cur = line[6:].strip()
        elif line.startswith("data:"):
            try:
                events.append((cur, json.loads(line[5:].strip())))
            except json.JSONDecodeError:
                pass
    return status, events


def multipart(filename: str, content: bytes) -> tuple[bytes, str]:
    """手工构造 multipart/form-data 请求体（仅标准库）。"""
    boundary = "----stage3testboundary"
    body = (f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f"Content-Type: application/octet-stream\r\n\r\n").encode("utf-8")
    body += content + f"\r\n--{boundary}--\r\n".encode("utf-8")
    return body, f"multipart/form-data; boundary={boundary}"


def main() -> int:
    print("═" * 60)
    print("阶段 3 批 1 端到端验证（JWT + 知识库管理）")
    print("═" * 60)

    # ── T1 管理员登录 ──
    print("[T1] 管理员登录")
    status, body = request("POST", "/api/auth/login",
                           {"username": "admin1", "password": "123456"})
    admin_token = body.get("token") if isinstance(body, dict) else None
    check("200 + 返回 token/role", status == 200 and admin_token and body["role"] == "admin")

    # ── T2 错误密码 ──
    print("[T2] 错误密码")
    status, body = request("POST", "/api/auth/login",
                           {"username": "admin1", "password": "wrong"})
    check("401 + 40102", status == 401 and body.get("code") == "40102", f"{status} {body}")

    # ── T3 当前用户 ──
    print("[T3] GET /api/auth/me（Bearer）")
    status, body = request("GET", "/api/auth/me", headers={
        "Authorization": "Bearer " + (admin_token or "")})
    check("200 + 管理员信息", status == 200 and body.get("role") == "admin", str(body)[:60])

    # ── T4 未登录问答 ──
    print("[T4] 未登录调 /api/chat")
    status, body = request("POST", "/api/chat", {"question": "测试"})
    check("401 + 40101", status == 401 and body.get("code") == "40101", f"{status} {body}")

    # ── T5 学生登录 + 提问 ──
    print("[T5] 学生登录 + 提问（SSE + 会话归属）")
    status, body = request("POST", "/api/auth/login",
                           {"username": "student1", "password": "123456"})
    student_token = body.get("token") if isinstance(body, dict) else None
    check("学生登录 200", status == 200 and body.get("role") == "student")
    status, ev = post_chat_sse({"question": "补退选的截止时间是什么时候？"}, student_token)
    names = [e for e, _ in ev] if isinstance(ev, list) else []
    answer = "".join(d.get("delta", "") for e, d in ev if e == "message") if isinstance(ev, list) else ""
    check("SSE 事件序列完整", "status" in names and "citations" in names and "done" in names)
    check("回答命中选课时间条文", "补退选" in answer, answer.split("\n")[0][:50])

    # ── T6 学生访问管理员接口 ──
    print("[T6] 学生访问管理员接口")
    status, body = request("GET", "/api/admin/kb/documents", headers={
        "Authorization": "Bearer " + (student_token or "")})
    check("403 + 40301", status == 403 and body.get("code") == "40301", f"{status} {body}")

    # ── T7 管理员文档列表 ──
    print("[T7] 管理员文档列表（种子文档）")
    status, body = request("GET", "/api/admin/kb/documents", headers={
        "Authorization": "Bearer " + (admin_token or "")})
    names_list = [d["filename"] for d in body.get("documents", [])]
    base_total = body.get("total", 0)
    check("200 + 含种子文档", status == 200 and "教务管理制度.md" in names_list,
          f"共 {base_total} 个：{names_list}")

    # ── T8 上传新文档 ──
    print("[T8] 上传场馆报修规定.md")
    venue_md = ("# 体育馆设施报修规定\n\n"
                "1.1 体育馆灯泡损坏需提前两周提交报修申请，由后勤处统一更换。\n"
                "1.2 报修期间场地状态标记为'维修中'，不得安排课程。\n").encode("utf-8")
    up_body, up_ct = multipart("场馆报修规定.md", venue_md)
    status, body = request("POST", "/api/admin/kb/upload", up_body, {
        "Content-Type": up_ct,
        "Authorization": "Bearer " + (admin_token or "")})
    check("200 + 切片入库", status == 200 and body.get("chunk_count", 0) >= 1,
          str(body)[:80])
    venue_doc_id = body.get("id")

    status, body = request("GET", "/api/admin/kb/documents", headers={
        "Authorization": "Bearer " + (admin_token or "")})
    check("列表 +1", body.get("total") == base_total + 1
          and any(d["filename"] == "场馆报修规定.md" for d in body.get("documents", [])))

    # ── T9 新文档立即可问答（索引热生效）──
    print("[T9] 提问场馆报修（新文档热生效）")
    status, ev = post_chat_sse({"question": "体育馆灯泡坏了怎么报修？"}, student_token)
    answer = "".join(d.get("delta", "") for e, d in ev if e == "message") if isinstance(ev, list) else ""
    cites = next((d for e, d in ev if e == "citations"), [])
    check("回答来自新上传文档", "提前两周" in answer and
          any("场馆报修规定.md" in c.get("source", "") for c in cites),
          answer.split("\n")[0][:50])

    # ── T10 删除文档 → 问答恢复"未找到" ──
    print("[T10] 删除文档（索引热移除）")
    status, body = request("DELETE", f"/api/admin/kb/documents/{venue_doc_id}", headers={
        "Authorization": "Bearer " + (admin_token or "")})
    check("删除 200", status == 200, str(body)[:60])
    status, body = request("GET", "/api/admin/kb/documents", headers={
        "Authorization": "Bearer " + (admin_token or "")})
    check("列表恢复", body.get("total") == base_total)
    status, ev = post_chat_sse({"question": "体育馆灯泡坏了怎么报修？"}, student_token)
    answer = "".join(d.get("delta", "") for e, d in ev if e == "message") if isinstance(ev, list) else ""
    check("同一问题 → '制度中未找到'", "制度中未找到" in answer, answer[:60])

    # ── T11 非法文件类型 ──
    print("[T11] 上传 .txt 被拒")
    up_body, up_ct = multipart("说明.txt", b"hello")
    status, body = request("POST", "/api/admin/kb/upload", up_body, {
        "Content-Type": up_ct,
        "Authorization": "Bearer " + (admin_token or "")})
    check("40001 拒绝", status == 400 and body.get("code") == "40001", f"{status} {body}")

    # ── T12/T13/T14 页面权限 ──
    print("[T12] GET /login 页面")
    status, body = request("GET", "/login")
    check("200 HTML", status == 200 and isinstance(body, str) and "登录" in body)

    print("[T13] GET /admin/kb 未登录")
    status, body = request("GET", "/admin/kb", follow_redirects=False)
    check("303 → /login", status == 303, f"status={status}")

    print("[T14] GET /admin/kb 管理员 Cookie")
    status, body = request("GET", "/admin/kb", headers={"Cookie": f"token={admin_token}"})
    check("200 HTML", status == 200 and isinstance(body, str) and "知识库" in body)

    # ── T15 数据库落库检查 ──
    print("[T15] SQLite 检查")
    if DB_PATH.exists():
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        users = cur.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        tpls = cur.execute("SELECT COUNT(*) FROM prompt_templates").fetchone()[0]
        linked = cur.execute(
            "SELECT COUNT(*) FROM conversations WHERE user_id IS NOT NULL").fetchone()[0]
        active_docs = cur.execute(
            "SELECT COUNT(*) FROM documents WHERE status='active'").fetchone()[0]
        con.close()
        check("users=3（三角色演示账号）", users == 3, f"实际 {users}")
        check("prompt_templates=1（默认模板）", tpls == 1, f"实际 {tpls}")
        check("conversations.user_id 已回填", linked >= 3, f"实际 {linked}")
        check(f"活跃文档={base_total}", active_docs == base_total, f"实际 {active_docs}")
    else:
        check("数据库文件存在", False, str(DB_PATH))

    passed = sum(1 for _, ok, _ in results if ok)
    print("─" * 60)
    print(f"结果：{passed}/{len(results)} 通过")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
