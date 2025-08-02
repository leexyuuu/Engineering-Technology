#!/usr/bin/env python3
"""
测试多文件答题和资料文件功能
"""

import requests
import json

# 测试配置
BASE_URL = "http://127.0.0.1:8000"
TOKEN = "your_token_here"  # 需要替换为实际的token

def test_create_question_with_files():
    """测试创建带文件要求的题目"""
    
    # 创建题目的数据
    question_data = {
        "exam_id": 1,
        "order": 1,
        "uuid": "test_uuid_001",
        "content": "这是一个测试题目，需要上传多个文件",
        "requires_file": True,
        "file_description": "请上传相关文件",
        "sub_questions_str": json.dumps([
            {
                "order": 1,
                "content": "子问题1",
                "question_type": "text",
                "score": 10,
                "options": []
            }
        ]),
        "required_files": json.dumps([
            {
                "name": "设计文档",
                "type": "pdf",
                "required": True,
                "description": "请上传项目设计文档",
                "uuid": "file_001"
            },
            {
                "name": "代码文件",
                "type": "other",
                "required": True,
                "description": "请上传源代码文件",
                "uuid": "file_002"
            }
        ]),
        "material_files": json.dumps([
            {
                "name": "参考资料",
                "type": "pdf",
                "description": "项目参考资料",
                "url": "/uploads/sample.pdf",
                "originalName": "参考资料.pdf",
                "uuid": "material_001"
            }
        ])
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/exam/questions/create",
            params=question_data,
            headers={"Authorization": TOKEN}
        )
        
        print("创建题目响应:", response.status_code)
        print("响应内容:", response.json())
        
    except Exception as e:
        print(f"测试失败: {e}")

def test_upload_file():
    """测试文件上传功能"""
    
    try:
        # 创建一个测试文件
        with open("test_file.txt", "w") as f:
            f.write("这是一个测试文件")
        
        with open("test_file.txt", "rb") as f:
            files = {"file": f}
            response = requests.post(
                f"{BASE_URL}/exam/upload-file",
                files=files,
                headers={"Authorization": TOKEN}
            )
        
        print("文件上传响应:", response.status_code)
        print("响应内容:", response.json())
        
        # 清理测试文件
        import os
        os.remove("test_file.txt")
        
    except Exception as e:
        print(f"文件上传测试失败: {e}")

if __name__ == "__main__":
    print("开始测试多文件答题和资料文件功能...")
    
    # 测试文件上传
    print("\n1. 测试文件上传功能")
    test_upload_file()
    
    # 测试创建题目
    print("\n2. 测试创建带文件要求的题目")
    test_create_question_with_files()
    
    print("\n测试完成！") 