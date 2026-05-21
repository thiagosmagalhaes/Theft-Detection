"""Auto-register new faces using InsightFace and track person detections"""

import os
import time
import cv2
import uuid
import random
import string
import threading
import numpy as np
from datetime import datetime
from ..config import FACE_REC_AVAILABLE, AUTO_REGISTER_DELAY
from ..database import insert_face, insert_person_detection
from .face_manager import get_face_manager

# InsightFace imports
try:
    import insightface
    from insightface.app import FaceAnalysis
    INSIGHTFACE_AVAILABLE = True
    
    # Initialize InsightFace model (global instance)
    face_app = None
    app_lock = threading.Lock()
    
    def get_face_app():
        """Get or initialize InsightFace model"""
        global face_app
        with app_lock:
            if face_app is None:
                face_app = FaceAnalysis(providers=['CPUExecutionProvider'])
                face_app.prepare(ctx_id=0, det_size=(640, 640))
            return face_app
            
except ImportError:
    INSIGHTFACE_AVAILABLE = False
    print("InsightFace not installed. Face recognition disabled.")

# Auto-register state
auto_register_lock = threading.Lock()
pending_face_registrations = {}  # {(cam_id, track_id): (embedding, frame_crop, first_seen_time)}


def get_face_embedding(face_image):
    """Extract face embedding using InsightFace"""
    if not INSIGHTFACE_AVAILABLE:
        return None
    
    try:
        app = get_face_app()
        
        # InsightFace expects BGR image
        if len(face_image.shape) == 2:
            face_image = cv2.cvtColor(face_image, cv2.COLOR_GRAY2BGR)
        elif face_image.shape[2] == 4:
            face_image = cv2.cvtColor(face_image, cv2.COLOR_BGRA2BGR)
        
        # Detect faces
        faces = app.get(face_image)
        
        if faces and len(faces) > 0:
            # Get the first face's embedding
            embedding = faces[0].embedding
            return np.array(embedding)
        return None
    except Exception as e:
        print(f"[INSIGHTFACE] Error extracting embedding: {e}")
        return None


def compare_faces(embedding1, embedding2, threshold=0.4):
    """Compare two face embeddings using cosine similarity"""
    if embedding1 is None or embedding2 is None:
        return False, 1.0
    
    # Validate dimensions match (InsightFace uses 512-dim)
    embedding1 = np.array(embedding1)
    embedding2 = np.array(embedding2)
    
    if embedding1.shape != embedding2.shape:
        print(f"[INSIGHTFACE] Dimension mismatch: {embedding1.shape} vs {embedding2.shape} - skipping")
        return False, 1.0
    
    # Additional validation: InsightFace should be 512-dim
    if embedding1.shape[0] != 512:
        print(f"[INSIGHTFACE] Warning: Expected 512-dim, got {embedding1.shape[0]}-dim (old encoding?)")
        return False, 1.0
    
    # Cosine similarity
    from scipy.spatial.distance import cosine
    try:
        distance = cosine(embedding1, embedding2)
        is_match = distance < threshold
        return is_match, distance
    except Exception as e:
        print(f"[INSIGHTFACE] Error comparing faces: {e}")
        return False, 1.0


def find_matching_person(face_embedding):
    """Find if this face matches any known person in database"""
    if not INSIGHTFACE_AVAILABLE or face_embedding is None:
        return None, None, 1.0
    
    face_manager = get_face_manager()
    encodings, names, types, face_ids = face_manager.get_faces()
    
    if len(encodings) == 0:
        return None, None, 1.0
    
    best_match_idx = None
    best_distance = 1.0
    valid_comparisons = 0
    
    for idx, known_embedding in enumerate(encodings):
        is_match, distance = compare_faces(face_embedding, known_embedding)
        if is_match and distance < best_distance:
            best_distance = distance
            best_match_idx = idx
            valid_comparisons += 1
    
    if valid_comparisons == 0:
        print(f"[INSIGHTFACE] Warning: No valid embeddings to compare (database may have old 128-dim encodings)")
    
    if best_match_idx is not None:
        return face_ids[best_match_idx], names[best_match_idx], best_distance
    
    return None, None, best_distance


def auto_register_or_track_person(face_image, cam_id, track_id):
    """Auto-register new person or track existing person detection"""
    if not INSIGHTFACE_AVAILABLE:
        return None
    
    print(f"[AUTO-REG] Processing person - cam:{cam_id}, track:{track_id}")
    
    # Extract face embedding
    face_embedding = get_face_embedding(face_image)
    if face_embedding is None:
        print(f"[AUTO-REG] Could not extract face embedding")
        return None
    
    # Check if this person already exists in database
    person_id, person_name, confidence = find_matching_person(face_embedding)
    
    if person_id:
        # Person already registered - just add to detection history
        print(f"[AUTO-REG] Person recognized: {person_name} (confidence: {1-confidence:.2f})")
        
        # Save detection snapshot
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        detection_image_path = f"faces/detections/{person_name}_{timestamp}.jpg"
        os.makedirs("faces/detections", exist_ok=True)
        cv2.imwrite(detection_image_path, face_image)
        
        # Insert detection record
        insert_person_detection(person_id, cam_id, detection_image_path, confidence=1-confidence)
        
        return person_id
    
    # New person - use delay-based registration
    registration_key = (cam_id, track_id)
    current_time = time.time()
    
    should_register = False
    with auto_register_lock:
        if registration_key in pending_face_registrations:
            first_seen_time = pending_face_registrations[registration_key][2]
            elapsed = current_time - first_seen_time
            print(f"[AUTO-REG] New person tracked. Elapsed: {elapsed:.1f}s (need {AUTO_REGISTER_DELAY}s)")
            
            if elapsed >= AUTO_REGISTER_DELAY:
                # Person has been seen long enough, register it
                print(f"[AUTO-REG] Time threshold met! Registering new person...")
                del pending_face_registrations[registration_key]
                should_register = True
            else:
                # Update with latest image
                pending_face_registrations[registration_key] = (face_embedding, face_image, first_seen_time)
                return None
        else:
            # First time seeing this person
            print(f"[AUTO-REG] New person detected. Starting tracking...")
            pending_face_registrations[registration_key] = (face_embedding, face_image, current_time)
            return None
    
    if not should_register:
        return None
    
    # Register new person
    print(f"[AUTO-REG] Registering new person...")
    
    # Generate name
    random_suffix = ''.join(random.choices(string.digits, k=4))
    name = f"Person_{random_suffix}"
    
    # Save main face image
    os.makedirs("faces", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    face_filename = f"faces/face_{timestamp}_{random_suffix}.jpg"
    cv2.imwrite(face_filename, face_image)
    print(f"[AUTO-REG] Saved face image: {face_filename}")
    
    # Save to database
    new_person_id = insert_face(name, "whitelist", face_embedding, image_path=face_filename)
    print(f"[AUTO-REG] Registered as: {name} (ID: {new_person_id})")
    
    # Add first detection record
    detection_image_path = f"faces/detections/{name}_{timestamp}.jpg"
    os.makedirs("faces/detections", exist_ok=True)
    cv2.imwrite(detection_image_path, face_image)
    insert_person_detection(new_person_id, cam_id, detection_image_path, confidence=1.0)
    
    # Reload face manager
    face_manager = get_face_manager()
    face_manager.reload()
    
    print(f"[AUTO-REG] Successfully registered new person: {name}")
    return new_person_id


def cleanup_pending_registrations():
    """Remove stale pending registrations (people who left)"""
    current_time = time.time()
    stale_threshold = AUTO_REGISTER_DELAY * 3  # 3x the registration delay
    
    with auto_register_lock:
        keys_to_remove = []
        for key, (_, _, first_seen) in pending_face_registrations.items():
            if current_time - first_seen > stale_threshold:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del pending_face_registrations[key]
        
        if keys_to_remove:
            print(f"[AUTO-REG] Cleaned up {len(keys_to_remove)} stale pending registrations")


# Legacy function for backward compatibility (deprecated)
def auto_register_new_face(face_encoding, face_image, cam_id, track_id, has_valid_encoding=True):
    """Legacy function - use auto_register_or_track_person instead"""
    return auto_register_or_track_person(face_image, cam_id, track_id)
