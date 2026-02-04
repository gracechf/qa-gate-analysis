import pandas as pd
from pathlib import Path
import os
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import config

# Use settings from config.py
DATABASE_URL = config.get_database_url()

# Create SQLAlchemy engine
# Use pool_pre_ping to handle dropped connections in cloud environments
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
Session = sessionmaker(bind=engine)

def init_db():
    """Initialize the database with required tables using SQLAlchemy."""
    with engine.connect() as conn:
        # PostgreSQL/SQLite compatible SQL
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
        
        # Handle serial vs integer autoincrement for SQLite
        if 'sqlite' in str(engine.url):
            # SQLAlchemy handles the ID mapping generally, but we'll ensure table exists
            pass
            
        conn.commit()

def insert_records(df: pd.DataFrame) -> tuple[int, int]:
    """
    Insert records into the database with deduplication.
    """
    new_count = 0
    dup_count = 0
    
    with engine.begin() as conn:
        for _, row in df.iterrows():
            issue_key = row.get('Issue key', '')
            if not issue_key:
                continue
                
            # Check if exists
            result = conn.execute(text('SELECT 1 FROM qa_records WHERE issue_key = :key'), {'key': issue_key})
            if result.fetchone():
                dup_count += 1
                continue
            
            # Insert
            try:
                conn.execute(text('''
                    INSERT INTO qa_records (
                        issue_key, summary, assignee, created,
                        start_quantity, rejected_quantity, passed_quantity,
                        conclusion, rejected_sensors, raw_data
                    ) VALUES (
                        :issue_key, :summary, :assignee, :created,
                        :start_quantity, :rejected_quantity, :passed_quantity,
                        :conclusion, :rejected_sensors, :raw_data
                    )
                '''), {
                    'issue_key': issue_key,
                    'summary': row.get('Summary', ''),
                    'assignee': row.get('Assignee', ''),
                    'created': row.get('Created', ''),
                    'start_quantity': row.get('Custom field (Start Quantity)', 0),
                    'rejected_quantity': row.get('Custom field (Rejected Quantity)', 0),
                    'passed_quantity': row.get('Passed Quantity', 0),
                    'conclusion': row.get('Custom field (Conclusion)', ''),
                    'rejected_sensors': row.get('Custom field (Rejected Sensors)', ''),
                    'raw_data': row.to_json()
                })
                new_count += 1
            except Exception as e:
                print(f"Error inserting {issue_key}: {e}")
                dup_count += 1
                
    return new_count, dup_count

def get_all_records() -> pd.DataFrame:
    """Retrieve all records as a DataFrame."""
    query = '''
        SELECT 
            issue_key as "Issue key",
            summary as "Summary",
            assignee as "Assignee",
            created as "Created",
            start_quantity as "Custom field (Start Quantity)",
            rejected_quantity as "Custom field (Rejected Quantity)",
            passed_quantity as "Passed Quantity",
            conclusion as "Custom field (Conclusion)",
            rejected_sensors as "Custom field (Rejected Sensors)"
        FROM qa_records
        ORDER BY created DESC
    '''
    
    with engine.connect() as conn:
        df = pd.read_sql_query(text(query), conn)
    
    return df

def get_record_count() -> int:
    """Get total number of records."""
    with engine.connect() as conn:
        result = conn.execute(text('SELECT COUNT(*) FROM qa_records'))
        count = result.scalar()
    return count

def clear_all_data():
    """Delete all records."""
    with engine.begin() as conn:
        conn.execute(text('DELETE FROM qa_records'))

# Initialize on import
init_db()
