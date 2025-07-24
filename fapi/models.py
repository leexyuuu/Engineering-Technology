from sqlalchemy import Column,Boolean, ForeignKey,Text, Integer,String,Date,DateTime,VARCHAR, TIMESTAMP, BOOLEAN, Float, text
from database import Base,engine
from sqlalchemy.orm import relationship  # 从orm模块导入relationship

import os
import uuid
from jose import JWTError, jwt
import shutil

def generate_uuid():
    return str(uuid.uuid4())  # 返回字符串类型的 UUID
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
    
    uuid = Column(String, primary_key=True)

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
    
    uuid = Column(String, primary_key=True)

    q_uuid = Column(String, ForeignKey("questions.uuid"), nullable=False)
    order = Column(Integer, nullable=False)  # 子问题顺序
    content = Column(Text, nullable=False)
    question_type = Column(String(20), nullable=False)  # "single_choice", "multiple_choice", "text"
    score = Column(Float, default=1.0)  # 题目分值
    
    question = relationship("Question", back_populates="sub_questions")
    options = relationship("Option", back_populates="sub_question", cascade="all, delete-orphan")
    student_answers = relationship("StudentAnswer", back_populates="sub_question", cascade="all, delete-orphan")

class Option(Base):
    __tablename__ = "options"
    
    uuid= Column(String, primary_key=True)

    subq_uuid= Column(String, ForeignKey("sub_questions.uuid"), nullable=False)
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
    question_id = Column(String, ForeignKey("questions.uuid"), nullable=False)
    sub_question_id = Column(String, ForeignKey("sub_questions.uuid"), nullable=False)
    answer_text = Column(Text)  # 用于填空题
    file_url = Column(String(255))  # 文件题的文件URL
    is_correct = Column(Boolean)  # 自动判题的题目是否正确
    
    student_exam = relationship("StudentExam", back_populates="answers")
    question = relationship("Question", back_populates="student_answers")
    sub_question = relationship("SubQuestion", back_populates="student_answers")

# 创建所有表
#Base.metadata.create_all(bind=engine)
    




