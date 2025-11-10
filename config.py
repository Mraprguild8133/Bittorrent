import os
from typing import Optional
from pydantic import BaseSettings

class Settings(BaseSettings):
    # Telegram API Configuration
    API_ID: int
    API_HASH: str
    BOT_TOKEN: str
    
    # Wasabi Configuration
    WASABI_ACCESS_KEY: Optional[str] = None
    WASABI_SECRET_KEY: Optional[str] = None
    WASABI_BUCKET: Optional[str] = None
    WASABI_REGION: str = "us-east-1"
    
    # Bot Behavior Configuration
    DOWNLOAD_PATH: str = "./downloads/"
    MAX_FILE_SIZE: int = 2000  # MB
    ALLOWED_FORMATS: list = ["mp4", "mkv", "avi", "mov", "jpg", "png", "pdf"]
    
    # FFmpeg Configuration
    FFMPEG_PATH: str = "ffmpeg"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Global config instance
config = Settings()
