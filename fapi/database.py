from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./test.db"

# 创建数据库引擎
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

# 创建会话
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基础类
Base = declarative_base()


ef generate_uuid():
    return str(uuid.uuid4())

class Exam(Base):
    __tablename__ = "exams"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    instructions = Column(Text, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, nullable=False)  # 考试时长(分钟)
    
    questions = relationship("Question", back_populates="exam", cascade="all, delete-orphan")
    student_exams = relationship("StudentExam", back_populates="exam", cascade="all, delete-orphan")

class Question(Base):
    __tablename__ = "questions"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    exam_id = Column(String, ForeignKey("exams.id"), nullable=False)
    order = Column(Integer, nullable=False)  # 题目顺序
    content = Column(Text, nullable=False)
    requires_file = Column(Boolean, default=False)
    file_description = Column(Text)
    
    exam = relationship("Exam", back_populates="questions")
    sub_questions = relationship("SubQuestion", back_populates="question", cascade="all, delete-orphan")
    student_answers = relationship("StudentAnswer", back_populates="question", cascade="all, delete-orphan")

class SubQuestion(Base):
    __tablename__ = "sub_questions"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    question_id = Column(String, ForeignKey("questions.id"), nullable=False)
    order = Column(Integer, nullable=False)  # 子问题顺序
    content = Column(Text, nullable=False)
    question_type = Column(String(20), nullable=False)  # "single_choice", "multiple_choice", "text"
    score = Column(Float, default=1.0)  # 题目分值
    
    question = relationship("Question", back_populates="sub_questions")
    options = relationship("Option", back_populates="sub_question", cascade="all, delete-orphan")
    student_answers = relationship("StudentAnswer", back_populates="sub_question", cascade="all, delete-orphan")

class Option(Base):
    __tablename__ = "options"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    sub_question_id = Column(String, ForeignKey("sub_questions.id"), nullable=False)
    content = Column(Text, nullable=False)
    is_correct = Column(Boolean, default=False)
    
    sub_question = relationship("SubQuestion", back_populates="options")

class Student(Base):
    __tablename__ = "students"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(50), nullable=False)
    avatar = Column(String(255))  # 头像URL
    gender = Column(String(10))
    id_number = Column(String(20))  # 证件号码
    exam_number = Column(String(20))  # 准考证号
    phone = Column(String(20), unique=True, nullable=False)
    password = Column(String(255), nullable=False)  # 存储加密后的密码
    
    exams = relationship("StudentExam", back_populates="student", cascade="all, delete-orphan")

class StudentExam(Base):
    __tablename__ = "student_exams"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    student_id = Column(String, ForeignKey("students.id"), nullable=False)
    exam_id = Column(String, ForeignKey("exams.id"), nullable=False)
    start_time = Column(DateTime)  # 学生开始考试时间
    end_time = Column(DateTime)  # 学生提交时间
    status = Column(String(20), default="not_started")  # not_started, in_progress, submitted
    
    student = relationship("Student", back_populates="exams")
    exam = relationship("Exam", back_populates="student_exams")
    answers = relationship("StudentAnswer", back_populates="student_exam", cascade="all, delete-orphan")

class StudentAnswer(Base):
    __tablename__ = "student_answers"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    student_exam_id = Column(String, ForeignKey("student_exams.id"), nullable=False)
    question_id = Column(String, ForeignKey("questions.id"), nullable=False)
    sub_question_id = Column(String, ForeignKey("sub_questions.id"), nullable=False)
    answer_text = Column(Text)  # 用于填空题
    file_url = Column(String(255))  # 文件题的文件URL
    is_correct = Column(Boolean)  # 自动判题的题目是否正确
    
    student_exam = relationship("StudentExam", back_populates="answers")
    question = relationship("Question", back_populates="student_answers")
    sub_question = relationship("SubQuestion", back_populates="student_answers")

# 创建所有表
Base.metadata.create_all(bind=engine)