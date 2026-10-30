# -*- coding: utf-8 -*-
"""阶段 2 · 限流验证脚本（仅标准库）：验证滑动窗口限流（默认 20 次/分钟/IP）。

注意：先等待 61 秒让历史请求滑出窗口，保证从干净窗口起测；
然后连发 21 个请求 —— 预期前 20 个 200、第 21 个 429（42901 + 中文信息）。
对应上线检查项"并发与限流"的雏形；阶段3 替换为 Redis 后此脚本仍可复用。
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000"
LIMIT = 20   # 与 app/config.py 的 rate_limit_per_minute 默认值一致

print("等待 61 秒，让历史请求滑出限流窗口…")
time.sleep(61)

codes = []
for i in range(LIMIT + 1):
    req = urllib.request.Request(
        BASE + "/api/chat",
        data=json.dumps({"question": "限流压力测试"}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
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
