
from fastapi import Body,Depends, Request,HTTPException, status, UploadFile, File, Form, Header
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel,Field,ConfigDict 
from models import engine, Exam, Question, Student, StudentExam, StudentAnswer
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from base import app,get_db
from fastapi.exceptions import RequestValidationError
import os
import uuid
import json
from admin import checkToken
from jose import JWTError, jwt
import shutil
from fastapi.responses import JSONResponse

# 安全相关配置
SECRET_KEY = "mysaasfad435435dggfyf4556dsfecretkey"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 3000

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# 文件上传配置
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.middleware("http")
async def add_cors_headers(request: Request, call_next):
    response = await call_next(request)
    if request.method == "OPTIONS":
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response

class ExamCreate(BaseModel):
    name: str
    description: Optional[str] = None
    instructions: str
    start_time: datetime
    end_time: datetime
    duration_minutes: int

class QuestionCreate(BaseModel):
    exam_id: int
    order: int
    uuid:str
    content: str
    requires_file: bool
    file_description: Optional[str] 
    sub_questions_str: Optional[str]
    required_files: Optional[str]  # JSON格式的多文件要求
    material_files: Optional[str]  # JSON格式的资料文件


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for error in exc.errors():
        loc = ".".join(str(l) for l in error["loc"])
        errors.append({
            "location": "query" if loc.startswith("query") else "body",
            "field": loc.replace("query.", "").replace("body.", ""),
            "message": error["msg"],
            "type": error["type"]
        })
    
    return JSONResponse(
        status_code=422,
        content={
            "detail": "参数验证失败",
            "errors": errors,
            "suggestion": "请检查查询参数和请求体格式"
        }
    )



# 考试相关接口
@app.post("/exam/create")
def create_exam(exam: ExamCreate=Depends(), token: str = Header(..., alias="Authorization"), db: Session = Depends(get_db)):
    checkToken(token)
    db_exam = Exam(**exam.dict())
    db.add(db_exam)
    db.commit()
    db.refresh(db_exam)
    return {"code":20000,"data":db_exam}

@app.get("/exam/list")
def read_exams(page: int = 1, page_size: int = 20, db: Session = Depends(get_db)):
    total = db.query(Exam).count()
    exams = db.query(Exam).offset(page_size*(page-1)).limit(page_size).all()
    return {"code":20000,"data":{"total":total,"items": exams}}


@app.get("/exam/{exam_id}")
def read_exam(exam_id: int, db: Session = Depends(get_db)):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if exam is None:
        raise HTTPException(status_code=404, detail="没有找到这个考试")
    return {"code":20000,"data":exam}


@app.put("/exam/{exam_id}")
def update_exam(exam_id: int, exam: ExamCreate=Depends(),token: str = Header(..., alias="Authorization"),  db: Session = Depends(get_db)):
    checkToken(token)
    db_exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if db_exam is None:
        return {"code":404,"message":"没有找到这个考试"}
    for key, value in exam.dict(exclude_unset=True).items():
        setattr(db_exam, key, value)
    
    db.commit()
    db.refresh(db_exam)
    return {"code":20000,"data":db_exam}

# 题目相关接口
@app.post("/exam/questions/create")
def create_question(question: QuestionCreate=Depends(), token: str = Header(..., alias="Authorization"), db: Session = Depends(get_db)):
    checkToken(token)

    db_question = Question(**question.dict())
   # db_question.sub_questions=str_to_sub_questions(question.sub_questions_str)
    db.add(db_question)
    db.commit()
    db.refresh(db_question)

    return {"code":20000,"data":db_question}

@app.put("/exam/questions/{question_id}")
def update_questions(question_id:int, question: QuestionCreate=Depends(),token: str = Header(..., alias="Authorization"),  db: Session = Depends(get_db)):
    checkToken(token)
    db_exam = db.query(Question).filter(Question.id == question_id).first()
    if db_exam is None:
        raise HTTPException(status_code=404, detail="Exam not found")
    for key, value in question.dict(exclude_unset=True).items():
        setattr(db_exam, key, value)
    
    db.commit()
    db.refresh(db_exam)
    return {"code":20000,"data":db_exam}

@app.delete("/exam/questions/{question_id}")
def delete_question(question_id:int,token: str = Header(..., alias="Authorization"),  db: Session = Depends(get_db)):
    checkToken(token)
    db_area = db.query(Question).filter(Question.id == question_id).first()
    if db_area is None:
        raise HTTPException(status_code=404, detail="question not found")
    
    db.delete(db_area)
    db.commit()
    return {"code":20000,"data":db_area}



@app.get("/exam/questions/{question_id}")
def read_question(question_id:int, db: Session = Depends(get_db)):
    question = db.query(Question).filter(Question.id == question_id).first()
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    
    return {"code":20000,"data":question}

@app.get("/exam/{exam_id}/questions")
def read_exam_questions(exam_id:int, db: Session = Depends(get_db)):
    questions = db.query(Question).filter(Question.exam_id == exam_id).order_by(Question.order).all()
    return {"code":20000,"data":{"items":  questions}}

@app.get("/exam/{exam_id}/students")
def read_exam_students(exam_id:int, page: int = 1, page_size: int = 20, db: Session = Depends(get_db)):
    """获取参加某场考试的学生列表，包含考试结果"""
    # 查询该考试的所有学生考试记录
    total = db.query(StudentExam).filter(StudentExam.exam_id == exam_id).count()
    student_exams = db.query(StudentExam).filter(StudentExam.exam_id == exam_id)\
        .offset(page_size * (page - 1)).limit(page_size).all()
    
    # 构建返回数据，包含学生信息和考试结果
    result = []
    for se in student_exams:
        student_data = {
            "id": se.student.id,
            "name": se.student.name,
            "phone": se.student.phone,
            "avatar": se.student.avatar,
            "gender": se.student.gender,
            "id_number": se.student.id_number,
            "exam_number": se.student.exam_number,
            # 考试结果信息
            "student_exam_id": se.id,
            "start_time": se.start_time,
            "end_time": se.end_time,
            "status": se.status,
            "duration_minutes": None  # 计算实际考试时长
        }
        
        # 计算考试时长
        if se.start_time and se.end_time:
            duration = se.end_time - se.start_time
            student_data["duration_minutes"] = int(duration.total_seconds() / 60)
        
        result.append(student_data)
    
    return {"code": 20000, "data": {"total": total, "items": result}}

# 文件上传接口
@app.post("/exam/upload-file")
async def upload_file(
    file: UploadFile = File(...),
    token: str = Header(..., alias="Authorization")
):
    """上传文件接口"""
    #checkToken(token)
    
    # 确保上传目录存在
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    
    # 生成唯一文件名
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
    
    try:
        # 保存文件
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 返回文件URL
        file_url = f"/uploads/{unique_filename}"
        
        return {
            "code": 20000,
            "data": {
                "filename": file.filename,
                "url": file_url,
                "size": os.path.getsize(file_path)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")

@app.get("/uploads/{filename}")
async def get_file(filename: str):
    """获取上传的文件"""
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")
    
    from fastapi.responses import FileResponse
    return FileResponse(file_path)
    
