"""
Test Supabase Connection
Run this to diagnose connection issues
"""
import sys
from src.database.config import supabase

def test_connection():
    print("🔍 Testing Supabase Connection...")
    print("-" * 50)
    
    try:
        # Try a simple query to test connection
        print("Attempting to connect and query 'teachers' table...")
        response = supabase.table("teachers").select("*", count="exact").execute()
        
        print(f"✅ SUCCESS! Connected to Supabase")
        print(f"   Teachers in database: {response.count or 0}")
        print(f"   Records retrieved: {len(response.data) if response.data else 0}")
        print()
        print("🎉 Database is ready to use!")
        return True
        
    except Exception as e:
        print(f"❌ CONNECTION FAILED")
        print(f"   Error Type: {type(e).__name__}")
        print(f"   Error Message: {str(e)}")
        print()
        print("⚠️  TROUBLESHOOTING:")
        print("   1. Check if .streamlit/secrets.toml has valid credentials")
        print("   2. Verify SUPABASE_URL starts with 'https://'")
        print("   3. Verify SUPABASE_KEY is not empty")
        print("   4. Check if your Supabase project is active")
        print("   5. Verify the 'teachers' table exists in Supabase")
        print("      → Run database_schema.sql in Supabase SQL Editor")
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
