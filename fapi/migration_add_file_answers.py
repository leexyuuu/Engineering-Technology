#!/usr/bin/env python3
"""
数据库迁移脚本：为StudentAnswer表添加file_answers字段
用于支持多文件答题功能
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import Base, engine

def migrate_add_file_answers():
    """添加file_answers字段到student_answers表"""
    
    # 创建数据库连接
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # 检查字段是否已存在
        result = db.execute(text("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'student_answers' 
            AND COLUMN_NAME = 'file_answers'
        """))
        
        if result.fetchone():
            print("✅ file_answers字段已存在，跳过迁移")
            return
        
        # 添加file_answers字段
        db.execute(text("""
            ALTER TABLE student_answers 
            ADD COLUMN file_answers LONGTEXT
        """))
        
        db.commit()
        print("✅ 成功添加file_answers字段到student_answers表")
        
    except Exception as e:
        db.rollback()
        print(f"❌ 迁移失败: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("开始数据库迁移...")
    migrate_add_file_answers()
    print("迁移完成！") 