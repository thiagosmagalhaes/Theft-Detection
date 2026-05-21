"""Face recognition manager using DeepFace (Windows-friendly)"""

import os
import threading
import numpy as np
from ..config import FACE_REC_AVAILABLE
from ..database import get_face_encodings


class FaceManager:
    """Manager for known face embeddings using DeepFace"""
    
    def __init__(self):
        self.known_face_encodings = []
        self.known_face_names = []
        self.known_face_types = []  # 'blacklist' or 'whitelist'
        self.known_face_ids = []  # Face IDs from database
        self.lock = threading.Lock()
        self.load_known_faces()
    
    def load_known_faces(self):
        """Load known faces from database"""
        if not FACE_REC_AVAILABLE:
            return
        
        try:
            encodings, names, types, face_ids = get_face_encodings()
            
            with self.lock:
                self.known_face_encodings = encodings
                self.known_face_names = names
                self.known_face_types = types
                self.known_face_ids = face_ids
                
            print(f"Loaded {len(self.known_face_names)} faces.")
        except Exception as e:
            print(f"Error loading faces: {e}")
    
    def get_faces(self):
        """Get current known faces (thread-safe)"""
        with self.lock:
            return (
                self.known_face_encodings.copy(),
                self.known_face_names.copy(),
                self.known_face_types.copy(),
                self.known_face_ids.copy()
            )
    
    def reload(self):
        """Reload faces from database"""
        self.load_known_faces()


# Global face manager instance
face_manager_instance = None

def get_face_manager():
    """Get or create global face manager instance"""
    global face_manager_instance
    if face_manager_instance is None:
        face_manager_instance = FaceManager()
    return face_manager_instance
