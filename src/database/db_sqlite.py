"""
SQLite Database Implementation for Local Testing
Use this when Supabase is not available
"""
import json
import secrets
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
            face_embedding TEXT,
            voice_embedding TEXT,
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
            section TEXT,
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

    # Migrate pre-existing databases created before `section` was added.
    columns = [row[1] for row in cursor.execute("PRAGMA table_info(subjects)")]
    if "section" not in columns:
        cursor.execute("ALTER TABLE subjects ADD COLUMN section TEXT")
        conn.commit()

    # Migrate pre-existing databases created before the face/voice
    # embeddings were stored: without these columns create_student() could
    # not persist the embeddings the FaceID registration flow captures.
    student_columns = [row[1] for row in cursor.execute("PRAGMA table_info(students)")]
    for column in ("face_embedding", "voice_embedding"):
        if column not in student_columns:
            cursor.execute(f"ALTER TABLE students ADD COLUMN {column} TEXT")
            conn.commit()

    conn.close()


def _parse_embedding(value):
    """Embeddings are stored as JSON text; hand them back as lists."""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            return value
    return value

def _subject_row(row):
    """Shape a subject row the way the screens (and the Supabase backend) expect."""
    return {
        "subject_id": row[0],
        "teacher_id": row[1],
        "name": row[2],
        "subject_code": row[3],
        "join_code": row[4],
        "section": row[5],
        "total_students": row[6],
        "total_classes": row[7],
    }

_SUBJECT_COLUMNS = """
    s.id, s.teacher_id, s.subject_name, s.subject_code, s.join_code, s.section,
    (SELECT COUNT(*) FROM enrollments e WHERE e.subject_id = s.id) AS total_students,
    (SELECT COUNT(DISTINCT a.attendance_date) FROM attendance a WHERE a.subject_id = s.id) AS total_classes
    FROM subjects s
"""

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
        return [{"teacher_id": teacher_id, "username": username, "name": name}]
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
            return {"teacher_id": teacher_id, "username": user, "name": name}
    return None

def check_student_exists(username):
    """Check if student username exists"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM students WHERE username = ?", (username,))
    result = cursor.fetchone() is not None
    conn.close()
    return result

def create_student(username, password=None, name=None, roll_number=None,
                   face_embedding=None, voice_embedding=None):
    """Create new student.

    FaceID registration (student_screen.py) has no password: it calls
    create_student(name, face_embedding=..., voice_embedding=...), so the
    password is optional here and a random hash nobody knows is stored
    instead, keeping password login impossible for a face-only account.
    Embeddings are stored as JSON so get_all_students() can hand them back
    to the face/voice pipelines as lists.
    """
    if name is None:
        name = username
    if password is None:
        password_hash = bcrypt.hashpw(
            secrets.token_bytes(32), bcrypt.gensalt()).decode()
    else:
        password_hash = hash_pass(password)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO students (username, password, name, roll_number, face_embedding, voice_embedding) VALUES (?, ?, ?, ?, ?, ?)",
            (username, password_hash, name, roll_number,
             json.dumps(face_embedding) if face_embedding is not None else None,
             json.dumps(voice_embedding) if voice_embedding is not None else None)
        )
        conn.commit()
        student_id = cursor.lastrowid
        conn.close()
        return [{"student_id": student_id, "username": username, "name": name}]
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
            return {"student_id": student_id, "username": user, "name": name}
    return None

def get_all_students():
    """Get all students"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, name, roll_number, face_embedding, voice_embedding FROM students")
    rows = cursor.fetchall()
    conn.close()
    return [{"student_id": r[0], "username": r[1], "name": r[2], "roll_number": r[3],
             "face_embedding": _parse_embedding(r[4]),
             "voice_embedding": _parse_embedding(r[5])} for r in rows]

def get_all_subjects():
    """Get all subjects in the database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT " + _SUBJECT_COLUMNS)
    rows = cursor.fetchall()
    conn.close()
    return [_subject_row(r) for r in rows]

def get_teacher_subjects(teacher_id):
    """Get all subjects for a teacher"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT " + _SUBJECT_COLUMNS + " WHERE s.teacher_id = ?", (teacher_id,))
    rows = cursor.fetchall()
    conn.close()
    return [_subject_row(r) for r in rows]

def create_subject(subject_code, name, section, teacher_id):
    """Create new subject"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO subjects (teacher_id, subject_name, subject_code, join_code, section) VALUES (?, ?, ?, ?, ?)",
            (teacher_id, name, subject_code, subject_code, section)
        )
        conn.commit()
        subject_id = cursor.lastrowid
        conn.close()
        return [{"subject_id": subject_id, "subject_code": subject_code, "name": name, "section": section}]
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

def get_enrolled_students(subject_id):
    """Get all students enrolled in a subject (same nested shape as the Supabase backend).

    The screens used to query a 'subject_students' table directly through the
    Supabase client; that table does not exist (enrollments live in the
    'enrollments' table) and the client is None in local mode, so Run Face
    Analysis / Voice Attendance crashed every time.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT st.id, st.username, st.name, st.roll_number,
               st.face_embedding, st.voice_embedding
        FROM enrollments en
        JOIN students st ON en.student_id = st.id
        WHERE en.subject_id = ?
    """, (subject_id,))
    rows = cursor.fetchall()
    conn.close()
    return [{"students": {"student_id": r[0], "username": r[1], "name": r[2], "roll_number": r[3],
                          "face_embedding": _parse_embedding(r[4]),
                          "voice_embedding": _parse_embedding(r[5])}} for r in rows]

def is_student_enrolled(student_id, subject_id):
    """Check whether a student is already enrolled in a subject"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM enrollments WHERE student_id = ? AND subject_id = ?", (student_id, subject_id))
    result = cursor.fetchone() is not None
    conn.close()
    return result

def get_subject_by_code(code):
    """Find a subject by the code teachers share (join_code / subject_code).

    Returns the same shaped dict as get_teacher_subjects(), or None.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT " + _SUBJECT_COLUMNS + " WHERE s.join_code = ? OR s.subject_code = ?", (code, code))
    row = cursor.fetchone()
    conn.close()
    return _subject_row(row) if row else None

def get_student_subjects(student_id):
    """Get all subjects for a student (same nested shape as the Supabase backend)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.id, s.teacher_id, s.subject_name, s.subject_code, s.join_code, s.section,
        (SELECT COUNT(*) FROM enrollments e WHERE e.subject_id = s.id) AS total_students,
        (SELECT COUNT(DISTINCT a.attendance_date) FROM attendance a WHERE a.subject_id = s.id) AS total_classes
        FROM enrollments en
        JOIN subjects s ON en.subject_id = s.id
        WHERE en.student_id = ?
    """, (student_id,))
    rows = cursor.fetchall()
    conn.close()
    return [{"subjects": _subject_row(r)} for r in rows]

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

def get_subject_total_classes(subject_id):
    """Number of classes actually held for a subject (distinct attendance
    dates with at least one present student).

    The student dashboard must use this for its 'Total' stat: only present
    students ever get an attendance row, so counting a student's own rows
    made Total == Attended for every student - a student who missed
    sessions still showed 100% attendance.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(DISTINCT attendance_date) FROM attendance "
        "WHERE subject_id = ?", (subject_id,))
    result = cursor.fetchone()[0]
    conn.close()
    return result

def create_attendance(logs):
    """Create attendance records.

    Accepts the 'timestamp' key the teacher flow sends (ISO datetime) as
    well as 'attendance_date'.

    One row per student per subject per day: re-taking attendance for the
    same subject on the same day (a second photo batch, or a re-run after
    a mistake) used to insert a second row for every present student, so
    the student dashboard counted them twice and showed Attended > Total
    (e.g. "Attended 2 / Total 1"). Rows already logged for that
    student/subject/date are skipped.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    inserted = []
    for log in logs:
        attendance_date = log.get("attendance_date") or log.get("timestamp")
        if attendance_date and "T" in str(attendance_date):
            attendance_date = str(attendance_date).split("T")[0]
        cursor.execute(
            "SELECT 1 FROM attendance WHERE subject_id = ? AND student_id = ? AND attendance_date = ?",
            (log.get("subject_id"), log.get("student_id"), attendance_date))
        if cursor.fetchone():
            continue
        cursor.execute(
            "INSERT INTO attendance (subject_id, student_id, attendance_date, status) VALUES (?, ?, ?, ?)",
            (log.get("subject_id"), log.get("student_id"), attendance_date, log.get("status", "present"))
        )
        inserted.append(log)
    conn.commit()
    conn.close()
    return inserted

def get_attendance_for_teacher(teacher_id):
    """Get all attendance records for a teacher's subjects.

    Same shape as the Supabase backend: nested 'subjects' dict plus a
    'timestamp' so the Attendance Records tab can group by session.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.id, a.subject_id, a.student_id, a.attendance_date, a.status,
               a.created_at, s.subject_name, s.subject_code
        FROM attendance a
        JOIN subjects s ON a.subject_id = s.id
        WHERE s.teacher_id = ?
    """, (teacher_id,))
    rows = cursor.fetchall()
    conn.close()
    return [{
        "id": r[0],
        "subject_id": r[1],
        "student_id": r[2],
        "attendance_date": r[3],
        "status": r[4],
        "timestamp": r[5],
        "subjects": {"subject_id": r[1], "name": r[6], "subject_code": r[7]},
    } for r in rows]
