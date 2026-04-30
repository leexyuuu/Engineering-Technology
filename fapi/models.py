from sqlalchemy import Column,Boolean, ForeignKey,Text, Integer,String,Date,DateTime,VARCHAR, TIMESTAMP, BOOLEAN, Float, text
from database import Base,engine
from sqlalchemy.orm import relationship  # 从orm模块导入relationship

import os
import uuid
from jose import JWTError, jwt
import shutil
import time

def generate_uuid():
   # new_uuid = uuid.uuid4()
    return str(time.time())  # 返回字符串类型的 UUID
class RoleModel(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(32), index=True, comment='key')
    description = Column(String(128), index=True, comment='描述')
    name = Column(String(32), index=True, comment='名字')

class UserModel(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    union_id = Column(String(64),unique=True, comment='微信开放平台下的用户唯一标识')
    open_id = Column(String(64),unique=True, comment='微信openid')
    nick_name = Column(String(32), index=True, comment='昵称')
    avatar_url = Column(String(255), server_default=text("''"), comment='头像')
    summary=Column(String,server_default=text("''"))
    session_key= Column(String,server_default=text("''"))
    cityId=Column(Integer,index=True)
    areaId=Column(Integer,index=True)
    cellId=Column(Integer,index=True)
    gender=Column(Integer,server_default=text("'0'"), comment='状态；0:未知 1:男 2:女')
    birth=Column(Date, comment='生日')
    phone = Column(String(11), comment='手机号')
    wechat=Column(String(30), comment='微信号')
    type=Column(Integer,index=True)
    status = Column(String(64), server_default=text("'show'"))
    last_login = Column(TIMESTAMP, comment='上次登录时间')
    delete_at = Column(TIMESTAMP, comment='删除时间')
    created_at = Column(TIMESTAMP, comment='创建时间')
    updated_at = Column(TIMESTAMP, comment='更新时间')
    address=Column(String,server_default=text("''"))

class CellModel(Base):
    __tablename__ = "cells"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(32),index=True)
    summary=Column(String)
    icon=Column(String(255), server_default=text("''"), comment='icon')
    index=Column(Integer)
    status= Column(String(32),server_default=text("'show'"),index=True)
    cityId=Column(Integer)
    areaId=Column(Integer)

class AreaModel(Base):
    __tablename__ = "areas"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(32),index=True)
    summary=Column(String)
    icon=Column(String(255), server_default=text("''"), comment='icon')
    index=Column(Integer)
    status= Column(String(32),server_default=text("'show'"),index=True)
    cityId=Column(Integer)

class CityModel(Base):
    __tablename__ = "citys"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(32),index=True)
    summary=Column(String)
    icon=Column(String(255), server_default=text("''"), comment='icon')
    index=Column(Integer)
    status= Column(String(32),server_default=text("'show'"),index=True)

class ContentModel(Base):
    __tablename__ = "contents"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    content=Column(String)
    timestamp=Column(TIMESTAMP)
    startTime=Column(TIMESTAMP)
    endTime=Column(TIMESTAMP)
    updateTime=Column(TIMESTAMP)
    comment_disabled=Column(BOOLEAN)
    userId=Column(Integer,index=True)
    type=Column(Integer,index=True)
    like_count=Column(Integer)
    collect_count=Column(Integer)
    images=Column(String)
    cityId=Column(Integer,index=True)
    cellId=Column(Integer,index=True)
    areaId=Column(Integer,index=True)
    address=Column(String)
    extras=Column(String)
    labels=Column(String)
    status= Column(String(32),server_default=text("'show'"),index=True)

class CommentModel(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True, index=True)
    content=Column(String)
    contentId=Column(Integer,index=True)
    timestamp=Column(TIMESTAMP)
    isAutor=Column(BOOLEAN)
    updateTime=Column(TIMESTAMP)
    userId=Column(Integer,index=True)
    top=Column(BOOLEAN,index=True)
    images=Column(String)
    status= Column(String(32),server_default=text("'show'"),index=True)

class MessageModel(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    content=Column(String)
    value=Column(Integer,index=True)
    timestamp=Column(TIMESTAMP)
    ready=Column(BOOLEAN)
    fromUserId=Column(Integer)
    userId=Column(Integer,index=True)
    type=Column(Integer,index=True)
    images=Column(String)
    
class MessageBoxModel(Base):
    __tablename__ = "messagegroups"
    id = Column(Integer, primary_key=True, index=True)
    content=Column(String)
    value=Column(Integer,index=True)
    timestamp=Column(TIMESTAMP)
    userId=Column(Integer,index=True)
    type=Column(Integer,index=True)
    count=Column(Integer)
    images=Column(String)

class LikeModel(Base):
    __tablename__ = "likes"
    id = Column(Integer, primary_key=True, index=True)
    value=Column(Integer,index=True)
    timestamp=Column(TIMESTAMP)
    userId=Column(Integer,index=True)
    type=Column(Integer,index=True)

class ReplyModel(Base):
    __tablename__ = "replys"
    id = Column(Integer, primary_key=True, index=True)
    content=Column(String)
    commentId=Column(Integer,index=True)
    contentId=Column(Integer)
    timestamp=Column(TIMESTAMP)
    userId=Column(Integer,index=True)
    isAuthor=Column(BOOLEAN)
    atUserId=Column(Integer)
    images=Column(String)
    status= Column(String(32),server_default=text("'show'"),index=True)



class Exam(Base):
    __tablename__ = "exams"
    id = Column(Integer, primary_key=True, index=True)

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
    
    id = Column(Integer, primary_key=True, index=True)

    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False)
    order = Column(Integer, nullable=False)  # 题目顺序
    content = Column(Text, nullable=False)
    requires_file = Column(Boolean, default=False)
    file_description = Column(Text)
    uuid = Column(Text)
    sub_questions_str = Column(Text().with_variant(Text(4294967295), 'mysql'))
    # 多文件答题相关字段
    required_files = Column(Text().with_variant(Text(4294967295), 'mysql'))  # JSON格式存储多个文件要求
    # 资料文件相关字段
    material_files = Column(Text().with_variant(Text(4294967295), 'mysql'))  # JSON格式存储资料文件
    reference_answer = Column(Text, nullable=True)
    exam = relationship("Exam", back_populates="questions")
    


class Student(Base):
    __tablename__ = "students"
    
    id = Column(Integer, primary_key=True, index=True)

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
    
    id = Column(Integer, primary_key=True, index=True)

    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False)
    start_time = Column(DateTime)  # 学生开始考试时间
    end_time = Column(DateTime)  # 学生提交时间
    status = Column(String(20), default="not_started")  # not_started, in_progress, submitted
    ai_total_score = Column(Float)
    final_total_score = Column(Float)
    grading_status = Column(String(20), default="not_graded")  # not_graded, ai_grading, ai_graded, reviewed
    
    student = relationship("Student", back_populates="exams")
    exam = relationship("Exam", back_populates="student_exams")
    answers = relationship("StudentAnswer", back_populates="student_exam", cascade="all, delete-orphan")

class StudentAnswer(Base):
    __tablename__ = "student_answers"
    
    id =  Column(Integer, primary_key=True, index=True)
    student_exam_id = Column(Integer, ForeignKey("student_exams.id"), nullable=False)
    answer_text = Column(Text)  # 用于填空题
    question_id=Column(Integer, ForeignKey("questions.id"), nullable=False)
    file_url = Column(String(255))  # 文件题的文件URL（向后兼容）
    option_answers = Column(Text().with_variant(Text(4294967295), 'mysql')) 
    # 多文件答题相关字段
    file_answers = Column(Text().with_variant(Text(4294967295), 'mysql'))  # JSON格式存储多个文件答案
    
    student_exam = relationship("StudentExam", back_populates="answers")
    grading_result = relationship("GradingResult", back_populates="student_answer", uselist=False)


class GradingRubric(Base):
    """评分细则表：存储每道题的标准答案和评分要点"""
    __tablename__ = "grading_rubrics"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False, unique=True)
    rubric_items = Column(Text().with_variant(Text(4294967295), 'mysql'), nullable=False)
    total_score = Column(Float, nullable=False)
    grading_type = Column(String(20), nullable=False, default="mixed")

    question = relationship("Question")


class GradingResult(Base):
    """阅卷结果表：存储AI评分和人工复核结果"""
    __tablename__ = "grading_results"

    id = Column(Integer, primary_key=True, index=True)
    student_answer_id = Column(Integer, ForeignKey("student_answers.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    student_exam_id = Column(Integer, ForeignKey("student_exams.id"), nullable=False)
    ai_score = Column(Float)
    final_score = Column(Float)
    item_scores = Column(Text().with_variant(Text(4294967295), 'mysql'))
    status = Column(String(20), default="pending")
    reviewed_by = Column(Integer)
    reviewed_at = Column(DateTime)

    student_answer = relationship("StudentAnswer", back_populates="grading_result")
    question = relationship("Question")
    student_exam = relationship("StudentExam")


# 创建所有表
#Base.metadata.create_all(bind=engine)
    




