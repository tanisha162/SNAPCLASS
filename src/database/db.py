from src.database.config import supabase, DB_TYPE
import bcrypt

# ============= Conditional imports based on database type =============
if DB_TYPE == "sqlite":
    from src.database.db_sqlite import (
        hash_pass, check_pass, check_teacher_exists, create_teacher,
        teacher_login, check_student_exists, create_student, student_login,
        get_all_students, get_all_subjects
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
