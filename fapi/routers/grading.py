"""
阅卷相关API路由
"""
from fastapi import Depends, Header, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
import json
import asyncio
import threading

from base import app, get_db
from admin import checkToken
from database import SessionLocal
from models import (
    Exam, Question, Student, StudentExam, StudentAnswer,
    GradingRubric, GradingResult,
)
from services.grading_engine import grade_student_exam


# ─── Pydantic Models ───

class RubricItemSchema(BaseModel):
    item_id: str
    description: str
    max_score: float
    type: str = "text"  # code / text / file
    standard_answer: Optional[str] = None
    keywords: Optional[List[str]] = None
    expected_file_uuid: Optional[str] = None


class RubricCreate(BaseModel):
    question_id: int
    total_score: float
    grading_type: str = "mixed"  # code / text / file / mixed
    rubric_items: str  # JSON string of list[RubricItemSchema]


class ScoreUpdate(BaseModel):
    item_id: str
    score: float


class ReviewSubmit(BaseModel):
    grading_result_id: int
    score_updates: Optional[List[ScoreUpdate]] = None
    final_score: Optional[float] = None


# ─── 评分细则 CRUD ───

@app.post("/grading/rubric")
def create_or_update_rubric(
    rubric: RubricCreate,
    token: str = Header(..., alias="Authorization"),
    db: Session = Depends(get_db),
):
    """创建或更新评分细则"""
    checkToken(token)

    # 验证 rubric_items 是合法 JSON
    try:
        items = json.loads(rubric.rubric_items)
        if not isinstance(items, list):
            raise ValueError
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="rubric_items 必须是合法的JSON数组")

    existing = db.query(GradingRubric).filter(
        GradingRubric.question_id == rubric.question_id
    ).first()

    if existing:
        existing.rubric_items = rubric.rubric_items
        existing.total_score = rubric.total_score
        existing.grading_type = rubric.grading_type
    else:
        existing = GradingRubric(
            question_id=rubric.question_id,
            rubric_items=rubric.rubric_items,
            total_score=rubric.total_score,
            grading_type=rubric.grading_type,
        )
        db.add(existing)

    db.commit()
    db.refresh(existing)
    return {"code": 20000, "data": {
        "id": existing.id,
        "question_id": existing.question_id,
        "total_score": existing.total_score,
        "grading_type": existing.grading_type,
    }}


@app.get("/grading/rubric/{question_id}")
def get_rubric(
    question_id: int,
    token: str = Header(..., alias="Authorization"),
    db: Session = Depends(get_db),
):
    """获取某道题的评分细则"""
    checkToken(token)
    rubric = db.query(GradingRubric).filter(
        GradingRubric.question_id == question_id
    ).first()
    if not rubric:
        return {"code": 20000, "data": None}

    return {"code": 20000, "data": {
        "id": rubric.id,
        "question_id": rubric.question_id,
        "rubric_items": rubric.rubric_items,
        "total_score": rubric.total_score,
        "grading_type": rubric.grading_type,
    }}


@app.get("/grading/rubrics/exam/{exam_id}")
def get_exam_rubrics(
    exam_id: int,
    token: str = Header(..., alias="Authorization"),
    db: Session = Depends(get_db),
):
    """获取某场考试所有题目的评分细则"""
    checkToken(token)
    questions = db.query(Question).filter(Question.exam_id == exam_id).all()
    qids = [q.id for q in questions]

    rubrics = db.query(GradingRubric).filter(GradingRubric.question_id.in_(qids)).all()
    rubric_map = {r.question_id: r for r in rubrics}

    result = []
    for q in questions:
        r = rubric_map.get(q.id)
        result.append({
            "question_id": q.id,
            "question_order": q.order,
            "has_rubric": r is not None,
            "total_score": r.total_score if r else None,
            "grading_type": r.grading_type if r else None,
        })

    return {"code": 20000, "data": result}


# ─── 后台阅卷任务 ───

def _run_grade_in_background(student_exam_id: int):
    """在后台线程中执行阅卷（使用独立的数据库session和事件循环）"""
    db = SessionLocal()
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(grade_student_exam(student_exam_id, db))
        loop.close()
    except Exception as e:
        print(f"[阅卷] 后台阅卷失败 student_exam_id={student_exam_id}: {e}")
        student_exam = db.query(StudentExam).filter(StudentExam.id == student_exam_id).first()
        if student_exam:
            student_exam.grading_status = "not_graded"
            db.commit()
    finally:
        db.close()


def _run_batch_grade_in_background(student_exam_ids: list[int]):
    """在后台线程中批量执行阅卷"""
    db = SessionLocal()
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        graded, failed = 0, 0
        for se_id in student_exam_ids:
            try:
                loop.run_until_complete(grade_student_exam(se_id, db))
                graded += 1
            except Exception as e:
                failed += 1
                print(f"[阅卷] 后台批量阅卷失败 student_exam_id={se_id}: {e}")
                student_exam = db.query(StudentExam).filter(StudentExam.id == se_id).first()
                if student_exam:
                    student_exam.grading_status = "not_graded"
                    db.commit()
        loop.close()
        print(f"[阅卷] 批量阅卷完成: {graded}份成功, {failed}份失败")
    finally:
        db.close()


# ─── 触发AI阅卷 ───

@app.post("/grading/grade/{student_exam_id}")
def trigger_grade_single(
    student_exam_id: int,
    token: str = Header(..., alias="Authorization"),
    db: Session = Depends(get_db),
):
    """对单个学生触发AI阅卷（立即返回，后台执行）"""
    checkToken(token)

    student_exam = db.query(StudentExam).filter(StudentExam.id == student_exam_id).first()
    if not student_exam:
        raise HTTPException(status_code=404, detail="考试记录不存在")
    if student_exam.status != "submitted":
        raise HTTPException(status_code=400, detail="只能对已提交的考试进行阅卷")
    if student_exam.grading_status == "ai_grading":
        return {"code": 20000, "data": {"message": "该学生正在阅卷中，请稍后刷新查看结果"}}

    student_exam.grading_status = "ai_grading"
    db.commit()

    thread = threading.Thread(target=_run_grade_in_background, args=(student_exam_id,))
    thread.start()

    return {"code": 20000, "data": {"message": "AI阅卷已开始，请稍后刷新查看结果"}}


@app.post("/grading/grade-batch/{exam_id}")
def trigger_grade_batch(
    exam_id: int,
    token: str = Header(..., alias="Authorization"),
    db: Session = Depends(get_db),
):
    """批量对整场考试所有已提交学生触发AI阅卷（立即返回，后台执行）"""
    checkToken(token)
    student_exams = db.query(StudentExam).filter(
        StudentExam.exam_id == exam_id,
        StudentExam.status == "submitted",
    ).all()

    if not student_exams:
        return {"code": 20000, "data": {"message": "没有已提交的考试记录", "total": 0}}

    ids_to_grade = []
    for se in student_exams:
        if se.grading_status != "ai_grading":
            se.grading_status = "ai_grading"
            ids_to_grade.append(se.id)
    db.commit()

    if not ids_to_grade:
        return {"code": 20000, "data": {"message": "所有学生都在阅卷中", "total": 0}}

    thread = threading.Thread(target=_run_batch_grade_in_background, args=(ids_to_grade,))
    thread.start()

    return {"code": 20000, "data": {
        "message": f"AI阅卷已开始，共{len(ids_to_grade)}份卷子，请稍后刷新查看结果",
        "total": len(ids_to_grade),
    }}


# ─── 查看阅卷结果 ───

@app.get("/grading/results/{student_exam_id}")
def get_grading_results(
    student_exam_id: int,
    token: str = Header(..., alias="Authorization"),
    db: Session = Depends(get_db),
):
    """获取某位学生的阅卷结果"""
    checkToken(token)
    student_exam = db.query(StudentExam).filter(StudentExam.id == student_exam_id).first()
    if not student_exam:
        raise HTTPException(status_code=404, detail="考试记录不存在")

    grading_results = db.query(GradingResult).filter(
        GradingResult.student_exam_id == student_exam_id
    ).all()

    items = []
    for gr in grading_results:
        question = db.query(Question).filter(Question.id == gr.question_id).first()
        items.append({
            "id": gr.id,
            "question_id": gr.question_id,
            "question_order": question.order if question else None,
            "ai_score": gr.ai_score,
            "final_score": gr.final_score,
            "item_scores": gr.item_scores,
            "status": gr.status,
            "reviewed_by": gr.reviewed_by,
            "reviewed_at": gr.reviewed_at.isoformat() if gr.reviewed_at else None,
        })

    return {"code": 20000, "data": {
        "student_exam_id": student_exam_id,
        "grading_status": student_exam.grading_status,
        "ai_total_score": student_exam.ai_total_score,
        "final_total_score": student_exam.final_total_score,
        "results": items,
    }}


# ─── 人工复核 ───

@app.post("/grading/review")
def submit_review(
    review: ReviewSubmit,
    token: str = Header(..., alias="Authorization"),
    db: Session = Depends(get_db),
):
    """提交人工复核结果"""
    checkToken(token)
    gr = db.query(GradingResult).filter(GradingResult.id == review.grading_result_id).first()
    if not gr:
        raise HTTPException(status_code=404, detail="阅卷结果不存在")

    if review.score_updates:
        item_scores = json.loads(gr.item_scores) if gr.item_scores else []
        score_map = {u.item_id: u.score for u in review.score_updates}
        for item in item_scores:
            if item["item_id"] in score_map:
                item["ai_score"] = score_map[item["item_id"]]
                item["needs_review"] = False
                item["method"] = "human_review"
        gr.item_scores = json.dumps(item_scores, ensure_ascii=False)
        gr.final_score = sum(item["ai_score"] for item in item_scores)
    elif review.final_score is not None:
        gr.final_score = review.final_score
    else:
        gr.final_score = gr.ai_score

    gr.status = "reviewed"
    gr.reviewed_at = datetime.now()
    db.commit()

    _update_student_exam_score(gr.student_exam_id, db)

    return {"code": 20000, "data": {
        "id": gr.id,
        "final_score": gr.final_score,
        "status": gr.status,
    }}


@app.post("/grading/finalize/{student_exam_id}")
def finalize_grading(
    student_exam_id: int,
    token: str = Header(..., alias="Authorization"),
    db: Session = Depends(get_db),
):
    """确认并锁定某位学生的最终成绩"""
    checkToken(token)
    student_exam = db.query(StudentExam).filter(StudentExam.id == student_exam_id).first()
    if not student_exam:
        raise HTTPException(status_code=404, detail="考试记录不存在")

    grading_results = db.query(GradingResult).filter(
        GradingResult.student_exam_id == student_exam_id
    ).all()

    total = 0.0
    for gr in grading_results:
        score = gr.final_score if gr.final_score is not None else gr.ai_score
        total += score or 0
        if gr.status != "reviewed":
            gr.status = "finalized"
            gr.final_score = gr.ai_score
        else:
            gr.status = "finalized"

    student_exam.final_total_score = total
    student_exam.grading_status = "reviewed"
    db.commit()

    return {"code": 20000, "data": {
        "student_exam_id": student_exam_id,
        "final_total_score": total,
    }}


def _update_student_exam_score(student_exam_id: int, db: Session):
    """更新学生考试的总分"""
    results = db.query(GradingResult).filter(
        GradingResult.student_exam_id == student_exam_id
    ).all()

    total = 0.0
    all_reviewed = True
    for gr in results:
        if gr.final_score is not None:
            total += gr.final_score
        elif gr.ai_score is not None:
            total += gr.ai_score
        if gr.status not in ("reviewed", "finalized"):
            all_reviewed = False

    student_exam = db.query(StudentExam).filter(StudentExam.id == student_exam_id).first()
    if student_exam:
        if all_reviewed:
            student_exam.final_total_score = total
        db.commit()
