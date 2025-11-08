import os
from typing import Optional

class Config:
    """Configuration class for the bot"""
    
    # Telegram API credentials
    API_ID = int(os.getenv("API_ID", 1234567))
    API_HASH = os.getenv("API_HASH", "your_api_hash_here")
    BOT_TOKEN = os.getenv("BOT_TOKEN", "your_bot_token_here")
    BOT_USERNAME = os.getenv("BOT_USERNAME", "@YourMagnetConverterBot")
    
    # Bot settings
    MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2GB Telegram limit
    DOWNLOAD_TIMEOUT = 3600  # 1 hour timeout for downloads
    REQUEST_COOLDOWN = 300  # 5 minutes between requests per user
    
    # Torrent settings (when implementing actual torrent client)
    TORRENT_DOWNLOAD_PATH = "./downloads"
    MAX_DOWNLOAD_SPEED = 0  # 0 = unlimited
    MAX_UPLOAD_SPEED = 0    # 0 = unlimited
    
    # Development settings
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Create config instance
config = Config()
