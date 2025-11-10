import os

class Config:
    """Simple configuration class."""
    
    # Telegram API
    API_ID = int(os.environ.get("API_ID", 0))
    API_HASH = os.environ.get("API_HASH", "")
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
    
    # Wasabi Configuration
    WASABI_ACCESS_KEY = os.environ.get("WASABI_ACCESS_KEY")
    WASABI_SECRET_KEY = os.environ.get("WASABI_SECRET_KEY")
    WASABI_BUCKET = os.environ.get("WASABI_BUCKET")
    WASABI_REGION = os.environ.get("WASABI_REGION", "us-east-1")
    
    # Bot Settings
    DOWNLOAD_PATH = os.environ.get("DOWNLOAD_PATH", "./downloads/")
    MAX_FILE_SIZE = int(os.environ.get("MAX_FILE_SIZE", "2000"))
    FFMPEG_PATH = os.environ.get("FFMPEG_PATH", "ffmpeg")

# Create config instance
config = Config()
