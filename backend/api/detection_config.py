"""Detection configuration API endpoint"""

import json
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

DETECTION_CONFIG_FILE = "detection_config.json"

# ---------------------------------------------------------------------------
# Pydantic model (mirrors the TypeScript DetectionConfig interface)
# ---------------------------------------------------------------------------

class RoiTypes(BaseModel):
    merchandiseZone: bool = True
    forbiddenZone: bool = False
    entryCounterZone: bool = True


class DetectionConfigModel(BaseModel):
    roiTypes: RoiTypes = RoiTypes()
    merchandiseTrigger: str = "hand_in_roi"          # hand_in_roi | object_near_hand | both
    bagClassification: str = "only_if_tracked_item"  # arrival_frames | always_personal | only_if_tracked_item
    bagArrivalFrames: int = 30
    hiddenFaceBehavior: str = "only_if_nape"          # ignore | half_weight | only_if_nape
    bagStrapSuppression: str = "full"                 # full | half | none
    entryZoneBehavior: str = "no_score"               # no_score | half_score | ignore_completely
    alertChain: str = "confirmed_chain_only"          # confirmed_chain_only | confirmed_chain_or_high_score | recalibrate_weights
    highScoreThreshold: float = 2.0
    preAlertLabel: str = "atencao_revisar"            # atencao_revisar | comportamento_suspeito | monitorar | suspeito
    confirmedAlertLabel: str = "ocultacao_confirmada" # furto_detectado | ocultacao_confirmada | revisar_urgente


# In-memory cache so the rest of the backend can read it without file I/O per frame
_current_config: DetectionConfigModel = DetectionConfigModel()


def get_detection_config() -> DetectionConfigModel:
    """Return the active detection config (in-memory)."""
    return _current_config


def _load_from_disk():
    global _current_config
    if os.path.exists(DETECTION_CONFIG_FILE):
        try:
            with open(DETECTION_CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            _current_config = DetectionConfigModel(**data)
            print(f"Detection config loaded from {DETECTION_CONFIG_FILE}.")
        except Exception as e:
            print(f"Error loading detection config: {e}")


# Load on module import
_load_from_disk()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/detection-config")
async def get_config():
    """Return the current detection configuration."""
    return _current_config


@router.post("/detection-config")
async def save_config(config: DetectionConfigModel):
    """Persist the detection configuration and apply it immediately."""
    global _current_config

    if not config.roiTypes.merchandiseZone:
        raise HTTPException(
            status_code=400,
            detail="merchandiseZone ROI type is mandatory — at least one merchandise polygon must be enabled."
        )

    _current_config = config

    try:
        with open(DETECTION_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config.model_dump(), f, indent=2, ensure_ascii=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to persist config: {e}")

    return {"status": "ok", "config": config}
