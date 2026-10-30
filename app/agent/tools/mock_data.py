# -*- coding: utf-8 -*-
"""Mock 业务数据（阶段4，提示词7）：课程库 / 课表 / 学籍 / 成绩 / 已选课程。

背景（需求评审 Q10 默认答案）：教务系统接口暂不可用，先用 mock 数据 +
回放方式验证 Agent 工具链；后续接真实接口时只需替换本模块的数据来源
（改为 HTTP 调用），工具签名与编排逻辑不变。

数据设计目标：支撑 3 条典型对话轨迹的离线验证——
    a.《数据结构》下学期课表查询      → query_course_schedule
    b. 选《人工智能基础》选修课全流程  → 规则→课程要求→确认→资格→申请→确认门
    c.《移动应用开发》资格询问（不符）→ validate_eligibility（先修课未修读）
"""
from __future__ import annotations

# ══════════ 演示账号 → 学号映射（接真实系统后改为统一身份认证）══════════
USER_STUDENT_MAP: dict[str, str] = {
    "student1": "2024010101",   # 演示学生账号
    "teacher1": "",             # 教师无学籍（查询学生数据类工具会明确提示）
    "admin1": "",
}

# 当前演示的"目标选课学期"（下学期；选课在第 18 周进行，制度 2.1）
SEMESTER = "2026-2027-2"

# ══════════ 课程库（含先修关系，供 check_course_requirements / 资格校验）══════════
# 字段：代码/名称/学院/类型(必修|选修)/学分/学时/先修课代码列表/容量
MOCK_COURSES: dict[str, dict] = {
    "CS101": {"code": "CS101", "name": "程序设计基础", "college": "信息工程学院",
              "type": "必修", "credits": 3, "hours": 48, "prerequisites": [],
              "capacity": {"enrolled": 90, "max": 100}},
    "CS201": {"code": "CS201", "name": "数据结构", "college": "信息工程学院",
              "type": "必修", "credits": 4, "hours": 64, "prerequisites": ["CS101"],
              "capacity": {"enrolled": 85, "max": 95}},
    "CS202": {"code": "CS202", "name": "离散数学", "college": "信息工程学院",
              "type": "必修", "credits": 4, "hours": 64, "prerequisites": ["CS101"],
              "capacity": {"enrolled": 80, "max": 90}},
    "CS204": {"code": "CS204", "name": "计算机网络", "college": "信息工程学院",
              "type": "必修", "credits": 4, "hours": 64, "prerequisites": ["CS201"],
              "capacity": {"enrolled": 76, "max": 90}},
    "CS208": {"code": "CS208", "name": "操作系统", "college": "信息工程学院",
              "type": "必修", "credits": 4, "hours": 64, "prerequisites": ["CS201"],
              "capacity": {"enrolled": 74, "max": 90}},
    "CS209": {"code": "CS209", "name": "算法设计", "college": "信息工程学院",
              "type": "必修", "credits": 3, "hours": 48, "prerequisites": ["CS201"],
              "capacity": {"enrolled": 60, "max": 80}},
    "CS302": {"code": "CS302", "name": "软件工程", "college": "信息工程学院",
              "type": "必修", "credits": 4, "hours": 64, "prerequisites": ["CS202"],
              "capacity": {"enrolled": 70, "max": 85}},
    "MT201": {"code": "MT201", "name": "高等数学（一）", "college": "通识教育学院",
              "type": "必修", "credits": 4, "hours": 64, "prerequisites": [],
              "capacity": {"enrolled": 120, "max": 130}},
    "MT202": {"code": "MT202", "name": "概率论与数理统计", "college": "通识教育学院",
              "type": "必修", "credits": 3, "hours": 48, "prerequisites": ["MT201"],
              "capacity": {"enrolled": 100, "max": 120}},
    "CS102": {"code": "CS102", "name": "Web 前端开发", "college": "信息工程学院",
              "type": "选修", "credits": 2, "hours": 32, "prerequisites": [],
              "capacity": {"enrolled": 40, "max": 50}},
    "CS220": {"code": "CS220", "name": "移动应用开发", "college": "信息工程学院",
              "type": "选修", "credits": 3, "hours": 48, "prerequisites": ["CS102"],
              "capacity": {"enrolled": 30, "max": 45}},
    "CS305": {"code": "CS305", "name": "人工智能基础", "college": "信息工程学院",
              "type": "选修", "credits": 3, "hours": 48, "prerequisites": ["CS201"],
              "capacity": {"enrolled": 38, "max": 45}},
    "CS401": {"code": "CS401", "name": "编译原理", "college": "信息工程学院",
              "type": "选修", "credits": 3, "hours": 48, "prerequisites": ["CS201"],
              "capacity": {"enrolled": 25, "max": 50}},
}

# ══════════ 学生学籍（供资格校验取已修学分等）══════════
MOCK_STUDENTS: dict[str, dict] = {
    "2024010101": {"student_no": "2024010101", "name": "张同学",
                   "grade": "2024 级", "major": "计算机应用技术",
                   "earned_credits": 68},        # 已修总学分（不含在读）
}

# ══════════ 成绩单（先修课校验依据，制度 2.2：60 分及以上为合格）══════════
MOCK_GRADES: dict[str, dict[str, int]] = {
    # 学号 → {课程代码: 成绩}
    "2024010101": {"CS101": 85, "MT201": 90, "CS201": 78},   # 数据结构 78 分 → 满足 AI 先修
}

# ══════════ 目标学期已选课程（选课进行中，供冲突/学分校验）══════════
# 时段字段 weekday/period 与课表同构，供时间冲突比对（制度 2.3）。
MOCK_ENROLLED: dict[str, list[dict]] = {
    "2024010101": [   # 下学期已选 24 学分（4+4+4+3+4+3+2）
        {"course_code": "CS202", "course_name": "离散数学", "credits": 4,
         "weekday": "周三", "period": "第1-2节"},
        {"course_code": "CS204", "course_name": "计算机网络", "credits": 4,
         "weekday": "周五", "period": "第3-4节"},
        {"course_code": "CS208", "course_name": "操作系统", "credits": 4,
         "weekday": "周二", "period": "第3-4节"},
        {"course_code": "CS209", "course_name": "算法设计", "credits": 3,
         "weekday": "周五", "period": "第1-2节"},
        {"course_code": "CS302", "course_name": "软件工程", "credits": 4,
         "weekday": "周四", "period": "第1-2节"},
        {"course_code": "MT202", "course_name": "概率论与数理统计", "credits": 3,
         "weekday": "周一", "period": "第3-4节"},
        {"course_code": "CS310", "course_name": "数据可视化", "credits": 2,
         "weekday": "周四", "period": "第7-8节"},
    ],
}

# ══════════ 下学期课表（版本管理 + 数据更新时间，制度 3.4 / 1.6）══════════
SCHEDULE_VERSION = "2026-2027-2-V1"          # 课表版本号（学期-版次）
SCHEDULE_UPDATED_AT = "2026-10-28 16:00"     # 数据更新时间（15 分钟同步周期内）
MOCK_SCHEDULE: dict[str, list[dict]] = {
    # 课程代码 → 排课时段列表
    "CS201": [  # 2025 级平行班（上机查询单例轨迹 a）
        {"weekday": "周二", "period": "第1-2节", "room": "A201",
         "teacher": "陈晨", "weeks": "1-16周"},
        {"weekday": "周四", "period": "第3-4节", "room": "A201",
         "teacher": "陈晨", "weeks": "1-16周"},
    ],
    "CS305": [  # 人工智能基础（轨迹 b 目标课程；周一5-6/周三7-8 与已选时段不冲突）
        {"weekday": "周一", "period": "第5-6节", "room": "机房A301",
         "teacher": "张伟", "weeks": "1-16周"},
        {"weekday": "周三", "period": "第7-8节", "room": "机房A301",
         "teacher": "张伟", "weeks": "1-16周"},
    ],
    "CS220": [  # 移动应用开发（轨迹 c：先修 CS102 未修读 → 资格不符）
        {"weekday": "周二", "period": "第5-6节", "room": "实训楼B202",
         "teacher": "李娜", "weeks": "1-16周"},
    ],
    "CS401": [
        {"weekday": "周四", "period": "第5-6节", "room": "A105",
         "teacher": "王强", "weeks": "1-16周"},
    ],
    "CS102": [
        {"weekday": "周一", "period": "第5-6节", "room": "机房B203",
         "teacher": "赵敏", "weeks": "1-16周"},
    ],
}

# ══════════ 常量：制度条文引用锚点（工具结论必须带依据，f45 事实引用要素）══════════
RULE_VERSION = "教务管理制度 v2026.1（JW-ZD-2026-001，2026-09-01 生效）"
CREDIT_LIMIT_MAX = 28     # 每学期学分上限（制度 2.4）
CREDIT_LIMIT_MIN = 16     # 每学期学分下限（制度 2.4，毕业班除外）
PASS_SCORE = 60           # 先修课合格线（制度 2.2）
