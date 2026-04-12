"""
测试数据准备脚本
创建 500 个测试学生账号 + 1 场测试考试 + 绑定学生到考试

使用方法:
    python setup_test_data.py --host http://127.0.0.1:8000 --students 500
"""

import argparse
import requests
import json
import sys
from datetime import datetime, timedelta


def parse_args():
    parser = argparse.ArgumentParser(description="准备压力测试数据")
    parser.add_argument("--host", default="http://127.0.0.1:8000", help="API 地址")
    parser.add_argument("--students", type=int, default=500, help="创建学生数量")
    parser.add_argument("--admin-user", default="admin", help="管理员用户名")
    parser.add_argument("--admin-pass", default="123456789", help="管理员密码")
    return parser.parse_args()


def admin_login(host, username, password):
    """管理员登录获取 token"""
    resp = requests.post(f"{host}/admin/token", data={
        "username": username,
        "password": password,
    })
    data = resp.json()
    if data.get("code") == 20000:
        return data["token"]
    print(f"[错误] 管理员登录失败: {data}")
    sys.exit(1)


def create_test_exam(host, token):
    """创建一场压力测试用的考试"""
    now = datetime.now()
    exam_data = {
        "name": f"压力测试考试_{now.strftime('%Y%m%d_%H%M')}",
        "description": "自动创建的压力测试考试",
        "instructions": "这是一场压力测试考试，请忽略。",
        "start_time": now.isoformat(),
        "end_time": (now + timedelta(hours=3)).isoformat(),
        "duration_minutes": 180,
    }
    resp = requests.post(
        f"{host}/exam/create",
        params=exam_data,
        headers={"Authorization": f"Bearer {token}"},
    )
    data = resp.json()
    if data.get("code") == 20000:
        exam_id = data["data"]["id"]
        print(f"[成功] 创建考试 ID: {exam_id}")
        return exam_id
    print(f"[错误] 创建考试失败: {data}")
    sys.exit(1)


def create_test_questions(host, token, exam_id, count=6):
    """为考试创建测试题目"""
    import uuid as uuid_lib
    for i in range(1, count + 1):
        q_data = {
            "exam_id": exam_id,
            "order": i,
            "uuid": str(uuid_lib.uuid4()),
            "content": f"压力测试题目 {i}：这是第 {i} 道测试题，请随意作答。",
            "requires_file": False,
            "file_description": "",
            "sub_questions_str": "",
            "required_files": "",
            "material_files": "",
            "reference_answer": f"参考答案 {i}",
        }
        resp = requests.post(
            f"{host}/exam/questions/create",
            params=q_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        data = resp.json()
        if data.get("code") == 20000:
            print(f"  题目 {i} 创建成功")
        else:
            print(f"  [警告] 题目 {i} 创建失败: {data}")

    print(f"[成功] 创建 {count} 道题目")


def create_test_students(host, token, exam_id, count):
    """批量创建测试学生并绑定到考试"""
    students = []
    for i in range(count):
        phone = f"test{i:05d}"
        students.append({"name": f"测试学生{i}", "phone": phone})

    # 每批 50 个
    batch_size = 50
    total_success = 0

    for batch_start in range(0, len(students), batch_size):
        batch = students[batch_start:batch_start + batch_size]
        import_data = {
            "exam_id": exam_id,
            "student_strs": json.dumps(batch),
        }
        resp = requests.post(
            f"{host}/exam/import-students",
            params=import_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        data = resp.json()
        if data.get("code") == 20000:
            success = data["data"].get("success_count", 0)
            total_success += success
            progress = min(batch_start + batch_size, count)
            print(f"  进度: {progress}/{count}，本批成功: {success}")
        else:
            print(f"  [警告] 批次导入失败: {data}")

    print(f"[成功] 共导入 {total_success} 名学生到考试 {exam_id}")
    return total_success


def verify_data(host, exam_id):
    """验证测试数据是否准备完成"""
    # 验证考试
    resp = requests.get(f"{host}/exam/{exam_id}")
    exam_data = resp.json()
    if exam_data.get("code") != 20000:
        print("[错误] 无法读取考试信息")
        return False

    # 验证题目
    resp = requests.get(f"{host}/exam/{exam_id}/questions")
    q_data = resp.json()
    q_count = len(q_data.get("data", {}).get("items", []))

    print(f"\n{'='*50}")
    print(f"数据验证结果:")
    print(f"  考试名称: {exam_data['data']['name']}")
    print(f"  考试 ID:  {exam_id}")
    print(f"  题目数量: {q_count}")
    print(f"  考试时间: {exam_data['data']['start_time']} ~ {exam_data['data']['end_time']}")
    print(f"{'='*50}")
    return True


def main():
    args = parse_args()
    host = args.host.rstrip("/")

    print(f"目标服务器: {host}")
    print(f"准备创建 {args.students} 个测试学生\n")

    # 1. 管理员登录
    print("[步骤 1/5] 管理员登录...")
    token = admin_login(host, args.admin_user, args.admin_pass)
    print(f"[成功] 管理员登录成功\n")

    # 2. 创建考试
    print("[步骤 2/5] 创建测试考试...")
    exam_id = create_test_exam(host, token)
    print()

    # 3. 创建题目
    print("[步骤 3/5] 创建测试题目...")
    create_test_questions(host, token, exam_id)
    print()

    # 4. 创建学生
    print(f"[步骤 4/5] 创建 {args.students} 名测试学生并绑定考试...")
    create_test_students(host, token, exam_id, args.students)
    print()

    # 5. 验证
    print("[步骤 5/5] 验证数据...")
    verify_data(host, exam_id)

    print(f"""
准备完成！接下来运行压测：

  1. 启动 Locust:
     cd fapi/loadtest
     locust -f locustfile.py

  2. 浏览器打开: http://localhost:8089

  3. 填写参数:
     - Number of users: {args.students}
     - Ramp up (users/second): 50
     - Host: {host}

  4. 点击 "Start" 开始测试

  5. 如果 locustfile.py 中 TEST_EXAM_ID 为 None，
     请修改为: TEST_EXAM_ID = {exam_id}
""")


if __name__ == "__main__":
    main()
