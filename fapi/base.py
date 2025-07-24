from fastapi import FastAPI
from database import SessionLocal, engine, Base
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()
from fastapi.middleware.cors import CORSMiddleware
origins = [
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 依赖项：获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()