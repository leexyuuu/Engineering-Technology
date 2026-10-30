# -*- coding: utf-8 -*-
"""限流验证脚本（仅标准库）：验证 /api/chat 滑动窗口限流（默认 20 次/分钟/IP）。

【上线演练发现4修复】适配阶段3鉴权：先登录获取 Bearer 令牌再连发请求
（原阶段2版本不带令牌，21 次全部 401，无法验证限流）。

注意：先等待 61 秒让历史请求滑出窗口，保证从干净窗口起测；
然后连发 21 个请求 —— 预期前 20 个 200、第 21 个 429（42901 + 中文信息）。
对应上线检查项 CL-1；多实例部署替换 Redis 后此脚本仍可复用。
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000"
LIMIT = 20   # 与 app/config.py 的 rate_limit_per_minute 默认值一致
USERNAME = "student1"
# 口令支持环境变量覆盖：生产口令库上运行时传 JWC_TEST_PASSWORD=<口令>；
# 默认 123456 适配干净演示库
PASSWORD = os.environ.get("JWC_TEST_PASSWORD", "123456")


def login() -> str:
    """登录获取 Bearer 令牌（限流按 IP 计数，登录接口不受 /api/chat 限流影响）。"""
    req = urllib.request.Request(
        BASE + "/api/auth/login",
        data=json.dumps({"username": USERNAME, "password": PASSWORD}).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.loads(r.read().decode("utf-8"))
    if r.status != 200 or not body.get("token"):
        raise SystemExit(f"登录失败：{r.status} {body}")
    return body["token"]


token = login()
print(f"登录成功（{USERNAME}），等待 61 秒让历史请求滑出限流窗口…")
time.sleep(61)

codes = []
for i in range(LIMIT + 1):
    req = urllib.request.Request(
        BASE + "/api/chat",
        data=json.dumps({"question": "限流压力测试"}).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + token},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            for _ in r:          # 消费完 SSE 流再发下一个
                pass
            codes.append(r.status)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        codes.append(e.code)
        if e.code == 429:
            print(f"第 {i + 1} 个请求 → 429：{body}")
    except Exception as exc:     # noqa: BLE001
        codes.append(-1)
        print(f"第 {i + 1} 个请求异常：{exc}")

print(f"\n状态码序列：{codes}")
allowed = codes.count(200)
ok = codes == [200] * LIMIT + [429]
print(f"限流验证：{'✅ 通过' if ok else '❌ 未达预期'}"
      f"（放行 {allowed}/{LIMIT + 1}，超限拒绝 {codes.count(429)}）")
raise SystemExit(0 if ok else 1)
