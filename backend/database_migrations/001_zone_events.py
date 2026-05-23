"""
Migration: Add zone_object_events table for tracking object movements in/out of zones
"""

import sqlite3
from ..config import DB_NAME


def migrate():
    """Create zone_object_events table"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Create zone events table
    c.execute('''
        CREATE TABLE IF NOT EXISTS zone_object_events (
            id TEXT PRIMARY KEY,
            camera_id TEXT NOT NULL,
            zone_name TEXT NOT NULL,
            object_class TEXT NOT NULL,
            object_id INTEGER,
            event_type TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            duration_seconds REAL,
            confidence REAL,
            bbox_x1 INTEGER,
            bbox_y1 INTEGER,
            bbox_x2 INTEGER,
            bbox_y2 INTEGER,
            image_path TEXT,
            video_path TEXT
        )
    ''')
    
    # Create indexes for common queries
    c.execute('CREATE INDEX IF NOT EXISTS idx_zone_events_camera ON zone_object_events(camera_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_zone_events_timestamp ON zone_object_events(timestamp)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_zone_events_type ON zone_object_events(event_type)')
    
    conn.commit()
    conn.close()
    print("✓ Migration 001_zone_events completed")


if __name__ == "__main__":
    migrate()
