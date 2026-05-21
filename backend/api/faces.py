"""Face recognition API endpoints"""

import asyncio
import os
import uuid
from fastapi import APIRouter, UploadFile, File, Form
from ..config import FACE_REC_AVAILABLE
from ..database import get_all_faces, delete_face as db_delete_face, insert_face

router = APIRouter()


@router.post("/faces/register")
async def register_face(file: UploadFile = File(...), name: str = Form(...), type: str = Form("blacklist")):
    """Register a new face"""
    if not FACE_REC_AVAILABLE:
        return {"status": "error", "message": "Face Rec not available"}
    
    temp_filename = f"temp_{uuid.uuid4()}.jpg"
    
    def _process_sync():
        import cv2
        from ..face_recognition.auto_register import get_face_embedding
        
        # Load image
        image = cv2.imread(temp_filename)
        if image is None:
            return {"status": "error", "message": "Failed to load image"}
        
        # Extract embedding using InsightFace
        embedding = get_face_embedding(image)
        
        if embedding is not None:
            face_id = insert_face(name, type, embedding)
            
            # Reload faces in face manager
            from ..face_recognition.face_manager import get_face_manager
            face_manager = get_face_manager()
            face_manager.reload()
            
            return {"status": "success", "message": f"Face registered: {name}"}
        else:
            return {"status": "error", "message": "No face found in image"}
    
    try:
        # Save uploaded file
        with open(temp_filename, "wb") as buffer:
            buffer.write(await file.read())
        
        # Process in background thread (heavy CPU + DB operations)
        result = await asyncio.to_thread(_process_sync)
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)


@router.get("/faces")
async def get_faces():
    """Get all registered faces"""
    try:
        return await asyncio.to_thread(get_all_faces)
    except Exception as e:
        return {"error": str(e)}


@router.delete("/faces/{face_id}")
async def delete_face(face_id: str):
    """Delete a face by ID"""
    def _delete_sync():
        db_delete_face(face_id)
        # Reload faces in face manager
        from ..face_recognition import FaceManager
        face_manager = FaceManager()
        face_manager.load_known_faces()
    
    try:
        await asyncio.to_thread(_delete_sync)
        return {"status": "success", "message": "Face deleted successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
