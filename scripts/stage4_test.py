# -*- coding: utf-8 -*-
"""阶段 4 · 端到端验证脚本（提示词7：Agent 执行循环，仅 Python 标准库）。

覆盖：三条典型对话轨迹、确认门（学生确认 + 教务审核状态机）、
决策日志落库、确认门硬约束（未校验直接建申请被拦截）、普通问答回归。

前置：服务已启动（默认 http://127.0.0.1:8000，mock LLM 供应商）。

用例分组：
  轨迹 a（课表查询）：
    A1 《数据结构》周几上课 → 恰好 1 个工具 query_course_schedule
    A2 回答含周二/周四 + 课表版本（15 分钟数据提示）
  轨迹 b（选课全流程六步）：
    B1 帮我选《人工智能基础》 → [查规则, 查课程要求] + 确认话术（不建申请）
    B2 回复"确认" → [校验资格, 建申请] + confirm_required 事件
    B3 学生确认 → draft→student_confirmed
    B4 管理员列表可见该申请
    B5 管理员同意 → admin_confirmed
    B6 重复审核 → 40901
    B7 学生再撤销已审核申请 → 40901
  轨迹 c（资格不符）：
    C1 学分不够能选《移动应用开发》吗 → [校验资格]
    C2 回答含"不符合"+先修原因，无 create
  回归（阶段2/3 行为兼容）：
    R1 普通制度问题 → 零工具调用 + 引用来源 + 制度抽取回答
  硬约束与角色边界：
    H1 未校验直接调 create（单元级）→ 被安全策略拦截
    H2 教师选课 → 资格校验返回"无学生学籍"
  决策日志与页面：
    L1 轨迹 a 会话日志 = 2 条（工具 + final_answer），字段完整
    L2 轨迹 b 第二问日志含 __confirm_gate__
    P1 /admin/applications 未登录 → 303
    P2 /admin/applications 管理员 → 200
"""
from __future__ import annotations

import asyncio
import json
import sqlite3
import sys
import urllib.error
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8000"
ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "app.db"

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"  {'✅' if ok else '❌'} {name}" + (f" —— {detail}" if detail else ""))


def request(method: str, path: str, body: dict | None = None,
            headers: dict | None = None, follow_redirects: bool = True):
    """通用请求：返回 (状态码, JSON/文本)。"""
    data = None
    hdrs = dict(headers or {})
    if isinstance(body, dict):
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/json")

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
    def redirect_request(self, *args, **kwargs):
        return None


_NO_REDIRECT = urllib.request.build_opener(_NoRedirect)


def login(username: str, password: str = "123456") -> str:
    """登录并返回 Bearer token。"""
    status, data = request("POST", "/api/auth/login",
                           {"username": username, "password": password})
    assert status == 200 and data.get("token"), f"登录失败：{username} {data}"
    return data["token"]


def chat_sse(token: str, question: str, session_id: str | None = None) -> dict:
    """发起一次问答，解析 SSE 流，返回聚合结果。

    返回：{answer, citations, tools(按序), confirm(确认事件数据或 None),
           session_id, error(错误事件或 None), tool_events}
    """
    status, _, raw = _post_chat(token, question, session_id)
    assert status == 200, f"chat HTTP {status}：{raw[:200]}"

    events = []
    # SSE 行尾可能是 \r\n（HTTP 标准）或 \n：先归一化再按空行分块
    for block in raw.replace("\r\n", "\n").split("\n\n"):
        ev, data = "message", ""
        for line in block.split("\n"):
            if line.startswith("event:"):
                ev = line[6:].strip()
            elif line.startswith("data:"):
                data += line[5:].strip()
        if not data:
            continue
        try:
            events.append((ev, json.loads(data)))
        except json.JSONDecodeError:
            continue

    out = {"answer": "", "citations": [], "tools": [], "confirm": None,
           "session_id": None, "error": None, "tool_events": []}
    for ev, data in events:
        if ev == "message":
            out["answer"] += data.get("delta", "")
        elif ev == "citations":
            out["citations"] = data
        elif ev == "tool" and data.get("phase") == "done":
            out["tools"].append(data["name"])
            out["tool_events"].append(data)
        elif ev == "confirm_required":
            out["confirm"] = data
        elif ev == "done":
            out["session_id"] = data.get("session_id")
            out["done"] = data
        elif ev == "error":
            out["error"] = data
    return out


def _post_chat(token: str, question: str, session_id: str | None):
    """底层 POST /api/chat：返回 (状态码, 响应头, 原始文本)。"""
    body = {"question": question}
    if session_id:
        body["session_id"] = session_id
    req = urllib.request.Request(
        BASE + "/api/chat",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, dict(r.headers), r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode("utf-8")


def db_query(sql: str, params: tuple = ()) -> list[tuple]:
    """只读查 SQLite（服务进程负责写入，测试进程只读，避免锁冲突）。"""
    conn = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True)
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


# ════════════════════════ 用例执行 ════════════════════════

def main() -> int:
    print("═" * 64)
    print("阶段 4 验证（提示词7：Agent 执行循环）")
    print("═" * 64)

    stu_token = login("student1")
    adm_token = login("admin1")
    tea_token = login("teacher1")

    # ── 轨迹 a：只查课表（1 个工具，回答含排课信息）──
    print("\n[轨迹 a] 课表查询")
    a = chat_sse(stu_token, "下学期的《数据结构》课程周几上课？")
    check("A1 工具序列 = [query_course_schedule]",
          a["tools"] == ["query_course_schedule"], f"实际：{a['tools']}")
    check("A2 回答含周二/周四与课表版本",
          "周二" in a["answer"] and "周四" in a["answer"]
          and "2026-2027-2-V1" in a["answer"],
          a["answer"][:80].replace("\n", " "))
    check("A3 含 15 分钟数据时效提示",
          "15 分钟" in a["answer"] or "以教务系统" in a["answer"])
    check("A4 无确认卡片（只读查询）", a["confirm"] is None)
    a_session = a["session_id"]

    # ── 轨迹 b：选课全流程（两段式：查规则/课程→确认话术；确认→校验→建申请）──
    print("\n[轨迹 b] 选课全流程")
    b1 = chat_sse(stu_token, "帮我选下学期的《人工智能基础》选修课")
    check("B1 首问工具序列 = [查规则, 查课程要求]",
          b1["tools"] == ["search_selection_rules", "check_course_requirements"],
          f"实际：{b1['tools']}")
    check("B2 首问输出确认话术（不直接建申请）",
          "确认" in b1["answer"] and b1["confirm"] is None
          and "create_selection_application" not in b1["tools"])
    check("B3 话术含学分/先修信息", "3 学分" in b1["answer"] and "先修" in b1["answer"])

    b2 = chat_sse(stu_token, "确认", session_id=b1["session_id"])
    check("B4 次问工具序列 = [校验资格, 建申请]",
          b2["tools"] == ["validate_eligibility", "create_selection_application"],
          f"实际：{b2['tools']}")
    check("B5 收到确认卡片（confirm_required）",
          b2["confirm"] is not None and b2["confirm"]["business_no"].startswith("XK"),
          str(b2["confirm"])[:80] if b2["confirm"] else "无")
    business_no = b2["confirm"]["business_no"]
    check("B6 卡片含资格校验明细与依据条文",
          b2["confirm"]["application"]["eligibility"]["eligible"] is True
          and len(b2["confirm"]["application"]["rule_refs"]) >= 2)

    # 学生确认（确认门后半段）
    st, data = request("POST", "/api/chat/confirm",
                       {"session_id": b1["session_id"], "business_no": business_no,
                        "action": "confirm"},
                       headers={"Authorization": f"Bearer {stu_token}"})
    check("B7 学生确认 → student_confirmed",
          st == 200 and data["application"]["status"] == "student_confirmed",
          str(data)[:100])

    # 教务审核链路
    st, data = request("GET", "/api/admin/applications",
                       headers={"Authorization": f"Bearer {adm_token}"})
    nos = [it["business_no"] for it in data.get("items", [])]
    check("B8 管理员列表含该申请", st == 200 and business_no in nos)

    st, data = request("POST", f"/api/admin/applications/{business_no}/review",
                       {"action": "approve", "note": ""},
                       headers={"Authorization": f"Bearer {adm_token}"})
    check("B9 管理员同意 → admin_confirmed",
          st == 200 and data["application"]["status"] == "admin_confirmed",
          str(data)[:100])

    st, data = request("POST", f"/api/admin/applications/{business_no}/review",
                       {"action": "approve", "note": ""},
                       headers={"Authorization": f"Bearer {adm_token}"})
    check("B10 重复审核 → 40901 状态不允许",
          st == 409 and data.get("code") == "40901", str(data)[:80])

    st, data = request("POST", "/api/chat/confirm",
                       {"session_id": b1["session_id"], "business_no": business_no,
                        "action": "reject"},
                       headers={"Authorization": f"Bearer {stu_token}"})
    check("B11 学生撤销已审核申请 → 40901",
          st == 409 and data.get("code") == "40901", str(data)[:80])

    # ── 轨迹 c：资格不符（先修课未修读）──
    print("\n[轨迹 c] 资格询问（不符分支）")
    c = chat_sse(stu_token, "我学分不够能选《移动应用开发》这门课吗")
    check("C1 工具序列 = [validate_eligibility]",
          c["tools"] == ["validate_eligibility"], f"实际：{c['tools']}")
    check("C2 结论为不符合 + 先修原因",
          "不符合" in c["answer"] and "先修" in c["answer"]
          and "Web 前端开发" in c["answer"], c["answer"][:100].replace("\n", " "))
    check("C3 提示特殊申请出口（制度 2.6）", "特殊申请" in c["answer"])
    check("C4 无 create / 无确认卡片",
          "create_selection_application" not in c["tools"] and c["confirm"] is None)

    # ── 回归：普通制度问答（阶段2/3 行为完全兼容）──
    print("\n[回归] 普通制度问答")
    r = chat_sse(stu_token, "选课时间是什么时候")
    check("R1 零工具调用 + 有引用来源",
          r["tools"] == [] and len(r["citations"]) > 0, f"tools={r['tools']}")
    check("R2 回答来自制度条文（含第 18 周）", "18" in r["answer"])

    # ── 硬约束：未校验直接建申请（单元级，绕过 LLM 直击工具层）──
    print("\n[硬约束] 确认门代码层拦截")
    ok, detail = _test_hard_guard()
    check("H1 未 validate 直接 create → created=False 且被拦截", ok, detail)

    # ── 角色边界：教师无学籍 ──
    print("\n[角色边界] 教师选课")
    t1 = chat_sse(tea_token, "帮我选下学期的《人工智能基础》选修课")
    t2 = chat_sse(tea_token, "确认", session_id=t1["session_id"])
    check("H2 教师确认后校验返回无学籍（不建申请）",
          t2["tools"] == ["validate_eligibility"] and "学籍" in t2["answer"]
          and t2["confirm"] is None,
          f"tools={t2['tools']}；回答：{t2['answer'][:60]}".replace("\n", " "))

    # ── 决策日志（阶段5 评测数据基础）──
    print("\n[决策日志] agent_decision_logs")
    logs_a = db_query(
        "SELECT round, tool_name, params, duration_ms, result_summary "
        "FROM agent_decision_logs ad JOIN conversations c ON ad.conversation_id=c.id "
        "WHERE c.session_id=? ORDER BY ad.id", (a_session,))
    check("L1 轨迹 a：2 条日志（工具 + final_answer）且字段完整",
          len(logs_a) == 2 and logs_a[0][1] == "query_course_schedule"
          and logs_a[1][1] == "__final_answer__"
          and all(row[3] >= 0 and row[4] for row in logs_a),
          f"{[(r[0], r[1]) for r in logs_a]}")

    logs_b = db_query(
        "SELECT tool_name FROM agent_decision_logs ad "
        "JOIN conversations c ON ad.conversation_id=c.id "
        "WHERE c.session_id=? ORDER BY ad.id", (b1["session_id"],))
    names_b = [r[0] for r in logs_b]
    check("L2 轨迹 b 全程：规则→课程→final→校验→申请→确认门",
          names_b == ["search_selection_rules", "check_course_requirements",
                      "__final_answer__", "validate_eligibility",
                      "create_selection_application", "__confirm_gate__"],
          f"实际：{names_b}")

    # ── 管理页面 ──
    print("\n[页面] 选课申请审核页")
    st, _ = request("GET", "/admin/applications", follow_redirects=False)
    check("P1 未登录 → 303 跳转 /login", st == 303)
    st, _ = request("GET", "/admin/applications",
                    headers={"Cookie": f"token={adm_token}"})
    check("P2 管理员 Cookie → 200", st == 200)

    # ── 汇总 ──
    passed = sum(1 for _, ok, _ in results if ok)
    print("\n" + "═" * 64)
    print(f"结果：{passed}/{len(results)} 通过")
    print("═" * 64)
    return 0 if passed == len(results) else 1


def _test_hard_guard() -> tuple[bool, str]:
    """单元级硬约束验证：全新 ToolContext（未 validate）直接调 create 工具。

    需要异步环境与 app 包导入；失败不影响其余用例（返回 False + 原因）。
    """
    try:
        sys.path.insert(0, str(ROOT))
        from app.agent.tools import ToolContext, execute_tool

        async def _run():
            # 借用最近的学生会话 id（日志外键指向真实会话）
            row = db_query("SELECT c.id FROM conversations c "
                           "JOIN users u ON c.user_id=u.id "
                           "WHERE u.username='student1' ORDER BY c.id DESC LIMIT 1")
            conv_id = row[0][0] if row else 1
            ctx = ToolContext(conversation_id=conv_id, user_id=1,
                              username="student1", role="student",
                              student_no="2024010101")
            return await execute_tool(ctx, 1, "create_selection_application",
                                      {"course_name_or_code": "人工智能基础"})

        result = asyncio.run(_run())
        if result.get("created") is False and "拦截" in result.get("message", ""):
            return True, result["message"][:80]
        return False, str(result)[:120]
    except Exception as exc:   # noqa: BLE001
        return False, f"测试执行异常：{exc}"


if __name__ == "__main__":
    sys.exit(main())
