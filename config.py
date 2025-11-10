import os
from typing import Optional
from pydantic import BaseModel, Field

class Settings(BaseModel):
    # Telegram API Configuration
    API_ID: int = Field(..., description="Telegram API ID")
    API_HASH: str = Field(..., description="Telegram API Hash")
    BOT_TOKEN: str = Field(..., description="Telegram Bot Token")
    
    # Wasabi Configuration
    WASABI_ACCESS_KEY: Optional[str] = Field(None, description="Wasabi Access Key")
    WASABI_SECRET_KEY: Optional[str] = Field(None, description="Wasabi Secret Key")
    WASABI_BUCKET: Optional[str] = Field(None, description="Wasabi Bucket Name")
    WASABI_REGION: str = Field("us-east-1", description="Wasabi Region")
    
    # Bot Behavior Configuration
    DOWNLOAD_PATH: str = Field("./downloads/", description="Download directory")
    MAX_FILE_SIZE: int = Field(2000, description="Max file size in MB")
    
    # FFmpeg Configuration
    FFMPEG_PATH: str = Field("ffmpeg", description="FFmpeg executable path")

    @classmethod
    def from_env(cls):
        """Load configuration from environment variables."""
        return cls(
            API_ID=int(os.environ.get("API_ID", 0)),
            API_HASH=os.environ.get("API_HASH", ""),
            BOT_TOKEN=os.environ.get("BOT_TOKEN", ""),
            WASABI_ACCESS_KEY=os.environ.get("WASABI_ACCESS_KEY"),
            WASABI_SECRET_KEY=os.environ.get("WASABI_SECRET_KEY"),
            WASABI_BUCKET=os.environ.get("WASABI_BUCKET"),
            WASABI_REGION=os.environ.get("WASABI_REGION", "us-east-1"),
            DOWNLOAD_PATH=os.environ.get("DOWNLOAD_PATH", "./downloads/"),
            MAX_FILE_SIZE=int(os.environ.get("MAX_FILE_SIZE", "2000")),
            FFMPEG_PATH=os.environ.get("FFMPEG_PATH", "ffmpeg")
        )

# Global config instance
config = Settings.from_env()
