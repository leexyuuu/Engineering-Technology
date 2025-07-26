
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

class StudentResponse(BaseModel):
    id: str
    name: str
    phone: str
    avatar: Optional[str]
    gender: Optional[str]
    id_number: Optional[str]
    exam_number: Optional[str]

class ExamCreate(BaseModel):
    name: str
    description: Optional[str] = None
    instructions: str
    start_time: datetime
    end_time: datetime
    duration_minutes: int

class ExamResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    instructions: str
    start_time: datetime
    end_time: datetime
    duration_minutes: int


class QuestionResponse(BaseModel):
    id: str
    exam_id: str
    order: int
    content: str
    requires_file: bool
    file_description: Optional[str]


class OptionCreate(BaseModel):
    content: str
    uuid:str
    subq_uuid:str
    is_correct: bool = False

class SubQuestionCreate(BaseModel):
    order: int
    content: str
    uuid:str
    q_uuid:str
    question_type: str
    score: float
    options: Optional[List[OptionCreate]]


class QuestionCreate(BaseModel):
    exam_id: str
    order: int
    uuid:str
    content: str
    requires_file: bool
    file_description: Optional[str] 
    sub_questions_str: Optional[str]
    

class SubQuestionResponse(BaseModel):
    id: str
    question_id: str
    order: int
    content: str
    question_type: str
    score: float



class OptionResponse(BaseModel):
    id: str
    sub_question_id: str
    content: str
    is_correct: bool

class StudentExamStart(BaseModel):
    exam_id: str

class StudentExamResponse(BaseModel):
    id: str
    student_id: str
    exam_id: str
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    status: str

class AnswerSubmit(BaseModel):
    question_id: str
    sub_question_id: str
    answer_text: Optional[str] = None
    file_url: Optional[str] = None

class ExamResult(BaseModel):
    total_questions: int
    correct_answers: int
    score: float
    answers: List[dict]

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

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_student(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        phone: str = payload.get("sub")
        if phone is None:
            raise credentials_exception
        token_data = TokenData(phone=phone)
    except JWTError:
        raise credentials_exception
    
    student = db.query(Student).filter(Student.phone == token_data.phone).first()
    if student is None:
        raise credentials_exception
    return student

def check_exam_time(exam: Exam):
    now = datetime.now()
    if now < exam.start_time:
        return "not_started"
    elif now > exam.end_time:
        return "ended"
    else:
        return "in_progress"

def calculate_score(student_exam: StudentExam, db: Session):
    answers = db.query(StudentAnswer).filter(StudentAnswer.student_exam_id == student_exam.id).all()
    
    total_score = 0.0
    correct_answers = 0
    
    for answer in answers:
        sub_question = db.query(SubQuestion).filter(SubQuestion.id == answer.sub_question_id).first()
        if not sub_question:
            continue
            
        if sub_question.question_type in ["single_choice", "multiple_choice"]:
            # 自动判断选择题是否正确
            if sub_question.question_type == "single_choice":
                correct_option = db.query(Option).filter(
                    Option.sub_question_id == sub_question.id,
                    Option.is_correct == True
                ).first()
                if correct_option and answer.answer_text == correct_option.id:
                    answer.is_correct = True
                    total_score += sub_question.score
                    correct_answers += 1
                else:
                    answer.is_correct = False
            else:  # multiple_choice
                correct_options = db.query(Option).filter(
                    Option.sub_question_id == sub_question.id,
                    Option.is_correct == True
                ).all()
                selected_options = set(answer.answer_text.split(",")) if answer.answer_text else set()
                correct_option_ids = {opt.id for opt in correct_options}
                
                if selected_options == correct_option_ids:
                    answer.is_correct = True
                    total_score += sub_question.score
                    correct_answers += 1
                else:
                    answer.is_correct = False
        else:
            # 填空题需要手动批改，不自动计算分数
            answer.is_correct = None
    
    db.commit()
    return {
        "total_questions": len(answers),
        "correct_answers": correct_answers,
        "score": total_score
    }




# 认证相关接口
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    student = authenticate_student(form_data.username, form_data.password, db)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect phone or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": student.phone}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/students/me")
async def read_students_me(current_student: Student = Depends(get_current_student)):
    return current_student

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
def read_exam(exam_id: str, db: Session = Depends(get_db)):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if exam is None:
        raise HTTPException(status_code=404, detail="没有找到这个考试")
    return {"code":20000,"data":exam}


@app.put("/exam/{exam_id}")
def update_exam(exam_id: str, exam: ExamCreate=Depends(),token: str = Header(..., alias="Authorization"),  db: Session = Depends(get_db)):
    checkToken(token)
    db_exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if db_exam is None:
        return {"code":404,"message":"没有找到这个考试"}
    for key, value in exam.dict(exclude_unset=True).items():
        setattr(db_exam, key, value)
    
    db.commit()
    db.refresh(db_exam)
    return {"code":20000,"data":db_exam}

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
def update_student(id:str,student: StudentCreate = Depends(), token: str = Header(..., alias="Authorization"),db: Session = Depends(get_db)):
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
def read_student(id: str, token: str = Header(..., alias="Authorization"),db: Session = Depends(get_db)):
    checkToken(token)
    student = db.query(Student).filter(Student.id == id).first()
    if student is None:
        return {"code":404,"message":"没有找到这个学生"}
    return {"code":20000,"data":student}

@app.delete("/students/{id}")
def delete_question(id: str,token: str = Header(..., alias="Authorization"),  db: Session = Depends(get_db)):
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




@app.middleware("http")
async def add_cors_headers(request: Request, call_next):
    response = await call_next(request)
    if request.method == "OPTIONS":
        response.headers["Access-Control-Allow-Origin"] = "http://localhost:9527"
        response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response
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
def update_questions(question_id: str, question: QuestionCreate=Depends(),token: str = Header(..., alias="Authorization"),  db: Session = Depends(get_db)):
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
def delete_question(question_id: str,token: str = Header(..., alias="Authorization"),  db: Session = Depends(get_db)):
    checkToken(token)
    db_area = db.query(Question).filter(Question.id == question_id).first()
    if db_area is None:
        raise HTTPException(status_code=404, detail="question not found")
    
    db.delete(db_area)
    db.commit()
    return {"code":20000,"data":db_area}


def create_subquestions_bulk(
    id:str,
    subquestions: List[SubQuestionCreate],
    db: Session = Depends(get_db)
):
    try:
        # 创建子问题对象列表
        subq_objs = []
        for sq in subquestions:
            # 创建子问题 ORM 实例（不包括 options 关系）
            subq_obj = SubQuestion(
                q_id=id,
                order=sq.order,
                content=sq.content,
                question_type=sq.question_type,
                score=sq.score
            )
            subq_objs.append(subq_obj)
            
            # 处理选项（如果存在）
            if sq.options:
                for opt in sq.options:
                    # 验证选项属于当前子问题
                    if opt.subq_uuid != sq.uuid:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Option {opt.uuid} belongs to wrong subquestion"
                        )
                    
                    # 创建选项 ORM 实例
                    opt_obj = Option(
                        uuid=opt.uuid,
                        subq_uuid=opt.subq_uuid,
                        content=opt.content,
                        is_correct=opt.is_correct
                    )
                    db.add(opt_obj)
        
        # 批量添加子问题
        db.bulk_save_objects(subq_objs)
        db.commit()
        
        # 刷新对象以获取数据库状态（如果需要返回完整数据）
        for obj in subq_objs:
            db.refresh(obj)
            
        return subquestions
    
    except Exception as e:
       # db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error creating subquestions: {str(e)}"
        )

@app.get("/exam/questions/{question_id}")
def read_question(question_id: str, db: Session = Depends(get_db)):
    question = db.query(Question).filter(Question.id == question_id).first()
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    
    return {"code":20000,"data":question}

@app.get("/exam/{exam_id}/questions")
def read_exam_questions(exam_id: str, db: Session = Depends(get_db)):
    questions = db.query(Question).filter(Question.exam_id == exam_id).order_by(Question.order).all()
    return {"code":20000,"data":{"items":  questions}}
    

# 子问题相关接口
@app.post("/subquestions/")
def create_subquestion(subquestion: SubQuestionCreate, db: Session = Depends(get_db)):
    db_subquestion = SubQuestion(**subquestion.dict())
    db.add(db_subquestion)
    db.commit()
    db.refresh(db_subquestion)
    return db_subquestion
    
# 转换函数：将字符串转换为SubQuestionCreate列表
def str_to_sub_questions(strs: str) -> Optional[List[SubQuestionCreate]]:
    try:
        # 解析JSON字符串
        data = json.loads(strs)
        
        # 验证并转换为SubQuestionCreate列表
        sub_questions = [SubQuestionCreate(**item) for item in data]
        return sub_questions
    except json.JSONDecodeError:
       return None
    except Exception as e:
      return None

@app.get("/questions/{question_id}/subquestions")
def read_question_subquestions(question_id: str, db: Session = Depends(get_db)):
    subquestions = db.query(SubQuestion).filter(SubQuestion.question_id == question_id).order_by(SubQuestion.order).all()
    return subquestions

# 选项相关接口
@app.post("/options/")
def create_option(option: OptionCreate, db: Session = Depends(get_db)):
    db_option = Option(**option.dict())
    db.add(db_option)
    db.commit()
    db.refresh(db_option)
    return db_option

@app.get("/subquestions/{subquestion_id}/options")
def read_subquestion_options(subquestion_id: str, db: Session = Depends(get_db)):
    options = db.query(Option).filter(Option.sub_question_id == subquestion_id).all()
    return options

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
        return existing_exam
    
    # 创建新的考试记录
    student_exam = StudentExam(
        student_id=current_student.id,
        exam_id=exam_data.exam_id,
        start_time=datetime.now(),
        status="in_progress"
    )
    db.add(student_exam)
    db.commit()
    db.refresh(student_exam)
    return student_exam

@app.get("/student/exams/{exam_id}")
def get_student_exam(
    exam_id: str,
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
    exam_id: str,
    answers: List[AnswerSubmit],
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    # 获取学生考试记录
    student_exam = db.query(StudentExam).filter(
        StudentExam.student_id == current_student.id,
        StudentExam.exam_id == exam_id
    ).first()
    
    if not student_exam:
        raise HTTPException(status_code=404, detail="Exam not found for this student")
    
    if student_exam.status == "submitted":
        raise HTTPException(status_code=400, detail="Exam already submitted")
    
    # 检查考试是否已结束
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    
    if datetime.now() > exam.end_time:
        raise HTTPException(status_code=400, detail="Exam has ended")
    
    # 保存所有答案
    for answer in answers:
        # 检查问题和子问题是否存在
        question = db.query(Question).filter(
            Question.id == answer.question_id,
            Question.exam_id == exam_id
        ).first()
        
        if not question:
            raise HTTPException(status_code=404, detail=f"Question {answer.question_id} not found in this exam")
        
        sub_question = db.query(SubQuestion).filter(
            SubQuestion.id == answer.sub_question_id,
            SubQuestion.question_id == answer.question_id
        ).first()
        
        if not sub_question:
            raise HTTPException(status_code=404, detail=f"SubQuestion {answer.sub_question_id} not found in question {answer.question_id}")
        
        # 检查是否已经回答过这个问题
        existing_answer = db.query(StudentAnswer).filter(
            StudentAnswer.student_exam_id == student_exam.id,
            StudentAnswer.question_id == answer.question_id,
            StudentAnswer.sub_question_id == answer.sub_question_id
        ).first()
        
        if existing_answer:
            # 更新现有答案
            existing_answer.answer_text = answer.answer_text
            existing_answer.file_url = answer.file_url
        else:
            # 创建新答案
            db_answer = StudentAnswer(
                student_exam_id=student_exam.id,
                question_id=answer.question_id,
                sub_question_id=answer.sub_question_id,
                answer_text=answer.answer_text,
                file_url=answer.file_url
            )
            db.add(db_answer)
    
    # 更新考试状态
    student_exam.end_time = datetime.now()
    student_exam.status = "submitted"
    db.commit()
    
    # 计算分数
    result = calculate_score(student_exam, db)
    result["answers"] = [
        {
            "question_id": answer.question_id,
            "sub_question_id": answer.sub_question_id,
            "is_correct": answer.is_correct
        }
        for answer in db.query(StudentAnswer).filter(
            StudentAnswer.student_exam_id == student_exam.id
        ).all()
    ]
    
    return result

@app.post("/student/answers/file")
async def upload_answer_file(
    question_id: str = Form(...),
    sub_question_id: str = Form(...),
    exam_id: str = Form(...),
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
    
    # 检查问题和子问题是否存在
    question = db.query(Question).filter(
        Question.id == question_id,
        Question.exam_id == exam_id,
        Question.requires_file == True
    ).first()
    
    if not question:
        raise HTTPException(status_code=404, detail="File upload not allowed for this question or question not found")
    
    sub_question = db.query(SubQuestion).filter(
        SubQuestion.id == sub_question_id,
        SubQuestion.question_id == question_id
    ).first()
    
    if not sub_question:
        raise HTTPException(status_code=404, detail="SubQuestion not found")
    
    # 保存文件
    file_ext = os.path.splitext(file.filename)[1]
    filename = f"{current_student.id}_{question_id}_{sub_question_id}_{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    file_url = f"/uploads/{filename}"
    
    # 保存答案
    existing_answer = db.query(StudentAnswer).filter(
        StudentAnswer.student_exam_id == student_exam.id,
        StudentAnswer.question_id == question_id,
        StudentAnswer.sub_question_id == sub_question_id
    ).first()
    
    if existing_answer:
        # 删除旧文件
        if existing_answer.file_url:
            old_file_path = os.path.join(UPLOAD_FOLDER, existing_answer.file_url.split("/")[-1])
            if os.path.exists(old_file_path):
                os.remove(old_file_path)
        existing_answer.file_url = file_url
    else:
        db_answer = StudentAnswer(
            student_exam_id=student_exam.id,
            question_id=question_id,
            sub_question_id=sub_question_id,
            file_url=file_url
        )
        db.add(db_answer)
    
    db.commit()
    
    return {"file_url": file_url}

@app.get("/student/exams/{exam_id}/result", response_model=ExamResult)
def get_exam_result(
    exam_id: str,
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    student_exam = db.query(StudentExam).filter(
        StudentExam.student_id == current_student.id,
        StudentExam.exam_id == exam_id,
        StudentExam.status == "submitted"
    ).first()
    
    if not student_exam:
        raise HTTPException(status_code=404, detail="Submitted exam not found")
    
    answers = db.query(StudentAnswer).filter(
        StudentAnswer.student_exam_id == student_exam.id
    ).all()
    
    correct_answers = sum(1 for answer in answers if answer.is_correct)
    total_score = sum(
        answer.sub_question.score 
        for answer in answers 
        if answer.is_correct and answer.sub_question
    )
    
    return {
        "total_questions": len(answers),
        "correct_answers": correct_answers,
        "score": total_score,
        "answers": [
            {
                "question_id": answer.question_id,
                "sub_question_id": answer.sub_question_id,
                "is_correct": answer.is_correct
            }
            for answer in answers
        ]
    }

# 静态文件服务
from fastapi.staticfiles import StaticFiles
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")