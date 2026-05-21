"""
Quick test script to verify modular structure
"""

print("=" * 60)
print("Testing Modular Structure")
print("=" * 60)
print()

# Test imports
print("1. Testing imports...")
try:
    import backend
    print("   ✓ backend")
    
    from backend import config
    print("   ✓ backend.config")
    
    from backend import database
    print("   ✓ backend.database")
    
    from backend.models import SettingsModel, PersonState
    print("   ✓ backend.models")
    
    from backend.camera import ThreadedCamera, CameraManager
    print("   ✓ backend.camera")
    
    from backend.detection import update_heatmap, check_reaching
    print("   ✓ backend.detection")
    
    from backend.api import settings_router, cameras_router
    print("   ✓ backend.api")
    
    from backend.alerts import trigger_alert
    print("   ✓ backend.alerts")
    
    from backend.video import camera_manager, video_loop
    print("   ✓ backend.video")
    
    print()
    print("✓ All imports successful!")
    print()
    
except Exception as e:
    print(f"✗ Import error: {e}")
    exit(1)

# Test database initialization
print("2. Testing database...")
try:
    from backend.database import init_db
    init_db()
    print("   ✓ Database initialized")
    print()
except Exception as e:
    print(f"✗ Database error: {e}")
    exit(1)

# Test configuration
print("3. Testing configuration...")
try:
    from backend.config import (
        LOITERING_THRESHOLD,
        ALERT_COOLDOWN,
        YOLO_POSE_MODEL,
        FACE_REC_AVAILABLE
    )
    print(f"   ✓ LOITERING_THRESHOLD: {LOITERING_THRESHOLD}")
    print(f"   ✓ ALERT_COOLDOWN: {ALERT_COOLDOWN}")
    print(f"   ✓ YOLO_POSE_MODEL: {YOLO_POSE_MODEL}")
    print(f"   ✓ FACE_REC_AVAILABLE: {FACE_REC_AVAILABLE}")
    print()
except Exception as e:
    print(f"✗ Configuration error: {e}")
    exit(1)

# Test models
print("4. Testing models...")
try:
    settings = SettingsModel()
    print(f"   ✓ SettingsModel created")
    
    person = PersonState(track_id=1)
    print(f"   ✓ PersonState created")
    print()
except Exception as e:
    print(f"✗ Model error: {e}")
    exit(1)

# Summary
print("=" * 60)
print("✓ ALL TESTS PASSED!")
print("=" * 60)
print()
print("The modular structure is working correctly.")
print("You can now run the system with: py main.py")
print()
