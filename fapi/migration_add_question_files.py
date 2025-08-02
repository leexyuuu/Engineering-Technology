#!/usr/bin/env python3
"""
数据库迁移脚本：为Question表添加多文件答题和资料文件字段
"""

from sqlalchemy import create_engine, text
from database import Base
from models import Question
import os

# 数据库连接配置
DATABASE_URL = "sqlite:///./test.db"  # 根据实际情况修改

def migrate():
    """执行数据库迁移"""
    engine = create_engine(DATABASE_URL)
    
    try:
        # 添加新字段
        with engine.connect() as conn:
            # 检查字段是否已存在
            result = conn.execute(text("PRAGMA table_info(questions)"))
            columns = [row[1] for row in result.fetchall()]
            
            # 添加required_files字段
            if 'required_files' not in columns:
                conn.execute(text("ALTER TABLE questions ADD COLUMN required_files TEXT"))
                print("已添加 required_files 字段")
            
            # 添加material_files字段
            if 'material_files' not in columns:
                conn.execute(text("ALTER TABLE questions ADD COLUMN material_files TEXT"))
                print("已添加 material_files 字段")
            
            conn.commit()
            print("数据库迁移完成")
            
    except Exception as e:
        print(f"迁移失败: {e}")
        raise

if __name__ == "__main__":
    migrate() 