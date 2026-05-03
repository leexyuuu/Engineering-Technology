import os
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 先读仓库根目录 .env，再读 fapi/.env（后者同名变量覆盖前者）；勿提交真实 .env
_fapi_dir = Path(__file__).resolve().parent
_repo_root = _fapi_dir.parent
load_dotenv(_repo_root / ".env")
load_dotenv(_fapi_dir / ".env", override=True)


def _resolve_database_url() -> str:
    explicit = os.getenv("DATABASE_URL")
    if explicit:
        return explicit
    password = os.getenv("MYSQL_PASSWORD")
    if password:
        user = os.getenv("MYSQL_USER", "root")
        host = os.getenv("MYSQL_HOST", "localhost")
        port = os.getenv("MYSQL_PORT", "3306")
        database = os.getenv("MYSQL_DATABASE", "mock_exam")
        return (
            f"mysql+pymysql://{quote_plus(user)}:{quote_plus(password)}"
            f"@{host}:{port}/{database}?charset=utf8mb4"
        )
    return (
        "mysql+pymysql://root:your_mysql_password@localhost:3306/"
        "mock_exam?charset=utf8mb4"
    )


DATABASE_URL = _resolve_database_url()

engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_recycle=1800,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
