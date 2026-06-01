from src.database.config import supabase
import json

try:
    # First get a valid student and subject
    students = supabase.table('students').select('id').limit(1).execute()
    subjects = supabase.table('subjects').select('id').limit(1).execute()
    
    if not students.data or not subjects.data:
        print("ERROR: No students or subjects in database")
        print("Create a teacher and subject first, then a student and enroll them")
        exit(1)
    
    student_id = students.data[0]['id']
    subject_id = subjects.data[0]['id']
    
    print(f"Using real IDs: student_id={student_id}, subject_id={subject_id}")
    print("\n" + "="*50)
    
    # Try different column combinations
    test_columns = [
        # Try with just required fields
        {'student_id': student_id, 'subject_id': subject_id, 'timestamp': '2024-01-01T00:00:00'},
        # Try with boolean attendance
        {'student_id': student_id, 'subject_id': subject_id, 'timestamp': '2024-01-01T00:00:00', 'attended': True},
        # Try other possible column names
        {'student_id': student_id, 'subject_id': subject_id, 'timestamp': '2024-01-01T00:00:00', 'status': 'present'},
        {'student_id': student_id, 'subject_id': subject_id, 'timestamp': '2024-01-01T00:00:00', 'marked': True},
    ]
    
    for i, cols in enumerate(test_columns):
        try:
            response = supabase.table('attendance_logs').insert(cols).execute()
            print(f"\n✅ SUCCESS! Columns that work: {list(cols.keys())}")
            print(f"Full payload: {cols}")
            print("\nUse these columns for attendance inserts:")
            for key in cols.keys():
                print(f"  - {key}")
            break
        except Exception as e:
            print(f"\n❌ Attempt {i+1} - Columns: {list(cols.keys())}")
            print(f"Error: {str(e)[:100]}")
            
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
