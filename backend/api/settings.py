"""Settings API endpoints"""

import asyncio
import os
import json
from fastapi import APIRouter
from ..models.settings import SettingsModel
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import requests

router = APIRouter()


@router.get("/settings")
async def get_settings():
    """Get current settings"""
    from ..config import current_settings
    return current_settings


@router.post("/settings")
async def save_settings(settings: SettingsModel):
    """Save application settings"""
    from ..config import current_settings, SETTINGS_FILE
    import backend.config as config
    
    config.current_settings = settings
    config.roi_points = settings.roiPoints
    
    def _save_sync():
        from dotenv import set_key
        env_path = ".env"
        if not os.path.exists(env_path):
            open(env_path, 'a').close()
            
        if settings.senderPassword and settings.senderPassword != "********":
            set_key(env_path, "SMTP_PASSWORD", settings.senderPassword)
        if settings.telegramBotToken and settings.telegramBotToken != "********":
            set_key(env_path, "TELEGRAM_BOT_TOKEN", settings.telegramBotToken)
            
        safe_settings = settings.dict()
        safe_settings["senderPassword"] = ""
        safe_settings["telegramBotToken"] = ""
        
        with open(SETTINGS_FILE, "w") as f:
            json.dump(safe_settings, f, indent=4)
        
        from dotenv import load_dotenv
        load_dotenv(override=True)
    
    await asyncio.to_thread(_save_sync)
    return {"status": "success", "message": "Settings saved"}


@router.post("/settings/test")
async def test_settings(settings: SettingsModel):
    """Test email and Telegram settings"""
    def _test_sync():
        # Test Email
        if settings.emailEnabled:
            try:
                msg = MIMEMultipart()
                msg['From'] = settings.senderEmail
                msg['To'] = settings.receiverEmail
                msg['Subject'] = "Theft Detection - Test Email"
                msg.attach(MIMEText("This is a test email from your Theft Detection System.", 'plain'))
                server = smtplib.SMTP(settings.smtpServer, int(settings.smtpPort))
                server.starttls()
                server.login(settings.senderEmail, settings.senderPassword)
                server.send_message(msg)
                server.quit()
            except Exception as e:
                return {"status": "error", "message": f"Email Test Failed: {str(e)}"}

        # Test Telegram
        if settings.telegramEnabled:
            try:
                url = f"https://api.telegram.org/bot{settings.telegramBotToken}/sendMessage"
                data = {"chat_id": settings.telegramChatId, "text": "Theft Detection - Test Message"}
                resp = requests.post(url, data=data, timeout=10)
                if resp.status_code != 200:
                    return {"status": "error", "message": f"Telegram Test Failed: {resp.text}"}
            except Exception as e:
                return {"status": "error", "message": f"Telegram Test Failed: {str(e)}"}
                
        return {"status": "success", "message": "All enabled tests sent successfully!"}
    
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(_test_sync),
            timeout=30.0
        )
        return result
    except asyncio.TimeoutError:
        return {"status": "error", "message": "Test timed out (network issue)"}


@router.post("/roi")
async def save_roi(data: dict):
    """Save ROI points (legacy endpoint for backward compatibility)"""
    from ..config import current_settings, SETTINGS_FILE
    import backend.config as config
    
    if "points" in data:
        config.roi_points = data["points"]
        config.current_settings.roiPoints = data["points"]
        
        def _save_sync():
            with open(SETTINGS_FILE, "w") as f:
                json.dump(current_settings.dict(), f, indent=4)
        
        await asyncio.to_thread(_save_sync)
        
        print(f"ROI Updated: {data['points']}")
        return {"status": "success"}
    return {"status": "error"}


@router.get("/roi")
async def get_roi():
    """Get ROI points (legacy endpoint)"""
    from ..config import roi_points
    return {"points": roi_points}
