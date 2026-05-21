"""Person state tracking model"""


class PersonState:
    def __init__(self, track_id):
        self.track_id = track_id
        self.state = "NEUTRAL"  # NEUTRAL, REACHING, HOLDING, SUSPICIOUS
        self.last_reach_time = 0
        self.holding_object = False
        self.holding_hand = None
        self.last_holding_time = 0
        self.face_checked = False
        self.face_check_time = 0
