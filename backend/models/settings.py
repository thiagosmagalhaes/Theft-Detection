"""Settings data model"""

from pydantic import BaseModel
from typing import Literal


class SettingsModel(BaseModel):
    emailEnabled: bool = False
    smtpServer: str = "smtp.gmail.com"
    smtpPort: str = "587"
    senderEmail: str = ""
    senderPassword: str = ""
    receiverEmail: str = ""
    telegramEnabled: bool = False
    telegramBotToken: str = ""
    telegramChatId: str = ""
    roiPoints: list[list[int]] = []
    showHeatmap: bool = False


class RoiZone(BaseModel):
    """A named polygon zone with a type that determines scoring behaviour."""
    name: str = "Zona"
    zone_type: Literal["merchandise", "forbidden", "entry"] = "merchandise"
    points: list[list[int]] = []


class CameraInput(BaseModel):
    name: str
    source: str
