
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
import zipfile
import tempfile
import re
from urllib.parse import quote
from admin import checkToken
from jose import JWTError, jwt
import shutil
from fastapi.responses import JSONResponse, FileResponse


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
    
    # 设置Content-Disposition头强制下载
    return FileResponse(
        file_path,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

def clean_filename(name):
    """清理文件名中的非法字符"""
    # Windows和Unix系统不允许的字符
    illegal_chars = r'[<>:"/\\|?*]'
    return re.sub(illegal_chars, '_', name)

def extract_filename_from_url(url):
    """从URL中提取文件名"""
    if not url:
        return None
    # 处理完整URL: https://51ai-exam.com/uploads/filename
    # 处理相对路径: /uploads/filename
    parts = url.split('/')
    filename = parts[-1] if parts else None
    return filename

@app.get("/exam/{exam_id}/student/{student_id}/download-files")
async def download_student_files(
    exam_id: int,
    student_id: int,
    token: str = Header(..., alias="Authorization"),
    db: Session = Depends(get_db)
):
    """下载指定学生在指定考试中上传的所有文件"""
    checkToken(token)
    
    # 获取考试信息
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="考试不存在")
    
    # 获取学生信息
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    
    # 获取学生考试记录
    student_exam = db.query(StudentExam).filter(
        StudentExam.exam_id == exam_id,
        StudentExam.student_id == student_id
    ).first()
    
    if not student_exam:
        raise HTTPException(status_code=404, detail="该学生未参加此考试")
    
    # 获取该学生的所有答案
    student_answers = db.query(StudentAnswer).filter(
        StudentAnswer.student_exam_id == student_exam.id
    ).all()
    
    if not student_answers:
        raise HTTPException(status_code=404, detail="该学生没有提交任何答案文件")
    
    # 获取所有题目信息
    questions = db.query(Question).filter(Question.exam_id == exam_id).order_by(Question.order).all()
    question_dict = {q.id: q for q in questions}
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    zip_filename = None
    
    try:
        # 创建学生文件夹（使用清理后的考试名称、姓名和手机号）
        clean_exam_name = clean_filename(exam.name)
        clean_student_name = clean_filename(student.name)
        clean_phone = clean_filename(student.phone)
        student_folder = os.path.join(temp_dir, f"{clean_exam_name}_{clean_student_name}_{clean_phone}")
        os.makedirs(student_folder, exist_ok=True)
        
        file_count = 0
        
        # 处理每个答案的文件
        for answer in student_answers:
            question = question_dict.get(answer.question_id)
            if not question:
                continue
            
            question_order = question.order if question.order else answer.question_id
            question_content = question.content[:50] if question.content else f"题目{question_order}"  # 截取前50个字符作为文件名
            
            # 创建题号文件夹
            question_folder = os.path.join(student_folder, f"题目{question_order}")
            os.makedirs(question_folder, exist_ok=True)
            
            # 处理多文件答案 (file_answers)
            if answer.file_answers:
                try:
                    file_answers = json.loads(answer.file_answers)
                    if isinstance(file_answers, dict):
                        # 获取题目的required_files信息用于生成文件名
                        required_files_info = {}
                        if question.required_files:
                            try:
                                required_files_list = json.loads(question.required_files)
                                if isinstance(required_files_list, list):
                                    for req_file in required_files_list:
                                        if 'uuid' in req_file and 'name' in req_file:
                                            required_files_info[req_file['uuid']] = req_file['name']
                            except json.JSONDecodeError:
                                pass
                        
                        # 为每个文件创建有意义的文件名
                        file_index = 0
                        for file_uuid, file_url in file_answers.items():
                            file_index += 1
                            filename = extract_filename_from_url(file_url)
                            if not filename:
                                continue
                            
                            source_file = os.path.join(UPLOAD_FOLDER, filename)
                            if not os.path.exists(source_file):
                                continue
                            
                            # 生成目标文件名（去掉题号前缀，因为已经在题号文件夹中）
                            if file_uuid in required_files_info:
                                # 使用题目中定义的文件名
                                req_file_name = clean_filename(required_files_info[file_uuid])
                                # 检查req_file_name是否已经包含扩展名
                                req_file_ext = os.path.splitext(req_file_name)[1]
                                if req_file_ext:
                                    # 如果已经包含扩展名，直接使用
                                    target_filename = req_file_name
                                else:
                                    # 如果没有扩展名，从实际文件名中提取并添加
                                    file_ext = os.path.splitext(filename)[1]
                                    target_filename = f"{req_file_name}{file_ext}"
                            else:
                                # 使用默认文件名
                                file_ext = os.path.splitext(filename)[1]
                                target_filename = f"第{file_index}个文件{file_ext}"
                            
                            target_file = os.path.join(question_folder, target_filename)
                            
                            # 如果文件名冲突，添加序号
                            if os.path.exists(target_file):
                                base_name, ext = os.path.splitext(target_filename)
                                counter = 1
                                while os.path.exists(target_file):
                                    target_filename = f"{base_name}_{counter}{ext}"
                                    target_file = os.path.join(question_folder, target_filename)
                                    counter += 1
                            
                            shutil.copy2(source_file, target_file)
                            file_count += 1
                except json.JSONDecodeError:
                    pass
            
            # 处理单文件答案 (file_url) - 向后兼容
            if answer.file_url:
                filename = extract_filename_from_url(answer.file_url)
                if filename:
                    source_file = os.path.join(UPLOAD_FOLDER, filename)
                    if os.path.exists(source_file):
                        file_ext = os.path.splitext(filename)[1]
                        target_filename = f"文件{file_ext}"
                        target_file = os.path.join(question_folder, target_filename)
                        
                        # 如果文件名冲突，添加序号
                        if os.path.exists(target_file):
                            base_name, ext = os.path.splitext(target_filename)
                            counter = 1
                            while os.path.exists(target_file):
                                target_filename = f"{base_name}_{counter}{ext}"
                                target_file = os.path.join(question_folder, target_filename)
                                counter += 1
                        
                        shutil.copy2(source_file, target_file)
                        file_count += 1
        
        if file_count == 0:
            raise HTTPException(status_code=404, detail="该学生没有可下载的文件")
        
        # 创建ZIP文件（文件名格式：{考试名称}_{学生姓名}_{手机号}.zip）
        zip_filename = f"{clean_exam_name}_{clean_student_name}_{clean_phone}.zip"
        zip_path = os.path.join(temp_dir, zip_filename)
        
        # 使用UTF-8编码创建ZIP文件（Python 3.7+支持）
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 设置文件名编码为UTF-8
            for root, dirs, files in os.walk(student_folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    # ZIP文件内文件名保持UTF-8（Python 3.7+默认支持）
                    zipf.write(file_path, arcname)
        
        # 对文件名进行URL编码以用于HTTP头（RFC 5987格式）
        encoded_filename = quote(zip_filename, safe='')
        
        # 返回ZIP文件
        # 注意：不传递filename参数，避免编码问题，只在headers中设置
        return FileResponse(
            zip_path,
            media_type='application/zip',
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
            }
        )
    
    except Exception as e:
        # 清理临时文件
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        raise HTTPException(status_code=500, detail=f"生成下载文件失败: {str(e)}")

