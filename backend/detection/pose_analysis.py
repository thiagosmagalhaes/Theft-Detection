"""Pose analysis functions for detecting suspicious behavior"""

import cv2
import numpy as np


def check_reaching(keypoints, roi_poly):
    """Check if person is reaching into ROI area"""
    if len(keypoints) < 11:
        return False, None
    
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
    """Check if any object box is close to the specified wrist"""
    if len(keypoints) < 11:
        return False
    
    wrist = keypoints[9] if hand == "LEFT" else keypoints[10]
    
    if wrist[0] == 0:
        return False
    
    for box in object_boxes:
        # Box: x1, y1, x2, y2
        # Check distance from wrist to box center
        box_cx = (box[0] + box[2]) / 2
        box_cy = (box[1] + box[3]) / 2
        
        dist = np.sqrt((wrist[0] - box_cx)**2 + (wrist[1] - box_cy)**2)
        
        # If wrist is CLOSE to object center (e.g. < 100px) OR wrist is INSIDE box
        if dist < 120:  # Threshold
            return True
        if box[0] < wrist[0] < box[2] and box[1] < wrist[1] < box[3]:
            return True
            
    return False


def check_concealment(keypoints, reaching_hand):
    """Check if person is concealing object near hip area"""
    if len(keypoints) < 13:
        return False
    
    left_hip = keypoints[11]
    right_hip = keypoints[12]
    target_wrist = keypoints[9] if reaching_hand == "LEFT" else keypoints[10]
    
    if target_wrist[0] == 0 or left_hip[0] == 0 or right_hip[0] == 0:
        return False
    
    hip_center_x = (left_hip[0] + right_hip[0]) / 2
    hip_center_y = (left_hip[1] + right_hip[1]) / 2
    
    dist_x = target_wrist[0] - hip_center_x
    dist_y = target_wrist[1] - hip_center_y
    distance = np.sqrt(dist_x**2 + dist_y**2)
    
    hip_width = np.abs(left_hip[0] - right_hip[0])
    threshold = max(hip_width * 1.5, 100)
    
    return distance < threshold


def check_bending(keypoints):
    """Check if person is in bending posture"""
    if len(keypoints) < 12:
        return False
    
    l_shoulder = keypoints[5]
    l_hip = keypoints[11]
    
    if l_shoulder[1] == 0 or l_hip[1] == 0:
        return False
    
    vertical_dist = l_hip[1] - l_shoulder[1]
    return vertical_dist < 50
