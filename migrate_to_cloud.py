"""
Migration script to move data from local SQLite to Cloud PostgreSQL.
Usage: 
1. Set up your Supabase project and get the connection string.
2. Add the connection string to your environment as DATABASE_URL.
3. Run: python migrate_to_cloud.py
"""

import pandas as pd
import sqlite3
import sqlalchemy
from sqlalchemy import create_engine, text
import os
from pathlib import Path

# Config
SQLITE_DB = Path('data/qa_gate_data.db')

def migrate():
    # 1. Get Destination Database URL
    dest_url = os.getenv('DATABASE_URL')
    if not dest_url:
        print("❌ Error: DATABASE_URL environment variable not set.")
        print("Example: set DATABASE_URL=postgresql://user:pass@host:port/db")
        return

    if not SQLITE_DB.exists():
        print(f"❌ Error: Local database {SQLITE_DB} not found.")
        return

    print(f"🔗 Connecting to destination: {dest_url.split('@')[-1]}") # Log host only for safety
    dest_engine = create_engine(dest_url)

    # 2. Read from SQLite
    print(f"📖 Reading data from {SQLITE_DB}...")
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    df = pd.read_sql_query("SELECT * FROM qa_records", sqlite_conn)
    sqlite_conn.close()

    if df.empty:
        print("⚠️ Local database is empty. Nothing to migrate.")
        return

    print(f"✅ Found {len(df)} records.")

    # 3. Write to Cloud (PostgreSQL)
    print("🚀 Pushing to cloud database...")
    
    # Define column types for SQLAlchemy to ensure JSON compatibility if needed
    # But read_sql_query already gave us a clean DF
    
    try:
        # Ensure table exists with correct schema
        with dest_engine.connect() as conn:
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS qa_records (
                    id SERIAL PRIMARY KEY,
                    issue_key TEXT UNIQUE NOT NULL,
                    summary TEXT,
                    assignee TEXT,
                    created TEXT,
                    start_quantity DOUBLE PRECISION,
                    rejected_quantity DOUBLE PRECISION,
                    passed_quantity DOUBLE PRECISION,
                    conclusion TEXT,
                    rejected_sensors TEXT,
                    raw_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            '''))
            conn.commit()

        # Remove the 'id' column from dataframe to let Postgres handle auto-increment
        if 'id' in df.columns:
            df = df.drop(columns=['id'])

        # Use to_sql for bulk insert
        df.to_sql('qa_records', dest_engine, if_exists='append', index=False)
        print(f"🎉 Successfully migrated {len(df)} records to the cloud!")

    except Exception as e:
        print(f"❌ Migration failed: {e}")

if __name__ == "__main__":
    migrate()
