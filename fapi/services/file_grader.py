"""
文件比对阅卷引擎：图片截图分析、CSV数据比对、模型文件验证
"""
import os
import json
import logging
from models import Question, StudentAnswer
from services.llm_client import vision_completion_json

logger = logging.getLogger(__name__)

UPLOAD_FOLDER = "uploads"


def _resolve_file_path(file_url: str) -> str | None:
    """从文件URL中解析出本地文件路径"""
    if not file_url:
        return None
    filename = file_url.split("/")[-1]
    path = os.path.join(UPLOAD_FOLDER, filename)
    return path if os.path.exists(path) else None


def _is_image(file_url: str) -> bool:
    if not file_url:
        return False
    ext = os.path.splitext(file_url)[1].lower()
    return ext in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")


def _get_submitted_files(answer: StudentAnswer) -> dict[str, str]:
    """获取学生提交的所有文件 {uuid_or_key: file_url}"""
    files = {}
    if answer.file_answers:
        try:
            fa = json.loads(answer.file_answers)
            if isinstance(fa, dict):
                files.update(fa)
        except (json.JSONDecodeError, TypeError):
            pass
    if answer.file_url:
        files["single_file"] = answer.file_url
    return files


async def _grade_image_item(item: dict, image_path: str) -> dict:
    """用Vision模型分析截图内容并评分"""
    description = item.get("description", "")
    standard_answer = item.get("standard_answer", "")
    max_score = item.get("max_score", 0)

    prompt = f"""你是AI训练师实操考试的阅卷专家。请分析这张截图，判断其中的数据是否正确。

## 评分项
- 描述: {description}
- 满分: {max_score}分
- 标准答案/期望内容: {standard_answer if standard_answer else '请根据描述判断截图内容是否合理'}

## 评分要求
1. 仔细识别截图中的文字和数据
2. 判断数据是否与评分项描述的要求一致
3. 如果截图清晰且数据正确，给满分
4. 如果截图模糊无法识别，或数据不正确，酌情扣分

请返回JSON:
{{"score": 分数, "confidence": 置信度0-1, "reason": "评分理由", "extracted_text": "从截图中识别出的关键数据"}}"""

    try:
        result = await vision_completion_json(prompt, [image_path])
        score = min(max(0, result.get("score", 0)), max_score)
        confidence = result.get("confidence", 0.7)
        reason = result.get("reason", "Vision模型评分")
        extracted = result.get("extracted_text", "")
        if extracted:
            reason = f"{reason} [识别内容: {extracted[:100]}]"

        return {
            "ai_score": score,
            "confidence": confidence,
            "reason": reason,
            "method": "vision_analysis",
            "needs_review": confidence < 0.8,
        }
    except Exception as e:
        logger.error(f"Vision analysis failed: {e}")
        return {
            "ai_score": 0,
            "confidence": 0,
            "reason": f"图片分析失败: {str(e)}，需人工评分",
            "method": "vision_error",
            "needs_review": True,
        }


async def grade_file_question(
    question: Question,
    answer: StudentAnswer,
    rubric_items: list[dict],
) -> list[dict]:
    """对文件产出物类评分项进行评分"""
    results = []
    submitted_files = _get_submitted_files(answer)

    for item in rubric_items:
        item_id = item.get("item_id", "")
        max_score = item.get("max_score", 0)
        expected_uuid = item.get("expected_file_uuid", "")

        target_url = None
        if expected_uuid and expected_uuid in submitted_files:
            target_url = submitted_files[expected_uuid]
        elif not expected_uuid and len(submitted_files) > 0:
            target_url = list(submitted_files.values())[0]

        if not target_url:
            results.append({
                "item_id": item_id,
                "max_score": max_score,
                "ai_score": 0,
                "confidence": 0.9,
                "reason": "未提交要求的文件",
                "method": "file_check",
                "needs_review": False,
            })
            continue

        file_path = _resolve_file_path(target_url)

        if file_path and _is_image(target_url):
            scored = await _grade_image_item(item, file_path)
            results.append({
                "item_id": item_id,
                "max_score": max_score,
                **scored,
            })
        elif file_path:
            results.append({
                "item_id": item_id,
                "max_score": max_score,
                "ai_score": max_score,
                "confidence": 0.7,
                "reason": "非图片文件已提交，内容需人工确认",
                "method": "file_check",
                "needs_review": True,
            })
        else:
            results.append({
                "item_id": item_id,
                "max_score": max_score,
                "ai_score": 0,
                "confidence": 0.5,
                "reason": "文件URL存在但服务器上未找到文件",
                "method": "file_missing",
                "needs_review": True,
            })

    return results
