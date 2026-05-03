from fastapi import FastAPI
from sqlalchemy import inspect, text
from database import SessionLocal, engine, Base
import admin
import routers.content,routers.cell,routers.city,routers.area,routers.role,routers.user,routers.Message,routers.Comment,routers.Reply,routers.exam,routers.student
import routers.grading
from base import app, get_db

# 创建所有表
Base.metadata.create_all(bind=engine)


def run_migrations():
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    if 'questions' in tables:
        columns = [col['name'] for col in inspector.get_columns('questions')]
        if 'reference_answer' not in columns:
            with engine.begin() as conn:
                conn.execute(text('ALTER TABLE questions ADD COLUMN reference_answer TEXT'))

    if 'student_exams' in tables:
        columns = [col['name'] for col in inspector.get_columns('student_exams')]
        with engine.begin() as conn:
            if 'ai_total_score' not in columns:
                conn.execute(text('ALTER TABLE student_exams ADD COLUMN ai_total_score FLOAT'))
            if 'final_total_score' not in columns:
                conn.execute(text('ALTER TABLE student_exams ADD COLUMN final_total_score FLOAT'))
            if 'grading_status' not in columns:
                conn.execute(text("ALTER TABLE student_exams ADD COLUMN grading_status VARCHAR(20) DEFAULT 'not_graded'"))


run_migrations()


@app.get("/")
def read_root():
    return {"Hello": "World"}
