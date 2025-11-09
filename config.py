import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    API_ID = int(os.getenv("API_ID"))
    API_HASH = os.getenv("API_HASH")
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    
    # qBittorrent settings
    QBIT_HOST = os.getenv("QBIT_HOST", "http://localhost:8080")
    QBIT_USERNAME = os.getenv("QBIT_USERNAME", "admin")
    QBIT_PASSWORD = os.getenv("QBIT_PASSWORD", "adminadmin")
    
    # Download settings
    MAX_FILE_SIZE = 4 * 1024 * 1024 * 1024  # 4GB
    DOWNLOAD_PATH = "downloads"
    UPLOAD_PATH = "uploads"

config = Config()
