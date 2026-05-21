"""API endpoints for person management and detection history"""

from fastapi import APIRouter, HTTPException
from ..database import (
    get_all_persons_with_stats,
    get_person_detections,
    get_person_stats,
    get_all_faces
)

router = APIRouter()


@router.get("/persons")
def get_persons():
    """Get all registered persons with their statistics"""
    try:
        persons = get_all_persons_with_stats()
        return {"persons": persons}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/persons/{person_id}")
def get_person_details(person_id: str):
    """Get detailed information about a specific person"""
    try:
        # Get person info
        all_faces = get_all_faces()
        person = next((f for f in all_faces if f['id'] == person_id), None)
        
        if not person:
            raise HTTPException(status_code=404, detail="Person not found")
        
        # Get statistics
        stats = get_person_stats(person_id)
        
        return {
            "person": person,
            "stats": stats
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/persons/{person_id}/detections")
def get_person_detection_history(person_id: str, limit: int = 100):
    """Get detection history for a specific person"""
    try:
        detections = get_person_detections(person_id=person_id, limit=limit)
        return {"detections": detections}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/detections")
def get_all_detections(camera_id: str = None, limit: int = 100):
    """Get all person detections with optional camera filter"""
    try:
        detections = get_person_detections(camera_id=camera_id, limit=limit)
        return {"detections": detections}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/detections/stats")
def get_detection_stats():
    """Get overall detection statistics"""
    try:
        from ..database import sqlite3, DB_NAME
        
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        # Total detections
        c.execute("SELECT COUNT(*) as total FROM person_detections")
        total = c.fetchone()['total']
        
        # Detections today
        c.execute("""
            SELECT COUNT(*) as today 
            FROM person_detections 
            WHERE DATE(timestamp) = DATE('now')
        """)
        today = c.fetchone()['today']
        
        # Unique persons detected
        c.execute("SELECT COUNT(DISTINCT person_id) as unique_persons FROM person_detections")
        unique_persons = c.fetchone()['unique_persons']
        
        # Top 5 most detected persons
        c.execute("""
            SELECT f.name, COUNT(*) as count
            FROM person_detections pd
            JOIN faces f ON pd.person_id = f.id
            GROUP BY pd.person_id
            ORDER BY count DESC
            LIMIT 5
        """)
        top_persons = [{"name": row['name'], "count": row['count']} for row in c.fetchall()]
        
        conn.close()
        
        return {
            "total_detections": total,
            "detections_today": today,
            "unique_persons": unique_persons,
            "top_persons": top_persons
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
