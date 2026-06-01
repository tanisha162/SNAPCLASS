import streamlit as st

# Try to use Supabase, fall back to SQLite if not configured
try:
    from supabase import create_client, Client
    
    # Check if Supabase credentials are available
    if "SUPABASE_URL" in st.secrets and "SUPABASE_KEY" in st.secrets:
        supabase: Client = create_client(
            st.secrets["SUPABASE_URL"],
            st.secrets["SUPABASE_KEY"]
        )
        DB_TYPE = "supabase"
    else:
        raise KeyError("Supabase credentials not found")
        
except Exception as e:
    # Fall back to SQLite for local development
    st.warning("⚠️ Using Local SQLite Database (Not Connected to Supabase)")
    st.info("To use Supabase: Add credentials to .streamlit/secrets.toml")
    DB_TYPE = "sqlite"
    supabase = None