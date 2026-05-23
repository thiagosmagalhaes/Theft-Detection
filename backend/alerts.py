"""Alert triggering and notification logic"""

import cv2
import os
import smtplib
import subprocess
import threading
import time
from datetime import datetime, timedelta
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests

from .config import current_settings
from .database import insert_alert


def _build_video_writer(video_path, fps, width, height):
    """Create VideoWriter with browser-compatible H.264 codec.
    
    Uses a temporary file that will be converted to H.264 MP4 using FFmpeg
    for guaranteed browser compatibility.
    """
    # Try direct H.264 encoding first (works if OpenCV is built with proper codecs)
    codec_candidates = [
        ("avc1", "H.264/AVC"),
        ("H264", "H.264"),
        ("X264", "x264"),
    ]

    for fourcc_code, codec_name in codec_candidates:
        fourcc = cv2.VideoWriter_fourcc(*fourcc_code)
        writer = cv2.VideoWriter(video_path, fourcc, fps, (width, height))
        if writer.isOpened():
            print(f"[ALERT] Video codec selected: {fourcc_code} ({codec_name})")
            return writer

    # Fallback: use any working codec, will convert with FFmpeg later
    print("[ALERT] H.264 codec not available, using fallback (will convert with FFmpeg)")
    fallback_codecs = [("mp4v", "MPEG-4"), ("XVID", "Xvid")]
    
    for fourcc_code, codec_name in fallback_codecs:
        fourcc = cv2.VideoWriter_fourcc(*fourcc_code)
        writer = cv2.VideoWriter(video_path + ".tmp", fourcc, fps, (width, height))
        if writer.isOpened():
            print(f"[ALERT] Temporary codec: {fourcc_code} ({codec_name})")
            return writer

    return None


def _convert_to_browser_compatible_mp4(input_path, output_path):
    """Convert video to browser-compatible MP4 with H.264 video and AAC audio.
    
    Args:
        input_path: Path to input video file
        output_path: Path to output MP4 file
        
    Returns:
        bool: True if conversion succeeded, False otherwise
    """
    try:
        # Check if ffmpeg is available
        try:
            subprocess.run(
                ["ffmpeg", "-version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5,
                check=True
            )
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            print("[ALERT] FFmpeg not found. Install FFmpeg for guaranteed browser compatibility.")
            print("[ALERT] Using original video file without conversion.")
            # If input is .tmp file, rename it to final output
            if input_path.endswith(".tmp"):
                if os.path.exists(input_path):
                    os.rename(input_path, output_path)
            return False

        # Convert to H.264 MP4 (silent video - OpenCV doesn't capture audio anyway)
        # Using web-optimized settings:
        # - H.264 codec (libx264) with baseline profile for maximum compatibility
        # - Constant Rate Factor (CRF) 23 for good quality/size balance
        # - faststart flag moves metadata to beginning for streaming
        # - pixel format yuv420p for maximum compatibility
        cmd = [
            "ffmpeg",
            "-y",  # Overwrite output file if exists
            "-i", input_path,  # Input file
            "-c:v", "libx264",  # H.264 video codec
            "-preset", "fast",  # Encoding speed preset
            "-crf", "23",  # Quality (lower = better, 23 is default)
            "-profile:v", "baseline",  # Baseline profile for maximum compatibility
            "-level", "3.0",  # H.264 level
            "-pix_fmt", "yuv420p",  # Pixel format (required for some players)
            "-movflags", "+faststart",  # Enable streaming/progressive download
            "-an",  # No audio (OpenCV doesn't capture audio)
            output_path
        ]
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            check=True
        )
        
        # Clean up temporary file
        if input_path.endswith(".tmp") and os.path.exists(input_path):
            os.remove(input_path)
            
        print(f"[ALERT] Video converted to browser-compatible H.264 MP4: {output_path}")
        return True
        
    except subprocess.TimeoutExpired:
        print("[ALERT] FFmpeg conversion timed out")
        return False
    except subprocess.CalledProcessError as e:
        print(f"[ALERT] FFmpeg conversion failed: {e.stderr.decode() if e.stderr else str(e)}")
        return False
    except Exception as e:
        print(f"[ALERT] Video conversion error: {e}")
        return False


def _save_alert_video(video_path, frame_buffer, event_time):
    """Persist one clip containing 20s before and 10s after the alert event."""
    try:
        if not frame_buffer or not hasattr(frame_buffer, "get_buffer_frames"):
            print("[ALERT] Video buffer unavailable, skipping video save.")
            return False

        # Wait until we have 10s of post-event frames available in the buffer.
        post_window_seconds = 10
        while datetime.now() < (event_time + timedelta(seconds=post_window_seconds)):
            time.sleep(0.2)

        frames, timestamps = frame_buffer.get_buffer_frames()
        if not frames:
            print("[ALERT] Video buffer is empty, skipping video save.")
            return False

        # Select exactly: 20s before event + 10s after event.
        start_time = event_time - timedelta(seconds=20)
        end_time = event_time + timedelta(seconds=10)
        selected_frames = []

        if timestamps and len(timestamps) == len(frames):
            for frame, ts in zip(frames, timestamps):
                if start_time <= ts <= end_time:
                    selected_frames.append(frame)
        else:
            selected_frames = frames

        if not selected_frames:
            print("[ALERT] No frames found in requested 30s window, using all buffered frames.")
            selected_frames = frames

        first_frame = selected_frames[0]
        height, width = first_frame.shape[:2]

        fps = 25.0
        try:
            if hasattr(frame_buffer, "video_buffer") and hasattr(frame_buffer.video_buffer, "fps"):
                candidate_fps = float(frame_buffer.video_buffer.fps)
                if candidate_fps > 0:
                    fps = candidate_fps
        except Exception:
            pass

        # Check if we need a temporary file for conversion
        temp_path = None
        out = _build_video_writer(video_path, fps, width, height)
        
        # If writer opened a .tmp file, we'll need to convert it
        if out is not None and os.path.exists(video_path + ".tmp"):
            temp_path = video_path + ".tmp"
        
        if out is None:
            print("[ALERT] Could not open VideoWriter with any supported codec.")
            return False

        for frame in selected_frames:
            if frame is None:
                continue

            if frame.shape[:2] != (height, width):
                frame = cv2.resize(frame, (width, height))
            out.write(frame)

        out.release()
        
        # If we used a temporary file, convert to browser-compatible MP4
        if temp_path and os.path.exists(temp_path):
            print(f"[ALERT] Converting video to browser-compatible MP4...")
            _convert_to_browser_compatible_mp4(temp_path, video_path)
        
        print(f"[ALERT] Video saved: {video_path} ({len(selected_frames)} frames, ~30s window)")
        return True

    except Exception as e:
        print(f"[ALERT] Video save error: {e}")
        return False


def trigger_alert(cam_id, cam_name, message, frame, alert_payload_wrapper=None, frame_buffer=None):
    """Save alert image, persist to DB, fire notifications, and populate alert_payload_wrapper."""
    try:
        print(f"ALERT: {message}")
        event_time = datetime.now()
        timestamp = event_time.strftime("%Y%m%d_%H%M%S")
        image_path = f"alerts/alert_{cam_id}_{timestamp}.jpg"
        video_path = f"alerts/alert_{cam_id}_{timestamp}.mp4" if frame_buffer is not None else None
        cv2.imwrite(image_path, frame)

        alert_id = insert_alert(message, timestamp, image_path, cam_id=cam_id, video_path=video_path)

        # Save buffered video in background so alerts remain non-blocking.
        if video_path is not None:
            threading.Thread(
                target=_save_alert_video,
                args=(video_path, frame_buffer, event_time),
                daemon=True,
            ).start()

        payload = {
            "id": alert_id,
            "message": message,
            "timestamp": timestamp,
            "image_path": image_path,
            "video_path": video_path,
            "camera_id": cam_id,
        }

        if alert_payload_wrapper is not None:
            alert_payload_wrapper["data"] = payload

        threading.Thread(
            target=_send_notifications, args=(message, image_path), daemon=True
        ).start()

    except Exception as e:
        print(f"Alert Error: {e}")


def _send_notifications(message, image_path):
    try:
        if current_settings.emailEnabled:
            sender_email = os.getenv("SENDER_EMAIL", current_settings.senderEmail)
            sender_password = os.getenv("SMTP_PASSWORD", current_settings.senderPassword)
            if sender_email and sender_password:
                msg = MIMEMultipart()
                msg["From"] = sender_email
                msg["To"] = current_settings.receiverEmail
                msg["Subject"] = "Theft Guard AI - Security Alert"
                msg.attach(MIMEText(
                    f"ALERT: {message}\nTimestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    "plain",
                ))
                try:
                    with open(image_path, "rb") as f:
                        msg.attach(MIMEImage(f.read(), name=os.path.basename(image_path)))
                except Exception:
                    pass
                server = smtplib.SMTP(current_settings.smtpServer, int(current_settings.smtpPort))
                server.starttls()
                server.login(sender_email, sender_password)
                server.send_message(msg)
                server.quit()
                print("Email notification sent.")

        if current_settings.telegramEnabled:
            bot_token = os.getenv("TELEGRAM_BOT_TOKEN", current_settings.telegramBotToken)
            chat_id = current_settings.telegramChatId
            if bot_token and chat_id:
                url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
                with open(image_path, "rb") as photo:
                    resp = requests.post(
                        url,
                        data={"chat_id": chat_id, "caption": f"🚨 THEFT GUARD ALERT 🚨\n\n{message}"},
                        files={"photo": photo},
                        timeout=15,
                    )
                if resp.status_code == 200:
                    print("Telegram notification sent.")
                else:
                    print(f"Telegram Error: {resp.text}")

    except Exception as e:
        print(f"Notification Error: {e}")
