# -*- coding: utf-8 -*-
"""上线演练执行脚本（提示词 9 · 清单第 8 节演练顺序的可编程部分）。

用法（服务须已启动，默认 mock 供应商基线）：
  python scripts/_drill.py phase1   # DS-3 密码哈希 / DS-4 越权隔离 / DS-5 备份
  python scripts/_drill.py phase2   # CS-4 十问抽查 / FB-2 零命中 / FB-4 工具异常 / FB-5 畸形请求
  python scripts/_drill.py phase3   # CL-4 并发压测（50 线程混合请求）
  python scripts/_drill.py phase4   # DS-1 换钥验证（服务已换 JWT_SECRET；旧令牌经 DRILL_OLD_TOKEN 传入）
  python scripts/_drill.py phase5   # FB-1 供应商故障验证（服务已指向无效 LLM 端点）
  python scripts/_drill.py phase6   # DS-2 改密验证（种子账号口令已被改为 Drill@2026#30）
  python scripts/_drill.py phase7   # RB-2 恢复验证（已从 drill 备份恢复 data/）

phase4-7 由 PowerShell 编排配合 .env 切换与服务起停执行。
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BASE = "http://127.0.0.1:8000"
ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "app.db"

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"  {'✅' if ok else '❌'} {name}" + (f" —— {detail}" if detail else ""))


def request(method: str, path: str, body=None, token: str | None = None,
            raw_body: bytes | None = None, timeout: int = 90):
    """通用请求：返回 (状态码, 解析后 JSON / 原始文本)。"""
    headers = {}
    data = raw_body
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
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


def login(username: str, password: str = "123456") -> str | None:
    status, body = request("POST", "/api/auth/login", {"username": username, "password": password})
    if status == 200 and isinstance(body, dict):
        return body.get("token")
    return None


def chat_sse(token: str, question: str, session_id: str | None = None, timeout: int = 90) -> dict:
    """POST /api/chat 并消费 SSE：返回 {status, events, error}。"""
    body: dict = {"question": question}
    if session_id:
        body["session_id"] = session_id
    status, events = _post_chat_raw(body, token, timeout)
    if status != 200:
        return {"status": status, "events": [], "error": events}
    return {"status": status, "events": events, "error": None}


def _post_chat_raw(body: dict, token: str, timeout: int):
    req = urllib.request.Request(
        BASE + "/api/chat", data=json.dumps(body).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + token})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8").replace("\r\n", "\n")
            events, cur = [], "message"
            for line in raw.split("\n"):
                if line.startswith("event:"):
                    cur = line[6:].strip()
                elif line.startswith("data:"):
                    try:
                        events.append((cur, json.loads(line[5:].strip())))
                    except json.JSONDecodeError:
                        pass
            return r.status, events
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8"))
        except Exception:
            return e.code, None


def answer_of(events) -> str:
    return "".join(d.get("delta", "") for e, d in events if e == "message")


def citations_of(events) -> list:
    return next((d for e, d in events if e == "citations"), []) or []


def has_event(events, name: str) -> bool:
    return any(e == name for e, _ in events)


def db_query(sql: str, params: tuple = ()) -> list[tuple]:
    with sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True) as conn:
        return conn.execute(sql, params).fetchall()


# ════════════════ phase1：数据安全（DS-3 / DS-4 / DS-5）════════════════
def phase1() -> int:
    print("═" * 60)
    print("演练 phase1 · 数据安全（DS-3 / DS-4 / DS-5）")
    print("═" * 60)

    # ── DS-3 密码哈希格式 ──
    print("[DS-3] 敏感数据存储合规")
    rows = db_query("SELECT username, password_hash FROM users")
    pat = re.compile(r"^[0-9a-f]{32}\$[0-9a-f]{64}$")
    bad = [u for u, h in rows if not pat.match(h or "")]
    check(f"全部 {len(rows)} 个账号口令均为「盐$哈希」PBKDF2 格式、0 明文", not bad,
          f"异常账号：{bad}" if bad else "格式 100% 匹配")

    # ── DS-4 越权隔离 ──
    print("[DS-4] 数据归属与越权隔离")
    teacher_tok = login("teacher1")
    student_tok = login("student1")
    check("教师/学生登录获取令牌", bool(teacher_tok) and bool(student_tok))

    conv_id = db_query(
        "SELECT c.id FROM conversations c JOIN users u ON u.id = c.user_id "
        "WHERE u.username = 'student1' ORDER BY c.id DESC LIMIT 1")
    app_row = db_query(
        "SELECT business_no, conversation_id FROM selection_applications "
        "ORDER BY id DESC LIMIT 1")
    check("库中存在可用的他人会话/申请单（演练数据）", bool(conv_id) and bool(app_row),
          f"conv={conv_id[0][0] if conv_id else '无'}; app={app_row[0][0] if app_row else '无'}")

    if conv_id:
        st, body = request("POST", "/api/chat",
                           {"question": "测试越权", "session_id": str(conv_id[0][0])},
                           token=teacher_tok)
        check("教师携带学生会话 → 拒绝（403/404 均为安全拒绝，404 不泄露他人会话存在性）",
              st in (403, 404) and isinstance(body, dict)
              and str(body.get("code", "")).startswith(("403", "404")),
              f"{st} {str(body)[:60]}")

    st, body = request("GET", "/api/admin/applications", token=student_tok)
    check("学生调管理端申请接口 → 403+40301", st == 403 and isinstance(body, dict)
          and body.get("code") == "40301", f"{st} {str(body)[:60]}")

    if app_row:
        business_no, app_conv = app_row[0]
        st, body = request("POST", "/api/chat/confirm",
                           {"session_id": str(app_conv), "business_no": business_no,
                            "action": "confirm"}, token=teacher_tok)
        check("教师确认他人申请单 → 拒绝（403 系）", st == 403 and isinstance(body, dict)
              and str(body.get("code", "")).startswith("403"), f"{st} {str(body)[:60]}")

    # ── DS-5 备份 ──
    print("[DS-5] 数据备份")
    ts = time.strftime("%Y%m%d-%H%M%S")
    dest = ROOT / "data" / "backups" / f"drill-{ts}"
    src = ROOT / "data"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns("backups"))
    files = [p for p in dest.rglob("*") if p.is_file()]
    has_db = (dest / "app.db").exists()
    has_index = any(p.suffix in (".faiss", ".index") or "faiss" in p.parent.name.lower()
                    for p in files)
    check(f"全量备份完成 → data/backups/drill-{ts}", has_db and len(files) >= 3,
          f"共 {len(files)} 个文件；含数据库={has_db}；含索引目录={has_index}")

    passed = sum(1 for _, ok, _ in results if ok)
    print("─" * 60)
    print(f"phase1 结果：{passed}/{len(results)} 通过")
    return 0 if passed == len(results) else 1


# ════════════════ phase2：内容安全抽查 + 异常注入（CS-4 / FB-2 / FB-4 / FB-5）════════════════
def phase2() -> int:
    print("═" * 60)
    print("演练 phase2 · 内容安全抽查 + 异常注入（CS-4 / FB-2 / FB-4 / FB-5）")
    print("═" * 60)

    token = login("student1")
    check("学生登录", bool(token))

    # ── CS-4 十问抽查（复用评测集 R01-R07 + T01-T03）──
    print("[CS-4] 回答可溯源（抽查 10 问）")
    cases = json.loads((ROOT / "eval" / "eval_cases.json").read_text(encoding="utf-8"))
    picked = [c for c in cases if c.get("category") in ("制度类", "制度类-陷阱")][:10]
    check("评测集中抽取 10 条制度/陷阱用例", len(picked) == 10, f"实际 {len(picked)} 条")
    cite_ok, kw_ok = 0, 0
    for c in picked:
        r = chat_sse(token, c["question"])
        ans = answer_of(r["events"])
        cites = citations_of(r["events"])
        kws = c["expected_behavior"].get("answer_contains_any") or []
        hit = any(k in ans for k in kws) if kws else True
        if cites:
            cite_ok += 1
        if hit and ans:
            kw_ok += 1
        else:
            print(f"    ⚠ {c['id']} 未命中：{ans[:50]}")
    check("10 问回答均命中关键词", kw_ok == len(picked), f"{kw_ok}/{len(picked)}")
    check("10 问均附引用来源（citations 非空）", cite_ok == len(picked), f"{cite_ok}/{len(picked)}")

    # ── FB-2 检索零命中 ──
    print("[FB-2] 零命中不编造")
    r = chat_sse(token, "食堂本周菜单有什么好吃的？")
    ans = answer_of(r["events"])
    cites = citations_of(r["events"])
    check("超范围问题 → 明确『制度中未找到』", "制度中未找到" in ans, ans[:60])
    check("零命中时 citations 为空（不编造来源）", not cites, f"citations={len(cites)} 条")

    # ── FB-4 工具异常受控 ──
    print("[FB-4] 工具执行异常受控")
    r = chat_sse(token, "《量子计算导论》什么时候上课？")
    ans = answer_of(r["events"])
    crashed = has_event(r["events"], "error")
    done = has_event(r["events"], "done")
    check("查询不存在课程 → 流式正常收尾（done）且无 error 崩溃", done and not crashed,
          f"回答摘要：{ans[:60]}")

    # ── FB-5 畸形请求 ──
    print("[FB-5] 参数校验兜底")
    st, body = request("POST", "/api/chat", raw_body=b"not-a-json{", token=token)
    check("非法 JSON → 400+40001", st == 400 and isinstance(body, dict)
          and body.get("code") == "40001", f"{st} {str(body)[:60]}")
    st, body = request("POST", "/api/chat", {"session_id": "x"}, token=token)
    check("缺失 question 字段 → 400+40001", st == 400 and isinstance(body, dict)
          and body.get("code") == "40001", f"{st} {str(body)[:60]}")
    st, body = request("POST", "/api/chat", {"question": "长" * 501}, token=token)
    check("超长 question（501 字）→ 400+40001", st == 400 and isinstance(body, dict)
          and body.get("code") == "40001", f"{st} {str(body)[:60]}")

    passed = sum(1 for _, ok, _ in results if ok)
    print("─" * 60)
    print(f"phase2 结果：{passed}/{len(results)} 通过")
    return 0 if passed == len(results) else 1


# ════════════════ phase3：并发压测（CL-4）════════════════
def _hit_login(i: int) -> tuple[str, int, str]:
    users = ("student1", "teacher1", "admin1")
    st, body = request("POST", "/api/auth/login",
                       {"username": users[i % 3], "password": "123456"}, timeout=60)
    return ("login", st, json.dumps(body, ensure_ascii=False)[:80] if isinstance(body, dict) else "")


def _hit_chat(token: str) -> tuple[str, int, str]:
    st, events = _post_chat_raw({"question": "理论课多少学时算一个学分"}, token, 60)
    if st == 200:
        return ("chat", st, "")
    try:
        return ("chat", st, json.dumps(events, ensure_ascii=False)[:80])
    except Exception:
        return ("chat", st, str(events)[:80])


def phase3() -> int:
    print("═" * 60)
    print("演练 phase3 · 并发压测（CL-4：50 线程混合请求）")
    print("═" * 60)
    token = login("student1")
    check("学生登录（压测令牌）", bool(token))

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=50) as pool:
        futures = [pool.submit(_hit_login, i) for i in range(25)]
        futures += [pool.submit(_hit_chat, token) for _ in range(25)]
        outs = [f.result() for f in futures]
    cost = time.time() - t0

    login_ok = sum(1 for k, st, _ in outs if k == "login" and st == 200)
    chat_ok = sum(1 for k, st, _ in outs if k == "chat" and st == 200)
    chat_429 = sum(1 for k, st, _ in outs if k == "chat" and st == 429)
    fatal = [(k, st, d) for k, st, d in outs
             if st >= 500 or "50001" in d or "database is locked" in d.lower()]
    print(f"    50 线程完成耗时 {cost:.1f}s；login 200×{login_ok}/25；"
          f"chat 200×{chat_ok}/25、429×{chat_429}（限流预期）")
    check("登录读并发 25/25 成功", login_ok == 25, f"{login_ok}/25")
    check("chat 成功+限流 = 25（无其他状态码）", chat_ok + chat_429 == 25,
          f"200×{chat_ok} + 429×{chat_429}")
    check("无 500/50001/database is locked（数据库并发安全）", not fatal,
          f"异常样本：{fatal[:3]}" if fatal else "0 例")

    passed = sum(1 for _, ok, _ in results if ok)
    print("─" * 60)
    print(f"phase3 结果：{passed}/{len(results)} 通过")
    return 0 if passed == len(results) else 1


# ════════════════ phase4：DS-1 换钥验证（服务已更换 JWT_SECRET）════════════════
def phase4() -> int:
    print("═" * 60)
    print("演练 phase4 · DS-1 JWT 密钥更换实证")
    print("═" * 60)
    old_tok = os.environ.get("DRILL_OLD_TOKEN", "")
    check("已传入换钥前签发的旧令牌", bool(old_tok))

    st, body = request("GET", "/api/auth/me", token=old_tok or "invalid")
    check("旧令牌 → 401+40101（旧密钥全部失效）",
          st == 401 and isinstance(body, dict) and body.get("code") == "40101",
          f"{st} {str(body)[:60]}")

    st, body = request("POST", "/api/auth/login",
                       {"username": "student1", "password": "123456"})
    new_tok = body.get("token") if isinstance(body, dict) else None
    check("口令登录不受换钥影响（新密钥签发新令牌）", st == 200 and bool(new_tok),
          f"{st}")

    st, body = request("GET", "/api/auth/me", token=new_tok)
    check("新令牌访问正常", st == 200 and isinstance(body, dict)
          and body.get("username") == "student1", f"{st} {str(body)[:50]}")

    passed = sum(1 for _, ok, _ in results if ok)
    print("─" * 60)
    print(f"phase4 结果：{passed}/{len(results)} 通过")
    return 0 if passed == len(results) else 1


# ════════════════ phase5：FB-1 供应商故障验证（LLM 指向无效端点）════════════════
def phase5() -> int:
    print("═" * 60)
    print("演练 phase5 · FB-1 LLM 供应商故障降级实证")
    print("═" * 60)
    token = login("student1")
    check("登录正常（鉴权链路不依赖 LLM 供应商）", bool(token))

    r = chat_sse(token, "理论课多少学时算一个学分")
    ev_names = [e for e, _ in r["events"]]
    err = next((d for e, d in r["events"] if e == "error"), None)
    check("SSE 流正常建立（HTTP 200，非裸 500）", r["status"] == 200, f"status={r['status']}")
    check("收到 error 事件（故障不崩溃、流式收尾）", err is not None, f"事件序列：{ev_names}")
    if err:
        code = str(err.get("code", ""))
        msg = str(err.get("message", ""))
        check("错误码为 50301/50302（供应商调用失败/超时）", code in ("50301", "50302"),
              f"code={code}")
        check("结构化错误且无堆栈泄露", "traceback" not in (code + msg).lower(), msg[:60])

    passed = sum(1 for _, ok, _ in results if ok)
    print("─" * 60)
    print(f"phase5 结果：{passed}/{len(results)} 通过")
    return 0 if passed == len(results) else 1


# ════════════════ phase6：DS-2 改密验证（种子账号已改密）════════════════
def phase6() -> int:
    print("═" * 60)
    print("演练 phase6 · DS-2 默认口令清零实证")
    print("═" * 60)
    new_pw = os.environ.get("DRILL_NEW_PW", "Drill@2026#30")
    fails = []
    for u in ("student1", "teacher1", "admin1"):
        st, body = request("POST", "/api/auth/login",
                           {"username": u, "password": "123456"})
        if not (st == 401 and isinstance(body, dict) and body.get("code") == "40102"):
            fails.append(f"{u}→{st}")
    check("三账号默认口令 123456 全部失效（401+40102）", not fails,
          f"异常：{fails}" if fails else "401×3")

    st, body = request("POST", "/api/auth/login",
                       {"username": "student1", "password": new_pw})
    check("新口令可正常登录（证明是改密而非账号损坏）", st == 200, f"{st}")

    passed = sum(1 for _, ok, _ in results if ok)
    print("─" * 60)
    print(f"phase6 结果：{passed}/{len(results)} 通过")
    return 0 if passed == len(results) else 1


# ════════════════ phase7：RB-2 恢复验证（已从备份恢复 data/）════════════════
def phase7() -> int:
    print("═" * 60)
    print("演练 phase7 · RB-2 备份恢复实证")
    print("═" * 60)
    st, body = request("POST", "/api/auth/login",
                       {"username": "student1", "password": "123456"})
    check("备份库口令恢复（123456 重新可登录）", st == 200, f"{st}")

    rows = db_query("SELECT business_no, status FROM selection_applications "
                    "ORDER BY id DESC LIMIT 3")
    check("备份前申请单数据完整恢复（状态机字段无损）", len(rows) >= 1,
          f"恢复 {len(rows)} 张：{[(r[0], r[1]) for r in rows]}")

    token = login("student1")
    r = chat_sse(token, "补退选的截止时间是什么时候？")
    ans = answer_of(r["events"])
    check("恢复库冒烟问答正常（done 收尾 + 命中条文）",
          has_event(r["events"], "done") and "补退选" in ans, ans[:50])
    check("索引与库内容一致（citations 非空）", bool(citations_of(r["events"])), "")

    passed = sum(1 for _, ok, _ in results if ok)
    print("─" * 60)
    print(f"phase7 结果：{passed}/{len(results)} 通过")
    return 0 if passed == len(results) else 1


# ════════════════ phase8：CL-1 限流边界规范验证 ════════════════
def phase8() -> int:
    print("═" * 60)
    print("演练 phase8 · CL-1 问答接口限流边界（带鉴权 21 连发）")
    print("═" * 60)
    token = login("student1")
    check("登录（限流验证令牌）", bool(token))

    codes = []
    for i in range(21):
        st, _ = request("POST", "/api/chat",
                        {"question": "理论课多少学时算一个学分"}, token=token, timeout=60)
        codes.append(st)
    ok200 = sum(1 for s in codes[:20] if s == 200)
    st21 = codes[20] if len(codes) > 20 else None
    check("前 20 次全部放行（200）", ok200 == 20, f"{ok200}/20")
    check("第 21 次被限流拒绝（429）", st21 == 429, f"status={st21}")

    st, body = request("POST", "/api/chat", {"question": "超限复验"}, token=token, timeout=60)
    check("持续超限仍拒绝且错误码 42901", st == 429 and isinstance(body, dict)
          and body.get("code") == "42901", f"{st} {str(body)[:60]}")

    print("    等待 61 秒验证窗口滑动恢复…")
    time.sleep(61)
    st, body = request("POST", "/api/chat", {"question": "窗口恢复验证"}, token=token, timeout=60)
    check("60 秒后窗口滑动恢复访问（200）", st == 200, f"status={st}")

    passed = sum(1 for _, ok, _ in results if ok)
    print("─" * 60)
    print(f"phase8 结果：{passed}/{len(results)} 通过")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    phase = sys.argv[1] if len(sys.argv) > 1 else ""
    code = {"phase1": phase1, "phase2": phase2, "phase3": phase3,
            "phase4": phase4, "phase5": phase5, "phase6": phase6,
            "phase7": phase7, "phase8": phase8}.get(phase)
    if code is None:
        print("用法：python scripts/_drill.py phase1|…|phase8")
        sys.exit(2)
    sys.exit(code())
