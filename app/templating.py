# -*- coding: utf-8 -*-
"""Jinja2 模板实例（管理后台服务端渲染共用）。"""
from __future__ import annotations

from fastapi.templating import Jinja2Templates

from .config import BASE_DIR

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
