from src.database.config import supabase

# Try to select all columns without filtering
try:
    response = supabase.table('attendance_logs').select('*').limit(0).execute()
    print("Success! Table can be queried")
    print(f"Response: {response}")
except Exception as e:
    print(f"Error when selecting *: {e}")
    
    # Try to get schema info through Supabase API
    try:
        import json
        from supabase import create_client
        
        # Get the Supabase URL and key from config
        from src.database.config import SUPABASE_URL, SUPABASE_KEY
        
        print(f"\n\nTrying to check Supabase REST API directly...")
        print("Please manually check the Supabase dashboard:")
        print("1. Go to your Supabase project")
        print("2. Navigate to SQL Editor or Tables")
        print("3. Look at the 'attendance_logs' table schema")
        print("4. Share what columns exist in that table")
        print("\nCommon columns might be:")
        print("- timestamp (DateTime)")
        print("- student_id (Integer/UUID)")
        print("- subject_id (Integer/UUID)")
        print("- present (Boolean) - instead of is_present")
        print("- created_at (DateTime)")
        print("- id (Primary Key)")
    except Exception as e2:
        print(f"Error: {e2}")
