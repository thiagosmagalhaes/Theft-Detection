"""Alert triggering and notification logic"""

import cv2
import os
import smtplib
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
    """Create VideoWriter prioritizing browser-friendly codecs for HTML5 playback."""
    codec_candidates = [
        ("avc1", "H.264/AVC"),
        ("H264", "H.264"),
        ("X264", "x264"),
        ("mp4v", "MPEG-4 Part 2"),
    ]

    for fourcc_code, codec_name in codec_candidates:
        fourcc = cv2.VideoWriter_fourcc(*fourcc_code)
        writer = cv2.VideoWriter(video_path, fourcc, fps, (width, height))
        if writer.isOpened():
            print(f"[ALERT] Video codec selected: {fourcc_code} ({codec_name})")
            if fourcc_code == "mp4v":
                print("[ALERT] Warning: mp4v may fail in some browsers. Prefer avc1/H264 if available.")
            return writer

    return None


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

        out = _build_video_writer(video_path, fps, width, height)
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
