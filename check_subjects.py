from src.database.db import get_all_subjects

try:
    subjects = get_all_subjects()
    print("=== All Subjects in Database ===\n")
    
    if subjects:
        for subject in subjects:
            print(f"Subject Code: {subject.get('subject_code')}")
            print(f"Name: {subject.get('name')}")
            print(f"Section: {subject.get('section')}")
            print(f"Subject ID: {subject.get('subject_id')}")
            print("---")
    else:
        print("No subjects found in database. You need to create subjects first.")
        print("\nTo create a subject:")
        print("1. Click 'Teacher Portal' on home page")
        print("2. Register as a teacher or login")
        print("3. Go to 'Create Subject' section")
        print("4. Fill in subject code, name, and section")
        print("5. Click 'Create Subject'")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
