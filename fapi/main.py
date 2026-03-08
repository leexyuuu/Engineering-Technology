from fastapi import FastAPI
from sqlalchemy import inspect, text
from database import SessionLocal, engine, Base
import admin
import routers.content,routers.cell,routers.city,routers.area,routers.role,routers.user,routers.Message,routers.Comment,routers.Reply,routers.exam,routers.student
from base import app,get_db
# 创建所有表
Base.metadata.create_all(bind=engine)

def run_migrations():
    inspector = inspect(engine)
    if 'questions' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('questions')]
        if 'reference_answer' not in columns:
            with engine.begin() as conn:
                conn.execute(text('ALTER TABLE questions ADD COLUMN reference_answer TEXT'))

run_migrations()


@app.get("/")
def read_root():
    return {"Hello": "World"}
 
@app.get("/items/{item_id}")
def read_item(item_id: int, q: str = None):
    return test.read_item(item_id,q)