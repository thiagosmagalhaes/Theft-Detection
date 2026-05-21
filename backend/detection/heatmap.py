"""Heatmap visualization utilities"""

import cv2
import numpy as np


def update_heatmap(cam_data, center_x, center_y, frame_shape):
    """Update heatmap accumulator with new person position"""
    if cam_data.get("heatmap_accumulator") is None or cam_data["heatmap_accumulator"].shape[:2] != frame_shape[:2]:
        cam_data["heatmap_accumulator"] = np.zeros(frame_shape[:2], dtype=np.float32)
    try:
        cam_data["heatmap_accumulator"][center_y, center_x] += 1
    except:
        pass


def get_heatmap_overlay(cam_data, frame):
    """Generate heatmap overlay on frame"""
    if cam_data.get("heatmap_accumulator") is None:
        return frame
    
    msg_max = np.max(cam_data["heatmap_accumulator"])
    if msg_max == 0:
        return frame
    
    norm_heatmap = cam_data["heatmap_accumulator"] / msg_max
    norm_heatmap = (norm_heatmap * 255).astype(np.uint8)
    color_map = cv2.applyColorMap(norm_heatmap, cv2.COLORMAP_JET)
    result = cv2.addWeighted(frame, 0.7, color_map, 0.3, 0)
    return result
