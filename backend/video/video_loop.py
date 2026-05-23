"""Main video processing loop"""

import cv2
import base64
import time
import threading
import numpy as np
from datetime import datetime
from ultralytics import YOLO

from ..config import (
    YOLO_POSE_MODEL,
    YOLO_OBJ_MODEL,
    YOLO_SPECIALIZED_MODEL,
    TARGET_CLASSES,
    LOITERING_THRESHOLD,
    ALERT_COOLDOWN,
    MIN_BOX_SIZE,
    MIN_VISIBLE_KEYPOINTS,
    FACE_REC_AVAILABLE
)
from ..camera import CameraManager
from ..models.person_state import PersonState
from ..detection import (
    update_heatmap,
    get_heatmap_overlay,
    check_reaching,
    check_object_in_hand,
    check_concealment,
    check_bending,
    is_person_facing_away
)
from ..alerts import trigger_alert

# Global state
camera_manager = CameraManager()
person_states = {}  # {(cam_id, track_id): PersonState}
latest_frame = None
alert_payload = None
lock = threading.Lock()


def get_camera_buffer(cam_data):
    """Get camera capture object as live source for alert video recording"""
    try:
        cap = cam_data.get("cap")
        if cap and hasattr(cap, 'get_buffer_frames'):
            return cap
    except Exception as e:
        print(f"Error getting camera buffer: {e}")
    return None


def normalize_roi_points(points):
    """Convert ROI points to OpenCV-friendly int tuples."""
    normalized = []
    if not isinstance(points, list):
        return normalized

    for point in points:
        x = None
        y = None

        if isinstance(point, dict):
            x = point.get("x")
            y = point.get("y")
        elif isinstance(point, (list, tuple)) and len(point) >= 2:
            x = point[0]
            y = point[1]

        if x is None or y is None:
            continue

        try:
            normalized.append((int(float(x)), int(float(y))))
        except (TypeError, ValueError):
            continue

    return normalized


def video_loop():
    """Main video processing loop"""
    global latest_frame, alert_payload, person_states
    
    print("Video Loop Başlatılıyor...") 
    model_obj = None
    model_is_specialized = False
    
    try:
        print("Loading Pose Model...")
        model_pose = YOLO(YOLO_POSE_MODEL) 
        
        print("Loading Theft Detection Model...")
        try:
            # Try to load specialized model first
            model_obj = YOLO(YOLO_SPECIALIZED_MODEL)
            model_is_specialized = True
            print("Özel Hırsızlık Modeli Yüklendi! (shoplifting.pt)")
        except:
            print("Özel model bulunamadı, standart nesne takibine (yolov8n.pt) geçiliyor...")
            try:
                model_obj = YOLO(YOLO_OBJ_MODEL)
            except Exception as e:
                print(f"Standart Model de yüklenemedi: {e}")
                model_obj = None

        print("Modeller hazır.")
    except Exception as e:
        print(f"CRITICAL MODEL ERROR: {e}")
        with open("error_log.txt", "a") as f:
            f.write(f"{datetime.now()}: CRITICAL LOAD ERROR: {e}\n")
        return

    frame_count = 0
    no_signal_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    cv2.putText(no_signal_frame, "SINYAL YOK", (400, 360), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 3)

    while True:
        try:
            with camera_manager.lock:
                current_cams = list(camera_manager.cameras.items())

            frames_payload = [] 
            
            # Optimization: Run Object Det every 5 frames
            run_obj_det = (frame_count % 5 == 0) and (model_obj is not None)
            
            for cam_id, cam_data in current_cams:
                cap = cam_data["cap"]
                name = cam_data["name"]
                current_time = time.time()
                
                # Fetch specific camera ROI (legacy single-zone)
                cam_roi = normalize_roi_points(cam_data.get("roi_points", []))
                # Multi-zone ROIs (new): list of dicts {zone_type, points}
                raw_zones = cam_data.get("roi_zones", [])
                merchandise_rois = [
                    normalize_roi_points(z["points"])
                    for z in raw_zones if z.get("zone_type") == "merchandise"
                ]
                forbidden_rois = [
                    normalize_roi_points(z["points"])
                    for z in raw_zones if z.get("zone_type") == "forbidden"
                ]
                entry_rois = [
                    normalize_roi_points(z["points"])
                    for z in raw_zones if z.get("zone_type") == "entry"
                ]
                # Fallback: treat legacy single roi_points as merchandise zone
                if not merchandise_rois and cam_roi:
                    merchandise_rois = [cam_roi]
                
                if cap.isOpened():
                    ret, frame = cap.read()
                    if not ret:
                        frame = no_signal_frame.copy()
                else:
                    frame = no_signal_frame.copy()

                if cap.isOpened() and 'ret' in locals() and ret:
                    # 1. POSE INFERENCE (Every Frame for tracking)
                    results_pose = model_pose.track(frame, persist=True, verbose=False, classes=[0], conf=0.5) 
                    
                    # 2. THEFT / OBJECT INFERENCE
                    detected_objects = []
                    suspicious_activity_detected = False
                    
                    if run_obj_det:
                        if model_is_specialized:
                            results_obj = model_obj(frame, verbose=False, conf=0.4)
                            if len(results_obj) > 0:
                                boxes = results_obj[0].boxes.xyxy.cpu().numpy().astype(int)
                                clss = results_obj[0].boxes.cls.cpu().numpy().astype(int)
                                confs = results_obj[0].boxes.conf.cpu().numpy()
                                
                                for b, c, conf in zip(boxes, clss, confs):
                                    class_name = model_obj.names[c].lower()
                                    if "shoplift" in class_name or "suspicious" in class_name or "theft" in class_name or "fight" in class_name:
                                        label = f"{class_name.upper()} {conf:.2f}"
                                        cv2.rectangle(frame, (b[0], b[1]), (b[2], b[3]), (0, 0, 255), 3)
                                        cv2.putText(frame, label, (b[0], b[1]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                                        suspicious_activity_detected = True
                                        
                                        if current_time - cam_data["last_alert_time"] > ALERT_COOLDOWN:
                                            alert_payload_wrapper = {}
                                            frame_buffer = get_camera_buffer(cam_data)
                                            trigger_alert(cam_id, name, f"CRIMINAL ACTIVITY: {class_name}", frame, alert_payload_wrapper, frame_buffer)
                                            cam_data["last_alert_time"] = current_time
                                            with lock:
                                                alert_payload = alert_payload_wrapper.get('data')
                                    else:
                                        cv2.rectangle(frame, (b[0], b[1]), (b[2], b[3]), (0, 255, 0), 1)
                        else:
                            # Fallback Logic - Target classes for stealable items
                            results_obj = model_obj(frame, verbose=False, conf=0.3) 
                            if len(results_obj) > 0:
                                boxes_obj = results_obj[0].boxes.xyxy.cpu().numpy().astype(int)
                                cls_obj = results_obj[0].boxes.cls.cpu().numpy().astype(int)
                                conf_obj = results_obj[0].boxes.conf.cpu().numpy()
                                
                                for b, c, conf in zip(boxes_obj, cls_obj, conf_obj):
                                    if c in TARGET_CLASSES: 
                                        detected_objects.append(b)
                                        label = f"ITEM: {model_obj.names[c]} {conf:.2f}"
                                        cv2.rectangle(frame, (b[0], b[1]), (b[2], b[3]), (0, 165, 255), 2)
                                        cv2.putText(frame, label, (b[0], b[1]-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1)
                    
                    if run_obj_det:
                        cam_data["last_objects"] = detected_objects
                    else:
                        detected_objects = cam_data.get("last_objects", [])

                    # 3. PROCESS DETECTIONS
                    if results_pose[0].boxes.id is not None:
                        boxes = results_pose[0].boxes.xyxy.cpu().numpy().astype(int)
                        track_ids = results_pose[0].boxes.id.cpu().numpy().astype(int)
                        
                        try:
                            keypoints_all = results_pose[0].keypoints.xy.cpu().numpy()
                        except:
                            keypoints_all = []

                        for i, track_id in enumerate(track_ids):
                            box = boxes[i]
                            kpts = keypoints_all[i] if len(keypoints_all) > i else []
                            
                            # ANTI-FALSE POSITIVE VALIDATIONS
                            # 1. Check minimum bounding box size
                            box_width = box[2] - box[0]
                            box_height = box[3] - box[1]
                            
                            if box_width < MIN_BOX_SIZE or box_height < MIN_BOX_SIZE:
                                print(f"[FILTER] Track {track_id}: Ignorado - bounding box muito pequena ({box_width}x{box_height})")
                                continue
                            
                            # 2. Check visible keypoints
                            if len(kpts) >= 17:
                                visible_keypoints = sum([1 for kp in kpts if kp[0] > 0 and kp[1] > 0])
                                
                                if visible_keypoints < MIN_VISIBLE_KEYPOINTS:
                                    print(f"[FILTER] Track {track_id}: Ignorado - poucos keypoints visíveis ({visible_keypoints}/17)")
                                    continue
                            else:
                                print(f"[FILTER] Track {track_id}: Ignorado - sem keypoints")
                                continue
                            
                            # Multi-camera safe tracking key
                            state_key = (cam_id, track_id)
                            if state_key not in person_states:
                                person_states[state_key] = PersonState(track_id)
                            p_state = person_states[state_key]
                            
                            # FACE RECOGNITION
                            process_face_recognition(
                                frame, box, kpts, cam_id, cam_data, 
                                name, track_id, p_state, current_time
                            )

                            # POSE & THEFT LOGIC
                            is_bending = check_bending(kpts)
                            is_facing_away = is_person_facing_away(kpts)
                            
                            if not model_is_specialized:
                                process_theft_detection(
                                    frame, box, kpts, detected_objects, 
                                    cam_id, cam_data, name, p_state, 
                                    current_time
                                )

                            # ROI LOGIC — zone-aware
                            center_x = int((box[0] + box[2]) / 2)
                            center_y = int((box[1] + box[3]) / 2)
                            person_center = (center_x, center_y)

                            # 1. Entry zone: person is in counter/entry → skip all scoring
                            in_entry_zone = any(
                                len(z) >= 3 and
                                cv2.pointPolygonTest(np.array(z, dtype=np.int32), person_center, False) >= 0
                                for z in entry_rois
                            )

                            # 2. Forbidden zone: immediate alert
                            in_forbidden_zone = any(
                                len(z) >= 3 and
                                cv2.pointPolygonTest(np.array(z, dtype=np.int32), person_center, False) >= 0
                                for z in forbidden_rois
                            )

                            # 3. Merchandise zones: hand inside → triggers scoring gate
                            is_reaching = False
                            for merch_roi in merchandise_rois:
                                r, _ = check_reaching(kpts, merch_roi)
                                if r:
                                    is_reaching = True
                                    break

                            if in_entry_zone:
                                # Person is at entry/counter — draw neutral label, no scoring
                                cv2.putText(frame, "ENTRADA/BALCAO", (box[0], box[1]-10),
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 200, 100), 1)
                            elif in_forbidden_zone:
                                cv2.putText(frame, "ZONA PROIBIDA!", (box[0], box[1]-40),
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                                if current_time - cam_data["last_alert_time"] > ALERT_COOLDOWN:
                                    alert_payload_wrapper = {}
                                    frame_buffer = get_camera_buffer(cam_data)
                                    trigger_alert(cam_id, name, "ZONA PROIBIDA - INTRUSAO", frame, alert_payload_wrapper, frame_buffer)
                                    cam_data["last_alert_time"] = current_time
                                    with lock:
                                        alert_payload = alert_payload_wrapper.get('data')
                            elif is_reaching:
                                cv2.putText(frame, "MERCADORIA - AREA MONITORADA", (box[0], box[1]-40),
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)

                            if is_bending:
                                cv2.putText(frame, "BENDING", (box[0], box[1] + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
                            
                            # Show when person is facing away (for debugging/transparency)
                            if is_facing_away:
                                cv2.putText(frame, "FACING AWAY", (box[0], box[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (128, 128, 128), 2)
                            
                            # LOITERING — only in merchandise zones, skip entry zones
                            if not in_entry_zone:
                                process_loitering(
                                    frame, box, cam_data, cam_id, name, 
                                    merchandise_rois[0] if merchandise_rois else cam_roi,
                                    track_id, current_time
                                )

                    # Apply heatmap overlay
                    frame = get_heatmap_overlay(cam_data, frame) 
                    
                    # Plot keypoints
                    if results_pose[0].keypoints is not None:
                        res_plotted = results_pose[0].plot()
                        frame = res_plotted

                    # Draw all ROI zones with type-specific colours
                    zone_colours = {
                        "merchandise": (0, 200, 255),   # amber/orange
                        "forbidden":   (0, 0, 220),     # red
                        "entry":       (80, 200, 80),   # green
                    }
                    for z in raw_zones:
                        pts = normalize_roi_points(z.get("points", []))
                        if len(pts) >= 3:
                            colour = zone_colours.get(z.get("zone_type", "merchandise"), (0, 200, 255))
                            cv2.polylines(frame, [np.array(pts, dtype=np.int32)], isClosed=True, color=colour, thickness=2)
                            # Label in top-left corner of zone bounding box
                            xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
                            cv2.putText(frame, z.get("name", "Zona"), (min(xs), min(ys) - 6),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, colour, 1)
                    # Legacy single roi_points (if no zones defined)
                    if not raw_zones and len(cam_roi) > 0:
                        cv2.polylines(frame, [np.array(cam_roi, dtype=np.int32)], isClosed=True, color=(0, 255, 255), thickness=2)

                # Encode frame
                _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
                jpg_as_text = base64.b64encode(buffer).decode('utf-8')
                
                frames_payload.append({
                    "camera_id": cam_id,
                    "name": name,
                    "data": jpg_as_text
                })
            
            frame_count += 1
            if frames_payload:
                with lock:
                    latest_frame = {
                        "type": "multi_frame",
                        "cameras": frames_payload,
                        "alert": alert_payload,
                        "audio": "siren" if alert_payload else None
                    }
                    # Clear alert_payload after packing
                    alert_payload = None
            
            time.sleep(0.04) 

        except Exception as e:
            print(f"Loop Error: {e}")
            with open("error_log.txt", "a") as f:
                f.write(f"{datetime.now()}: Loop Runtime Error: {e}\n")
            time.sleep(1)


def process_face_recognition(frame, box, kpts, cam_id, cam_data, cam_name, track_id, p_state, current_time):
    """Process face recognition for a person"""
    if not FACE_REC_AVAILABLE:
        return
    
    if not p_state.face_checked or (current_time - p_state.face_check_time > 2.0):
        p_state.face_check_time = current_time
        
        # Validate face keypoints
        has_valid_face_keypoints = False
        if len(kpts) >= 5:
            nose, left_eye, right_eye, left_ear, right_ear = kpts[0:5]
            visible_face_keypoints = sum([
                1 if nose[0] > 0 and nose[1] > 0 else 0,
                1 if left_eye[0] > 0 and left_eye[1] > 0 else 0,
                1 if right_eye[0] > 0 and right_eye[1] > 0 else 0,
                1 if left_ear[0] > 0 and left_ear[1] > 0 else 0,
                1 if right_ear[0] > 0 and right_ear[1] > 0 else 0
            ])
            has_valid_face_keypoints = visible_face_keypoints >= 2
        
        if has_valid_face_keypoints:
            from ..face_recognition.auto_register import get_face_embedding, auto_register_or_track_person
            
            # Get face crop
            face_img, fx1, fy1, fx2, fy2 = extract_face_crop(frame, box, kpts)
            
            if face_img is not None and face_img.size > 0:
                # Resize for faster processing
                h, w = face_img.shape[:2]
                if w > 600:
                    scale = 600 / w
                    face_img = cv2.resize(face_img, (600, int(h * scale)))
                
                # Extract embedding using InsightFace
                face_embedding = get_face_embedding(face_img)
                
                if face_embedding is not None:
                    # Try to recognize
                    face_recognized = recognize_face(frame, box, face_embedding, cam_id, cam_data, cam_name, current_time)
                    
                    if not face_recognized:
                        # Auto-register or track person
                        person_id = auto_register_or_track_person(face_img, cam_id, track_id)
                        
                        if person_id:
                            cv2.putText(frame, f"Tracked", (box[0], box[1]-30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,0), 2)
                        else:
                            cv2.putText(frame, "Processing...", (box[0], box[1]-30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (128,128,128), 2)
                else:
                    cv2.putText(frame, "No face detected", (box[0], box[1]-30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (128,128,128), 2)
                        
                p_state.face_checked = True


def extract_face_crop(frame, box, kpts):
    """Extract face region from frame"""
    face_img = None
    fx1, fy1, fx2, fy2 = 0, 0, 0, 0
    
    if len(kpts) >= 5:
        nose = kpts[0]
        if nose[0] > 0 and nose[1] > 0:
            crop_size = int((box[2] - box[0]) * 0.5)
            fx1 = max(0, int(nose[0] - crop_size))
            fy1 = max(0, int(nose[1] - crop_size))
            fx2 = min(frame.shape[1], int(nose[0] + crop_size))
            fy2 = min(frame.shape[0], int(nose[1] + crop_size))
            face_img = frame[fy1:fy2, fx1:fx2]
    
    # Fallback: use top portion of bounding box
    if face_img is None or face_img.size == 0:
        box_height = box[3] - box[1]
        fx1 = max(0, box[0])
        fy1 = max(0, box[1])
        fx2 = min(frame.shape[1], box[2])
        fy2 = min(frame.shape[0], box[1] + int(box_height * 0.5))
        face_img = frame[fy1:fy2, fx1:fx2]
    
    return face_img, fx1, fy1, fx2, fy2


def recognize_face(frame, box, encoding, cam_id, cam_data, cam_name, current_time):
    """Recognize a face against known faces"""
    from ..face_recognition.auto_register import compare_faces
    from ..face_recognition.face_manager import get_face_manager
    
    face_manager = get_face_manager()
    known_encodings, known_names, known_types, known_ids = face_manager.get_faces()
    
    if len(known_encodings) > 0:
        best_match_idx = None
        best_distance = 1.0
        
        for idx, known_encoding in enumerate(known_encodings):
            is_match, distance = compare_faces(encoding, known_encoding)
            if is_match and distance < best_distance:
                best_distance = distance
                best_match_idx = idx
        
        if best_match_idx is not None:
            match_name = known_names[best_match_idx]
            match_type = known_types[best_match_idx]
            
            if match_type == "blacklist":
                cv2.putText(frame, f"BLACKLIST: {match_name}", (box[0], box[1]-30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 3)
                if current_time - cam_data["last_alert_time"] > ALERT_COOLDOWN:
                    global alert_payload
                    alert_payload_wrapper = {}
                    frame_buffer = get_camera_buffer(cam_data)
                    trigger_alert(cam_id, cam_name, f"BLACKLIST FACE: {match_name}", frame, alert_payload_wrapper, frame_buffer)
                    cam_data["last_alert_time"] = current_time
                    with lock:
                        alert_payload = alert_payload_wrapper.get('data')
            else:
                cv2.putText(frame, f"VIP: {match_name}", (box[0], box[1]-30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)
            return True
    return False


def process_theft_detection(frame, box, kpts, detected_objects, cam_id, cam_data, cam_name, p_state, current_time):
    """Process theft detection logic"""
    left_has_obj = check_object_in_hand(kpts, detected_objects, "LEFT")
    right_has_obj = check_object_in_hand(kpts, detected_objects, "RIGHT")
    current_holding = left_has_obj or right_has_obj
    holding_hand = "LEFT" if left_has_obj else "RIGHT" if right_has_obj else None

    if current_holding:
        p_state.holding_object = True
        p_state.last_holding_time = current_time
        p_state.holding_hand = holding_hand
        cv2.putText(frame, f"HOLDING ({holding_hand})", (box[0], box[1]-60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,0), 2)
    
    if p_state.holding_object and not current_holding:
        time_since_hold = current_time - p_state.last_holding_time
        if time_since_hold < 3.0: 
            hand_to_check = p_state.holding_hand
            if hand_to_check and check_concealment(kpts, hand_to_check):
                cv2.putText(frame, "THEFT DETECTED!", (box[0], box[1]-80), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
                cv2.rectangle(frame, (box[0], box[1]), (box[2], box[3]), (0, 0, 255), 3)
                if current_time - cam_data["last_alert_time"] > ALERT_COOLDOWN:
                    global alert_payload
                    alert_payload_wrapper = {}
                    frame_buffer = get_camera_buffer(cam_data)
                    trigger_alert(cam_id, cam_name, "THEFT CONFIRMED (Item Concealed)", frame, alert_payload_wrapper, frame_buffer)
                    cam_data["last_alert_time"] = current_time
                    p_state.holding_object = False
                    with lock:
                        alert_payload = alert_payload_wrapper.get('data')
        else:
            if time_since_hold > 3.0:
                p_state.holding_object = False
                p_state.holding_hand = None


def process_loitering(frame, box, cam_data, cam_id, cam_name, cam_roi, track_id, current_time):
    """Process loitering detection"""
    center_x = int((box[0] + box[2]) / 2)
    center_y = int((box[1] + box[3]) / 2)
    update_heatmap(cam_data, center_x, center_y, frame.shape)
    
    is_inside_roi = False
    if len(cam_roi) >= 3:
        if cv2.pointPolygonTest(np.array(cam_roi), (center_x, center_y), False) >= 0:
            is_inside_roi = True
    
    if is_inside_roi:
        if track_id not in cam_data["roi_entry_times"]:
            cam_data["roi_entry_times"][track_id] = time.time()
        duration = time.time() - cam_data["roi_entry_times"][track_id]
        cv2.putText(frame, f"{duration:.1f}s", (box[0], box[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)

        if duration > LOITERING_THRESHOLD:
            if current_time - cam_data["last_alert_time"] > ALERT_COOLDOWN:
                global alert_payload
                alert_payload_wrapper = {}
                frame_buffer = get_camera_buffer(cam_data)
                trigger_alert(cam_id, cam_name, "LOITERING SUSPICION", frame, alert_payload_wrapper, frame_buffer)
                cam_data["last_alert_time"] = current_time
                with lock:
                    alert_payload = alert_payload_wrapper.get('data')
    else:
        if track_id in cam_data["roi_entry_times"]:
            del cam_data["roi_entry_times"][track_id]
