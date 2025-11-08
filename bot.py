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

def get_time_until_next_request(user_id: int) -> int:
    """Get remaining time until user can make next request"""
    if user_id not in user_requests:
        return 0
    last_request = user_requests[user_id]
    elapsed = time.time() - last_request
    return max(0, config.REQUEST_COOLDOWN - elapsed)

@app.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: types.Message):
    """Handle /start command"""
    welcome_text = f"""
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
- One request per {config.REQUEST_COOLDOWN // 60} minutes

Send a magnet link to get started!
"""
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
- `/stats` - Show your usage statistics

**Examples:**
If you encounter issues:
- Ensure your magnet link is valid
- Check file size limits
- Try again later if servers are busy
"""
    await message.reply_text(help_text)

@app.on_message(filters.command("status") & filters.private)
async def status_command(client: Client, message: types.Message):
    """Handle /status command"""
    user_id = message.from_user.id
    last_request = user_requests.get(user_id, "Never")
    if last_request != "Never":
        last_request = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(last_request))
    
    status_text = f"""
🟢 **Bot Status: Online**

**System Info:**
- Max File Size: 2GB
- Request Cooldown: {config.REQUEST_COOLDOWN // 60} minutes
- Download Path: Configured

**Your Status:**
- User ID: {user_id}
- Last Request: {last_request}
"""
    await message.reply_text(status_text)

@app.on_message(filters.command("stats") & filters.private)
async def stats_command(client: Client, message: types.Message):
    """Handle /stats command"""
    user_id = message.from_user.id
    total_requests = len([uid for uid in user_requests if uid == user_id])
    
    if user_id in user_requests:
        time_remaining = get_time_until_next_request(user_id)
        if time_remaining > 0:
            cooldown_info = f"{int(time_remaining // 60)} minutes {int(time_remaining % 60)} seconds"
        else:
            cooldown_info = "Ready to make requests"
    else:
        cooldown_info = "Ready to make requests"
    
    stats_text = f"""
📊 **Your Statistics**

- Total Requests: {total_requests}
- Cooldown Status: {cooldown_info}
- Max File Size: 2GB
- Requests Limit: 1 per {config.REQUEST_COOLDOWN // 60} minutes
"""
    await message.reply_text(stats_text)

@app.on_message(filters.text & filters.private)
async def handle_text_input(client: Client, message: types.Message):
    """Handle incoming text messages"""
    text = message.text.strip()
    user_id = message.from_user.id

    # Ignore commands (they are handled separately)
    if text.startswith('/'):
        return

    # Check for magnet link
    if MAGNET_PATTERN.match(text):
        logger.info(f"Magnet link received from user {user_id}")
        
        # Rate limiting check
        if not is_user_allowed(user_id):
            remaining_time = get_time_until_next_request(user_id)
            minutes = int(remaining_time // 60)
            seconds = int(remaining_time % 60)
            
            await message.reply_text(
                f"⏳ Please wait {minutes} minutes and {seconds} seconds before making another request."
            )
            return
        
        # Process magnet link
        await process_magnet_link(client, message, text)
    else:
        await message.reply_text(
            "❌ That doesn't look like a valid magnet link.\n"
            "Please send a magnet URI that starts with `magnet:?xt=urn...`\n\n"
            "Use /help for more information."
        )

async def process_magnet_link(client: Client, message: types.Message, magnet_uri: str):
    """Process magnet link and handle download/upload"""
    user_id = message.from_user.id
    
    try:
        # Send initial response
        status_msg = await message.reply_text(
            "🔍 **Processing Magnet Link...**\n"
            "- Validating link... ✅\n"
            "- Preparing download... ⏳"
        )
        
        # Simulate validation
        await asyncio.sleep(1)
        
        # Update status
        await status_msg.edit_text(
            "📥 **Download Starting...**\n"
            "- Link validated... ✅\n"
            "- Download prepared... ✅\n"
            "- Starting torrent... ⏳"
        )
        
        # Simulate download process
        for i in range(5):
            await asyncio.sleep(1)
            progress = (i + 1) * 20
            await status_msg.edit_text(
                f"📥 **Downloading...**\n"
                f"- Link validated... ✅\n"
                f"- Download prepared... ✅\n"
                f"- Download progress: {progress}% ⏳"
            )
        
        # Update to processing
        await status_msg.edit_text(
            "⚙️ **Processing Content...**\n"
            "- Download completed... ✅\n"
            "- Analyzing files... ✅\n"
            "- Preparing upload... ⏳"
        )
        
        # Simulate file processing
        await asyncio.sleep(2)
        
        # Final simulation response
        await status_msg.edit_text(
            "🎉 **Conversion Complete!**\n\n"
            "In a production environment, your video file would now be uploaded.\n\n"
            "**Next Steps for Implementation:**\n"
            "1. Integrate libtorrent for actual torrent downloading\n"
            "2. Implement file type detection\n"
            "3. Add video conversion if needed\n"
            "4. Implement actual file upload with send_video()"
        )
        
        logger.info(f"Successfully processed magnet link for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error processing magnet link for user {user_id}: {e}")
        await message.reply_text(
            f"❌ **Error Processing Request**\n\n"
            f"Error: `{str(e)}`\n\n"
            f"Please try again later or contact support if the issue persists."
        )

@app.on_message(filters.document | filters.video)
async def handle_files(client: Client, message: types.Message):
    """Handle files sent to bot"""
    await message.reply_text(
        "📁 **File Received**\n\n"
        "I currently only process magnet links. "
        "Please send a magnet URI to convert torrents to videos.\n\n"
        "Use /help for more information."
    )

# Error handlers
@app.on_error()
async def error_handler(client: Client, update: types.Update, error: Exception):
    """Global error handler"""
    logger.error(f"Error in update {update}: {error}")
    
    if isinstance(error, FloodWait):
        wait_time = error.value
        logger.warning(f"Flood wait for {wait_time} seconds")
        await asyncio.sleep(wait_time)
    elif isinstance(error, FileTooLarge):
        logger.error("File too large for Telegram")
    else:
        logger.error(f"Unexpected error: {error}")

if __name__ == "__main__":
    logger.info("Starting Magnet Converter Bot...")
    try:
        app.run()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot failed to start: {e}")
