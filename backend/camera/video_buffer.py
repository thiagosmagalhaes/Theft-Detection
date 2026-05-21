"""Video buffer for storing recent frames"""

import threading
from collections import deque
from datetime import datetime


class VideoBuffer:
    """Circular buffer to store recent video frames for alert recording"""
    
    def __init__(self, fps=25, duration_seconds=20):
        """
        Initialize video buffer
        
        Args:
            fps: Frames per second (default 25)
            duration_seconds: How many seconds to buffer (default 20)
        """
        self.fps = fps
        self.duration_seconds = duration_seconds
        self.max_frames = fps * duration_seconds
        self.buffer = deque(maxlen=self.max_frames)
        self.lock = threading.Lock()
        self.frame_timestamps = deque(maxlen=self.max_frames)
    
    def add_frame(self, frame, timestamp=None):
        """
        Add a frame to the buffer
        
        Args:
            frame: The video frame (numpy array)
            timestamp: Optional timestamp (defaults to now)
        """
        if timestamp is None:
            timestamp = datetime.now()
            
        with self.lock:
            self.buffer.append(frame.copy())
            self.frame_timestamps.append(timestamp)
    
    def get_frames(self):
        """
        Get all buffered frames
        
        Returns:
            List of frames and their timestamps
        """
        with self.lock:
            return list(self.buffer), list(self.frame_timestamps)
    
    def clear(self):
        """Clear the buffer"""
        with self.lock:
            self.buffer.clear()
            self.frame_timestamps.clear()
    
    def is_full(self):
        """Check if buffer has reached its maximum capacity"""
        with self.lock:
            return len(self.buffer) >= self.max_frames
    
    def get_frame_count(self):
        """Get current number of frames in buffer"""
        with self.lock:
            return len(self.buffer)
