from fastapi import FastAPI
from database import SessionLocal, engine, Base
import admin
import routers.content,routers.cell,routers.city,routers.area,routers.role,routers.user,routers.Message,routers.Comment,routers.Reply
from base import app,get_db
# 创建所有表
Base.metadata.create_all(bind=engine)


@app.get("/")
def read_root():
    return {"Hello": "World"}
 
@app.get("/items/{item_id}")
def read_item(item_id: int, q: str = None):
    return test.read_item(item_id,q)