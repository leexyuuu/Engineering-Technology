# -*- coding: utf-8 -*-
"""应用入口（阶段4）：路由挂载、lifespan 初始化、统一异常处理。

lifespan 启动顺序（依赖链）：
    ① init_db 建表（含阶段4 新表：agent_decision_logs / selection_applications）
    ② seed_demo_users 演示账号 → ③ init_default 提示词模板（含旧默认平滑升级）
    ④ kb_service.seed_if_empty 种子文档 → ⑤ retrieval.load_or_build 索引装载
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .api.admin_app import router as admin_app_router
from .api.admin_audit import router as admin_audit_router
from .api.admin_kb import router as admin_kb_router
from .api.admin_prompt import router as admin_prompt_router
from .api.auth import router as auth_router
from .api.chat import router as chat_router
from .db import init_db
from .schemas import ApiError, ErrorCode
from .security import seed_demo_users
from .services.kb_service import kb_service
from .services.prompt_service import init_default
from .services.retrieval_service import retrieval

# 静态资源目录（项目根 /static：学生聊天页与样式）
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动初始化（建表 → 种子 → 索引）；关停时无需清理（SQLite/FAISS 均落盘）。"""
    await init_db()
    await seed_demo_users()
    await init_default()
    await kb_service.seed_if_empty()
    await retrieval.load_or_build()
    yield


app = FastAPI(title="排课选课与教务协作智能体系统", version="0.4.0", lifespan=lifespan)

# ── 路由 ──
app.include_router(auth_router)             # 登录/当前用户
app.include_router(chat_router)             # 学生/教师问答（SSE，Agent 循环）+ 申请确认
app.include_router(admin_kb_router)         # 知识库管理（admin）+ 登录页
app.include_router(admin_prompt_router)     # 提示词模板管理（admin）
app.include_router(admin_audit_router)      # 对话审计（admin）
app.include_router(admin_app_router)        # 选课申请审核（admin）

# ── 静态资源与学生聊天页 ──
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
async def index():
    """学生聊天页（登录校验由前端 /api/auth/me 完成）。"""
    return FileResponse(STATIC_DIR / "index.html")


# ── 统一异常处理：任何错误都以 {code, message} 中文结构返回 ──

@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError):
    """业务错误（含错误码表中的所有可预期错误）。"""
    return JSONResponse(status_code=exc.status_code,
                        content={"code": exc.code, "message": exc.message})


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """参数校验错误 → 40001（中文提示，不暴露内部细节）。"""
    return JSONResponse(status_code=400,
                        content={"code": ErrorCode.BAD_REQUEST[0],
                                 "message": ErrorCode.BAD_REQUEST[2]})
