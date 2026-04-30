"""
阅卷引擎主调度：按题型分发到不同的阅卷策略
"""
import json
import logging
from sqlalchemy.orm import Session
from models import (
    Question, StudentAnswer, StudentExam, GradingRubric, GradingResult,
)
from services.code_grader import grade_code_question
from services.text_grader import grade_text_question
from services.file_grader import grade_file_question

logger = logging.getLogger(__name__)


async def grade_student_exam(student_exam_id: int, db: Session) -> dict:
    """
    对一位考生的整场考试进行AI阅卷。
    返回 {"ai_total_score": float, "results": [...]}
    """
    student_exam = db.query(StudentExam).filter(StudentExam.id == student_exam_id).first()
    if not student_exam:
        raise ValueError(f"StudentExam {student_exam_id} not found")

    if student_exam.status != "submitted":
        raise ValueError("只能对已提交的考试进行阅卷")

    print(f"\n{'='*50}")
    print(f"[阅卷] 开始阅卷 student_exam_id={student_exam_id}")
    print(f"{'='*50}")

    answers = db.query(StudentAnswer).filter(
        StudentAnswer.student_exam_id == student_exam_id
    ).all()

    total_ai_score = 0.0
    results = []

    for answer in answers:
        rubric = db.query(GradingRubric).filter(
            GradingRubric.question_id == answer.question_id
        ).first()

        if not rubric:
            print(f"[阅卷] 题目 {answer.question_id} 没有评分细则，跳过")
            continue

        question = db.query(Question).filter(Question.id == answer.question_id).first()
        print(f"\n[阅卷] 正在评分: 题目{question.order if question else '?'} (question_id={answer.question_id}, 类型={rubric.grading_type})")

        try:
            item_scores = await _grade_single_answer(question, answer, rubric)
        except Exception as e:
            print(f"[阅卷] 评分失败: {e}")
            item_scores = _empty_scores(rubric)

        ai_score = sum(item["ai_score"] for item in item_scores)
        print(f"[阅卷] 题目{question.order if question else '?'} AI得分: {ai_score}/{rubric.total_score}")
        total_ai_score += ai_score

        existing = db.query(GradingResult).filter(
            GradingResult.student_answer_id == answer.id
        ).first()

        if existing:
            existing.ai_score = ai_score
            existing.item_scores = json.dumps(item_scores, ensure_ascii=False)
            existing.status = "ai_graded"
            existing.final_score = None
            existing.reviewed_by = None
            existing.reviewed_at = None
        else:
            gr = GradingResult(
                student_answer_id=answer.id,
                question_id=answer.question_id,
                student_exam_id=student_exam_id,
                ai_score=ai_score,
                item_scores=json.dumps(item_scores, ensure_ascii=False),
                status="ai_graded",
            )
            db.add(gr)

        results.append({
            "question_id": answer.question_id,
            "ai_score": ai_score,
            "item_scores": item_scores,
        })

    student_exam.ai_total_score = total_ai_score
    student_exam.grading_status = "ai_graded"
    db.commit()

    print(f"\n{'='*50}")
    print(f"[阅卷] 阅卷完成! AI总分: {total_ai_score}")
    print(f"{'='*50}\n")

    return {"ai_total_score": total_ai_score, "results": results}


async def _grade_single_answer(
    question: Question,
    answer: StudentAnswer,
    rubric: GradingRubric,
) -> list[dict]:
    """对单道题的答案进行AI评分，返回每个得分点的评分列表"""
    rubric_items = json.loads(rubric.rubric_items)
    grading_type = rubric.grading_type

    if grading_type == "code":
        return await grade_code_question(question, answer, rubric_items)
    elif grading_type == "text":
        return await grade_text_question(question, answer, rubric_items)
    elif grading_type == "file":
        return await grade_file_question(question, answer, rubric_items)
    else:
        # mixed: 按每个评分项的 type 分别处理
        results = []
        for item in rubric_items:
            item_type = item.get("type", "text")
            if item_type == "code":
                scored = await grade_code_question(question, answer, [item])
            elif item_type == "file":
                scored = await grade_file_question(question, answer, [item])
            else:
                scored = await grade_text_question(question, answer, [item])
            results.extend(scored)
        return results


def _empty_scores(rubric: GradingRubric) -> list[dict]:
    """阅卷失败时返回全0分"""
    items = json.loads(rubric.rubric_items)
    return [
        {
            "item_id": item.get("item_id", f"M{i+1}"),
            "max_score": item.get("max_score", 0),
            "ai_score": 0,
            "confidence": 0,
            "reason": "阅卷引擎异常，需人工评分",
            "method": "error",
            "needs_review": True,
        }
        for i, item in enumerate(items)
    ]
