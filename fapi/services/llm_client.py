"""
LLM API 统一调用层
默认使用通义千问（qwen），也支持 DeepSeek / OpenAI
图片分析使用 qwen-vl-max 视觉模型
"""
import os
import json
import base64
import httpx
from typing import Optional

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "qwen")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "")

VISION_PROVIDER = os.getenv("VISION_PROVIDER", "")
VISION_API_KEY = os.getenv("VISION_API_KEY", "")
VISION_MODEL = os.getenv("VISION_MODEL", "")

PROVIDER_CONFIG = {
    "qwen": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_model": "qwen-max",
        "default_vision_model": "qwen-vl-max",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
        "default_vision_model": "deepseek-chat",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "default_vision_model": "gpt-4o-mini",
    },
}


async def chat_completion(
    messages: list[dict],
    temperature: float = 0.1,
    max_tokens: int = 4096,
    response_format: Optional[dict] = None,
) -> str:
    """
    调用 LLM Chat Completion API，返回助手消息文本。
    messages 格式: [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
    """
    provider = LLM_PROVIDER
    cfg = PROVIDER_CONFIG.get(provider)
    if not cfg:
        raise ValueError(f"Unsupported LLM provider: {provider}")

    api_key = LLM_API_KEY
    if not api_key:
        raise ValueError("LLM_API_KEY environment variable is not set")

    model = LLM_MODEL or cfg["default_model"]
    url = f"{cfg['base_url']}/chat/completions"

    print(f"[LLM] 调用 {provider}/{model} ...")

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_format:
        payload["response_format"] = response_format

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code != 200:
            print(f"[LLM] 错误 {resp.status_code}: {resp.text[:500]}")
        resp.raise_for_status()
        data = resp.json()

    content = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    print(f"[LLM] 完成 | tokens: 输入{usage.get('prompt_tokens', '?')} 输出{usage.get('completion_tokens', '?')} | 回复前100字: {content[:100]}")
    return content


async def chat_completion_json(
    messages: list[dict],
    temperature: float = 0.1,
    max_tokens: int = 4096,
) -> dict:
    """
    调用 LLM 并要求返回 JSON，自动解析为 dict。
    对于不支持 response_format 的模型，会从文本中提取 JSON。
    """
    provider = LLM_PROVIDER
    response_format = None
    if provider in ("qwen", "deepseek", "openai"):
        response_format = {"type": "json_object"}

    text = await chat_completion(
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        response_format=response_format,
    )

    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]  # remove ```json
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    return json.loads(text)


def _encode_image_to_base64(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _get_image_mime(image_path: str) -> str:
    ext = os.path.splitext(image_path)[1].lower()
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }.get(ext, "image/jpeg")


async def vision_completion(
    prompt: str,
    image_paths: list[str],
    temperature: float = 0.1,
    max_tokens: int = 4096,
) -> str:
    """
    调用 Vision 模型分析图片内容。
    image_paths: 本地图片文件路径列表
    """
    provider = VISION_PROVIDER or LLM_PROVIDER
    cfg = PROVIDER_CONFIG.get(provider)
    if not cfg:
        raise ValueError(f"Unsupported vision provider: {provider}")

    api_key = VISION_API_KEY or LLM_API_KEY
    if not api_key:
        raise ValueError("Vision API key is not set")

    model = VISION_MODEL or cfg.get("default_vision_model", cfg["default_model"])
    url = f"{cfg['base_url']}/chat/completions"

    print(f"[Vision] 调用 {provider}/{model} | 图片数: {len(image_paths)} ...")

    content_parts = [{"type": "text", "text": prompt}]
    for path in image_paths:
        if not os.path.exists(path):
            continue
        b64 = _encode_image_to_base64(path)
        mime = _get_image_mime(path)
        content_parts.append({
            "type": "image_url",
            "image_url": {"url": f"data:{mime};base64,{b64}"},
        })

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": content_parts}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    content = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    print(f"[Vision] 完成 | tokens: 输入{usage.get('prompt_tokens', '?')} 输出{usage.get('completion_tokens', '?')} | 回复前100字: {content[:100]}")
    return content


async def vision_completion_json(
    prompt: str,
    image_paths: list[str],
    temperature: float = 0.1,
    max_tokens: int = 4096,
) -> dict:
    """调用 Vision 模型分析图片，返回 JSON dict"""
    json_prompt = prompt + "\n\n请以JSON格式返回结果。"
    text = await vision_completion(json_prompt, image_paths, temperature, max_tokens)

    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    return json.loads(text)
