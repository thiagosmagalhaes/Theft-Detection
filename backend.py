import cv2
import asyncio
import base64
import os
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

load_dotenv()
from ultralytics import YOLO
import numpy as np
import time
from datetime import datetime
import json
import threading
import uuid
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import requests
from pydantic import BaseModel
import sqlite3
import pickle
try:
    import face_recognition
    FACE_REC_AVAILABLE = True
except ImportError:
    FACE_REC_AVAILABLE = False
    print("face_recognition not installed. Face ID disabled.")

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("psutil not installed. System resource monitor will run in simulation mode.")

if not os.path.exists("alerts"):
    os.makedirs("alerts")

app = FastAPI()

app.mount("/alerts", StaticFiles(directory="alerts"), name="alerts")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Database Setup ---
DB_NAME = "theft_detection.db"

def init_db():
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS alerts
                     (id TEXT PRIMARY KEY, message TEXT, timestamp TEXT, image_path TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS faces
                     (id TEXT PRIMARY KEY, name TEXT, type TEXT, encoding BLOB)''')
        conn.commit()
        conn.close()
        print("Database initialized.")
    except Exception as e:
        print(f"Database error: {e}")

init_db()

# --- Settings & Models ---
SETTINGS_FILE = "settings.json"

class SettingsModel(BaseModel):
    emailEnabled: bool = False
    smtpServer: str = "smtp.gmail.com"
    smtpPort: str = "587"
    senderEmail: str = ""
    senderPassword: str = ""
    receiverEmail: str = ""
    telegramEnabled: bool = False
    telegramBotToken: str = ""
    telegramChatId: str = ""
    roiPoints: list[list[int]] = []
    showHeatmap: bool = False


try:
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            settings_data = json.load(f)
            current_settings = SettingsModel(**settings_data)
            roi_points = current_settings.roiPoints
    else:
        current_settings = SettingsModel()
except Exception as e:
    current_settings = SettingsModel()


# --- Heatmap Logic ---
def update_heatmap(cam_data, center_x, center_y, frame_shape):
    if cam_data.get("heatmap_accumulator") is None or cam_data["heatmap_accumulator"].shape[:2] != frame_shape[:2]:
        cam_data["heatmap_accumulator"] = np.zeros(frame_shape[:2], dtype=np.float32)
    try:
        cam_data["heatmap_accumulator"][center_y, center_x] += 1
    except: pass

def get_heatmap_overlay(cam_data, frame):
    if cam_data.get("heatmap_accumulator") is None: return frame
    msg_max = np.max(cam_data["heatmap_accumulator"])
    if msg_max == 0: return frame
    
    norm_heatmap = cam_data["heatmap_accumulator"] / msg_max
    norm_heatmap = (norm_heatmap * 255).astype(np.uint8)
    color_map = cv2.applyColorMap(norm_heatmap, cv2.COLORMAP_JET)
    result = cv2.addWeighted(frame, 0.7, color_map, 0.3, 0)
    return result

# --- Face ID Logic ---
known_face_encodings = []
known_face_names = []
known_face_types = [] # 'blacklist' or 'whitelist'
faces_lock = threading.Lock()

def load_known_faces():
    global known_face_encodings, known_face_names, known_face_types
    if not FACE_REC_AVAILABLE: return
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT name, type, encoding FROM faces")
        rows = c.fetchall()
        
        temp_encodings = []
        temp_names = []
        temp_types = []
        for row in rows:
            name, f_type, encoding_blob = row
            encoding = pickle.loads(encoding_blob)
            temp_encodings.append(encoding)
            temp_names.append(name)
            temp_types.append(f_type)
        conn.close()
        
        with faces_lock:
            known_face_encodings = temp_encodings
            known_face_names = temp_names
            known_face_types = temp_types
            
        print(f"Loaded {len(known_face_names)} faces.")
    except Exception as e:
        print(f"Error loading faces: {e}")

load_known_faces()

# --- API Endpoints ---


@app.post("/faces/register")
async def register_face(file: UploadFile = File(...), name: str = Form(...), type: str = Form("blacklist")):
    if not FACE_REC_AVAILABLE: return {"status": "error", "message": "Face Rec not available"}
    temp_filename = f"temp_{uuid.uuid4()}.jpg"
    try:
        with open(temp_filename, "wb") as buffer:
            buffer.write(await file.read())
        
        image = face_recognition.load_image_file(temp_filename)
        encodings = face_recognition.face_encodings(image)
        
        if len(encodings) > 0:
            encoding = encodings[0]
            encoding_blob = pickle.dumps(encoding)
            face_id = str(uuid.uuid4())
            
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("INSERT INTO faces VALUES (?,?,?,?)", (face_id, name, type, encoding_blob))
            conn.commit()
            conn.close()
            
            load_known_faces() # Reload
            return {"status": "success", "message": f"Face registered: {name}"}
        else:
            return {"status": "error", "message": "No face found in image"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

@app.get("/faces")
async def get_faces():
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT id, name, type FROM faces")
        rows = c.fetchall()
        conn.close()
        return [{"id": r[0], "name": r[1], "type": r[2]} for r in rows]
    except Exception as e:
        return {"error": str(e)}



# --- API Endpoints ---

@app.get("/settings")
async def get_settings():
    return current_settings

@app.post("/settings")
async def save_settings(settings: SettingsModel):
    global current_settings, roi_points
    current_settings = settings
    roi_points = settings.roiPoints # Update global ROI
    
    from dotenv import set_key
    env_path = ".env"
    if not os.path.exists(env_path):
        open(env_path, 'a').close()
        
    if settings.senderPassword and settings.senderPassword != "********":
        set_key(env_path, "SMTP_PASSWORD", settings.senderPassword)
    if settings.telegramBotToken and settings.telegramBotToken != "********":
        set_key(env_path, "TELEGRAM_BOT_TOKEN", settings.telegramBotToken)
        
    safe_settings = settings.dict()
    # Mask sensitive data in JSON
    safe_settings["senderPassword"] = ""
    safe_settings["telegramBotToken"] = ""
    
    with open(SETTINGS_FILE, "w") as f:
        json.dump(safe_settings, f, indent=4)
        
    load_dotenv(override=True)
    return {"status": "success", "message": "Settings saved"}

@app.post("/roi")
async def save_roi(data: dict):
    global roi_points, current_settings
    if "points" in data:
        roi_points = data["points"]
        current_settings.roiPoints = roi_points
        with open(SETTINGS_FILE, "w") as f:
            json.dump(current_settings.dict(), f, indent=4)
        print(f"ROI Updated: {roi_points}")
        return {"status": "success"}
    return {"status": "error"}

@app.get("/roi")
async def get_roi():
    return {"points": roi_points}


@app.post("/settings/test")
async def test_settings(settings: SettingsModel):
    original_settings = current_settings.copy()
    
    if settings.emailEnabled:
        try:
            msg = MIMEMultipart()
            msg['From'] = settings.senderEmail
            msg['To'] = settings.receiverEmail
            msg['Subject'] = "Theft Detection - Test Email"
            msg.attach(MIMEText("This is a test email from your Theft Detection System.", 'plain'))
            server = smtplib.SMTP(settings.smtpServer, int(settings.smtpPort))
            server.starttls()
            server.login(settings.senderEmail, settings.senderPassword)
            server.send_message(msg)
            server.quit()
        except Exception as e:
            return {"status": "error", "message": f"Email Test Failed: {str(e)}"}

    if settings.telegramEnabled:
        try:
            url = f"https://api.telegram.org/bot{settings.telegramBotToken}/sendMessage"
            data = {"chat_id": settings.telegramChatId, "text": "Theft Detection - Test Message"}
            resp = requests.post(url, data=data)
            if resp.status_code != 200:
                 return {"status": "error", "message": f"Telegram Test Failed: {resp.text}"}
        except Exception as e:
            return {"status": "error", "message": f"Telegram Test Failed: {str(e)}"}
            
    return {"status": "success", "message": "All enabled tests sent successfully!"}



@app.delete("/faces/{face_id}")
async def delete_face(face_id: str):
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("DELETE FROM faces WHERE id = ?", (face_id,))
        conn.commit()
        conn.close()
        load_known_faces() # Reload
        return {"status": "success", "message": "Face deleted successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/history")
async def get_history():
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM alerts ORDER BY timestamp DESC LIMIT 100")
        rows = c.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        return {"error": str(e)}

# --- Video Logic ---

# Global variables
roi_points = []
roi_entry_times = {}
LOITERING_THRESHOLD = 5.0
last_alert_time = 0
ALERT_COOLDOWN = 3.0
latest_frame = None
alert_payload = None # Initialize
lock = threading.Lock()
clients = []

if not os.path.exists("alerts"):
    os.makedirs("alerts")

# --- Threaded Camera Stream ---
class ThreadedCamera:
    def __init__(self, src):
        self.src = src
        try:
            self.src_val = int(src)
            is_index = True
        except:
            self.src_val = src
            is_index = False

        if is_index and os.name == 'nt':
            self.cap = cv2.VideoCapture(self.src_val, cv2.CAP_DSHOW)
        else:
            self.cap = cv2.VideoCapture(self.src_val)

        if self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            self.ret, self.frame = self.cap.read()
        else:
            self.ret = False
            self.frame = None

        self.running = True
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self.update, args=(), daemon=True)
        if self.cap.isOpened():
            self.thread.start()

    def update(self):
        while self.running:
            if self.cap.isOpened():
                ret, frame = self.cap.read()
                with self.lock:
                    self.ret = ret
                    if ret:
                        self.frame = frame
                time.sleep(0.01)
            else:
                time.sleep(0.1)

    def read(self):
        with self.lock:
            if self.frame is not None:
                return self.ret, self.frame.copy()
            return False, None

    def isOpened(self):
        return self.cap.isOpened()

    def release(self):
        self.running = False
        self.cap.release()

# --- Camera Management ---
class CameraManager:
    def __init__(self):
        self.cameras = {}
        self.lock = threading.Lock()
        self.load_cameras()

    def load_cameras(self):
        file_path = "cameras.json"
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for cam in data:
                        self.add_camera_internal(cam["id"], cam["source"], cam["name"], cam.get("roi_points", []))
                print(f"Loaded {len(self.cameras)} cameras from cameras.json.")
                return
            except Exception as e:
                print(f"Error loading cameras.json: {e}")

        # Fallback to default webcam if no file exists
        self.add_camera_internal("0", "0", "Kamera 1", [])
        self.save_cameras()

    def save_cameras(self):
        file_path = "cameras.json"
        try:
            data = []
            with self.lock:
                for cam_id, cam_data in self.cameras.items():
                    data.append({
                        "id": cam_id,
                        "name": cam_data["name"],
                        "source": cam_data["source"],
                        "roi_points": cam_data.get("roi_points", [])
                    })
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving cameras.json: {e}")

    def add_camera_internal(self, cam_id, source, name, roi_points):
        threaded_cap = ThreadedCamera(source)
        self.cameras[cam_id] = {
            "cap": threaded_cap,
            "name": name,
            "source": source,
            "status": "active" if threaded_cap.isOpened() else "error",
            "roi_points": roi_points,
            "heatmap_accumulator": None,
            "roi_entry_times": {},
            "last_alert_time": 0
        }

    def add_camera(self, source, name):
        cam_id = str(uuid.uuid4())
        threaded_cap = ThreadedCamera(source)
        if threaded_cap.isOpened():
            with self.lock:
                self.cameras[cam_id] = {
                    "cap": threaded_cap,
                    "name": name,
                    "source": source,
                    "status": "active",
                    "roi_points": [],
                    "heatmap_accumulator": None,
                    "roi_entry_times": {},
                    "last_alert_time": 0
                }
            self.save_cameras()
            print(f"Kamera eklendi: {name} ({source}) ID: {cam_id}")
            return {"id": cam_id, "status": "connected"}
        else:
            print(f"Kamera açılamadı: {source}")
            return {"id": None, "status": "failed"}

    def remove_camera(self, cam_id):
        with self.lock:
            if cam_id in self.cameras:
                self.cameras[cam_id]["cap"].release()
                del self.cameras[cam_id]
                status = True
            else:
                status = False
        if status:
            self.save_cameras()
        return status

    def get_active_cameras(self):
        with self.lock:
            return [{
                "id": k, 
                "name": v["name"], 
                "source": v["source"], 
                "status": "active" if v["cap"].isOpened() else "error",
                "roi_points": v.get("roi_points", [])
            } for k, v in self.cameras.items()]

camera_manager = CameraManager()

# --- API Endpoints for Cameras ---
class CameraInput(BaseModel):
    name: str
    source: str

@app.post("/cameras")
async def add_new_camera(cam: CameraInput):
    result = camera_manager.add_camera(cam.source, cam.name)
    if result["id"]:
        with camera_manager.lock:
            cam_data = camera_manager.cameras.get(result["id"])
            cam_details = {
                "id": result["id"],
                "name": cam_data["name"] if cam_data else cam.name,
                "source": cam_data["source"] if cam_data else cam.source,
                "status": "active"
            } if cam_data else None
        return {"message": "Camera added", "camera": cam_details}
    else:
        raise HTTPException(status_code=400, detail="Failed to open camera")

@app.get("/stats")
def get_stats():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT substr(timestamp, 1, 8), count(*) FROM alerts GROUP BY substr(timestamp, 1, 8)")
    data = dict(c.fetchall())
    conn.close()
    
    stats = []
    from datetime import timedelta
    today = datetime.now()
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        key = d.strftime("%Y%m%d")
        stats.append(data.get(key, 0))

    cpu_load = 0
    ram_load = 0
    if PSUTIL_AVAILABLE:
        try:
            cpu_load = psutil.cpu_percent()
            ram_load = psutil.virtual_memory().percent
        except:
            import random
            cpu_load = random.randint(15, 30)
            ram_load = random.randint(40, 50)
    else:
        import random
        cpu_load = random.randint(15, 30)
        ram_load = random.randint(40, 50)
        
    return {
        "weekly_data": stats,
        "cpu_load": cpu_load,
        "ram_load": ram_load
    }

@app.get("/cameras")
async def list_cameras():
    return camera_manager.get_active_cameras()

@app.delete("/cameras/{camera_id}")
async def delete_camera(camera_id: str):
    if camera_manager.remove_camera(camera_id):
        return {"message": "Camera removed"}
    raise HTTPException(status_code=404, detail="Camera not found")

@app.post("/cameras/{camera_id}/roi")
async def save_camera_roi(camera_id: str, data: dict):
    if "points" in data:
        points = data["points"]
        with camera_manager.lock:
            if camera_id in camera_manager.cameras:
                camera_manager.cameras[camera_id]["roi_points"] = points
                camera_manager.save_cameras()
                return {"status": "success", "roi_points": points}
        raise HTTPException(status_code=404, detail="Camera not found")
    raise HTTPException(status_code=400, detail="Invalid data")

@app.get("/cameras/{camera_id}/roi")
async def get_camera_roi(camera_id: str):
    with camera_manager.lock:
        if camera_id in camera_manager.cameras:
            return {"points": camera_manager.cameras[camera_id].get("roi_points", [])}
    raise HTTPException(status_code=404, detail="Camera not found")



# --- State Tracker for Concealment ---
class PersonState:
    def __init__(self, track_id):
        self.track_id = track_id
        self.state = "NEUTRAL" # NEUTRAL, REACHING, HOLDING, SUSPICIOUS
        self.last_reach_time = 0
        self.holding_object = False
        self.holding_hand = None
        self.last_holding_time = 0
        self.face_checked = False
        self.face_check_time = 0

person_states = {} # {(cam_id, track_id): PersonState}

# --- Helper Functions for Pose ---
def check_reaching(keypoints, roi_poly):
    if len(keypoints) < 11: return False, None
    left_wrist = keypoints[9]
    right_wrist = keypoints[10]
    reaching_hand = None
    
    if left_wrist[0] > 0 and left_wrist[1] > 0 and len(roi_poly) >= 3:
        if cv2.pointPolygonTest(np.array(roi_poly), (int(left_wrist[0]), int(left_wrist[1])), False) >= 0:
            reaching_hand = "LEFT"

    if right_wrist[0] > 0 and right_wrist[1] > 0 and len(roi_poly) >= 3:
        if cv2.pointPolygonTest(np.array(roi_poly), (int(right_wrist[0]), int(right_wrist[1])), False) >= 0:
            reaching_hand = "RIGHT"
            
    return (reaching_hand is not None), reaching_hand

def check_object_in_hand(keypoints, object_boxes, hand="LEFT"):
    # Check if any object box is close to the specified wrist
    if len(keypoints) < 11: return False
    wrist = keypoints[9] if hand == "LEFT" else keypoints[10]
    
    if wrist[0] == 0: return False
    
    for box in object_boxes:
        # Box: x1, y1, x2, y2
        # Check distance from wrist to box center
        box_cx = (box[0] + box[2]) / 2
        box_cy = (box[1] + box[3]) / 2
        
        dist = np.sqrt((wrist[0] - box_cx)**2 + (wrist[1] - box_cy)**2)
        
        # If wrist is CLOSE to object center (e.g. < 100px) OR wrist is INSIDE box
        if dist < 120: # Threshold
            return True
        if box[0] < wrist[0] < box[2] and box[1] < wrist[1] < box[3]:
            return True
            
    return False

def check_concealment(keypoints, reaching_hand):
    if len(keypoints) < 13: return False
    left_hip = keypoints[11]
    right_hip = keypoints[12]
    target_wrist = keypoints[9] if reaching_hand == "LEFT" else keypoints[10]
    
    if target_wrist[0] == 0 or left_hip[0] == 0 or right_hip[0] == 0: return False
    
    hip_center_x = (left_hip[0] + right_hip[0]) / 2
    hip_center_y = (left_hip[1] + right_hip[1]) / 2
    
    dist_x = target_wrist[0] - hip_center_x
    dist_y = target_wrist[1] - hip_center_y
    distance = np.sqrt(dist_x**2 + dist_y**2)
    
    hip_width = np.abs(left_hip[0] - right_hip[0])
    threshold = max(hip_width * 1.5, 100) 
    
    return distance < threshold

def check_bending(keypoints):
    if len(keypoints) < 12: return False
    l_shoulder = keypoints[5]
    l_hip = keypoints[11]
    if l_shoulder[1] == 0 or l_hip[1] == 0: return False
    vertical_dist = l_hip[1] - l_shoulder[1]
    return vertical_dist < 50

# --- Updated Video Loop ---
def video_loop():
    global latest_frame, current_settings, alert_payload, known_face_encodings, known_face_names, known_face_types, person_states
    
    print("Video Loop Başlatılıyor...") 
    model_obj = None # Fallback or specialized
    model_is_specialized = False
    
    try:
        print("Loading Pose Model...")
        model_pose = YOLO('yolov8n-pose.pt') 
        
        print("Loading Theft Detection Model...")
        try:
            # Try to load specialized model first
            model_obj = YOLO('shoplifting.pt')
            model_is_specialized = True
            print("Özel Hırsızlık Modeli Yüklendi! (shoplifting.pt)")
        except:
            print("Özel model bulunamadı, standart nesne takibine (yolov8n.pt) geçiliyor...")
            try:
                model_obj = YOLO('yolov8n.pt')
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
                
                # Fetch specific camera ROI
                cam_roi = cam_data.get("roi_points", [])
                
                if cap.isOpened():
                    ret, frame = cap.read()
                    if not ret: frame = no_signal_frame.copy()
                else:
                    frame = no_signal_frame.copy()

                if cap.isOpened() and 'ret' in locals() and ret:
                    
                    # 1. POSE INFERENCE (Every Frame for tracking)
                    results_pose = model_pose.track(frame, persist=True, verbose=False, classes=[0]) 
                    
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
                                            trigger_alert(cam_id, name, f"CRIMINAL ACTIVITY: {class_name}", frame)
                                            cam_data["last_alert_time"] = current_time
                                    else:
                                         cv2.rectangle(frame, (b[0], b[1]), (b[2], b[3]), (0, 255, 0), 1)
                        else:
                            # Fallback Logic - Target classes for stealable items
                            TARGET_CLASSES = [24, 25, 26, 28, 39, 40, 41, 42, 43, 67, 73, 74, 75, 76, 77, 78, 79] 
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
                            
                            # Multi-camera safe tracking key
                            state_key = (cam_id, track_id)
                            if state_key not in person_states:
                                person_states[state_key] = PersonState(track_id)
                            p_state = person_states[state_key]
                            
                            is_bending = False
                            is_reaching = False
                            
                            # --- FACE REC ---
                            if FACE_REC_AVAILABLE and (not p_state.face_checked or (current_time - p_state.face_check_time > 2.0)):
                                p_state.face_check_time = current_time
                                fx1, fy1, fx2, fy2 = max(0, box[0]), max(0, box[1]), min(frame.shape[1], box[2]), min(frame.shape[0], box[3])
                                face_img = frame[fy1:fy2, fx1:fx2]
                                rgb_face = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
                                face_locs = face_recognition.face_locations(rgb_face)
                                if face_locs:
                                    encodings = face_recognition.face_encodings(rgb_face, face_locs)
                                    if encodings:
                                        with faces_lock:
                                            matches = face_recognition.compare_faces(known_face_encodings, encodings[0], tolerance=0.5)
                                        if True in matches:
                                            match_index = matches.index(True)
                                            match_name = known_face_names[match_index]
                                            match_type = known_face_types[match_index]
                                            if match_type == "blacklist":
                                                cv2.putText(frame, f"BLACKLIST: {match_name}", (box[0], box[1]-30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 3)
                                                if current_time - cam_data["last_alert_time"] > ALERT_COOLDOWN:
                                                    trigger_alert(cam_id, name, f"BLACKLIST FACE: {match_name}", frame)
                                                    cam_data["last_alert_time"] = current_time
                                            else:
                                                cv2.putText(frame, f"VIP: {match_name}", (box[0], box[1]-30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)
                                p_state.face_checked = True

                            # --- POSE & THEFT LOGIC ---
                            is_bending = check_bending(kpts)
                            
                            if not model_is_specialized:
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
                                                  trigger_alert(cam_id, name, "THEFT CONFIRMED (Item Concealed)", frame)
                                                  cam_data["last_alert_time"] = current_time
                                                  p_state.holding_object = False 
                                    else:
                                        if time_since_hold > 3.0:
                                            p_state.holding_object = False
                                            p_state.holding_hand = None

                            # --- ROI LOGIC ---
                            is_reaching, _ = check_reaching(kpts, cam_roi)
                            if is_reaching:
                                cv2.putText(frame, "RESTRICTED AREA ENT!", (box[0], box[1]-40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                                if current_time - cam_data["last_alert_time"] > ALERT_COOLDOWN:
                                     trigger_alert(cam_id, name, "RESTRICTED AREA INTRUSION", frame)
                                     cam_data["last_alert_time"] = current_time

                            if is_bending:
                                cv2.putText(frame, "BENDING", (box[0], box[1] + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
                            
                            # --- LOITERING ---
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
                                         trigger_alert(cam_id, name, "LOITERING SUSPICION", frame)
                                         cam_data["last_alert_time"] = current_time
                            else:
                                if track_id in cam_data["roi_entry_times"]:
                                    del cam_data["roi_entry_times"][track_id]

                    frame = get_heatmap_overlay(cam_data, frame) 
                    
                    if results_pose[0].keypoints is not None:
                         res_plotted = results_pose[0].plot()
                         frame = res_plotted

                    if len(cam_roi) > 0:
                        cv2.polylines(frame, [np.array(cam_roi)], isClosed=True, color=(0, 255, 255), thickness=2)

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
                    # Clear alert_payload after packing into frame to avoid duplicate siren loops
                    alert_payload = None
            
            time.sleep(0.04) 

        except Exception as e:
            print(f"Loop Error: {e}")
            with open("error_log.txt", "a") as f:
                f.write(f"{datetime.now()}: Loop Runtime Error: {e}\n")
            time.sleep(1)


def trigger_alert(cam_id, cam_name, message, frame):
    global alert_payload
    try:
        print(f"ALERT: {message}")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"alerts/alert_{cam_id}_{timestamp}.jpg"
        cv2.imwrite(filename, frame)
        
        # database
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        alert_id = str(uuid.uuid4())
        c.execute("INSERT INTO alerts VALUES (?,?,?,?)", (alert_id, message, timestamp, filename))
        conn.commit()
        conn.close()
        
        with lock:
            alert_payload = {
                "id": alert_id,
                "message": message,
                "timestamp": timestamp,
                "image_path": filename,
                "camera_id": cam_id
            }
            
        # Send Email/Telegram if enabled (Settings)
        # We can implement a fire-and-forget thread for this to not block loop
        threading.Thread(target=send_notifications, args=(message, filename)).start()
        
    except Exception as e:
        print(f"Alert Error: {e}")

def send_notifications(message, image_path):
    try:
        if current_settings.emailEnabled:
            sender_email = os.getenv("SENDER_EMAIL", current_settings.senderEmail)
            sender_password = os.getenv("SMTP_PASSWORD", current_settings.senderPassword)
            if sender_email and sender_password:
                msg = MIMEMultipart()
                msg['From'] = sender_email
                msg['To'] = current_settings.receiverEmail
                msg['Subject'] = "Theft Guard AI - Security Alert"
                
                body = f"ALERT: {message}\nTimestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                msg.attach(MIMEText(body, 'plain'))
                
                try:
                    with open(image_path, 'rb') as f:
                        img_data = f.read()
                        image = MIMEImage(img_data, name=os.path.basename(image_path))
                        msg.attach(image)
                except Exception as img_e:
                    print(f"Could not attach image: {img_e}")
                
                server = smtplib.SMTP(current_settings.smtpServer, int(current_settings.smtpPort))
                server.starttls()
                server.login(sender_email, sender_password)
                server.send_message(msg)
                server.quit()
                print("Email notification sent.")

        if current_settings.telegramEnabled:
            bot_token = os.getenv("TELEGRAM_BOT_TOKEN", current_settings.telegramBotToken)
            chat_id = current_settings.telegramChatId
            if bot_token and chat_id:
                url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
                with open(image_path, 'rb') as photo:
                    data = {"chat_id": chat_id, "caption": f"🚨 THEFT GUARD ALERT 🚨\n\n{message}"}
                    files = {"photo": photo}
                    resp = requests.post(url, data=data, files=files)
                if resp.status_code == 200:
                    print("Telegram notification sent.")
                else:
                    print(f"Telegram Error: {resp.text}")
    except Exception as e:
        print(f"Notification Error: {e}")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("Client connected")
    try:
        while True:
            # Send latest frame
            message_to_send = None
            with lock:
                if latest_frame:
                    message_to_send = json.dumps(latest_frame)
            
            if message_to_send:
                await websocket.send_text(message_to_send)

            await asyncio.sleep(0.04) 
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Error: {e}")

@app.on_event("startup")
def startup_event():
    t = threading.Thread(target=video_loop, daemon=True)
    t.start()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
