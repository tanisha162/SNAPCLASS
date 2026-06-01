# SNAPCLASS - Setup Guide

## Database Setup Instructions

Your app uses **Supabase** as the database. Follow these steps to initialize it:

### Step 1: Access Supabase SQL Editor
1. Go to: https://app.supabase.com
2. Login with your account
3. Select your project: `edhvvfcjmagiziwludmj`
4. Click **SQL Editor** (left sidebar)

### Step 2: Create Database Tables
1. Click **+ New Query**
2. Copy the entire content from `database_schema.sql`
3. Paste it into the SQL editor
4. Click **Run** (or press Ctrl+Enter)
5. Wait for success message ✅

### Step 3: Test the App
Run locally:
```bash
streamlit run app.py
```

You should now be able to:
- ✅ Register as a teacher
- ✅ Register as a student
- ✅ Create subjects
- ✅ Take attendance

---

## Credentials Already Set
✅ `SUPABASE_URL`: Configured in `.streamlit/secrets.toml`
✅ `SUPABASE_KEY`: Configured in `.streamlit/secrets.toml`

## Deployment (Railway)
After database is set up, deploy on Railway:
1. Go to https://railway.app
2. Click **"New Project"** → **"Deploy from GitHub"**
3. Select `tanisha162/SNAPCLASS`
4. Add variables:
   ```
   SUPABASE_URL = https://edhvvfcjmagiziwludmj.supabase.co
   SUPABASE_KEY = [your-key-from-secrets.toml]
   ```
5. Deploy! 🚀

---

## Troubleshooting

**Error: "table 'teachers' does not exist"**
→ Run the SQL schema (Step 2 above)

**Error: "permission denied"**
→ Check RLS policies: Supabase > Authentication > Policies

**App still not connecting?**
→ Verify credentials in `.streamlit/secrets.toml` match your Supabase project
