# -*- coding: utf-8 -*-
"""上线前动作 · 真实学籍导入工具（CSV → users 表）。

用法（建议停服执行，避免并发写入）：
    python scripts/import_students.py students.csv

CSV 格式（UTF-8，首行表头，逗号分隔）：
    student_no,real_name,initial_password
    2026040101,张三,Init@2026#001

规则：
  - 学号非空且唯一（重复跳过并列出）；密码长度 ≥8；
  - 口令以 PBKDF2-HMAC-SHA256（100,000 迭代 + 16 字节随机盐）哈希入库，
    与 app/security.py 实现一致（存储格式：<32hex盐>$<64hex哈希>）；
  - 角色固定 student；导入后建议通知学生首次登录后自行改密。
"""
from __future__ import annotations

import csv
import hashlib
import secrets
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "app.db"
MIN_PWD_LEN = 8


def hash_password(password: str) -> str:
    """与 app/security.py 一致的 PBKDF2 哈希（盐$哈希）。"""
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                             salt.encode("utf-8"), 100_000)
    return f"{salt}${dk.hex()}"


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    csv_path = Path(sys.argv[1])
    if not csv_path.exists():
        print(f"❌ 文件不存在：{csv_path}")
        return 2

    rows: list[tuple[str, str, str]] = []
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        missing = {"student_no", "real_name", "initial_password"} - set(reader.fieldnames or [])
        if missing:
            print(f"❌ CSV 缺少列：{sorted(missing)}（需要 student_no, real_name, initial_password）")
            return 2
        for i, r in enumerate(reader, start=2):
            no, name, pwd = (r["student_no"] or "").strip(), \
                (r["real_name"] or "").strip(), (r["initial_password"] or "")
            if not no or not name:
                print(f"  ⚠ 第 {i} 行学号/姓名为空，跳过")
                continue
            if len(pwd) < MIN_PWD_LEN:
                print(f"  ⚠ 第 {i} 行 {no} 密码不足 {MIN_PWD_LEN} 位，跳过")
                continue
            rows.append((no, name, pwd))

    if not rows:
        print("❌ 无有效数据行")
        return 1

    inserted, skipped_dup = 0, []
    with sqlite3.connect(DB_PATH) as conn:
        for no, name, pwd in rows:
            exists = conn.execute(
                "SELECT 1 FROM users WHERE username=?", (no,)).fetchone()
            if exists:
                skipped_dup.append(no)
                continue
            conn.execute(
                "INSERT INTO users (username, password_hash, role, real_name, "
                "is_active, created_at) VALUES (?, ?, 'student', ?, 1, "
                "datetime('now', 'localtime'))",
                (no, hash_password(pwd), name))
            inserted += 1
        conn.commit()
        total = conn.execute(
            "SELECT COUNT(*) FROM users WHERE role='student'").fetchone()[0]

    print(f"✅ 导入完成：新增 {inserted} 名学生"
          f"（重复跳过 {len(skipped_dup)}：{skipped_dup[:10]}）")
    print(f"   当前学生账号总数：{total}")
    print("   提示：请通知学生首次登录后自行修改初始密码。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
