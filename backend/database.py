"""Database operations for the application"""

import sqlite3
import pickle
import uuid
from datetime import datetime
from .config import DB_NAME


def init_db():
    """Initialize the database with required tables"""
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS alerts
                     (id TEXT PRIMARY KEY, message TEXT, timestamp TEXT, image_path TEXT, video_path TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS faces
                     (id TEXT PRIMARY KEY, name TEXT, type TEXT, encoding BLOB, first_seen TEXT, last_seen TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS person_detections
                     (id TEXT PRIMARY KEY, person_id TEXT, timestamp TEXT, camera_id TEXT, 
                      image_path TEXT, confidence REAL,
                      FOREIGN KEY (person_id) REFERENCES faces(id))''')
        
        # Check if video_path column exists, add it if not (for existing databases)
        try:
            c.execute("SELECT video_path FROM alerts LIMIT 1")
        except sqlite3.OperationalError:
            print("Adicionando coluna video_path à tabela alerts...")
            c.execute("ALTER TABLE alerts ADD COLUMN video_path TEXT")
        
        conn.commit()
        conn.close()
        print("Database initialized.")
    except Exception as e:
        print(f"Database error: {e}")


def get_all_faces():
    """Retrieve all faces from database"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, name, type FROM faces")
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "type": r[2]} for r in rows]


def get_face_encodings():
    """Load all face encodings from database"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, name, type, encoding FROM faces")
    rows = c.fetchall()
    
    encodings = []
    names = []
    types = []
    face_ids = []
    for row in rows:
        face_id, name, f_type, encoding_blob = row
        encoding = pickle.loads(encoding_blob)
        encodings.append(encoding)
        names.append(name)
        types.append(f_type)
        face_ids.append(face_id)
    conn.close()
    
    return encodings, names, types, face_ids


def insert_face(name, face_type, encoding, image_path=None):
    """Insert a new face into database"""
    encoding_blob = pickle.dumps(encoding)
    face_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO faces VALUES (?,?,?,?,?,?)", 
              (face_id, name, face_type, encoding_blob, timestamp, timestamp))
    conn.commit()
    conn.close()
    
    return face_id


def delete_face(face_id):
    """Delete a face from database"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM faces WHERE id = ?", (face_id,))
    conn.commit()
    conn.close()


def insert_alert(message, timestamp, image_path, cam_id=None, video_path=None):
    """Insert a new alert into database"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    alert_id = str(uuid.uuid4())
    c.execute("INSERT INTO alerts VALUES (?,?,?,?,?)", (alert_id, message, timestamp, image_path, video_path))
    conn.commit()
    conn.close()
    return alert_id


def get_recent_alerts(limit=100):
    """Get recent alerts from database"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM alerts ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_alert_stats():
    """Get alert statistics grouped by date"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT substr(timestamp, 1, 8), count(*) FROM alerts GROUP BY substr(timestamp, 1, 8)")
    data = dict(c.fetchall())
    conn.close()
    return data


def insert_person_detection(person_id, camera_id, image_path, confidence=1.0):
    """Insert a person detection into history"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    detection_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    
    c.execute("INSERT INTO person_detections VALUES (?,?,?,?,?,?)", 
              (detection_id, person_id, timestamp, camera_id, image_path, confidence))
    
    # Update last_seen timestamp for the person
    c.execute("UPDATE faces SET last_seen = ? WHERE id = ?", (timestamp, person_id))
    
    conn.commit()
    conn.close()
    return detection_id


def get_person_detections(person_id=None, camera_id=None, limit=100):
    """Get person detection history with optional filters"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    query = """SELECT pd.*, f.name as person_name 
               FROM person_detections pd
               JOIN faces f ON pd.person_id = f.id
               WHERE 1=1"""
    params = []
    
    if person_id:
        query += " AND pd.person_id = ?"
        params.append(person_id)
    if camera_id:
        query += " AND pd.camera_id = ?"
        params.append(camera_id)
    
    query += " ORDER BY pd.timestamp DESC LIMIT ?"
    params.append(limit)
    
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_person_stats(person_id):
    """Get statistics for a specific person"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Total detections
    c.execute("SELECT COUNT(*) as total FROM person_detections WHERE person_id = ?", (person_id,))
    total = c.fetchone()['total']
    
    # Detections by camera
    c.execute("""SELECT camera_id, COUNT(*) as count 
                 FROM person_detections 
                 WHERE person_id = ? 
                 GROUP BY camera_id""", (person_id,))
    by_camera = {row['camera_id']: row['count'] for row in c.fetchall()}
    
    # First and last seen
    c.execute("""SELECT MIN(timestamp) as first_seen, MAX(timestamp) as last_seen 
                 FROM person_detections 
                 WHERE person_id = ?""", (person_id,))
    times = c.fetchone()
    
    conn.close()
    return {
        'total_detections': total,
        'by_camera': by_camera,
        'first_seen': times['first_seen'],
        'last_seen': times['last_seen']
    }


def get_all_persons_with_stats():
    """Get all persons with their detection statistics"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("""
        SELECT f.id, f.name, f.type, f.first_seen, f.last_seen,
               COUNT(pd.id) as detection_count
        FROM faces f
        LEFT JOIN person_detections pd ON f.id = pd.person_id
        GROUP BY f.id
        ORDER BY f.last_seen DESC
    """)
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]
