
from fastapi import Body,Depends, Request,HTTPException, status, UploadFile, File, Form, Header
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel,Field,ConfigDict 
from models import engine, Exam, Question, Student, StudentExam, StudentAnswer
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from base import app,get_db
from fastapi.exceptions import RequestValidationError
import os
import uuid
import json
import random
from login import checkUserToken,checkEdit,create_access_token
from admin import checkToken
from jose import JWTError, jwt
import shutil
from fastapi.responses import JSONResponse


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 文件上传配置
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 服务器基础URL配置
BASE_URL = os.getenv("BASE_URL", "http://106.14.190.33:8000")

def convert_to_full_url(file_url):
    """将相对路径转换为完整的URL"""
    if not file_url:
        return file_url
    if file_url.startswith('http'):
        return file_url
    return f"{BASE_URL}{file_url}"


@app.middleware("http")
async def add_cors_headers(request: Request, call_next):
    response = await call_next(request)
    if request.method == "OPTIONS":
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response


# Pydantic模型
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    phone: Optional[str] = None

class StudentCreate(BaseModel):
    name: str
    phone: str
    password: str
    avatar: Optional[str] = None
    gender: Optional[str] = None
    id_number: Optional[str] = None
    exam_number: Optional[str] = None

class StudentLogin(BaseModel):
    phone: str
    password: str


class StudentExamStart(BaseModel):
    exam_id: int


class AnswerSubmit(BaseModel):
    question_id: int
    exam_id: int
    option_answers: Optional[str] = None

class FileAnswerSubmit(BaseModel):
    question_id: int
    exam_id: int
    required_file_uuid: str  # 对应required_files中的uuid



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

# 辅助函数
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def authenticate_student(phone: str, password: str, db: Session):
    student = db.query(Student).filter(Student.phone == phone).first()
    if not student:
        return False
    if not verify_password(password, student.password):
        return False
    return student


@app.post("/student/register")
def create_student(student: StudentCreate, db: Session = Depends(get_db)):
    db_student = authenticate_student(student.phone,student.password,db)
    if db_student:
        token = create_access_token(data={"sub": db_student.id})
        return {"code":20000,"data":db_student,"token": token}

    hashed_password = get_password_hash(student.password)
    db_student = Student(
        name=student.name,
        phone=student.phone,
        password=hashed_password,
        avatar=student.avatar,
        gender=student.gender,
        id_number=student.id_number,
        exam_number=student.exam_number
    )
    db.add(db_student)
    db.commit()
    db.refresh(db_student)
    token = create_access_token(data={"sub": db_student.id})
    return {"code":20000,"data":db_student,"token": token}




async def get_current_student(token: str = Header(..., alias="Authorization"), db: Session = Depends(get_db)):
    return checkUserToken(token, db)
    

def check_exam_time(exam: Exam):
    now = datetime.now()
    if now < exam.start_time:
        return "not_started"
    elif now > exam.end_time:
        return "ended"
    else:
        return "in_progress"

def get_student_with_upcoming_exam(student: Student, db: Session):
    """获取学生数据，包含最近即将开始的考试信息"""
    from datetime import datetime
    now = datetime.now()
    
    # 查询学生绑定的考试，按考试开始时间排序，只获取未开始且即将开始的考试
    upcoming_exam = db.query(StudentExam).join(Exam).filter(
        and_(
            StudentExam.student_id == student.id,
            Exam.end_time > now,  # 考试还未结束
            StudentExam.status != "submitted"  # 学生还未交卷
        )
    ).order_by(Exam.start_time.asc()).first()
    
    # 构建学生数据，包含最近的考试信息
    student_data = {
        "id": student.id,
        "name": student.name,
        "phone": student.phone,
        "avatar": student.avatar,
        "gender": student.gender,
        "id_number": student.id_number,
        "exam_number": student.exam_number,
        "upcoming_exam": None
    }
    
    # 如果有即将开始的考试，添加到学生数据中
    if upcoming_exam:
        student_data["upcoming_exam"] = {
            "id": upcoming_exam.id,
            "exam_id": upcoming_exam.exam_id,
            "exam_name": upcoming_exam.exam.name,
            "exam_description": upcoming_exam.exam.description,
            "exam_instructions": upcoming_exam.exam.instructions,
            "exam_start_time": upcoming_exam.exam.start_time.isoformat() if upcoming_exam.exam.start_time else None,
            "exam_end_time": upcoming_exam.exam.end_time.isoformat() if upcoming_exam.exam.end_time else None,
            "exam_duration_minutes": upcoming_exam.exam.duration_minutes,
            "student_start_time": upcoming_exam.start_time.isoformat() if upcoming_exam.start_time else None,
            "student_end_time": upcoming_exam.end_time.isoformat() if upcoming_exam.end_time else None,
            "status": upcoming_exam.status
        }
    
    return student_data


@app.post("/student/login")
async def login(student: StudentLogin, db: Session = Depends(get_db)):
    db_student = authenticate_student(student.phone, student.password, db)
    if db_student:
        student_data = get_student_with_upcoming_exam(db_student, db)
        token = create_access_token(data={"sub": db_student.id})
        return {"code": 20000, "data": student_data, "token": token}
    return {"code": 1, "message": "登录失败，请检测电话跟密码是否正确"}
    

# 认证相关接口
@app.post("/student/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    student = authenticate_student(form_data.username, form_data.password, db)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect phone or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    student_data = get_student_with_upcoming_exam(student, db)
    token = create_access_token(data={"sub": student.id})
    return {"code": 20000, "data": student_data, "token": token}


@app.get("/students/me")
async def read_students_me(current_student: Student = Depends(get_current_student), db: Session = Depends(get_db)):
    return get_student_with_upcoming_exam(current_student, db)


@app.post("/students/create")
def create_student(student: StudentCreate = Depends(), token: str = Header(..., alias="Authorization"),db: Session = Depends(get_db)):
    checkToken(token)
    db_student = db.query(Student).filter(Student.phone == student.phone).first()
    if db_student:
        return {"code":404,"message":"此电话已经注册过了，不能重复提交"}
    hashed_password = get_password_hash(student.password)
    db_student = Student(
        name=student.name,
        phone=student.phone,
        password=hashed_password,
        avatar=student.avatar,
        gender=student.gender,
        id_number=student.id_number,
        exam_number=student.exam_number
    )
    db.add(db_student)
    db.commit()
    db.refresh(db_student)
    return {"code":20000,"data":db_student}

@app.put("/students/{id}")
def update_student(id:int,student: StudentCreate = Depends(), token: str = Header(..., alias="Authorization"),db: Session = Depends(get_db)):
    checkToken(token)
    db_student = db.query(Student).filter(Student.id ==id).first()
    if db_student is None:
        return {"code":404,"message":"没有找到这个学生"}
    update_data = student.dict(exclude_unset=True, exclude={"password"})
    if student.password and len(student.password)>0 and student.password!=db_student.password:
            print("Password has changed")
            h_password = get_password_hash(student.password)
            setattr(db_student, "password",  h_password)
       
    for key, value in update_data.items():
        setattr(db_student, key, value)
    db.commit()
    db.refresh(db_student)
    return {"code":20000,"data":db_student}

@app.get("/students/{id}")
def read_student(id: int, token: str = Header(..., alias="Authorization"),db: Session = Depends(get_db)):
    checkToken(token)
    student = db.query(Student).filter(Student.id == id).first()
    if student is None:
        return {"code":404,"message":"没有找到这个学生"}
    return {"code":20000,"data":student}

@app.delete("/students/{id}")
def delete_question(id:int,token: str = Header(..., alias="Authorization"),  db: Session = Depends(get_db)):
    checkToken(token)
    db_area = db.query(Student).filter(Student.id == id).first()
    if db_area is None:
           return {"code":20000}
    
    db.delete(db_area)
    db.commit()
    return {"code":20000,"data":db_area}


@app.get("/studentslist")
def read_students(page: int = 1, page_size: int = 50,token: str = Header(..., alias="Authorization"), db: Session = Depends(get_db)):
    checkToken(token)
    total = db.query(Student).count()
    students = db.query(Student).offset(page_size*(page-1)).limit(page_size).all()
    return {"code":20000,"data":{"total":total,"items":students}}



# 学生考试相关接口
@app.post("/student/exams/start")
def start_exam(
    exam_data: StudentExamStart, 
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    # 检查考试是否存在
    exam = db.query(Exam).filter(Exam.id == exam_data.exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    
    # 检查考试时间
    exam_status = check_exam_time(exam)
    if exam_status == "not_started":
        raise HTTPException(status_code=400, detail="Exam has not started yet")
    elif exam_status == "ended":
        raise HTTPException(status_code=400, detail="Exam has already ended")
    
    # 检查是否已经参加过考试
    existing_exam = db.query(StudentExam).filter(
        StudentExam.student_id == current_student.id,
        StudentExam.exam_id == exam_data.exam_id
    ).first()
    
    if existing_exam:
        if existing_exam.status == "submitted":
            raise HTTPException(status_code=400, detail="You have already submitted this exam")
        
        # 如果状态是not_started，更新为in_progress
        if existing_exam.status == "not_started":
            print("更新现有考试记录状态为in_progress")
            existing_exam.status = "in_progress"
            existing_exam.start_time = datetime.now()
            db.commit()
            db.refresh(existing_exam)
            print(f"更新后的状态: {existing_exam.status}")
        
        return existing_exam
    
    # 创建新的考试记录
    print("创建新的考试记录")
    student_exam = StudentExam(
        student_id=current_student.id,
        exam_id=exam_data.exam_id,
        start_time=datetime.now(),
        status="in_progress"
    )
    db.add(student_exam)
    db.commit()
    db.refresh(student_exam)
    print(f"新考试记录创建成功 - 状态: {student_exam.status}")
    
    # 随机选择5道题
    all_questions = db.query(Question).filter(Question.exam_id == exam_data.exam_id).all()
    if len(all_questions) >= 5:
        selected_questions = random.sample(all_questions, 5)
        # 重新排序
        for i, question in enumerate(selected_questions):
            question.order = i + 1
    else:
        selected_questions = all_questions
    
    return {
        "student_exam": student_exam,
        "questions": selected_questions
    }

@app.get("/student/exams/{exam_id}")
def get_student_exam(
    exam_id: int,
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    student_exam = db.query(StudentExam).filter(
        StudentExam.student_id == current_student.id,
        StudentExam.exam_id == exam_id
    ).first()
    
    if not student_exam:
        raise HTTPException(status_code=404, detail="Exam not found for this student")
    
    return student_exam

@app.post("/student/exams/{exam_id}/submit")
def submit_exam(
    exam_id: int,
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db)
    
):
    # 获取学生考试记录
    student_exam = db.query(StudentExam).filter(
        StudentExam.student_id == current_student.id,
        StudentExam.exam_id == exam_id
    ).first()
    
    if not student_exam:
        return {"code":404,"message":"没有开始考试"}
    
    if student_exam.status == "submitted":
        return {"code":20000}
    
    # 检查考试是否已结束
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        return {"code":404,"message":"考试不存在"}
    
    if datetime.now() > exam.end_time:
        return {"code":400,"message":"考试已经截止了"}
  
    # 更新考试状态
    student_exam.end_time = datetime.now()
    student_exam.status = "submitted"
    db.commit()

    return {"code":20000}



@app.get("/students/me")
async def read_students_me(current_student: Student = Depends(get_current_student)):
    return current_student


@app.post("/student/answers/save")
async def upload_answer(
    item: AnswerSubmit,
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    student_exam = db.query(StudentExam).filter(
        StudentExam.student_id == current_student.id,
        StudentExam.exam_id ==item.exam_id,
        StudentExam.status == "in_progress"
    ).first()
    
    if not student_exam:
        raise HTTPException(status_code=403, detail="You are not allowed to submit answers for this exam")
    
    # 检查问题和子问题是否存在
    question = db.query(Question).filter(
        Question.id == item.question_id
    ).first()
    
    if not question:
        raise HTTPException(status_code=404, detail="File upload not allowed for this question or question not found")
    
      # 保存答案
    existing_answer = db.query(StudentAnswer).filter(
        StudentAnswer.student_exam_id == student_exam.id,
        StudentAnswer.question_id == item.question_id
    ).first()

    if existing_answer:
        existing_answer.option_answers = item.option_answers
    else:
        db_answer = StudentAnswer(
            student_exam_id=student_exam.id,
            question_id=item.question_id,
            option_answers=item.option_answers
        )
        db.add(db_answer)
    
    db.commit()
    
    return {"code":20000}


@app.post("/student/answers/file")
async def upload_answer_file(
    question_id: int = Form(...),
    exam_id: int = Form(...),
    required_file_uuid: str = Form(...),  # 对应required_files中的uuid
    file: UploadFile = File(...),
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    # 检查学生是否有权限参加这个考试
    student_exam = db.query(StudentExam).filter(
        StudentExam.student_id == current_student.id,
        StudentExam.exam_id == exam_id,
        StudentExam.status == "in_progress"
    ).first()
    
    if not student_exam:
        raise HTTPException(status_code=403, detail="You are not allowed to submit answers for this exam")
    
    # 检查问题是否存在
    question = db.query(Question).filter(
        Question.id == question_id,
        Question.exam_id == exam_id
    ).first()
    
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    # 检查是否为多文件题
    if question.required_files:
        try:
            required_files = json.loads(question.required_files)
            # 验证required_file_uuid是否在required_files中
            if not any(req_file.get('uuid') == required_file_uuid for req_file in required_files):
                raise HTTPException(status_code=400, detail="Invalid required_file_uuid")
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid required_files format")
    elif not question.requires_file:
        raise HTTPException(status_code=404, detail="File upload not allowed for this question")
    
    # 保存文件
    file_ext = os.path.splitext(file.filename)[1]
    filename = f"{current_student.id}_{question_id}_{required_file_uuid}_{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    file_url = f"{BASE_URL}/uploads/{filename}"
    
    # 保存答案
    existing_answer = db.query(StudentAnswer).filter(
        StudentAnswer.student_exam_id == student_exam.id,
        StudentAnswer.question_id == question_id
    ).first()
    
    if existing_answer:
        # 获取现有的file_answers
        file_answers = {}
        if existing_answer.file_answers:
            try:
                file_answers = json.loads(existing_answer.file_answers)
            except json.JSONDecodeError:
                file_answers = {}
        
        # 删除旧文件（如果存在）
        if required_file_uuid in file_answers:
            old_file_path = os.path.join(UPLOAD_FOLDER, file_answers[required_file_uuid].split("/")[-1])
            if os.path.exists(old_file_path):
                os.remove(old_file_path)
        
        # 更新文件答案
        file_answers[required_file_uuid] = file_url
        existing_answer.file_answers = json.dumps(file_answers)
        
        # 如果是单文件题，也更新file_url（向后兼容）
        if question.requires_file and not question.required_files:
            existing_answer.file_url = file_url
    else:
        # 创建新的答案记录
        file_answers = {required_file_uuid: file_url}
        db_answer = StudentAnswer(
            student_exam_id=student_exam.id,
            question_id=question_id,
            file_url=file_url if question.requires_file and not question.required_files else None,
            file_answers=json.dumps(file_answers) if question.required_files else None
        )
        db.add(db_answer)
    
    db.commit()
    
    return {"code": 20000, "data": {"file_url": file_url}}



#返回考试跟题目数据
@app.get("/student/exams/{exam_id}/result/{student_id}")
def get_exam_result(
    exam_id: int,
    student_id:int,
    token: str = Header(..., alias="Authorization"),
    db: Session = Depends(get_db)
):
  
    checkEdit(token, student_id, db)
    # 获取学生考试记录
    student_exam = db.query(StudentExam).filter(
        StudentExam.student_id == student_id,
        StudentExam.exam_id == exam_id
    ).first()

    exam = db.query(Exam).filter(
        Exam.id == exam_id
    ).first()
    
    if not student_exam:
        raise HTTPException(status_code=404, detail="Submitted exam not found")
    
    # 获取考试的所有题目（按顺序）
    questions = db.query(Question).filter(
        Question.exam_id == exam_id
    ).order_by(Question.order).all()
    
    # 获取学生的所有答案并映射到字典（question_id -> answer）
    student_answers = db.query(StudentAnswer).filter(
        StudentAnswer.student_exam_id == student_exam.id
    ).all()
    answer_dict = {answer.question_id: answer for answer in student_answers}
    
    # 构建返回结果
    results = []
    for question in questions:
        # 查找该题目的学生答案
        student_answer = answer_dict.get(question.id)
        
        # 处理文件URL转换
        processed_file_answers = None
        processed_file_url = None
        
        if student_answer:
            # 处理file_answers（多文件题）
            if student_answer.file_answers:
                try:
                    file_answers = json.loads(student_answer.file_answers)
                    # 转换所有文件URL为完整URL
                    for key, url in file_answers.items():
                        file_answers[key] = convert_to_full_url(url)
                    processed_file_answers = json.dumps(file_answers)
                except json.JSONDecodeError:
                    processed_file_answers = student_answer.file_answers
            
            # 处理file_url（单文件题）
            if student_answer.file_url:
                processed_file_url = convert_to_full_url(student_answer.file_url)
        
        # 构建题目信息+答案的复合对象
        question_data = {
            "id": question.id,
            "order": question.order,
            "content": question.content,
            "required_files": question.required_files,
            "material_files": question.material_files,
            "file_description": question.file_description,
            "uuid": question.uuid,
            "sub_questions_str": question.sub_questions_str,
            "student_answer": {
                "id": student_answer.id if student_answer else None,
                "answer_text": student_answer.answer_text if student_answer else None,
                "option_answers": student_answer.option_answers if student_answer else None,
                "file_answers": processed_file_answers,
                "file_url": processed_file_url
            } if student_answer else None
        }
        results.append(question_data)
    
    return {
        "code": 20000,
        "data":{'exam':exam,"student_exam":student_exam,'questions':results}
    }

# 静态文件服务
from fastapi.staticfiles import StaticFiles
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

class StudentImportItem(BaseModel):
    name: str
    phone: str

class StudentImportRequest(BaseModel):
    exam_id: int
    student_strs: str
    
@app.post("/exam/import-students")
def import_students_to_exam(
    import_data: StudentImportRequest=Depends(),
    token: str = Header(..., alias="Authorization"),
    db: Session = Depends(get_db)
):
    """导入学生到考试"""
    checkToken(token)
    exam_id=import_data.exam_id
    
    # 检查考试是否存在
    exam = db.query(Exam).filter(Exam.id == import_data.exam_id).first()
    if not exam:
        return {"code": 404, "message": "考试不存在"}
    
    success_count = 0
    error_count = 0
    errors = []
    python_list = json.loads(import_data.student_strs)
        
    students: List[StudentImportItem]  = [StudentImportItem(**item) for item in python_list]
       
    for student_data in students:
        try:
            # 检查学生是否已存在
            existing_student = db.query(Student).filter(Student.phone == student_data.phone).first()
            
            if existing_student:
                # 学生已存在，直接使用
                student = existing_student
            else:
                # 学生不存在，创建新学生
                # 密码默认为电话号码后四位
                password = student_data.phone[-4:]
                hashed_password = get_password_hash(password)
                
                student = Student(
                    name=student_data.name,
                    phone=student_data.phone,
                    password=hashed_password
                )
                db.add(student)
                db.commit()
                db.refresh(student)
            
            # 检查学生是否已经绑定到这场考试
            existing_exam = db.query(StudentExam).filter(
                StudentExam.student_id == student.id,
                StudentExam.exam_id == exam_id
            ).first()
            
            if not existing_exam:
                # 创建学生考试绑定记录
                student_exam = StudentExam(
                    student_id=student.id,
                    exam_id=exam_id,
                    start_time=None,  # 学生还没有开始考试
                    status="not_started"  # 未开始状态
                )
                db.add(student_exam)
                db.commit()
                success_count += 1
            else:
                # 学生已经绑定到这场考试
                errors.append(f"学生 {student_data.name} ({student_data.phone}) 已经绑定到这场考试")
                error_count += 1
                
        except Exception as e:
            errors.append(f"导入学生 {student_data.name} ({student_data.phone}) 失败: {str(e)}")
            error_count += 1
    
    return {
        "code": 20000,
        "data": {
            "success_count": success_count,
            "error_count": error_count,
            "errors": errors,
            "message": f"成功导入 {success_count} 名学生，失败 {error_count} 名"
        }
    }
    


