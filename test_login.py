#!/usr/bin/env python3
import requests
import json

def test_student_login():
    """测试学生登录接口"""
    base_url = "http://localhost:8000"
    
    # 测试数据
    login_data = {
        "phone": "13800138001",
        "password": "8001"  # 电话号码后四位
    }
    
    try:
        print("测试学生登录接口...")
        print(f"登录数据: {json.dumps(login_data, ensure_ascii=False, indent=2)}")
        
        response = requests.post(f"{base_url}/student/login", json=login_data)
        print(f"状态码: {response.status_code}")
        
        try:
            response_json = response.json()
            print(f"响应JSON: {json.dumps(response_json, ensure_ascii=False, indent=2)}")
            
            if response.status_code == 200:
                result = response_json
                if result.get("code") == 20000:
                    print("✅ 登录成功!")
                    student_data = result["data"]
                    print(f"学生ID: {student_data['id']}")
                    print(f"学生姓名: {student_data['name']}")
                    print(f"学生电话: {student_data['phone']}")
                    
                    if student_data.get("upcoming_exam"):
                        exam = student_data["upcoming_exam"]
                        print(f"✅ 找到即将开始的考试:")
                        print(f"  考试ID: {exam['exam_id']}")
                        print(f"  考试名称: {exam['exam_name']}")
                        print(f"  考试开始时间: {exam['exam_start_time']}")
                        print(f"  考试结束时间: {exam['exam_end_time']}")
                        print(f"  考试时长: {exam['exam_duration_minutes']} 分钟")
                        print(f"  学生考试状态: {exam['status']}")
                    else:
                        print("ℹ️  没有找到即将开始的考试")
                    
                    if result.get("token"):
                        print(f"✅ 获取到访问令牌")
                else:
                    print("❌ 登录失败:", result.get("message"))
            else:
                print("❌ 请求失败")
                
        except json.JSONDecodeError:
            print(f"响应文本: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ 连接失败: 无法连接到服务器")
    except Exception as e:
        print(f"❌ 请求异常: {e}")

if __name__ == "__main__":
    test_student_login() 