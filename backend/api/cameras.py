"""Camera API endpoints"""

import asyncio
from urllib.parse import quote
from fastapi import APIRouter, HTTPException
from ..models.settings import CameraInput, RoiZone, DVRInput

router = APIRouter()


def _build_dvr_rtsp_url(brand: str, ip: str, port: int, username: str, password: str, channel: int) -> str:
    if username and password:
        creds = f"{quote(username, safe='')}:{quote(password, safe='')}@"
    elif username:
        creds = f"{quote(username, safe='')}@"
    else:
        creds = ""
    base = f"rtsp://{creds}{ip}:{port}"
    if brand == "hikvision":
        return f"{base}/Streaming/Channels/{channel}01"
    if brand in ("dahua", "intelbras"):
        return f"{base}/cam/realmonitor?channel={channel}&subtype=0"
    return f"{base}/stream{channel}"


def _normalize_roi_points(raw_points):
    """Normalize ROI points to [[x, y], ...] preserving float precision."""
    normalized = []
    if not isinstance(raw_points, list):
        return normalized

    for point in raw_points:
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
            normalized.append([round(float(x), 6), round(float(y), 6)])
        except (TypeError, ValueError):
            continue

    return normalized


@router.get("/cameras")
async def list_cameras():
    """List all active cameras"""
    from ..camera import CameraManager
    from ..video.video_loop import camera_manager
    return camera_manager.get_active_cameras()


@router.post("/cameras")
async def add_new_camera(cam: CameraInput):
    """Add a new camera"""
    from ..video.video_loop import camera_manager
    
    # Opening an unavailable RTSP/camera source can block for a long time.
    # Run it in a worker thread and enforce an API timeout to keep backend responsive.
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(camera_manager.add_camera, cam.source, cam.name),
            timeout=12.0,
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="Camera connection timed out. Check source/RTSP URL and try again.",
        )

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


@router.post("/cameras/dvr")
async def add_dvr_cameras(dvr: DVRInput):
    """Connect multiple cameras from a DVR/NVR via RTSP, one per channel."""
    from ..video.video_loop import camera_manager

    results = []
    for channel in dvr.channels:
        url = _build_dvr_rtsp_url(dvr.brand, dvr.ip, dvr.port, dvr.username, dvr.password, channel)
        cam_name = f"{dvr.name_prefix} - Canal {channel}"
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(camera_manager.add_camera, url, cam_name),
                timeout=15.0,
            )
            results.append({
                "channel": channel,
                "name": cam_name,
                "status": "connected" if result["id"] else "failed",
                "id": result["id"],
            })
        except asyncio.TimeoutError:
            results.append({
                "channel": channel,
                "name": cam_name,
                "status": "timeout",
                "id": None,
            })

    connected = sum(1 for r in results if r["status"] == "connected")
    return {"results": results, "connected": connected, "failed": len(results) - connected}


@router.delete("/cameras/{camera_id}")
async def delete_camera(camera_id: str):
    """Delete a camera"""
    from ..video.video_loop import camera_manager
    
    result = await asyncio.to_thread(camera_manager.remove_camera, camera_id)
    if result:
        return {"message": "Camera removed"}
    raise HTTPException(status_code=404, detail="Camera not found")


@router.post("/cameras/{camera_id}/roi")
async def save_camera_roi(camera_id: str, data: dict):
    """Save ROI points for a specific camera"""
    from ..video.video_loop import camera_manager
    
    if "points" in data:
        points = _normalize_roi_points(data["points"])
        if len(points) < 3:
            raise HTTPException(status_code=400, detail="ROI must have at least 3 valid points")

        camera_found = False
        
        # Update ROI in memory (with lock)
        with camera_manager.lock:
            if camera_id in camera_manager.cameras:
                camera_manager.cameras[camera_id]["roi_points"] = points
                camera_found = True
        
        # Save to file (without lock to avoid deadlock)
        if camera_found:
            await asyncio.to_thread(camera_manager.save_cameras)
            return {"status": "success", "roi_points": points}
        
        raise HTTPException(status_code=404, detail="Camera not found")
    raise HTTPException(status_code=400, detail="Invalid data")


@router.get("/cameras/{camera_id}/roi")
async def get_camera_roi(camera_id: str):
    """Get ROI points for a specific camera"""
    from ..video.video_loop import camera_manager
    
    with camera_manager.lock:
        if camera_id in camera_manager.cameras:
            raw_points = camera_manager.cameras[camera_id].get("roi_points", [])
            return {"points": _normalize_roi_points(raw_points)}
    raise HTTPException(status_code=404, detail="Camera not found")


# ---------------------------------------------------------------------------
# Multi-zone ROI endpoints
# ---------------------------------------------------------------------------

@router.get("/cameras/{camera_id}/roi-zones")
async def get_camera_roi_zones(camera_id: str):
    """Get all named ROI zones for a camera."""
    from ..video.video_loop import camera_manager

    with camera_manager.lock:
        if camera_id not in camera_manager.cameras:
            raise HTTPException(status_code=404, detail="Camera not found")
        zones = camera_manager.cameras[camera_id].get("roi_zones", [])
    return {"zones": zones}


@router.post("/cameras/{camera_id}/roi-zones")
async def save_camera_roi_zones(camera_id: str, payload: dict):
    """Replace all ROI zones for a camera.

    Expected body: {"zones": [{"name": str, "zone_type": str, "points": [[x,y],...]}]}
    """
    from ..video.video_loop import camera_manager

    raw_zones = payload.get("zones")
    if not isinstance(raw_zones, list):
        raise HTTPException(status_code=400, detail="'zones' must be a list")

    validated: list[dict] = []
    allowed_types = {"merchandise", "forbidden", "entry"}
    for z in raw_zones:
        if not isinstance(z, dict):
            continue
        zone_type = z.get("zone_type", "merchandise")
        if zone_type not in allowed_types:
            zone_type = "merchandise"
        pts = _normalize_roi_points(z.get("points", []))
        if len(pts) < 3:
            raise HTTPException(
                status_code=400,
                detail=f"Zone '{z.get('name', '?')}' must have at least 3 points"
            )
        validated.append({
            "name": str(z.get("name", "Zona"))[:60],
            "zone_type": zone_type,
            "points": pts,
        })

    camera_found = False
    with camera_manager.lock:
        if camera_id in camera_manager.cameras:
            camera_manager.cameras[camera_id]["roi_zones"] = validated
            camera_found = True

    if not camera_found:
        raise HTTPException(status_code=404, detail="Camera not found")

    await asyncio.to_thread(camera_manager.save_cameras)
    return {"status": "success", "zones": validated}
