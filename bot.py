import asyncio
import re
import logging
import time
import os
import shutil
from pathlib import Path
from typing import List, Optional
import tempfile
from pyrogram import Client, filters, types
from pyrogram.errors import FloodWait
import libtorrent as lt

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
    r"^magnet:\?xt=urn:[a-z0-9]+:[a-z0-9]{32,40}.*", 
    re.IGNORECASE
)

# Rate limiting storage
user_requests = {}
user_stats = {}

# Video file extensions
VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.3gp'}

# Maximum file size for Telegram (2GB in bytes)
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024

class DownloadProgress:
    def __init__(self, user_id: int, message: types.Message):
        self.user_id = user_id
        self.message = message
        self.last_update = 0
    
    async def update_progress(self, progress: float, status: str, download_speed: str = ""):
        """Update progress message with rate limiting"""
        current_time = time.time()
        if current_time - self.last_update < 3:  # Update every 3 seconds
            return
        
        progress_percent = min(100, max(0, progress))
        progress_bar = "▓" * int(progress_percent / 10) + "░" * (10 - int(progress_percent / 10))
        
        text = f"📥 **Downloading...** {progress_percent:.1f}%\n"
        text += f"`{progress_bar}`\n"
        text += f"**Status:** {status}\n"
        if download_speed:
            text += f"**Speed:** {download_speed}"
        
        try:
            await self.message.edit_text(text)
            self.last_update = current_time
        except Exception as e:
            logger.error(f"Failed to update progress: {e}")

def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal"""
    filename = os.path.basename(filename)
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename[:255]

def get_user_download_path(user_id: int) -> Path:
    """Get user-specific download directory"""
    user_path = Path(config.TORRENT_DOWNLOAD_PATH) / str(user_id)
    user_path.mkdir(exist_ok=True, parents=True)
    return user_path

def cleanup_user_downloads(user_id: int):
    """Clean up user download directory"""
    user_dir = get_user_download_path(user_id)
    if user_dir.exists():
        try:
            shutil.rmtree(user_dir)
            logger.info(f"Cleaned up downloads for user {user_id}")
        except Exception as e:
            logger.error(f"Error cleaning up user {user_id} downloads: {e}")

def find_video_files(directory: Path) -> List[Path]:
    """Find video files in directory"""
    video_files = []
    for ext in VIDEO_EXTENSIONS:
        video_files.extend(directory.rglob(f"*{ext}"))
    
    return sorted(
        [f for f in video_files if f.is_file() and f.stat().st_size > 0],
        key=lambda x: x.stat().st_size,
        reverse=True
    )

def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.2f} {size_names[i]}"

def format_speed(bytes_per_second: float) -> str:
    """Format download speed"""
    if bytes_per_second < 1024:
        return f"{bytes_per_second:.0f} B/s"
    elif bytes_per_second < 1024 * 1024:
        return f"{bytes_per_second / 1024:.1f} KB/s"
    else:
        return f"{bytes_per_second / (1024 * 1024):.1f} MB/s"

async def download_torrent(magnet_uri: str, download_path: Path, progress_tracker: DownloadProgress) -> Optional[lt.torrent_handle]:
    """Download torrent using libtorrent"""
    try:
        ses = lt.session()
        ses.listen_on(6881, 6891)
        
        # Set download settings
        settings = ses.get_settings()
        settings['download_rate_limit'] = 0
        settings['upload_rate_limit'] = 0
        settings['active_downloads'] = 1
        ses.set_settings(settings)
        
        params = {
            'save_path': str(download_path),
            'storage_mode': lt.storage_mode_t(2)
        }
        
        # Add magnet URI
        handle = lt.add_magnet_uri(ses, magnet_uri, params)
        
        logger.info(f"Started download: {magnet_uri}")
        
        # Wait for metadata
        await progress_tracker.update_progress(0, "Fetching metadata...")
        while not handle.has_metadata():
            await asyncio.sleep(1)
            status = handle.status()
            if status.state == lt.torrent_status.downloading_metadata:
                await progress_tracker.update_progress(5, "Downloading metadata...")
        
        await progress_tracker.update_progress(10, "Metadata received, starting download...")
        
        # Start the actual download
        handle.set_flags(lt.torrent_flags.sequential_download)
        
        # Download loop
        last_progress = 0
        while handle.status().state != lt.torrent_status.seeding:
            status = handle.status()
            progress = status.progress * 100
            
            # Only update if progress actually changed
            if progress > last_progress + 1 or status.state != lt.torrent_status.downloading:
                speed = format_speed(status.download_rate)
                state_str = str(status.state).split('.')[-1].replace('_', ' ').title()
                await progress_tracker.update_progress(progress, state_str, speed)
                last_progress = progress
            
            # Check if download is stuck
            if status.state == lt.torrent_status.downloading and status.download_rate == 0:
                await asyncio.sleep(5)
            else:
                await asyncio.sleep(1)
        
        await progress_tracker.update_progress(100, "Download completed!", "0 B/s")
        logger.info(f"Download completed: {magnet_uri}")
        
        return handle
        
    except Exception as e:
        logger.error(f"Error in torrent download: {e}")
        return None

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

def update_user_stats(user_id: int, success: bool = True):
    """Update user statistics"""
    if user_id not in user_stats:
        user_stats[user_id] = {'total_requests': 0, 'successful_requests': 0, 'failed_requests': 0}
    
    user_stats[user_id]['total_requests'] += 1
    if success:
        user_stats[user_id]['successful_requests'] += 1
    else:
        user_stats[user_id]['failed_requests'] += 1

@app.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: types.Message):
    """Handle /start command"""
    welcome_text = f"""
👋 Welcome to **Magnet to Video Converter Bot**!

🤖 **How to use:**
1. Send me a magnet link
2. I'll download and process the content
3. Receive your video files

⚡ **Features:**
- Fast torrent processing
- Automatic video detection
- Support for multiple formats
- Progress tracking

⚠️ **Important:**
- Files must be under {format_file_size(MAX_FILE_SIZE)}
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
- `/cleanup` - Clean up your downloads

**Video Formats:**
MP4, MKV, AVI, MOV, WMV, FLV, WebM, M4V, 3GP

**File Size Limit:** 2GB

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
- Max File Size: {format_file_size(MAX_FILE_SIZE)}
- Request Cooldown: {config.REQUEST_COOLDOWN // 60} minutes
- Download Path: Configured
- Active Users: {len(user_requests)}

**Your Status:**
- User ID: {user_id}
- Last Request: {last_request}
"""
    await message.reply_text(status_text)

@app.on_message(filters.command("stats") & filters.private)
async def stats_command(client: Client, message: types.Message):
    """Handle /stats command"""
    user_id = message.from_user.id
    
    if user_id in user_stats:
        stats = user_stats[user_id]
        total = stats['total_requests']
        success = stats['successful_requests']
        failed = stats['failed_requests']
        success_rate = (success / total * 100) if total > 0 else 0
    else:
        total = success = failed = success_rate = 0
    
    if user_id in user_requests:
        time_remaining = get_time_until_next_request(user_id)
        if time_remaining > 0:
            cooldown_info = f"{int(time_remaining // 60)}m {int(time_remaining % 60)}s"
        else:
            cooldown_info = "Ready to make requests"
    else:
        cooldown_info = "Ready to make requests"
    
    stats_text = f"""
📊 **Your Statistics**

- Total Requests: {total}
- Successful: {success}
- Failed: {failed}
- Success Rate: {success_rate:.1f}%
- Cooldown Status: {cooldown_info}
- Max File Size: {format_file_size(MAX_FILE_SIZE)}
- Requests Limit: 1 per {config.REQUEST_COOLDOWN // 60} minutes
"""
    await message.reply_text(stats_text)

@app.on_message(filters.command("cleanup") & filters.private)
async def cleanup_command(client: Client, message: types.Message):
    """Handle /cleanup command"""
    user_id = message.from_user.id
    try:
        cleanup_user_downloads(user_id)
        await message.reply_text("✅ Your download cache has been cleaned up!")
    except Exception as e:
        await message.reply_text("❌ Error during cleanup. Please try again later.")

async def process_magnet_link(client: Client, message: types.Message, magnet_uri: str):
    """Process magnet link and handle download/upload"""
    user_id = message.from_user.id
    
    try:
        # Send initial response
        status_msg = await message.reply_text(
            "🔍 **Processing Magnet Link...**\n"
            "- Validating link... ⏳\n"
            "- Preparing download... Waiting"
        )
        
        progress_tracker = DownloadProgress(user_id, status_msg)
        
        # Get user download path
        download_path = get_user_download_path(user_id)
        
        # Start download
        await status_msg.edit_text(
            "📥 **Starting Download...**\n"
            "- Link validated... ✅\n"
            "- Download prepared... ✅\n"
            "- Connecting to peers... ⏳"
        )
        
        # Download torrent
        handle = await download_torrent(magnet_uri, download_path, progress_tracker)
        
        if not handle:
            await status_msg.edit_text(
                "❌ **Download Failed**\n\n"
                "The torrent download failed. This could be due to:\n"
                "- No seeds available\n"
                "- Network issues\n"
                "- Invalid magnet link\n\n"
                "Please try again with a different magnet link."
            )
            update_user_stats(user_id, success=False)
            cleanup_user_downloads(user_id)
            return
        
        # Find video files
        await status_msg.edit_text(
            "🔍 **Searching for video files...**\n"
            "- Download completed... ✅\n"
            "- Scanning directory... ⏳"
        )
        
        video_files = find_video_files(download_path)
        
        if not video_files:
            await status_msg.edit_text(
                "❌ **No Video Files Found**\n\n"
                "The downloaded content doesn't contain any supported video files.\n"
                "Supported formats: MP4, MKV, AVI, MOV, WMV, FLV, WebM, M4V, 3GP"
            )
            update_user_stats(user_id, success=False)
            cleanup_user_downloads(user_id)
            return
        
        # Process and send video files
        await status_msg.edit_text(
            f"📹 **Found {len(video_files)} video file(s)**\n"
            "- Scanning completed... ✅\n"
            "- Preparing to send... ⏳"
        )
        
        sent_files = 0
        for video_file in video_files:
            try:
                file_size = video_file.stat().st_size
                
                if file_size > MAX_FILE_SIZE:
                    await message.reply_text(
                        f"📁 **File Too Large**: {video_file.name}\n"
                        f"Size: {format_file_size(file_size)} (Limit: {format_file_size(MAX_FILE_SIZE)})\n"
                        "Skipping this file..."
                    )
                    continue
                
                # Send the video file
                await status_msg.edit_text(f"📤 **Uploading**: {video_file.name}...")
                
                await client.send_video(
                    chat_id=user_id,
                    video=str(video_file),
                    caption=f"🎬 {sanitize_filename(video_file.name)}\n"
                           f"📦 Size: {format_file_size(file_size)}",
                    supports_streaming=True,
                    progress=progress_tracker.update_progress if sent_files == 0 else None
                )
                
                sent_files += 1
                logger.info(f"Sent video file {video_file.name} to user {user_id}")
                
                # Small delay between files
                await asyncio.sleep(1)
                
            except FloodWait as e:
                await status_msg.edit_text(f"⏳ Rate limited. Waiting {e.value} seconds...")
                await asyncio.sleep(e.value)
                continue
            except Exception as e:
                logger.error(f"Error sending file {video_file.name}: {e}")
                await message.reply_text(f"❌ Failed to send: {video_file.name}")
                continue
        
        # Final status
        if sent_files > 0:
            await status_msg.edit_text(
                f"🎉 **Download Complete!**\n\n"
                f"Successfully sent {sent_files} video file(s)\n"
                f"Your files have been delivered above ↑\n\n"
                f"Use /cleanup to clear your download cache"
            )
            update_user_stats(user_id, success=True)
        else:
            await status_msg.edit_text(
                "❌ **No files could be sent**\n\n"
                "All video files were either too large or encountered errors during upload."
            )
            update_user_stats(user_id, success=False)
        
        # Cleanup
        cleanup_user_downloads(user_id)
        
    except Exception as e:
        logger.error(f"Error processing magnet link for user {user_id}: {e}")
        await message.reply_text(
            f"❌ **Error Processing Request**\n\n"
            f"Error: `{str(e)}`\n\n"
            f"Please try again later or use /help for assistance."
        )
        update_user_stats(user_id, success=False)
        cleanup_user_downloads(user_id)

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

@app.on_message(filters.document | filters.video)
async def handle_files(client: Client, message: types.Message):
    """Handle files sent to bot"""
    await message.reply_text(
        "📁 **File Received**\n\n"
        "I currently only process magnet links. "
        "Please send a magnet URI to download and send video files from torrents.\n\n"
        "Use /help for more information."
    )

# Error handler
@app.on_error()
async def error_handler(client: Client, update: types.Update, error: Exception):
    """Global error handler"""
    logger.error(f"Error in update {update}: {error}")
    
    if isinstance(error, FloodWait):
        wait_time = error.value
        logger.warning(f"Flood wait for {wait_time} seconds")
        await asyncio.sleep(wait_time)
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
