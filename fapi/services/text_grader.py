"""
文字论述阅卷引擎：LLM按Rubric逐要点评分
"""
import json
import logging
from models import Question, StudentAnswer
from services.llm_client import chat_completion_json

logger = logging.getLogger(__name__)


def _extract_text_from_answer(answer: StudentAnswer) -> str:
    """从学生答案中提取文字内容"""
    text = ""
    if answer.answer_text:
        text = answer.answer_text
    if not text and answer.option_answers:
        try:
            data = json.loads(answer.option_answers)
            if isinstance(data, dict) and data.get("text"):
                text = data["text"]
            elif isinstance(data, str):
                text = data
        except (json.JSONDecodeError, TypeError):
            text = answer.option_answers
    return text


async def grade_text_question(
    question: Question,
    answer: StudentAnswer,
    rubric_items: list[dict],
) -> list[dict]:
    """对文字论述题的所有评分项进行LLM评分"""
    student_text = _extract_text_from_answer(answer)
    results = []

    if not student_text.strip():
        for item in rubric_items:
            results.append({
                "item_id": item.get("item_id", ""),
                "max_score": item.get("max_score", 0),
                "ai_score": 0,
                "confidence": 0.95,
                "reason": "学生未提交答案",
                "method": "empty_check",
                "needs_review": False,
            })
        return results

    items_desc = json.dumps(rubric_items, ensure_ascii=False, indent=2)

    system_prompt = """你是一名专业的AI训练师实操考试阅卷专家。
你需要根据评分细则，逐项判断学生的文字答案是否满足要求并给分。

请返回JSON格式，包含一个 "scores" 数组，每个元素对应一个评分项：
{
  "scores": [
    {
      "item_id": "M1",
      "score": 2,
      "confidence": 0.85,
      "reason": "学生答案中包含了XXX要点，论述合理"
    }
  ]
}

评分要求：
- score 必须在 0 到该项 max_score 之间
- confidence 表示你对这个评分的把握程度(0-1)
- reason 用中文简要说明评分理由
- 如果学生答案提到了评分项要求的关键概念但表述不同，应当给分
- 如果学生答案完全未涉及该评分项的内容，给0分"""

    user_prompt = f"""## 题目内容
{question.content[:2000] if question.content else '无'}

## 评分细则
{items_desc}

## 学生答案
{student_text[:4000]}

请逐项评分。"""

    try:
        result = await chat_completion_json(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=4096,
        )

        scores_list = result.get("scores", [])
        score_map = {s["item_id"]: s for s in scores_list}

        for item in rubric_items:
            item_id = item.get("item_id", "")
            max_score = item.get("max_score", 0)
            llm_item = score_map.get(item_id, {})

            score = min(max(0, llm_item.get("score", 0)), max_score)
            confidence = llm_item.get("confidence", 0.7)
            reason = llm_item.get("reason", "LLM评分")

            results.append({
                "item_id": item_id,
                "max_score": max_score,
                "ai_score": score,
                "confidence": confidence,
                "reason": reason,
                "method": "llm_rubric",
                "needs_review": confidence < 0.8,
            })

    except Exception as e:
        logger.error(f"LLM text grading failed: {e}")
        for item in rubric_items:
            results.append({
                "item_id": item.get("item_id", ""),
                "max_score": item.get("max_score", 0),
                "ai_score": 0,
                "confidence": 0,
                "reason": f"LLM调用失败: {str(e)}",
                "method": "llm_error",
                "needs_review": True,
            })

    return results
