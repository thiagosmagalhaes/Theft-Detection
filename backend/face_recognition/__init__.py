"""Face recognition modules"""

from .face_manager import FaceManager
from .auto_register import auto_register_new_face, pending_face_registrations

__all__ = ['FaceManager', 'auto_register_new_face', 'pending_face_registrations']
