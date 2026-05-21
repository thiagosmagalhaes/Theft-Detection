"""Settings data model"""

from pydantic import BaseModel


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


class CameraInput(BaseModel):
    name: str
    source: str
