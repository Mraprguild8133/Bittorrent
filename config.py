# config.py
import os
from typing import Dict, Any

class Config:
    """Configuration class for the Telegram Downloader Bot"""
    
    def __init__(self):
        # Telegram API Configuration
        self.API_ID: int = int(os.environ.get("API_ID", 0))
        self.API_HASH: str = os.environ.get("API_HASH", "")
        self.BOT_TOKEN: str = os.environ.get("BOT_TOKEN", "")
        
        # Wasabi (S3 Compatible) Configuration
        self.WASABI_ACCESS_KEY: str = os.environ.get("WASABI_ACCESS_KEY", "")
        self.WASABI_SECRET_KEY: str = os.environ.get("WASABI_SECRET_KEY", "")
        self.WASABI_BUCKET: str = os.environ.get("WASABI_BUCKET", "")
        self.WASABI_REGION: str = os.environ.get("WASABI_REGION", "")
        self.WASABI_ENABLED: bool = os.environ.get("WASABI_ENABLED", "true").lower() == "true"
        
        # GDToT Configuration
        self.GDToT_API_KEY: str = os.environ.get("GDToT_API_KEY", "")
        self.GDTOT_ENABLED: bool = os.environ.get("GDTOT_ENABLED", "true").lower() == "true"
        self.GDTOT_API_URL: str = "https://new.gdtot.com/api/upload/link"
        
        # Bot Constants
        self.TEMP_DOWNLOAD_DIR: str = "downloads/"
        self.LARGE_FILE_THRESHOLD_GB: int = 4
        self.CHUNK_SIZE: int = 8192 * 1024  # 8MB
    
    def validate_required(self) -> bool:
        """Validate that all required variables are present"""
        required_vars = {
            "API_ID": self.API_ID,
            "API_HASH": self.API_HASH,
            "BOT_TOKEN": self.BOT_TOKEN
        }
        
        missing = [var for var, value in required_vars.items() if not value]
        if missing:
            print(f"❌ Missing required environment variables: {', '.join(missing)}")
            return False
        
        print("✅ All required configuration validated successfully")
        return True
    
    def get_services_status(self) -> Dict[str, Dict[str, Any]]:
        """Get detailed status of all services"""
        wasabi_configured = all([
            self.WASABI_ACCESS_KEY,
            self.WASABI_SECRET_KEY,
            self.WASABI_BUCKET,
            self.WASABI_REGION
        ])
        
        gdtot_configured = bool(self.GDToT_API_KEY)
        
        status = {
            "wasabi": {
                "configured": wasabi_configured,
                "enabled": self.WASABI_ENABLED and wasabi_configured,
                "reason": "Not configured" if not wasabi_configured else "Enabled" if self.WASABI_ENABLED else "Disabled by switch"
            },
            "gdtot": {
                "configured": gdtot_configured,
                "enabled": self.GDTOT_ENABLED and gdtot_configured,
                "reason": "Not configured" if not gdtot_configured else "Enabled" if self.GDTOT_ENABLED else "Disabled by switch"
            }
        }
        
        print("🔧 Services Status:")
        for service, info in status.items():
            status_icon = "✅" if info["enabled"] else "❌"
            print(f"   - {service.title()}: {status_icon} {info['reason']}")
        
        return status

# Create config instance
config = Config()
