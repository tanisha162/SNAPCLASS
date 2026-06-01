from src.database.config import supabase, DB_TYPE
import bcrypt

# ============= Conditional imports based on database type =============
if DB_TYPE == "sqlite":
    from src.database.db_sqlite import (
        hash_pass, check_pass, check_teacher_exists, create_teacher,
        teacher_login, check_student_exists, create_student, student_login,
        get_all_students, get_all_subjects, get_teacher_subjects, create_subject,
        enroll_student_to_subject, unenroll_student_to_subject, get_student_subjects,
        get_student_attendance, create_attendance, get_attendance_for_teacher
    )
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

    def create_student(username, password, name, roll_number=None):
        data = {"username": username, "password": hash_pass(password), "name": name, "roll_number": roll_number}
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
        return response.data

    def get_all_subjects():
        response = supabase.table('subjects').select("*").execute()
        if response.data:
            for record in response.data:
                if 'id' in record:
                    record['subject_id'] = record.pop('id')
        return response.data
    
    def get_teacher_subjects(teacher_id):
        response = supabase.table('subjects').select("*").eq('teacher_id', teacher_id).execute()
        if response.data:
            for record in response.data:
                if 'id' in record:
                    record['subject_id'] = record.pop('id')
        return response.data
    
    def create_subject(subject_code, name, section, teacher_id):
        data = {"subject_code": subject_code, "name": name, "section": section, "teacher_id": teacher_id, "join_code": subject_code}
        response = supabase.table("subjects").insert(data).execute()
        if response.data:
            for record in response.data:
                if 'id' in record:
                    record['subject_id'] = record.pop('id')
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
                    if 'id' in record['subjects']:
                        record['subjects']['subject_id'] = record['subjects'].pop('id')
        return response.data
    
    def get_student_attendance(student_id):
        response = supabase.table('attendance').select('*, subjects(*)').eq('student_id', student_id).execute()
        if response.data:
            for record in response.data:
                if 'subjects' in record and isinstance(record['subjects'], dict):
                    if 'id' in record['subjects']:
                        record['subjects']['subject_id'] = record['subjects'].pop('id')
        return response.data
    
    def create_attendance(logs):
        response = supabase.table('attendance').insert(logs).execute()
        return response.data
    
    def get_attendance_for_teacher(teacher_id):
        response = supabase.table('attendance').select("*, subjects!inner(*)").eq('subjects.teacher_id', teacher_id).execute()
        if response.data:
            for record in response.data:
                if 'subjects' in record and isinstance(record['subjects'], dict):
                    if 'id' in record['subjects']:
                        record['subjects']['subject_id'] = record['subjects'].pop('id')
        return response.data
