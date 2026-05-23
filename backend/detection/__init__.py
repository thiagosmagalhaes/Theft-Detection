"""Detection utilities"""

from .heatmap import update_heatmap, get_heatmap_overlay
from .object_detector import load_object_detector
from .pose_analysis import (
    check_reaching, 
    check_object_in_hand, 
    check_concealment, 
    check_bending,
    is_person_facing_away,
    body_scale,
    detect_concealment_zone,
    hand_in_pocket_zone,
    hand_in_waistband_zone,
    hand_in_chest_zone,
    hand_in_armpit_zone,
    hand_in_ankle_zone,
    hand_in_bag_zone,
    head_horizontal_offset,
    TheftBehaviorTracker,
    PersonState,
    RISK_WEIGHTS,
    ZONE_LABELS,
)

__all__ = [
    'update_heatmap',
    'get_heatmap_overlay',
    'load_object_detector',
    'check_reaching',
    'check_object_in_hand',
    'check_concealment',
    'check_bending',
    'is_person_facing_away',
    'body_scale',
    'detect_concealment_zone',
    'hand_in_pocket_zone',
    'hand_in_waistband_zone',
    'hand_in_chest_zone',
    'hand_in_armpit_zone',
    'hand_in_ankle_zone',
    'hand_in_bag_zone',
    'head_horizontal_offset',
    'TheftBehaviorTracker',
    'PersonState',
    'RISK_WEIGHTS',
    'ZONE_LABELS',
]
