"""
Migration script to update database schema for person detection tracking
Run this once to upgrade existing database
"""

import sqlite3
import os
from datetime import datetime

DB_NAME = "theft_detection.db"

def migrate_database():
    """Migrate database to new schema with person detection tracking"""
    
    if not os.path.exists(DB_NAME):
        print("No existing database found. Will be created on first run.")
        return
    
    print("Starting database migration...")
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    try:
        # Check if faces table needs migration (add first_seen and last_seen)
        c.execute("PRAGMA table_info(faces)")
        columns = [col[1] for col in c.fetchall()]
        
        if 'first_seen' not in columns:
            print("Adding first_seen and last_seen columns to faces table...")
            current_time = datetime.now().isoformat()
            
            # Add new columns
            c.execute("ALTER TABLE faces ADD COLUMN first_seen TEXT")
            c.execute("ALTER TABLE faces ADD COLUMN last_seen TEXT")
            
            # Set default values for existing records
            c.execute("UPDATE faces SET first_seen = ?, last_seen = ?", (current_time, current_time))
            print("✓ Updated faces table")
        else:
            print("✓ Faces table already up to date")
        
        # Check if person_detections table exists
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='person_detections'")
        if not c.fetchone():
            print("Creating person_detections table...")
            c.execute('''CREATE TABLE person_detections
                         (id TEXT PRIMARY KEY, 
                          person_id TEXT, 
                          timestamp TEXT, 
                          camera_id TEXT, 
                          image_path TEXT, 
                          confidence REAL,
                          FOREIGN KEY (person_id) REFERENCES faces(id))''')
            print("✓ Created person_detections table")
        else:
            print("✓ Person_detections table already exists")
        
        conn.commit()
        print("\n✅ Database migration completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()
