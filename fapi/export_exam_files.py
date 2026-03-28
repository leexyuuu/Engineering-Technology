"""
导出指定考试中所有学生提交的答卷文件。

用法:
    python export_exam_files.py                              # 交互式选择考试，默认只导出今天的
    python export_exam_files.py --exam-id 3                  # 指定考试ID，只导出今天参加的学生
    python export_exam_files.py --exam-id 3 --date 2026-03-28  # 指定日期
    python export_exam_files.py --exam-id 3 --all            # 导出所有学生（不限日期）
    python export_exam_files.py --exam-id 3 -o /tmp/out      # 指定输出目录

输出目录结构:
    {考试名称}/
    ├── 张三-13800138000/
    │   ├── 1-智慧交通中燃油效率模型的数据清洗和标注流程设计/
    │   │   ├── 上传1.2.5.docx
    │   │   └── 上传2.1.pdf
    │   └── 2-另一道题名称/
    │       └── 提交文件.xlsx
    └── 李四-13900139000/
        └── ...
"""

import argparse
import json
import os
import re
import shutil
import sys
from datetime import date, datetime

from sqlalchemy import create_engine, func, cast, Date
from sqlalchemy.orm import sessionmaker, Session

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from models import Exam, Question, Student, StudentExam, StudentAnswer

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(SCRIPT_DIR, "uploads")

SQLITE_PATH = os.path.join(SCRIPT_DIR, "test.db")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{SQLITE_PATH}")


def get_session() -> Session:
    connect_args = {}
    if DATABASE_URL.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    engine = create_engine(DATABASE_URL, connect_args=connect_args)
    return sessionmaker(bind=engine)()


def clean_filename(name: str) -> str:
    illegal_chars = r'[<>:"/\\|?*\x00-\x1f]'
    cleaned = re.sub(illegal_chars, '_', name).strip()
    return cleaned[:200] if cleaned else "unnamed"


def extract_question_title(content: str) -> str:
    """从 content 中提取 **试题名称** 与 **场地设备要求** 之间的文本作为试题名称"""
    match = re.search(r'\*\*试题名称\*\*\s*(.+?)\s*\*\*场地设备要求\*\*', content)
    if match:
        return match.group(1).strip()
    return content[:50]


def extract_filename_from_url(url: str) -> str | None:
    if not url:
        return None
    return url.split('/')[-1] or None


def pick_exam(db: Session) -> Exam:
    exams = db.query(Exam).order_by(Exam.id).all()
    if not exams:
        print("数据库中没有任何考试记录。")
        sys.exit(1)

    print("\n可用的考试列表：")
    for e in exams:
        print(f"  [{e.id}] {e.name}")
    print()

    while True:
        try:
            choice = int(input("请输入考试 ID: "))
            exam = next((e for e in exams if e.id == choice), None)
            if exam:
                return exam
            print("无效的 ID，请重新输入。")
        except (ValueError, EOFError):
            print("请输入数字。")


def export(exam_id: int, output_dir: str, target_date: date | None = None):
    db = get_session()

    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        print(f"错误：考试 ID {exam_id} 不存在。")
        sys.exit(1)

    print(f"\n考试：{exam.name} (ID={exam.id})")
    if target_date:
        print(f"筛选日期：{target_date}")
    else:
        print("筛选日期：全部")

    questions = (
        db.query(Question)
        .filter(Question.exam_id == exam_id)
        .order_by(Question.order)
        .all()
    )
    question_map = {q.id: q for q in questions}

    query = db.query(StudentExam).filter(StudentExam.exam_id == exam_id)
    if target_date:
        query = query.filter(cast(StudentExam.start_time, Date) == target_date)
    student_exams = query.all()

    if not student_exams:
        print("没有学生参加此考试。" if not target_date else f"{target_date} 没有学生参加此考试。")
        sys.exit(0)

    student_ids = [se.student_id for se in student_exams]
    students = db.query(Student).filter(Student.id.in_(student_ids)).all()
    student_map = {s.id: s for s in students}

    exam_folder_name = clean_filename(exam.name)
    exam_root = os.path.join(output_dir, exam_folder_name)
    os.makedirs(exam_root, exist_ok=True)

    total_files = 0
    total_students = 0

    for se in student_exams:
        student = student_map.get(se.student_id)
        if not student:
            continue

        student_folder_name = f"{clean_filename(student.name)}-{student.phone}"
        student_folder = os.path.join(exam_root, student_folder_name)
        os.makedirs(student_folder, exist_ok=True)

        answers = (
            db.query(StudentAnswer)
            .filter(StudentAnswer.student_exam_id == se.id)
            .all()
        )

        student_file_count = 0

        for answer in answers:
            question = question_map.get(answer.question_id)
            if not question:
                continue

            order = question.order if question.order else answer.question_id
            q_title = extract_question_title(question.content) if question.content else "未命名"
            question_folder_name = f"{order}-{clean_filename(q_title)}"
            question_folder = os.path.join(student_folder, question_folder_name)
            os.makedirs(question_folder, exist_ok=True)

            # --- 多文件答案 (file_answers) ---
            if answer.file_answers:
                try:
                    file_answers: dict = json.loads(answer.file_answers)
                except json.JSONDecodeError:
                    file_answers = {}

                if isinstance(file_answers, dict):
                    required_files_info = _build_required_files_map(question)

                    file_idx = 0
                    for file_uuid, file_url in file_answers.items():
                        file_idx += 1
                        stored_name = extract_filename_from_url(file_url)
                        if not stored_name:
                            continue

                        source = os.path.join(UPLOAD_FOLDER, stored_name)
                        if not os.path.exists(source):
                            print(f"  [跳过] 文件不存在: {source}")
                            continue

                        target_name = _resolve_target_filename(
                            file_uuid, stored_name, file_idx, required_files_info
                        )
                        dest = _safe_copy(source, question_folder, target_name)
                        if dest:
                            student_file_count += 1

            # --- 单文件答案 (file_url，向后兼容) ---
            if answer.file_url and not answer.file_answers:
                stored_name = extract_filename_from_url(answer.file_url)
                if stored_name:
                    source = os.path.join(UPLOAD_FOLDER, stored_name)
                    if os.path.exists(source):
                        ext = os.path.splitext(stored_name)[1]
                        target_name = f"文件{ext}"
                        dest = _safe_copy(source, question_folder, target_name)
                        if dest:
                            student_file_count += 1

        if student_file_count > 0:
            total_students += 1
            total_files += student_file_count
            print(f"  ✓ {student.name}-{student.phone}: {student_file_count} 个文件")
        else:
            shutil.rmtree(student_folder, ignore_errors=True)

    print(f"\n导出完成！共 {total_students} 名学生，{total_files} 个文件")
    print(f"输出目录: {os.path.abspath(exam_root)}")


def _build_required_files_map(question: Question) -> dict[str, str]:
    """从 question.required_files JSON 构建 {uuid: name} 映射"""
    if not question.required_files:
        return {}
    try:
        req_list = json.loads(question.required_files)
        if isinstance(req_list, list):
            return {
                item['uuid']: item['name']
                for item in req_list
                if 'uuid' in item and 'name' in item
            }
    except json.JSONDecodeError:
        pass
    return {}


def _resolve_target_filename(
    file_uuid: str,
    stored_name: str,
    file_idx: int,
    required_files_info: dict[str, str],
) -> str:
    """根据 required_files 中的定义确定目标文件名"""
    stored_ext = os.path.splitext(stored_name)[1]

    if file_uuid in required_files_info:
        req_name = required_files_info[file_uuid]
        if os.path.splitext(req_name)[1]:
            return req_name
        return f"{req_name}{stored_ext}"

    return f"第{file_idx}个文件{stored_ext}"


def _safe_copy(source: str, dest_dir: str, target_name: str) -> str | None:
    """复制文件到目标目录，自动处理文件名冲突"""
    target_name = clean_filename(target_name)
    dest = os.path.join(dest_dir, target_name)

    if os.path.exists(dest):
        base, ext = os.path.splitext(target_name)
        counter = 1
        while os.path.exists(dest):
            dest = os.path.join(dest_dir, f"{base}_{counter}{ext}")
            counter += 1

    shutil.copy2(source, dest)
    return dest


def main():
    parser = argparse.ArgumentParser(description="导出考试学生答卷文件")
    parser.add_argument("--exam-id", type=int, help="考试 ID（不指定则交互式选择）")
    parser.add_argument("-o", "--output", default=".", help="输出根目录（默认当前目录）")
    parser.add_argument("--date", type=str, default=None,
                        help="只导出该日期参加考试的学生 (格式: YYYY-MM-DD，默认今天)")
    parser.add_argument("--all", action="store_true", dest="export_all",
                        help="导出所有学生（不限日期）")
    args = parser.parse_args()

    if args.exam_id:
        exam_id = args.exam_id
    else:
        db = get_session()
        exam = pick_exam(db)
        exam_id = exam.id
        db.close()

    if args.export_all:
        target_date = None
    elif args.date:
        target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
    else:
        target_date = date.today()

    export(exam_id, args.output, target_date=target_date)


if __name__ == "__main__":
    main()
