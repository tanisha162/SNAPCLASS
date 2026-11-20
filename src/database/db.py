import json
import secrets

from src.database.config import supabase, DB_TYPE
import bcrypt

# ============= Conditional imports based on database type =============
if DB_TYPE == "sqlite":
    from src.database.db_sqlite import (
        init_db, hash_pass, check_pass, check_teacher_exists, create_teacher,
        teacher_login, check_student_exists, create_student, student_login,
        get_all_students, get_all_subjects, get_teacher_subjects, create_subject,
        enroll_student_to_subject, unenroll_student_to_subject, get_student_subjects,
        get_student_attendance, create_attendance, get_attendance_for_teacher,
        get_enrolled_students, is_student_enrolled, get_subject_by_code
    )
    # The SQLite backend is only usable once its tables exist; nothing else
    # in the app called init_db(), so every local-mode DB call failed with
    # "no such table". Create them when this backend is selected.
    init_db()
else:
    # ============= Supabase implementations =============
    def hash_pass(pwd):
        return bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()

    def check_pass(pwd, hashed):
        return bcrypt.checkpw(pwd.encode(), hashed.encode())

    def check_teacher_exists(username):
        response = supabase.table("teachers").select("username").eq("username", username).execute()
        return len(response.data) > 0

    def create_teacher(username, password, name):
        data = {"username": username, "password": hash_pass(password), "name": name}
        response = supabase.table("teachers").insert(data).execute()
        if response.data:
            for record in response.data:
                if 'id' in record:
                    record['teacher_id'] = record.pop('id')
        return response.data

    def teacher_login(username, password):
        response = supabase.table("teachers").select("*").eq("username", username).execute()
        if response.data:
            teacher = response.data[0]
            if check_pass(password, teacher['password']):
                if 'id' in teacher:
                    teacher['teacher_id'] = teacher.pop('id')
                return teacher
        return None

    def check_student_exists(username):
        response = supabase.table("students").select("username").eq("username", username).execute()
        return len(response.data) > 0

    def create_student(username, password=None, name=None, roll_number=None,
                       face_embedding=None, voice_embedding=None):
        # FaceID registration (student_screen.py) has no password: it calls
        # create_student(name, face_embedding=..., voice_embedding=...).
        # A random hash nobody knows keeps password login impossible for a
        # face-only account; embeddings are stored as JSON text.
        if name is None:
            name = username
        if password is None:
            password_hash = bcrypt.hashpw(
                secrets.token_bytes(32), bcrypt.gensalt()).decode()
        else:
            password_hash = hash_pass(password)
        data = {"username": username, "password": password_hash, "name": name,
                "roll_number": roll_number}
        if face_embedding is not None:
            data["face_embedding"] = json.dumps(face_embedding)
        if voice_embedding is not None:
            data["voice_embedding"] = json.dumps(voice_embedding)
        response = supabase.table("students").insert(data).execute()
        if response.data:
            for record in response.data:
                if 'id' in record:
                    record['student_id'] = record.pop('id')
        return response.data

    def student_login(username, password):
        response = supabase.table("students").select("*").eq("username", username).execute()
        if response.data:
            student = response.data[0]
            if check_pass(password, student['password']):
                if 'id' in student:
                    student['student_id'] = student.pop('id')
                return student
        return None

    def get_all_students():
        response = supabase.table("students").select("*").execute()
        if response.data:
            for record in response.data:
                if 'id' in record:
                    record['student_id'] = record.pop('id')
                # Embeddings are stored as JSON text; the face pipeline
                # expects lists (a jsonb column already returns lists).
                for key in ("face_embedding", "voice_embedding"):
                    if isinstance(record.get(key), str):
                        try:
                            record[key] = json.loads(record[key])
                        except ValueError:
                            pass
        return response.data

    def _shape_subject(record, total_students=None, total_classes=None):
        """Shape a subjects row (top-level or embedded subjects(*) dict)
        the way the screens expect - the same shape the SQLite backend
        returns: 'name' from subject_name, plus 'section' and the
        enrolment/class totals the teacher screens read.

        The subjects table (database_schema.sql) has no 'section' column,
        so reads carry None there unless the row already has one.
        """
        if "id" in record:
            record["subject_id"] = record.pop("id")
        if "subject_name" in record:
            record["name"] = record.pop("subject_name")
        record.setdefault("section", None)
        if total_students is not None:
            record["total_students"] = total_students
        if total_classes is not None:
            record["total_classes"] = total_classes
        return record

    def _subject_totals(subject_id):
        """Enrolment / class totals for one subject, matching the SQLite
        backend: total_students counts enrollments, total_classes counts
        distinct attendance dates."""
        enrolled = supabase.table("enrollments").select(
            "id", count="exact").eq("subject_id", subject_id).execute()
        classes = supabase.table("attendance").select(
            "attendance_date").eq("subject_id", subject_id).execute()
        total_classes = len({row.get("attendance_date")
                             for row in (classes.data or [])})
        return (enrolled.count or 0), total_classes

    def get_all_subjects():
        response = supabase.table('subjects').select("*").execute()
        if response.data:
            for record in response.data:
                total_students, total_classes = _subject_totals(
                    record.get("id"))
                _shape_subject(record, total_students, total_classes)
        return response.data

    def get_teacher_subjects(teacher_id):
        response = supabase.table('subjects').select("*").eq('teacher_id', teacher_id).execute()
        if response.data:
            for record in response.data:
                total_students, total_classes = _subject_totals(
                    record.get("id"))
                _shape_subject(record, total_students, total_classes)
        return response.data

    def create_subject(subject_code, name, section, teacher_id):
        # The subjects table (database_schema.sql) has subject_name, not
        # 'name', and no 'section' column - PostgREST rejects inserts
        # carrying unknown columns, so sending 'name'/'section' made
        # 'Create Subject' fail every time in Supabase mode. Insert only
        # real columns; the section the teacher typed is returned on the
        # created record (it is not persisted in Supabase mode).
        data = {"subject_code": subject_code, "subject_name": name,
                "teacher_id": teacher_id, "join_code": subject_code}
        response = supabase.table("subjects").insert(data).execute()
        if response.data:
            for record in response.data:
                _shape_subject(record, total_students=0, total_classes=0)
                record["section"] = section
        return response.data
    
    def enroll_student_to_subject(student_id, subject_id):
        data = {'student_id': student_id, 'subject_id': subject_id}
        response = supabase.table('enrollments').insert(data).execute()
        return response.data
    
    def unenroll_student_to_subject(student_id, subject_id):
        response = supabase.table('enrollments').delete().eq('student_id', student_id).eq('subject_id', subject_id).execute()
        return response.data
    
    def get_student_subjects(student_id):
        response = supabase.table('enrollments').select('*, subjects(*)').eq('student_id', student_id).execute()
        if response.data:
            for record in response.data:
                if 'subjects' in record and isinstance(record['subjects'], dict):
                    # The student dashboard reads sub['name'] /
                    # sub['section']; the embedded row carries
                    # 'subject_name' and no 'section'.
                    _shape_subject(record['subjects'])
        return response.data

    def get_student_attendance(student_id):
        response = supabase.table('attendance').select('*, subjects(*)').eq('student_id', student_id).execute()
        if response.data:
            for record in response.data:
                if 'subjects' in record and isinstance(record['subjects'], dict):
                    _shape_subject(record['subjects'])
        return response.data
    
    def create_attendance(logs):
        # The teacher/voice flows send a 'timestamp' key (ISO datetime),
        # but the attendance table has no 'timestamp' column - it has
        # attendance_date / status / created_at (see database_schema.sql).
        # PostgREST rejects inserts carrying an unknown column, so passing
        # the logs through verbatim made 'Confirm & Save' fail every time
        # in Supabase mode. Normalise to the real columns, mirroring the
        # SQLite backend.
        rows = []
        for log in logs:
            attendance_date = log.get("attendance_date") or log.get("timestamp")
            if attendance_date and "T" in str(attendance_date):
                attendance_date = str(attendance_date).split("T")[0]
            rows.append({
                "subject_id": log.get("subject_id"),
                "student_id": log.get("student_id"),
                "attendance_date": attendance_date,
                "status": log.get("status", "present"),
            })
        if not rows:
            return []
        response = supabase.table('attendance').insert(rows).execute()
        return response.data

    def get_attendance_for_teacher(teacher_id):
        response = supabase.table('attendance').select("*, subjects!inner(*)").eq('subjects.teacher_id', teacher_id).execute()
        if response.data:
            for record in response.data:
                if 'subjects' in record and isinstance(record['subjects'], dict):
                    # The records tab reads r['subjects']['name'] /
                    # r['subjects']['subject_code']; the embedded row
                    # carries 'subject_name' and no 'section'.
                    _shape_subject(record['subjects'])
                # teacher_tab_attendance_records groups and displays by a
                # 'timestamp' key; the table only has created_at, so expose
                # it under that name (as the SQLite backend does).
                record['timestamp'] = record.get('created_at')
        return response.data

    def get_enrolled_students(subject_id):
        # The attendance screens used to query a 'subject_students' table
        # directly; that table does not exist (enrollments live in
        # 'enrollments') and the client is None in local mode, so Run Face
        # Analysis / Voice Attendance crashed every time.
        response = supabase.table('enrollments').select('*, students(*)').eq('subject_id', subject_id).execute()
        if response.data:
            for record in response.data:
                if 'students' in record and isinstance(record['students'], dict):
                    if 'id' in record['students']:
                        record['students']['student_id'] = record['students'].pop('id')
                    # dialog_voice_attendance.py reads voice_embedding here.
                    for key in ("face_embedding", "voice_embedding"):
                        if isinstance(record['students'].get(key), str):
                            try:
                                record['students'][key] = json.loads(record['students'][key])
                            except ValueError:
                                pass
        return response.data

    def is_student_enrolled(student_id, subject_id):
        response = supabase.table('enrollments').select('id').eq('student_id', student_id).eq('subject_id', subject_id).execute()
        return len(response.data) > 0

    def get_subject_by_code(code):
        # Teachers share the subject_code (which create_subject also stores
        # as join_code); match either so a code typed from a share card works.
        response = supabase.table('subjects').select('*').eq('join_code', code).execute()
        if not response.data:
            response = supabase.table('subjects').select('*').eq('subject_code', code).execute()
        if response.data:
            subject = response.data[0]
            if 'id' in subject:
                subject['subject_id'] = subject.pop('id')
            return subject
        return None
