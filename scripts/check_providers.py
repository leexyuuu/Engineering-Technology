# -*- coding: utf-8 -*-
"""上线前动作 · 供应商连通性自检（运维填入 .env 后运行）。

用法（无需起服，独立运行）：
    python scripts/check_providers.py

检查项：
  1. .env 是否存在；JWT_SECRET 是否仍为开发默认值（生产必须已更换）；
  2. LLM / Embedding 供应商模式：mock → 提示离线演示；openai_compatible → 实测连通；
  3. 连通测试：GET {base_url}/models（Bearer 鉴权），报告状态码与耗时；
  4. 切换供应商后提醒重启服务生效。

仅标准库实现，不依赖项目代码。
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"

DEFAULT_SECRET = "dev-secret-生产环境务必修改"


def load_env() -> dict:
    """极简 .env 解析（KEY=VALUE，忽略注释与空行）。"""
    cfg: dict[str, str] = {}
    if not ENV_PATH.exists():
        return cfg
    for line in ENV_PATH.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        cfg[key.strip()] = value.strip()
    return cfg


def probe(base_url: str, api_key: str) -> tuple[bool, str]:
    """GET {base_url}/models 实测连通，返回 (是否可达, 摘要)。"""
    url = base_url.rstrip("/") + "/models"
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + api_key})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            ms = (time.time() - t0) * 1000
            return True, f"HTTP {r.status}，耗时 {ms:.0f}ms"
    except urllib.error.HTTPError as e:
        # 401/403 说明端点可达但鉴权失败——URL 对、key 需检查
        return False, f"HTTP {e.code}（端点可达，检查 API Key）"
    except Exception as e:  # noqa: BLE001
        return False, f"{type(e).__name__}: {e}"


def main() -> int:
    print("═" * 60)
    print("供应商连通性自检（.env 生产配置核验）")
    print("═" * 60)
    issues = 0

    cfg = load_env()
    if not cfg:
        print("❌ 未找到 .env（复制 .env.example 为 .env 后填写）")
        return 1

    # ── 1. JWT 密钥 ──
    secret = cfg.get("JWT_SECRET", "")
    if not secret:
        print("❌ JWT_SECRET 未设置")
        issues += 1
    elif secret == DEFAULT_SECRET:
        print("❌ JWT_SECRET 仍为开发默认值——生产必须更换")
        issues += 1
    else:
        print(f"✅ JWT_SECRET 已更换（长度 {len(secret)}）")

    # ── 2/3. LLM 供应商 ──
    llm_provider = cfg.get("LLM_PROVIDER", "mock")
    if llm_provider == "openai_compatible":
        base, key = cfg.get("LLM_BASE_URL", ""), cfg.get("LLM_API_KEY", "")
        if not base or not key or key.startswith("<"):
            print("❌ LLM_PROVIDER=openai_compatible 但 BASE_URL/API_KEY 未填写")
            issues += 1
        else:
            ok, detail = probe(base, key)
            print(f"{'✅' if ok else '❌'} LLM 供应商（{base}）：{detail}")
            issues += 0 if ok else 1
    else:
        print("⚠ LLM 供应商为 mock（离线演示）——上线前须切换 openai_compatible")

    # ── Embedding 供应商 ──
    emb_provider = cfg.get("EMBEDDING_PROVIDER", "local_hash")
    if emb_provider == "openai_compatible":
        base, key = cfg.get("EMBEDDING_BASE_URL", ""), cfg.get("EMBEDDING_API_KEY", "")
        if not base or not key or key.startswith("<"):
            print("❌ EMBEDDING_PROVIDER=openai_compatible 但 BASE_URL/API_KEY 未填写")
            issues += 1
        else:
            ok, detail = probe(base, key)
            print(f"{'✅' if ok else '❌'} Embedding 供应商（{base}）：{detail}")
            issues += 0 if ok else 1
    else:
        print("⚠ Embedding 供应商为 local_hash（无语义）——上线前建议切换 openai_compatible")

    # ── 4. 生效提示 ──
    print("─" * 60)
    print("提示：修改 .env 后需重启服务（uvicorn）方可生效。")
    if issues:
        print(f"结论：❌ {issues} 项待处理，暂不具备切换真实供应商条件")
        return 1
    print("结论：✅ 配置就绪（mock 提醒项除外），可重启服务切换真实供应商")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
