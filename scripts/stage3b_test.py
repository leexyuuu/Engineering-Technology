# -*- coding: utf-8 -*-
"""阶段 3 · 批 2 端到端验证脚本（仅 Python 标准库）。

覆盖：提示词模板读写热生效、对话审计筛选与违规标记。
前置：服务已启动（默认 http://127.0.0.1:8000），批 1 已通过（库中有种子数据）。

用例：
  T1  管理员登录
  T2  GET /api/admin/prompt → 默认模板（含"制度中未找到"）
  T3  PUT 修改提示词 → 200
  T4  GET 再次读取 → 内容已更新（数据库持久化）
  T5  学生/教师各提问 1 次（为审计制造数据）
  T6  提问陷阱题 → 回答仍为"制度中未找到"（改模板后功能不回归）
  T7  PUT 过短提示词 → 40001
  T8  学生访问审计接口 → 403 + 40301
  T9  审计列表：总数 ≥ 4，含用户信息（real_name/role）
  T10 角色筛选 student → 只含学生消息
  T11 关键词筛选"补退选" → 只含匹配内容
  T12 标记一条学生消息为疑似违规（含原因）→ 列表可见
  T13 flagged=true 筛选 → 仅已标记消息
  T14 标记消息不填原因 → 40001
  T15 取消标记 → 恢复正常
  T16 日期筛选：明天起 → 0 条
  T17 页面渲染：/admin/prompt、/admin/audit（管理员 Cookie）→ 200
  T18 未登录访问 /admin/prompt → 303
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from datetime import date, timedelta

BASE = "http://127.0.0.1:8000"

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"  {'✅' if ok else '❌'} {name}" + (f" —— {detail}" if detail else ""))


def request(method: str, path: str, body: dict | None = None,
            headers: dict | None = None):
    """通用请求：返回 (状态码, JSON)。"""
    data = None
    hdrs = dict(headers or {})
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=hdrs)
    opener = urllib.request.build_opener(_NoRedirect)
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
    def redirect_request(self, *args, **kwargs):
        return None


def chat_sse(question: str, token: str):
    """学生提问并消费 SSE，返回回答全文。"""
    status, body = request("POST", "/api/chat", {"question": question},
                           {"Authorization": "Bearer " + token})
    if status != 200:
        return ""
    answer, cur = "", "message"
    for line in body.split("\n"):
        line = line.rstrip()
        if line.startswith("event:"):
            cur = line[6:].strip()
        elif line.startswith("data:") and cur == "message":
            try:
                answer += json.loads(line[5:].strip()).get("delta", "")
            except json.JSONDecodeError:
                pass
    return answer


def login(username: str) -> tuple[int, dict]:
    return request("POST", "/api/auth/login",
                   {"username": username, "password": "123456"})


def main() -> int:
    print("═" * 60)
    print("阶段 3 批 2 端到端验证（提示词模板 + 对话审计）")
    print("═" * 60)

    # ── T1 登录 ──
    print("[T1] 管理员/学生/教师登录")
    _, admin = login("admin1")
    _, student = login("student1")
    _, teacher = login("teacher1")
    admin_token, student_token, teacher_token = (
        admin.get("token"), student.get("token"), teacher.get("token"))
    ah = {"Authorization": "Bearer " + admin_token}
    check("三角色登录成功", all([admin_token, student_token, teacher_token])
          and admin["role"] == "admin")

    # ── T2 默认模板 ──
    print("[T2] GET /api/admin/prompt（默认模板）")
    status, body = request("GET", "/api/admin/prompt", headers=ah)
    check("200 + 默认内容", status == 200 and "制度中未找到" in body.get("content", ""))
    default_content = body.get("content", "")

    # ── T3/T4 修改模板并回读 ──
    print("[T3] PUT 修改提示词")
    new_prompt = ("你是学校教务制度助手，只根据提供的制度条文回答，不确定时明确说'制度中未找到'，"
                  "回答末尾附引用来源，不得编造排课或选课规则。回答保持简洁，先给结论再给依据。")
    status, body = request("PUT", "/api/admin/prompt", {"content": new_prompt}, ah)
    check("200 + 生效提示", status == 200 and "立即" in body.get("message", ""), str(body)[:60])

    print("[T4] GET 回读（持久化验证）")
    status, body = request("GET", "/api/admin/prompt", headers=ah)
    check("内容已更新", status == 200 and body.get("content") == new_prompt)

    # ── T5/T6 制造审计数据 + 功能不回归 ──
    print("[T5] 学生/教师提问（制造审计数据）")
    a1 = chat_sse("补退选的截止时间是什么时候？", student_token)
    a2 = chat_sse("调课申请要提前几天提交？", teacher_token)
    check("两角色提问成功", "补退选" in a1 and "3 个工作日" in a2, a1[:30])

    print("[T6] 陷阱题功能不回归")
    a3 = chat_sse("学校食堂几点开门？", student_token)
    check("'制度中未找到'", "制度中未找到" in a3, a3[:40])

    # ── T7 过短提示词 ──
    print("[T7] PUT 过短提示词")
    status, body = request("PUT", "/api/admin/prompt", {"content": "太短"}, ah)
    check("40001 拒绝", status == 400 and body.get("code") == "40001")

    # ── T8 学生访问审计接口 ──
    print("[T8] 学生访问审计接口")
    status, body = request("GET", "/api/admin/audit/messages", headers={
        "Authorization": "Bearer " + student_token})
    check("403 + 40301", status == 403 and body.get("code") == "40301")

    # ── T9 审计列表 ──
    print("[T9] 审计列表（含用户信息）")
    status, body = request("GET", "/api/admin/audit/messages?page=1&page_size=50", headers=ah)
    items = body.get("items", [])
    student_items = [m for m in items if m["user_role"] == "student"]
    check("200 + 总数≥4 + 含用户信息", status == 200 and body.get("total", 0) >= 4
          and any(m["real_name"] == "张同学" for m in items),
          f"total={body.get('total')}")

    # ── T10 角色筛选 ──
    print("[T10] 角色筛选 student")
    status, body = request("GET", "/api/admin/audit/messages?role=student&page=1&page_size=50",
                           headers=ah)
    roles = {m["user_role"] for m in body.get("items", [])}
    check("仅学生消息", status == 200 and roles <= {"student"} and body.get("total", 0) >= 4,
          f"roles={roles}")

    # ── T11 关键词筛选 ──
    print("[T11] 关键词筛选'补退选'")
    status, body = request("GET",
                           "/api/admin/audit/messages?keyword=%E8%A1%A5%E9%80%80%E9%80%89&page=1&page_size=50",
                           headers=ah)
    kw_items = body.get("items", [])
    check("仅匹配内容", status == 200 and body.get("total", 0) >= 1
          and all("补退选" in m["content"] for m in kw_items),
          f"total={body.get('total')}")

    # ── T12 标记疑似违规 ──
    print("[T12] 标记一条学生消息")
    target = next((m for m in student_items if m["msg_role"] == "user"), None)
    if target:
        status, body = request("PUT",
                               f"/api/admin/audit/messages/{target['id']}/flag",
                               {"flagged": True, "reason": "疑似试图绕过选课资格"}, ah)
        check("标记 200", status == 200, str(body)[:50])
    else:
        check("找到可标记的学生提问", False)

    # ── T13 flagged 筛选 ──
    print("[T13] 仅看已标记")
    status, body = request("GET", "/api/admin/audit/messages?flagged=true&page=1&page_size=50",
                           headers=ah)
    flagged_items = body.get("items", [])
    check("仅已标记消息 + 原因可见", status == 200 and len(flagged_items) >= 1
          and all(m["is_flagged"] for m in flagged_items)
          and any("绕过" in m["flag_reason"] for m in flagged_items))

    # ── T14 标记不填原因 ──
    print("[T14] 标记不填原因")
    status, body = request("PUT",
                           f"/api/admin/audit/messages/{target['id']}/flag",
                           {"flagged": True, "reason": ""}, ah)
    check("40001 拒绝", status == 400 and body.get("code") == "40001")

    # ── T15 取消标记 ──
    print("[T15] 取消标记")
    status, body = request("PUT",
                           f"/api/admin/audit/messages/{target['id']}/flag",
                           {"flagged": False, "reason": ""}, ah)
    check("取消 200", status == 200)
    status, body = request("GET", "/api/admin/audit/messages?flagged=true", headers=ah)
    check("已无标记消息", body.get("total") == 0, f"total={body.get('total')}")

    # ── T16 日期筛选 ──
    print("[T16] 日期筛选（明天起 → 0 条）")
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    status, body = request("GET", f"/api/admin/audit/messages?start={tomorrow}", headers=ah)
    check("0 条", status == 200 and body.get("total") == 0, f"start={tomorrow}")

    # ── T17/T18 页面 ──
    print("[T17] 管理页渲染（Cookie）")
    for path, kw in [("/admin/prompt", "提示词"), ("/admin/audit", "审计")]:
        status, body = request("GET", path, headers={"Cookie": f"token={admin_token}"})
        check(f"{path} 200", status == 200 and isinstance(body, str) and kw in body)

    print("[T18] 未登录访问 /admin/prompt")
    status, body = request("GET", "/admin/prompt")
    check("303 → /login", status == 303, f"status={status}")

    # ── 恢复默认模板（收尾，避免影响后续阶段）──
    request("PUT", "/api/admin/prompt", {"content": default_content}, ah)

    passed = sum(1 for _, ok, _ in results if ok)
    print("─" * 60)
    print(f"结果：{passed}/{len(results)} 通过（系统提示词已恢复默认）")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
