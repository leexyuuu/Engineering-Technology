# -*- coding: utf-8 -*-
"""评测执行器（阶段5，提示词8）：跑 eval/eval_cases.json 的 30 条用例并出报告。

用法（服务已启动，默认 mock 供应商离线基线）：
    .venv\\Scripts\\python.exe scripts\\run_eval.py

评测维度（对应四类用例）：
- 制度类（含 3 陷阱）：零工具调用 + 制度关键词 + 引用来源；陷阱题验证
  "不编造 / 不承诺篡改 / 不附和谣言"；
- 工具调用类：expected_tools 精确序列匹配 + 回答内容断言 + 确认门边界；
- 违规意图类：forbidden_tools 不得出现 + 回答不得承诺越权操作；
- 多轮上下文类：同 session 逐轮发送，代词回指 / 目标切换 / 确认门衔接。

断言字段（expected_behavior，全部可选组合）：
- answer_contains_any / answer_contains_all：回答关键词（任一/全部）
- answer_not_contains：回答禁词（越权承诺类）
- has_citations / has_confirm_card / no_confirm_card：事件级断言
工具字段：expected_tools（必须出现）、forbidden_tools（不得出现）、
          exact_tools=true（精确序列匹配，否则按子集校验）。

限流适配：/api/chat 限流 20 次/分钟，脚本内置节流（每 18 次等 61 秒）。
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8000"
ROOT = Path(__file__).resolve().parent.parent
CASES_PATH = ROOT / "eval" / "eval_cases.json"

# 工具短名（报告展示用）
TOOL_SHORT = {
    "query_course_schedule": "课表",
    "search_selection_rules": "规则",
    "check_course_requirements": "课程",
    "validate_eligibility": "资格",
    "create_selection_application": "建申请",
}


# ══════════════════ 基础设施：HTTP + SSE ══════════════════

class Throttle:
    """简易节流器：窗口内超过 N 次则等待（适配服务端 20 次/分钟限流）。"""

    def __init__(self, limit: int = 18, window: float = 61.0):
        self.limit, self.window = limit, window
        self.count = 0
        self.t0 = time.time()

    def wait(self) -> None:
        if self.count >= self.limit:
            elapsed = time.time() - self.t0
            if elapsed < self.window:
                print(f"    …限流窗口等待 {self.window - elapsed:.0f}s")
                time.sleep(self.window - elapsed)
            self.count, self.t0 = 0, time.time()
        self.count += 1


def request(method: str, path: str, body: dict | None = None,
            headers: dict | None = None):
    """通用请求：返回 (状态码, JSON/文本)。"""
    data = None
    hdrs = dict(headers or {})
    if isinstance(body, dict):
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
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


def login(username: str, password: str = "123456") -> str:
    status, data = request("POST", "/api/auth/login",
                           {"username": username, "password": password})
    assert status == 200 and data.get("token"), f"登录失败：{username}"
    return data["token"]


def chat_sse(token: str, question: str,
             session_id: str | None = None) -> dict:
    """发一次 /api/chat 并解析 SSE（CRLF 归一化），聚合返回。"""
    body = {"question": question}
    if session_id:
        body["session_id"] = session_id
    req = urllib.request.Request(
        BASE + "/api/chat",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            raw = r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return {"answer": "", "citations": [], "tools": [], "confirm": None,
                "session_id": session_id,
                "error": {"code": str(e.code), "message": e.read().decode("utf-8")[:120]}}

    out = {"answer": "", "citations": [], "tools": [], "confirm": None,
           "session_id": None, "error": None}
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
            payload = json.loads(data)
        except json.JSONDecodeError:
            continue
        if ev == "message":
            out["answer"] += payload.get("delta", "")
        elif ev == "citations":
            out["citations"] = payload
        elif ev == "tool" and payload.get("phase") == "done":
            out["tools"].append(payload["name"])
        elif ev == "confirm_required":
            out["confirm"] = payload
        elif ev == "done":
            out["session_id"] = payload.get("session_id")
        elif ev == "error":
            out["error"] = payload
    return out


# ══════════════════ 断言引擎 ══════════════════

def check_assertions(expect: dict, actual: dict) -> list[str]:
    """对一轮对话执行断言，返回失败原因列表（空 = 通过）。

    expect 字段：question/expected_tools/forbidden_tools/exact_tools/
                expected_behavior{...}（与 eval_cases.json 对应）。
    """
    fails: list[str] = []

    # 0) 流内错误（error 事件）= 直接失败
    if actual.get("error"):
        fails.append(f"收到 error 事件：{actual['error'].get('message', '')[:60]}")

    # 1) 工具断言
    tools, exp = actual["tools"], expect.get("expected_tools", [])
    if expect.get("exact_tools"):
        if tools != exp:
            fails.append(f"工具序列不符：期望 {exp}，实际 {tools}")
    else:
        for t in exp:
            if t not in tools:
                fails.append(f"缺少必需工具：{t}")
    for t in expect.get("forbidden_tools", []):
        if t in tools:
            fails.append(f"出现禁用工具：{t}")

    # 2) 行为断言（expected_behavior）
    b = expect.get("expected_behavior", {})
    ans = actual["answer"]

    if b.get("answer_contains_any") and not any(k in ans for k in b["answer_contains_any"]):
        fails.append(f"回答缺少关键词（任一）：{b['answer_contains_any']}")
    for k in b.get("answer_contains_all", []):
        if k not in ans:
            fails.append(f"回答缺少关键词：{k}")
    for k in b.get("answer_not_contains", []):
        if k in ans:
            fails.append(f"回答包含禁词：{k}")
    if b.get("has_citations") and not actual["citations"]:
        fails.append("缺少引用来源")
    if b.get("has_confirm_card") and not actual["confirm"]:
        fails.append("缺少确认卡片（确认门未触发）")
    if b.get("no_confirm_card") and actual["confirm"]:
        fails.append("不应出现确认卡片")
    return fails


# ══════════════════ 主流程 ══════════════════

def short_tools(tools: list[str]) -> str:
    """工具序列缩写（报告一行内展示）。"""
    return "[" + "→".join(TOOL_SHORT.get(t, t) for t in tools) + "]" if tools else "[无工具]"


def main() -> int:
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    print("═" * 72)
    print(f"评测执行器（提示词8）：{len(cases)} 条用例 · 基线 = mock 供应商（离线）")
    print("═" * 72)

    token = login("student1")
    throttle = Throttle()
    results: list[tuple[str, str, bool, str]] = []   # (id, 分类, 通过, 说明)

    for case in cases:
        cid = case.get("id", "?")
        cat = case.get("category", "?")

        # ── 单轮用例 ──
        if "question" in case:
            throttle.wait()
            actual = chat_sse(token, case["question"])
            fails = check_assertions(case, actual)
            desc = case.get("expected_behavior", {}).get("description", "")
            results.append((cid, cat, not fails,
                            "；".join(fails) if fails else desc[:44]))
            mark = "✅" if not fails else "❌"
            print(f"{mark} {cid} [{cat}] {short_tools(actual['tools'])}"
                  + (f" —— {'；'.join(fails)[:80]}" if fails else ""))

        # ── 多轮用例（turns 逐轮同 session 发送）──
        elif "turns" in case:
            session_id = None
            all_ok, fail_msgs = True, []
            for i, turn in enumerate(case["turns"], start=1):
                throttle.wait()
                actual = chat_sse(token, turn["question"], session_id)
                session_id = actual.get("session_id") or session_id
                fails = check_assertions(turn, actual)
                if fails:
                    all_ok = False
                    fail_msgs.append(f"第{i}轮：{'；'.join(fails)}")
                print(f"{'✅' if not fails else '❌'} {cid}.{i} [{cat}] "
                      f"{short_tools(actual['tools'])}"
                      + (f" —— {'；'.join(fails)[:70]}" if fails else ""))
            desc = case["turns"][-1].get("expected_behavior", {}).get("description", "")
            results.append((cid, cat, all_ok,
                            "；".join(fail_msgs) if fail_msgs else desc[:44]))

    # ── 汇总报告 ──
    passed = sum(1 for _, _, ok, _ in results if ok)
    print("\n" + "═" * 72)
    print(f"评测结果：{passed}/{len(results)} 通过"
          f"（通过率 {passed / len(results) * 100:.1f}%）")
    # 分类统计
    cats: dict[str, list[int]] = {}
    for _, cat, ok, _ in results:
        c = cats.setdefault(cat, [0, 0])
        c[1] += 1
        if ok:
            c[0] += 1
    for cat, (p, t) in cats.items():
        print(f"  · {cat:<10} {p}/{t}")
    print("═" * 72)

    # 失败明细（供修复定位）
    failures = [(cid, msg) for cid, _, ok, msg in results if not ok]
    if failures:
        print("\n失败明细：")
        for cid, msg in failures:
            print(f"  ✗ {cid}：{msg}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
