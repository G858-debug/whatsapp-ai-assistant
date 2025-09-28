#!/usr/bin/env python3
"""
Migration Applier Script
Applies the core tables migration to Supabase using REST API
"""

import os
import sys
import requests
from dotenv import load_dotenv

def apply_migration():
    """Apply the core tables migration to Supabase"""
    
    # Load environment variables
    load_dotenv()
    
    # Get Supabase credentials
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ Error: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        return False
    
    print(f"🔗 Connecting to Supabase: {supabase_url}")
    
    try:
        # Read the migration file
        migration_file = "supabase/migrations/20250928_core_tables.sql"
        
        if not os.path.exists(migration_file):
            print(f"❌ Error: Migration file not found: {migration_file}")
            return False
        
        with open(migration_file, 'r', encoding='utf-8') as f:
            migration_sql = f.read()
        
        print(f"📄 Read migration file: {migration_file}")
        print(f"📊 Migration size: {len(migration_sql)} characters")
        
        # Use Supabase REST API to execute SQL
        headers = {
            'apikey': supabase_key,
            'Authorization': f'Bearer {supabase_key}',
            'Content-Type': 'application/json'
        }
        
        # Execute the SQL using the REST API
        sql_url = f"{supabase_url}/rest/v1/rpc/exec"
        
        payload = {
            'sql': migration_sql
        }
        
        print("🔧 Executing migration SQL...")
        
        response = requests.post(sql_url, json=payload, headers=headers)
        
        if response.status_code == 200:
            print("✅ Migration executed successfully!")
            return True
        else:
            print(f"❌ Migration failed with status {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
    except Exception as e:
        print(f"❌ Error applying migration: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Supabase Migration Applier")
    print("=" * 50)
    
    success = apply_migration()
    
    if success:
        print("\n✅ Migration applied successfully!")
        print("🎯 You can now run the tests again")
    else:
        print("\n❌ Migration failed!")
        print("💡 Try applying manually via Supabase Dashboard")
    
    sys.exit(0 if success else 1)