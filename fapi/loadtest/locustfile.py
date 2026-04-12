"""
mock-exam 压力测试脚本
模拟 500 个学生同时在线考试的完整流程：登录 → 开始考试 → 答题(多次保存) → 交卷

使用方法:
    1. pip install locust
    2. cd fapi/loadtest
    3. python setup_test_data.py          # 先准备测试数据
    4. locust -f locustfile.py            # 启动测试
    5. 浏览器打开 http://localhost:8089   # 配置并发数后开始
"""

import json
import random
import time
from locust import HttpUser, task, between, events


# ============================================================
#  配置区 —— 根据你的实际环境修改
# ============================================================
API_BASE = ""  # 留空，在 Locust Web UI 中填写 host（如 http://127.0.0.1:8000）
TEST_EXAM_ID = None  # 设为 None 则自动获取第一个可用考试


class ExamStudent(HttpUser):
    """
    模拟一个学生的完整考试流程。
    每个虚拟用户按顺序执行：登录 → 拉取考试 → 开始考试 → 循环答题保存 → 交卷
    """
    wait_time = between(2, 5)  # 每次操作之间等待 2-5 秒，模拟真人思考时间

    def on_start(self):
        """虚拟用户启动时执行：登录 + 准备考试"""
        self.token = None
        self.student_data = None
        self.exam_id = TEST_EXAM_ID
        self.questions = []
        self.current_question_index = 0
        self.exam_submitted = False

        self._login()
        if self.token:
            self._find_exam()
            if self.exam_id:
                self._start_exam()

    # --------------------------------------------------------
    #  步骤 1：登录
    # --------------------------------------------------------
    def _login(self):
        # 每个 Locust 用户有一个唯一的 greenlet id，用来选取不同的测试账号
        user_index = id(self.environment.runner.greenlet) if self.environment.runner else 0
        # 用 Locust 内部分配的用户序号来选账号
        # greenlet id 不连续，所以用 hash 取模
        idx = hash(id(self)) % 10000
        phone = f"test{idx:05d}"
        password = phone[-4:]  # 密码 = 手机号后4位

        with self.client.post(
            "/student/login",
            json={"phone": phone, "password": password},
            name="1-登录",
            catch_response=True,
        ) as resp:
            try:
                data = resp.json()
                if data.get("code") == 20000 and data.get("token"):
                    self.token = data["token"]
                    self.student_data = data.get("data", {})
                    resp.success()
                else:
                    resp.failure(f"登录失败: {data.get('message', 'unknown')}")
            except Exception as e:
                resp.failure(f"登录异常: {e}")

    # --------------------------------------------------------
    #  步骤 2：查找可用考试
    # --------------------------------------------------------
    def _find_exam(self):
        if self.exam_id:
            return

        # 尝试从登录返回的 upcoming_exam 获取
        upcoming = self.student_data.get("upcoming_exam") if self.student_data else None
        if upcoming and upcoming.get("exam_id"):
            self.exam_id = upcoming["exam_id"]
            return

        # 否则从考试列表取第一个
        with self.client.get(
            "/exam/list?page=1&page_size=5",
            name="2-获取考试列表",
            catch_response=True,
        ) as resp:
            try:
                data = resp.json()
                items = data.get("data", {}).get("items", [])
                if items:
                    self.exam_id = items[0]["id"]
                    resp.success()
                else:
                    resp.failure("没有可用的考试")
            except Exception as e:
                resp.failure(f"获取考试列表异常: {e}")

    # --------------------------------------------------------
    #  步骤 3：开始考试
    # --------------------------------------------------------
    def _start_exam(self):
        if not self.token or not self.exam_id:
            return

        headers = {"Authorization": f"Bearer {self.token}"}

        with self.client.post(
            "/student/exams/start",
            json={"exam_id": self.exam_id},
            headers=headers,
            name="3-开始考试",
            catch_response=True,
        ) as resp:
            try:
                if resp.status_code in (200, 400):
                    resp.success()
                else:
                    resp.failure(f"开始考试失败: {resp.status_code}")
            except Exception as e:
                resp.failure(f"开始考试异常: {e}")

        self._load_questions()

    # --------------------------------------------------------
    #  步骤 4：加载题目
    # --------------------------------------------------------
    def _load_questions(self):
        headers = {"Authorization": f"Bearer {self.token}"}

        with self.client.get(
            f"/student/exams/{self.exam_id}/answers",
            headers=headers,
            name="4-加载已有答案",
            catch_response=True,
        ) as resp:
            try:
                resp.success()
            except Exception:
                pass

        with self.client.get(
            f"/exam/{self.exam_id}/questions",
            headers=headers,
            name="4-加载题目列表",
            catch_response=True,
        ) as resp:
            try:
                data = resp.json()
                self.questions = data.get("data", {}).get("items", [])
                resp.success()
            except Exception as e:
                resp.failure(f"加载题目异常: {e}")

    # --------------------------------------------------------
    #  步骤 5：答题（主循环，Locust 会反复调用 @task）
    # --------------------------------------------------------
    @task(10)
    def save_answer(self):
        """模拟学生作答：每次保存一道题的答案"""
        if not self.token or not self.exam_id or self.exam_submitted:
            time.sleep(1)
            return

        if not self.questions:
            return

        # 循环答题
        q = self.questions[self.current_question_index % len(self.questions)]
        self.current_question_index += 1

        headers = {"Authorization": f"Bearer {self.token}"}
        answer_data = {
            "question_id": q["id"],
            "exam_id": self.exam_id,
            "option_answers": json.dumps({"answer": f"test_answer_{random.randint(1, 100)}"}),
        }

        with self.client.post(
            "/student/answers/save",
            json=answer_data,
            headers=headers,
            name="5-保存答案",
            catch_response=True,
        ) as resp:
            try:
                data = resp.json()
                if data.get("code") == 20000:
                    resp.success()
                else:
                    resp.failure(f"保存答案失败: {resp.status_code}")
            except Exception as e:
                resp.failure(f"保存答案异常: {e}")

        # 每答完所有题目一轮后交卷
        if self.current_question_index >= len(self.questions) * 2:
            self._submit_exam()

    @task(3)
    def check_answers(self):
        """模拟学生查看已保存的答案（切题时触发）"""
        if not self.token or not self.exam_id or self.exam_submitted:
            return

        headers = {"Authorization": f"Bearer {self.token}"}
        with self.client.get(
            f"/student/exams/{self.exam_id}/answers",
            headers=headers,
            name="5-查看已有答案",
            catch_response=True,
        ) as resp:
            try:
                resp.success()
            except Exception:
                pass

    # --------------------------------------------------------
    #  步骤 6：交卷
    # --------------------------------------------------------
    def _submit_exam(self):
        if self.exam_submitted:
            return

        headers = {"Authorization": f"Bearer {self.token}"}

        with self.client.post(
            f"/student/exams/{self.exam_id}/submit",
            headers=headers,
            name="6-交卷",
            catch_response=True,
        ) as resp:
            try:
                data = resp.json()
                if data.get("code") == 20000:
                    resp.success()
                    self.exam_submitted = True
                else:
                    resp.failure(f"交卷失败: {data}")
            except Exception as e:
                resp.failure(f"交卷异常: {e}")

    @task(1)
    def idle_after_submit(self):
        """交卷后停止操作"""
        if self.exam_submitted:
            self.environment.runner.quit()
