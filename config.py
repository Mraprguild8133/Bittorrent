# config.py
import os
from typing import Optional

class Config:
    """Configuration class for the Telegram Downloader Bot"""
    
    # Telegram API Configuration
    API_ID: int = int(os.environ.get("API_ID", 0))
    API_HASH: str = os.environ.get("API_HASH", "")
    BOT_TOKEN: str = os.environ.get("BOT_TOKEN", "")
    
    # Wasabi (S3 Compatible) Configuration
    WASABI_ACCESS_KEY: str = os.environ.get("WASABI_ACCESS_KEY", "")
    WASABI_SECRET_KEY: str = os.environ.get("WASABI_SECRET_KEY", "")
    WASABI_BUCKET: str = os.environ.get("WASABI_BUCKET", "")
    WASABI_REGION: str = os.environ.get("WASABI_REGION", "")
    
    # GDToT Configuration
    GDToT_API_KEY: str = os.environ.get("GDToT_API_KEY", "")
    
    # Bot Constants
    TEMP_DOWNLOAD_DIR: str = "downloads/"
    LARGE_FILE_THRESHOLD_GB: int = 4
    CHUNK_SIZE: int = 8192 * 1024  # 8MB
    
    @classmethod
    def validate_required(cls) -> bool:
        """Validate that all required variables are present"""
        required_vars = {
            "API_ID": cls.API_ID,
            "API_HASH": cls.API_HASH,
            "BOT_TOKEN": cls.BOT_TOKEN
        }
        
        missing = [var for var, value in required_vars.items() if not value]
        if missing:
            print(f"❌ Missing required environment variables: {', '.join(missing)}")
            return False
        return True
    
    @classmethod
    def get_optional_services_status(cls) -> dict:
        """Get status of optional services"""
        return {
            "wasabi": all([
                cls.WASABI_ACCESS_KEY,
                cls.WASABI_SECRET_KEY,
                cls.WASABI_BUCKET,
                cls.WASABI_REGION
            ]),
            "gdtot": bool(cls.GDToT_API_KEY)
        }

# Create config instance
config = Config()
