from src.database.config import supabase

# Get table info
try:
    # Try to get one record to see what columns exist
    response = supabase.table('attendance_logs').select('*').limit(1).execute()
    
    if response.data:
        print("Columns in attendance_logs table:")
        print(list(response.data[0].keys()))
    else:
        print("No records in attendance_logs table")
        print("\nTrying to query with specific columns to find the right schema...")
        
        # Try different possible column names
        possible_names = ['present', 'is_present', 'attended', 'attendance', 'status']
        for col_name in possible_names:
            try:
                test = supabase.table('attendance_logs').select(f'id, student_id, subject_id, timestamp, {col_name}').limit(1).execute()
                print(f"✓ Column '{col_name}' exists!")
            except:
                print(f"✗ Column '{col_name}' does not exist")
                
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
