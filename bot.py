import asyncio
import re
import logging
import time
import os
from pyrogram import Client, filters, types
from pyrogram.errors import FloodWait, FileTooLarge

# Import configuration
from config import config

# Set up logging
logging.basicConfig(
    level=logging.DEBUG if config.DEBUG else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ensure download directory exists
os.makedirs(config.TORRENT_DOWNLOAD_PATH, exist_ok=True)

# Initialize Pyrogram Client
app = Client(
    "magnet_bot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN
)

# Regex pattern for magnet links
MAGNET_PATTERN = re.compile(
    r"^magnet:\?xt=urn:[a-z0-9]+:[a-z0-9]{32}.*", 
    re.IGNORECASE
)

# Rate limiting storage
user_requests = {}

def is_user_allowed(user_id: int) -> bool:
    """Check if user can make a new request based on cooldown"""
    current_time = time.time()
    if user_id in user_requests:
        last_request = user_requests[user_id]
        if current_time - last_request < config.REQUEST_COOLDOWN:
            return False
    user_requests[user_id] = current_time
    return True

@app.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: types.Message):
    """Handle /start command"""
    welcome_text = """
👋 Welcome to **Magnet to Video Converter Bot**!

🤖 **How to use:**
1. Send me a magnet link
2. I'll download and convert the content
3. Receive your video file

⚡ **Features:**
- Fast torrent processing
- Automatic video conversion
- Support for multiple formats

⚠️ **Important:**
- Files must be under 2GB
- Please allow time for processing
- One request per {cooldown} minutes

Send a magnet link to get started!
""".format(cooldown=config.REQUEST_COOLDOWN // 60)
    
    await message.reply_text(welcome_text)

@app.on_message(filters.command("help") & filters.private)
async def help_command(client: Client, message: types.Message):
    """Handle /help command"""
    help_text = """
📖 **Help Guide**

**Supported Links:**
- Magnet URIs (starts with `magnet:?xt=urn...`)

**Commands:**
- `/start` - Start the bot
- `/help` - Show this help message
- `/status` - Check bot status

**Examples:**
