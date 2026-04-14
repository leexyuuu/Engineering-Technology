"""
代码阅卷引擎：AST/正则检查 + LLM兜底
支持从上传的 .ipynb / .py / .html (Jupyter导出) 文件中提取代码和输出
"""
import os
import re
import json
import logging
from models import Question, StudentAnswer
from services.llm_client import chat_completion_json

logger = logging.getLogger(__name__)

UPLOAD_FOLDER = "uploads"
CONFIDENCE_HIGH = 0.95
CONFIDENCE_MEDIUM = 0.8


# ─── 文件内容提取 ───

def _read_ipynb(file_path: str) -> tuple[str, str]:
    """从 .ipynb 文件中提取代码和输出，返回 (code, output)"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            nb = json.load(f)
        code_parts, output_parts = [], []
        for cell in nb.get("cells", []):
            if cell.get("cell_type") == "code":
                source = cell.get("source", [])
                if isinstance(source, list):
                    code_parts.append("".join(source))
                elif isinstance(source, str):
                    code_parts.append(source)
                for out in cell.get("outputs", []):
                    if out.get("output_type") == "stream":
                        text = out.get("text", [])
                        output_parts.append("".join(text) if isinstance(text, list) else str(text))
                    elif out.get("output_type") in ("execute_result", "display_data"):
                        data = out.get("data", {})
                        text = data.get("text/plain", [])
                        output_parts.append("".join(text) if isinstance(text, list) else str(text))
        return "\n\n".join(code_parts), "\n".join(output_parts)
    except Exception as e:
        print(f"[代码提取] 读取ipynb失败: {e}")
        return "", ""


def _read_html(file_path: str) -> tuple[str, str]:
    """从 Jupyter 导出的 HTML 文件中提取代码和输出，返回 (code, output)"""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        print("[代码提取] beautifulsoup4 未安装，无法解析HTML")
        return "", ""

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            html = f.read()

        soup = BeautifulSoup(html, "html.parser")
        code_parts, output_parts = [], []

        # Jupyter Notebook HTML 的代码在 .input_area 或 .highlight 中
        for el in soup.select(".input_area pre, .highlight pre, .jp-InputArea pre"):
            text = el.get_text()
            if text.strip():
                code_parts.append(text)

        # 输出在 .output_area 或 .output_text 中
        for el in soup.select(".output_area pre, .output_text pre, .output_subarea pre, .jp-OutputArea pre"):
            text = el.get_text()
            if text.strip():
                output_parts.append(text)

        # 如果上面的选择器没匹配到，尝试更通用的方式
        if not code_parts:
            for el in soup.select("pre"):
                text = el.get_text()
                if text.strip():
                    parent_classes = " ".join(el.parent.get("class", []) if el.parent else [])
                    if "input" in parent_classes or "highlight" in parent_classes or "code" in parent_classes:
                        code_parts.append(text)
                    elif "output" in parent_classes:
                        output_parts.append(text)

        # 最后兜底：如果还是没提取到，把所有 pre 标签当代码
        if not code_parts:
            all_pres = [el.get_text() for el in soup.select("pre") if el.get_text().strip()]
            if all_pres:
                code_parts = all_pres
                print(f"[代码提取] HTML解析使用兜底模式，提取了 {len(all_pres)} 个pre标签")

        code = "\n\n".join(code_parts)
        output = "\n".join(output_parts)
        print(f"[代码提取] 从 HTML 提取到 {len(code)} 字符代码, {len(output)} 字符输出")
        return code, output

    except Exception as e:
        print(f"[代码提取] 读取HTML失败: {e}")
        return "", ""


def _read_py(file_path: str) -> tuple[str, str]:
    """读取 .py 文件内容，返回 (code, '')"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read(), ""
    except Exception as e:
        print(f"[代码提取] 读取py文件失败: {e}")
        return "", ""


def _extract_from_files(answer: StudentAnswer) -> tuple[str, str]:
    """从学生上传的文件中提取代码和输出"""
    if not answer.file_answers:
        return "", ""

    try:
        file_answers = json.loads(answer.file_answers)
    except (json.JSONDecodeError, TypeError):
        return "", ""

    if not isinstance(file_answers, dict):
        return "", ""

    all_code, all_output = "", ""

    for uuid_key, file_url in file_answers.items():
        if not file_url:
            continue
        filename = file_url.split("/")[-1]
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if not os.path.exists(file_path):
            continue

        ext = os.path.splitext(filename)[1].lower()
        if ext == ".html" or ext == ".htm":
            code, output = _read_html(file_path)
            if code:
                all_code = code
                all_output = output
                break
        elif ext == ".ipynb":
            code, output = _read_ipynb(file_path)
            if code:
                all_code = code
                all_output = output
                break
        elif ext == ".py":
            code, output = _read_py(file_path)
            if code:
                all_code = code
                break

    return all_code, all_output


def _extract_code_and_output(answer: StudentAnswer) -> tuple[str, str]:
    """从学生答案中提取代码和输出，优先读取上传文件"""
    code, output = _extract_from_files(answer)
    if code:
        return code, output

    text_code = ""
    if answer.option_answers:
        try:
            data = json.loads(answer.option_answers)
            if isinstance(data, dict) and data.get("code"):
                text_code = data["code"]
            elif isinstance(data, str):
                text_code = data
        except (json.JSONDecodeError, TypeError):
            text_code = answer.option_answers

    if not text_code and answer.answer_text:
        text_code = answer.answer_text

    return text_code or "", ""


# ─── 评分逻辑 ───

def _ast_check(code: str, item: dict) -> dict | None:
    """
    AST/正则快速检查。
    如果能确定性地判断得分，返回评分 dict；否则返回 None 交给LLM。
    """
    keywords = item.get("keywords", [])
    if not keywords:
        return None

    matched = sum(1 for kw in keywords if kw in code)

    if matched == len(keywords):
        return {
            "ai_score": item["max_score"],
            "confidence": CONFIDENCE_HIGH,
            "reason": f"代码中包含所有关键特征: {', '.join(keywords)}",
            "method": "ast_match",
            "needs_review": False,
        }
    elif matched == 0:
        return {
            "ai_score": 0,
            "confidence": CONFIDENCE_MEDIUM,
            "reason": f"代码中未找到关键特征: {', '.join(keywords)}",
            "method": "ast_match",
            "needs_review": True,
        }
    return None


def _output_check(output: str, item: dict) -> dict | None:
    """
    检查运行输出是否包含期望的数据。
    用于M1~M3这类"输出数据正确"的评分项。
    """
    standard = item.get("standard_answer", "")
    if not standard or not output:
        return None

    keywords = item.get("keywords", [])
    if not keywords:
        if standard in output:
            return {
                "ai_score": item["max_score"],
                "confidence": 0.9,
                "reason": f"输出中包含期望数据",
                "method": "output_match",
                "needs_review": False,
            }
        return None

    matched = sum(1 for kw in keywords if kw in output)
    if matched == len(keywords):
        return {
            "ai_score": item["max_score"],
            "confidence": 0.9,
            "reason": f"输出中包含所有期望数据: {', '.join(keywords)}",
            "method": "output_match",
            "needs_review": False,
        }
    return None


async def _llm_code_review(question: Question, code: str, output: str, item: dict) -> dict:
    """用LLM判断代码逻辑是否正确"""
    system_prompt = """你是一名Python代码阅卷专家。你需要判断学生代码是否满足评分要求。
请返回JSON格式，包含以下字段：
- score: 得分(0到max_score之间的整数)
- confidence: 置信度(0-1之间的小数)
- reason: 评分理由(简要说明)"""

    output_section = ""
    if output:
        output_section = f"""
## 代码运行输出
```
{output[:2000]}
```
"""

    user_prompt = f"""## 评分项
- 编号: {item.get('item_id', 'N/A')}
- 描述: {item.get('description', '')}
- 满分: {item['max_score']}分
- 标准答案代码片段: {item.get('standard_answer', '未提供')}

## 学生代码
```python
{code[:3000]}
```
{output_section}
请判断学生代码是否满足上述评分项的要求，给出得分。"""

    try:
        result = await chat_completion_json(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
        )
        score = min(result.get("score", 0), item["max_score"])
        confidence = result.get("confidence", 0.7)
        reason = result.get("reason", "LLM评分")
        return {
            "ai_score": max(0, score),
            "confidence": confidence,
            "reason": reason,
            "method": "llm_review",
            "needs_review": confidence < 0.8,
        }
    except Exception as e:
        logger.error(f"LLM code review failed: {e}")
        return {
            "ai_score": 0,
            "confidence": 0,
            "reason": f"LLM调用失败: {str(e)}",
            "method": "llm_error",
            "needs_review": True,
        }


async def grade_code_question(
    question: Question,
    answer: StudentAnswer,
    rubric_items: list[dict],
) -> list[dict]:
    """对代码题的所有评分项进行评分"""
    code, output = _extract_code_and_output(answer)
    results = []

    for item in rubric_items:
        item_result = {
            "item_id": item.get("item_id", ""),
            "max_score": item.get("max_score", 0),
        }

        if not code.strip():
            item_result.update({
                "ai_score": 0,
                "confidence": CONFIDENCE_HIGH,
                "reason": "学生未提交代码",
                "method": "empty_check",
                "needs_review": False,
            })
            results.append(item_result)
            continue

        # 第1层：检查输出是否匹配（适用于"数据正确"类评分项）
        output_result = _output_check(output, item)
        if output_result:
            item_result.update(output_result)
            results.append(item_result)
            continue

        # 第2层：AST/关键词匹配
        ast_result = _ast_check(code, item)
        if ast_result:
            item_result.update(ast_result)
            results.append(item_result)
            continue

        # 第3层：LLM兜底（同时传入代码和输出）
        llm_result = await _llm_code_review(question, code, output, item)
        item_result.update(llm_result)
        results.append(item_result)

    return results
