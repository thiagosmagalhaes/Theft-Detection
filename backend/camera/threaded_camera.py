"""Threaded camera capture for non-blocking video streaming"""

import cv2
import os
import threading
import time
from .video_buffer import VideoBuffer


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
        elif not is_index:
            # Force TCP transport for RTSP streams - UDP drops packets inside Docker/NAT
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|timeout;10000000"
            self.cap = cv2.VideoCapture(self.src_val, cv2.CAP_FFMPEG)
        else:
            self.cap = cv2.VideoCapture(self.src_val)

        if self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            self.ret, self.frame = self.cap.read()
            
            # Get actual FPS from camera (fallback to 25 if not available)
            fps = self.cap.get(cv2.CAP_PROP_FPS)
            if fps == 0 or fps > 60:  # Some cameras return invalid values
                fps = 25
        else:
            self.ret = False
            self.frame = None
            fps = 25

        # Keep 30 seconds so alerts can include 20s before + 10s after the event
        self.video_buffer = VideoBuffer(fps=int(fps), duration_seconds=30)
        
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
                        # Add frame to video buffer for alert recording
                        self.video_buffer.add_frame(frame)
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

    def get(self, prop_id):
        """Proxy VideoCapture.get for compatibility with existing loop code."""
        if self.cap is None:
            return 0
        try:
            return self.cap.get(prop_id)
        except Exception:
            return 0
    
    def get_buffer_frames(self):
        """Get frames from the video buffer for alert recording"""
        return self.video_buffer.get_frames()

    def release(self):
        self.running = False
        self.cap.release()
