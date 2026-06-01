"""
SQLite Database Implementation for Local Testing
Use this when Supabase is not available
"""
import sqlite3
import os
from pathlib import Path
import bcrypt

# Database file location
DB_PATH = Path(__file__).parent / "snapclass.db"

def init_db():
    """Initialize SQLite database with required tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create teachers table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS teachers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create students table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT NOT NULL,
            roll_number TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create subjects table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id INTEGER NOT NULL,
            subject_name TEXT NOT NULL,
            subject_code TEXT UNIQUE,
            join_code TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (teacher_id) REFERENCES teachers(id)
        )
    ''')
    
    # Create attendance table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            attendance_date DATE NOT NULL,
            status TEXT DEFAULT 'absent',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (subject_id) REFERENCES subjects(id),
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
    ''')
    
    # Create enrollments table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS enrollments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(student_id, subject_id),
            FOREIGN KEY (student_id) REFERENCES students(id),
            FOREIGN KEY (subject_id) REFERENCES subjects(id)
        )
    ''')
    
    conn.commit()
    conn.close()

def hash_pass(pwd):
    """Hash password"""
    return bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()

def check_pass(pwd, hashed):
    """Verify password"""
    return bcrypt.checkpw(pwd.encode(), hashed.encode())

def check_teacher_exists(username):
    """Check if teacher username exists"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM teachers WHERE username = ?", (username,))
    result = cursor.fetchone() is not None
    conn.close()
    return result

def create_teacher(username, password, name):
    """Create new teacher"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO teachers (username, password, name) VALUES (?, ?, ?)",
            (username, hash_pass(password), name)
        )
        conn.commit()
        teacher_id = cursor.lastrowid
        conn.close()
        return [{"id": teacher_id, "username": username, "name": name}]
    except sqlite3.IntegrityError:
        conn.close()
        return []

def teacher_login(username, password):
    """Authenticate teacher"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, password, name FROM teachers WHERE username = ?", (username,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        teacher_id, user, pwd_hash, name = result
        if check_pass(password, pwd_hash):
            return {"id": teacher_id, "username": user, "name": name}
    return None

def check_student_exists(username):
    """Check if student username exists"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM students WHERE username = ?", (username,))
    result = cursor.fetchone() is not None
    conn.close()
    return result

def create_student(username, password, name, roll_number=None):
    """Create new student"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO students (username, password, name, roll_number) VALUES (?, ?, ?, ?)",
            (username, hash_pass(password), name, roll_number)
        )
        conn.commit()
        student_id = cursor.lastrowid
        conn.close()
        return [{"id": student_id, "username": username, "name": name}]
    except sqlite3.IntegrityError:
        conn.close()
        return []

def student_login(username, password):
    """Authenticate student"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, password, name FROM students WHERE username = ?", (username,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        student_id, user, pwd_hash, name = result
        if check_pass(password, pwd_hash):
            return {"id": student_id, "username": user, "name": name}
    return None

def get_all_students():
    """Get all students"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, name, roll_number FROM students")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "username": r[1], "name": r[2], "roll_number": r[3]} for r in rows]

def get_all_subjects(teacher_id):
    """Get all subjects for a teacher"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, teacher_id, subject_name, subject_code, join_code FROM subjects WHERE teacher_id = ?",
        (teacher_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "teacher_id": r[1], "subject_name": r[2], "subject_code": r[3], "join_code": r[4]} for r in rows]

def get_all_subjects():
    """Get all subjects in the database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, teacher_id, subject_name, subject_code, join_code FROM subjects")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "teacher_id": r[1], "subject_name": r[2], "subject_code": r[3], "join_code": r[4]} for r in rows]

def get_teacher_subjects(teacher_id):
    """Get all subjects for a teacher"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, teacher_id, subject_name, subject_code, join_code FROM subjects WHERE teacher_id = ?", (teacher_id,))
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "teacher_id": r[1], "subject_name": r[2], "subject_code": r[3], "join_code": r[4]} for r in rows]

def create_subject(subject_code, name, section, teacher_id):
    """Create new subject"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO subjects (teacher_id, subject_name, subject_code, join_code) VALUES (?, ?, ?, ?)",
            (teacher_id, name, subject_code, subject_code)
        )
        conn.commit()
        subject_id = cursor.lastrowid
        conn.close()
        return [{"id": subject_id, "subject_code": subject_code, "name": name}]
    except sqlite3.IntegrityError:
        conn.close()
        return []

def enroll_student_to_subject(student_id, subject_id):
    """Enroll a student to a subject"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO enrollments (student_id, subject_id) VALUES (?, ?)",
            (student_id, subject_id)
        )
        conn.commit()
        conn.close()
        return [{"student_id": student_id, "subject_id": subject_id}]
    except sqlite3.IntegrityError:
        conn.close()
        return []

def unenroll_student_to_subject(student_id, subject_id):
    """Unenroll a student from a subject"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM enrollments WHERE student_id = ? AND subject_id = ?", (student_id, subject_id))
    conn.commit()
    conn.close()
    return []

def get_student_subjects(student_id):
    """Get all subjects for a student"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.id, s.teacher_id, s.subject_name, s.subject_code, s.join_code
        FROM enrollments e
        JOIN subjects s ON e.subject_id = s.id
        WHERE e.student_id = ?
    """, (student_id,))
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "teacher_id": r[1], "subject_name": r[2], "subject_code": r[3], "join_code": r[4]} for r in rows]

def get_student_attendance(student_id):
    """Get attendance records for a student"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.id, a.subject_id, a.attendance_date, a.status, s.subject_name
        FROM attendance a
        JOIN subjects s ON a.subject_id = s.id
        WHERE a.student_id = ?
    """, (student_id,))
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "subject_id": r[1], "attendance_date": r[2], "status": r[3], "subject_name": r[4]} for r in rows]

def create_attendance(logs):
    """Create attendance records"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for log in logs:
        cursor.execute(
            "INSERT INTO attendance (subject_id, student_id, attendance_date, status) VALUES (?, ?, ?, ?)",
            (log.get("subject_id"), log.get("student_id"), log.get("attendance_date"), log.get("status", "present"))
        )
    conn.commit()
    conn.close()
    return logs

def get_attendance_for_teacher(teacher_id):
    """Get all attendance records for a teacher's subjects"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.id, a.subject_id, a.student_id, a.attendance_date, a.status, s.subject_name
        FROM attendance a
        JOIN subjects s ON a.subject_id = s.id
        WHERE s.teacher_id = ?
    """, (teacher_id,))
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "subject_id": r[1], "student_id": r[2], "attendance_date": r[3], "status": r[4], "subject_name": r[5]} for r in rows]
